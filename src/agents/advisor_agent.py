from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from src.agents.base import BaseAgent
from src.models.conversation import TurnState, LawyerCard
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AdvisorAgent(BaseAgent):
    """Compose final response with adaptive empathy and guidance"""
    
    def __init__(self):
        super().__init__("advisor")
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compose final advisor response"""
        
        # Skip if in safety hold
        if state.stage == "safety_hold":
            return {
                "assistant_response": context.get("safety_response", ""),
                "show_cards": False
            }
        
        # Get components
        listener_draft = context.get("listener_draft", "")
        lawyer_cards = context.get("lawyer_cards", [])
        legal_guidance = context.get("legal_guidance", "")
        suggestions = await self._generate_suggestions(state, context)
        
        # Compose adaptive response
        final_response = await self._compose_adaptive_response(
            state,
            listener_draft,
            legal_guidance,
            lawyer_cards,
            context
        )
        
        return {
            "assistant_response": final_response,
            "suggestions": suggestions,
            "show_cards": len(lawyer_cards) > 0 and state.distress_score < 7
        }
    
    async def _compose_adaptive_response(
        self,
        state: TurnState,
        listener_draft: str,
        legal_guidance: str,
        lawyer_cards: List[LawyerCard],
        context: Dict[str, Any]
    ) -> str:
        """Compose response with adaptive empathy"""
        
        # Determine response strategy based on alliance and state
        strategy = self._determine_response_strategy(state)
        
        # Build the prompt
        system_prompt = f"""You are composing the final response as a therapeutic family law assistant.

Current state:
- Distress: {state.distress_score}/10
- Engagement: {state.engagement_level}/10
- Alliance: Bond={state.alliance_bond}, Goal={state.alliance_goal}, Task={state.alliance_task}
- Strategy: {strategy}

Components available:
1. Empathetic opening: {listener_draft}
2. Legal guidance: {legal_guidance or 'None yet'}
3. Lawyer matches: {len(lawyer_cards)} available

Adaptive Empathy Rules:
- If distress >= 7: Focus on emotional support, minimal practical advice
- If engagement <= 3: Use open questions, offer choices, increase warmth
- If any alliance score <= 4: Rebuild connection before advice
- Always end with autonomy-preserving choice (what they'd like to focus on)

Response structure:
1. Start with empathetic acknowledgment (use/adapt the listener draft)
2. {self._get_middle_section_guidance(strategy)}
3. End with choice-based question

Keep response under 200 words."""

        user_prompt = f"""Create the final response for this situation:

User said: "{state.user_text}"

Craft a response following the adaptive empathy rules and structure above."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.advisor_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            final_response = response.choices[0].message.content.strip()
            
            # Add lawyer recommendation if appropriate
            if lawyer_cards and state.distress_score < 7 and strategy != "crisis_support":
                final_response += f"\n\nI've found {len(lawyer_cards)} lawyers who might be a good match for your situation. Would you like to see their profiles?"
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error composing adaptive response: {e}")
            return listener_draft + "\n\nHow would you like me to help you with this?"
    
    def _determine_response_strategy(self, state: TurnState) -> str:
        """Determine response strategy based on state"""
        
        # Crisis mode
        if state.distress_score >= 8:
            return "crisis_support"
        
        # Low alliance - need to rebuild
        if any([state.alliance_bond <= 4, state.alliance_goal <= 4, state.alliance_task <= 4]):
            return "alliance_building"
        
        # Low engagement
        if state.engagement_level <= 3:
            return "engagement_boost"
        
        # High distress but not crisis
        if state.distress_score >= 6:
            return "emotional_support"
        
        # Standard balanced approach
        return "balanced_guidance"
    
    def _get_middle_section_guidance(self, strategy: str) -> str:
        """Get guidance for middle section based on strategy"""
        
        strategies = {
            "crisis_support": "Provide grounding and immediate coping strategies",
            "alliance_building": "Use MI techniques - reflections, affirmations, open questions",
            "engagement_boost": "Increase warmth, show curiosity, offer multiple options",
            "emotional_support": "Validate extensively, normalize feelings, gentle hope",
            "balanced_guidance": "Brief validation, then practical next step or information"
        }
        
        return strategies.get(strategy, "Provide balanced support and guidance")
    
    async def _generate_suggestions(self, state: TurnState, context: Dict[str, Any]) -> List[str]:
        """Generate contextual suggestions for user"""
        
        suggestions = []
        
        # Based on legal intent
        if "divorce" in state.legal_intent:
            suggestions.extend([
                "What are the steps to file for divorce in my state?",
                "How is property divided in a divorce?",
                "What documents do I need to gather?"
            ])
        
        if "custody" in state.legal_intent:
            suggestions.extend([
                "What factors determine child custody?",
                "How do I document my parenting time?",
                "What's the difference between legal and physical custody?"
            ])
        
        # Based on emotional state
        if state.distress_score >= 6:
            suggestions.extend([
                "I need help managing my anxiety about this",
                "Can you help me break this down into smaller steps?",
                "What support resources are available?"
            ])
        
        # Based on stage
        if not state.facts.get("zip"):
            suggestions.append("Find lawyers near me")
        
        if state.facts.get("budget_range") == "$":
            suggestions.append("What are my options for low-cost legal help?")
        
        # Limit to 5 suggestions
        return suggestions[:5]