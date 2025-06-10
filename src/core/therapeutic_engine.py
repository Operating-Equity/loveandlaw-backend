from typing import Dict, Any, List, Optional
import asyncio
import json
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
from src.agents.reflection_agent import ReflectionAgent

# Import legal specialist agents
from src.agents.legal_specialists import (
    CaseGeneralAgent,
    FamilyLawAgent,
    DivorceAndSeparationAgent,
    ChildCustodyAgent,
    ChildSupportAgent,
    PropertyDivisionAgent,
    SpousalSupportAgent,
    DomesticViolenceAgent,
    AdoptionAgent,
    ChildAbuseAgent,
    GuardianshipAgent,
    JuvenileDelinquencyAgent,
    PaternityPracticeAgent,
    RestrainingOrdersAgent
)
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
            "progress": ProgressTracker(),
            "reflection": ReflectionAgent()
        }
        
        # Initialize legal specialist agents
        self.legal_specialists = {
            "case_general": CaseGeneralAgent(),
            "family_law": FamilyLawAgent(),
            "divorce_and_separation": DivorceAndSeparationAgent(),
            "child_custody": ChildCustodyAgent(),
            "child_support": ChildSupportAgent(),
            "property_division": PropertyDivisionAgent(),
            "spousal_support": SpousalSupportAgent(),
            "domestic_violence": DomesticViolenceAgent(),
            "adoption_process": AdoptionAgent(),
            "child_abuse": ChildAbuseAgent(),
            "guardianship_process": GuardianshipAgent(),
            "juvenile_delinquency": JuvenileDelinquencyAgent(),
            "paternity_practice": PaternityPracticeAgent(),
            "restraining_order": RestrainingOrdersAgent()
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
        workflow.add_node("legal_intake", self._legal_intake)
        workflow.add_node("parallel_analysis", self._parallel_analysis)
        workflow.add_node("reflection_check", self._reflection_check)
        workflow.add_node("advisor_compose", self._advisor_compose)
        workflow.add_node("persist_state", self._persist_state)
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "safety_check",
            self._route_after_safety,
            {
                "legal_intake": "legal_intake",
                "fetch_context": "fetch_context"
            }
        )
        
        workflow.add_conditional_edges(
            "legal_intake",
            self._route_after_legal_intake,
            {
                "legal_specialist": "legal_intake",  # Continue with specialist
                "fetch_context": "fetch_context"      # Move to main flow
            }
        )
        
        # Add regular edges
        workflow.add_edge("fetch_context", "parallel_analysis")
        workflow.add_edge("parallel_analysis", "reflection_check")
        workflow.add_edge("reflection_check", "advisor_compose")
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
        # Convert turn_state to dict with proper JSON encoding
        turn_state_dict = json.loads(turn_state.json())
        
        graph_input = {
            "turn_state": turn_state_dict,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "context": {}
        }
        
        # Configure for this conversation with recursion limit
        config = {
            "configurable": {"thread_id": conversation_id or user_id},
            "recursion_limit": 50
        }
        
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
                "scheduled_check_ins": result.get("scheduled_check_ins", []),
                "reflection": {
                    "needs_reflection": result.get("needs_reflection", False),
                    "reflection_type": result.get("reflection_type"),
                    "reflection_prompts": result.get("reflection_prompts", []),
                    "reflection_insights": result.get("reflection_insights", [])
                }
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
    
    async def _reflection_check(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if reflection is needed and generate reflection content"""
        
        if state.get("skip_remaining_agents"):
            return state
        
        turn_state = TurnState(**state["turn_state"])
        context = {
            **state["context"],
            "conversation_summary": state["context"].get("conversation_summary", []),
            "user_profile": state["context"].get("user_profile", {})
        }
        
        # Run reflection agent
        reflection_result = await self.agents["reflection"].process(turn_state, context)
        
        # Add reflection data to state
        state["needs_reflection"] = reflection_result.get("needs_reflection", False)
        state["reflection_type"] = reflection_result.get("reflection_type")
        state["reflection_prompts"] = reflection_result.get("reflection_prompts", [])
        state["reflection_insights"] = reflection_result.get("reflection_insights", [])
        
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
            "progress_insights": state.get("progress_insights", []),
            "needs_reflection": state.get("needs_reflection", False),
            "reflection_type": state.get("reflection_type"),
            "reflection_prompts": state.get("reflection_prompts", []),
            "reflection_insights": state.get("reflection_insights", []),
            "legal_intake_result": state.get("legal_intake_result", {}),
            "legal_question": state.get("legal_question", ""),
            "case_info": state.get("case_info", {}),
            "active_legal_specialist": state.get("active_legal_specialist")
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
    
    def _route_after_safety(self, state: Dict[str, Any]) -> str:
        """Determine routing after safety check"""
        # If safety hold needed, skip to main flow
        if state.get("skip_remaining_agents"):
            return "fetch_context"
            
        # Check if we need legal intake
        if self._needs_legal_intake(state):
            return "legal_intake"
            
        return "fetch_context"
    
    def _needs_legal_intake(self, state: Dict[str, Any]) -> bool:
        """Check if legal intake is needed"""
        # Check if we're in a legal specialist flow
        if state.get("active_legal_specialist"):
            return True
            
        # Check if this is the first message and contains legal keywords
        user_text = state["turn_state"]["user_text"].lower()
        legal_keywords = ["divorce", "custody", "lawyer", "attorney", "legal", 
                         "court", "sue", "rights", "visitation", "support", 
                         "property", "abuse", "adoption", "guardianship"]
        
        if any(keyword in user_text for keyword in legal_keywords):
            return True
            
        return False
    
    async def _legal_intake(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle legal intake and specialist routing"""
        
        # Determine which specialist to use
        active_specialist = state.get("active_legal_specialist")
        
        if not active_specialist:
            # Start with case general agent
            active_specialist = "case_general"
            state["active_legal_specialist"] = active_specialist
            
        # Get the appropriate specialist
        specialist = self.legal_specialists.get(active_specialist)
        if not specialist:
            logger.error(f"Unknown legal specialist: {active_specialist}")
            return state
            
        # Process with the specialist
        specialist_state = {
            "case_info": state.get("case_info", {}),
            "user_text": state["turn_state"]["user_text"],
            "chat_history": state.get("chat_history", []),
            "schema": state.get("legal_schema", {})
        }
        
        result = specialist.process(specialist_state)
        
        # Update state with results
        if result.get("extracted_info"):
            state["case_info"] = result["extracted_info"]
            state["legal_schema"] = result["extracted_info"]
            
        if result.get("question"):
            state["legal_question"] = result["question"]
            
        # Check for state transitions
        result_state = result.get("state", "")
        new_state = result.get("current_state", "")
        
        # Check if case general agent has collected a case
        if active_specialist == "case_general" and result_state == "case_collected":
            # Legal intake complete for now - we have basic info
            state["legal_intake_complete"] = True
            state["active_legal_specialist"] = None
        elif new_state in self.legal_specialists and new_state != active_specialist:
            # Transitioning to a new specialist
            state["active_legal_specialist"] = new_state
        elif new_state == "completed" or new_state == "complete" or result_state == "complete":
            # Legal intake complete
            state["legal_intake_complete"] = True
            state["active_legal_specialist"] = None
            
        # Store for advisor
        state["legal_intake_result"] = result
        
        return state
    
    def _route_after_legal_intake(self, state: Dict[str, Any]) -> str:
        """Determine routing after legal intake"""
        # Always proceed to fetch_context after legal intake
        # The specialist has already provided their response
        return "fetch_context"


# Global instance
therapeutic_engine = TherapeuticEngine()