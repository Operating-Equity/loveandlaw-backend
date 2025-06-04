from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.models.conversation import TurnState, ConversationState
from src.agents.safety_agent import SafetyAgent
from src.agents.profile_agent import ProfileAgent
from src.agents.listener_agent import ListenerAgent
from src.agents.emotion_gauge import EmotionGauge
from src.agents.signal_extract import SignalExtractAgent
from src.agents.alliance_meter import AllianceMeter
from src.agents.research_agent import ResearchAgent
from src.agents.matcher_agent import MatcherAgent
from src.agents.advisor_agent import AdvisorAgent
from src.agents.progress_tracker import ProgressTracker
from src.services.database import dynamodb_service, elasticsearch_service
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TherapeuticEngine:
    """LangGraph-based orchestrator for therapeutic conversation flow"""
    
    def __init__(self):
        self.agents = {
            "safety": SafetyAgent(),
            "profile": ProfileAgent(),
            "listener": ListenerAgent(),
            "emotion": EmotionGauge(),
            "signal": SignalExtractAgent(),
            "alliance": AllianceMeter(),
            "research": ResearchAgent(),
            "matcher": MatcherAgent(),
            "advisor": AdvisorAgent(),
            "progress": ProgressTracker()
        }
        
        # Initialize the graph
        self.graph = self._build_graph()
        self.memory = MemorySaver()
        self.app = self.graph.compile(checkpointer=self.memory)
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Define the graph
        workflow = StateGraph(Dict[str, Any])
        
        # Add nodes
        workflow.add_node("safety_check", self._safety_check)
        workflow.add_node("fetch_context", self._fetch_context)
        workflow.add_node("parallel_analysis", self._parallel_analysis)
        workflow.add_node("advisor_compose", self._advisor_compose)
        workflow.add_node("persist_state", self._persist_state)
        
        # Add edges
        workflow.add_edge("safety_check", "fetch_context")
        workflow.add_edge("fetch_context", "parallel_analysis")
        workflow.add_edge("parallel_analysis", "advisor_compose")
        workflow.add_edge("advisor_compose", "persist_state")
        workflow.add_edge("persist_state", END)
        
        # Set entry point
        workflow.set_entry_point("safety_check")
        
        return workflow
    
    async def process_turn(
        self, 
        user_id: str, 
        user_text: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a conversation turn through the therapeutic engine"""
        
        # Create initial state
        turn_state = TurnState(
            user_id=user_id,
            user_text=user_text
        )
        
        # Prepare graph input
        graph_input = {
            "turn_state": turn_state.dict(),
            "user_id": user_id,
            "conversation_id": conversation_id,
            "context": {}
        }
        
        # Configure for this conversation
        config = {"configurable": {"thread_id": conversation_id or user_id}}
        
        try:
            # Run the graph
            result = await self.app.ainvoke(graph_input, config)
            
            # Extract key outputs
            return {
                "turn_id": result["turn_state"]["turn_id"],
                "assistant_response": result.get("assistant_response", ""),
                "suggestions": result.get("suggestions", []),
                "lawyer_cards": result.get("lawyer_cards", []),
                "stage": result["turn_state"]["stage"],
                "metrics": {
                    "distress_score": result["turn_state"]["distress_score"],
                    "engagement_level": result["turn_state"]["engagement_level"],
                    "alliance_bond": result["turn_state"]["alliance_bond"],
                    "alliance_goal": result["turn_state"]["alliance_goal"],
                    "alliance_task": result["turn_state"]["alliance_task"],
                    "sentiment": result["turn_state"]["sentiment"]
                },
                "progress": result.get("progress_info", {}),
                "milestone_celebrations": result.get("milestone_celebrations", []),
                "scheduled_check_ins": result.get("scheduled_check_ins", [])
            }
            
        except Exception as e:
            logger.error(f"Error processing turn: {e}")
            raise
    
    async def _safety_check(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 0: Safety assessment and profile fetch"""
        turn_state = TurnState(**state["turn_state"])
        
        # Run safety check and profile fetch in parallel
        safety_task = self.agents["safety"].process(turn_state, state["context"])
        profile_task = self.agents["profile"].process(turn_state, state["context"])
        
        safety_result, profile_result = await asyncio.gather(safety_task, profile_task)
        
        # Update state with safety results
        state["turn_state"].update(safety_result)
        
        # Update context with profile data
        state["context"].update(profile_result)
        
        # Add safety response if needed
        if safety_result.get("needs_safety_hold"):
            state["safety_response"] = safety_result.get("safety_response", "")
            state["skip_remaining_agents"] = True
        
        return state
    
    async def _fetch_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Additional context fetching if needed"""
        
        if state.get("skip_remaining_agents"):
            return state
        
        # Profile data already fetched by ProfileAgent in safety_check phase
        # This method can be used for additional context needs in the future
        
        return state
    
    async def _parallel_analysis(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: Run parallel analysis agents"""
        
        if state.get("skip_remaining_agents"):
            return state
        
        turn_state = TurnState(**state["turn_state"])
        context = state["context"]
        
        # Run primary agents in parallel
        tasks = [
            self.agents["listener"].process(turn_state, context),
            self.agents["emotion"].process(turn_state, context),
            self.agents["signal"].process(turn_state, context),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Merge results into state
        for result in results:
            state["turn_state"].update(result)
            if "listener_draft" in result:
                state["listener_draft"] = result["listener_draft"]
        
        # Update turn state for next phase
        turn_state = TurnState(**state["turn_state"])
        
        # Run secondary agents (may depend on primary results)
        secondary_tasks = [
            self.agents["alliance"].process(turn_state, context),
            self.agents["research"].process(turn_state, context),
            self.agents["progress"].process(turn_state, context)
        ]
        
        # Add matcher if appropriate
        if self._should_match_lawyers(state):
            secondary_tasks.append(self.agents["matcher"].process(turn_state, context))
        
        secondary_results = await asyncio.gather(*secondary_tasks)
        
        # Process secondary results
        for result in secondary_results:
            if "alliance_bond" in result:
                state["turn_state"].update(result)
            elif "legal_research" in result:
                state["legal_research"] = result.get("legal_research")
                state["research_sources"] = result.get("research_sources", [])
            elif "lawyer_cards" in result:
                state["lawyer_cards"] = result.get("lawyer_cards", [])
                state["match_info"] = {
                    "reason": result.get("match_reason"),
                    "total_matches": result.get("total_matches", 0)
                }
            elif "progress_info" in result:
                state["progress_info"] = result.get("progress_info")
                state["milestone_celebrations"] = result.get("milestone_celebrations", [])
                state["scheduled_check_ins"] = result.get("scheduled_check_ins", [])
                state["progress_insights"] = result.get("progress_insights", [])
                # Update turn state with new progress markers
                if "new_milestones" in result:
                    state["turn_state"]["progress_markers"] = turn_state.progress_markers
        
        return state
    
    async def _advisor_compose(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Compose final response"""
        
        turn_state = TurnState(**state["turn_state"])
        
        # Prepare advisor context
        advisor_context = {
            **state["context"],
            "listener_draft": state.get("listener_draft", ""),
            "lawyer_cards": state.get("lawyer_cards", []),
            "safety_response": state.get("safety_response", ""),
            "legal_guidance": state.get("legal_research", ""),
            "research_sources": state.get("research_sources", []),
            "progress_info": state.get("progress_info", {}),
            "milestone_celebrations": state.get("milestone_celebrations", []),
            "progress_insights": state.get("progress_insights", [])
        }
        
        # Get final response
        advisor_result = await self.agents["advisor"].process(turn_state, advisor_context)
        
        state["assistant_response"] = advisor_result["assistant_response"]
        state["suggestions"] = advisor_result.get("suggestions", [])
        state["show_cards"] = advisor_result.get("show_cards", False)
        
        return state
    
    async def _persist_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Persist turn state and update user profile"""
        
        turn_data = state["turn_state"]
        turn_data["assistant_response"] = state.get("assistant_response", "")
        turn_data["created_at"] = datetime.utcnow().isoformat()
        
        # Save turn state
        await dynamodb_service.save_turn_state(turn_data)
        
        # Update user profile metrics
        await self._update_user_profile(state)
        
        return state
    
    def _should_match_lawyers(self, state: Dict[str, Any]) -> bool:
        """Determine if lawyer matching should run"""
        turn_state = state["turn_state"]
        
        # Skip if in crisis
        if turn_state.get("distress_score", 0) >= 7:
            return False
        
        # Skip if no location info
        if not turn_state.get("facts", {}).get("zip"):
            return False
        
        # Match if legal intent identified
        if turn_state.get("legal_intent"):
            return True
        
        # Match if explicitly requested
        user_text = turn_state["user_text"].lower()
        match_keywords = ["lawyer", "attorney", "legal help", "representation"]
        return any(keyword in user_text for keyword in match_keywords)
    
    
    async def _update_user_profile(self, state: Dict[str, Any]) -> None:
        """Update user profile with latest metrics"""
        user_id = state["user_id"]
        turn_state = TurnState(**state["turn_state"])
        
        # Use ProfileAgent's update method
        profile_agent = self.agents["profile"]
        await profile_agent.update_profile_emotional_state(user_id, turn_state)


# Global instance
therapeutic_engine = TherapeuticEngine()