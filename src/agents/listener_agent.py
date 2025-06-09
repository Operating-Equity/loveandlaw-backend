from typing import Dict, Any, Optional, List
import asyncio
from groq import AsyncGroq
from src.agents.base import BaseAgent
from src.models.conversation import TurnState
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ListenerAgent(BaseAgent):
    """Generate empathetic, therapeutic responses using active listening"""
    
    def __init__(self):
        super().__init__("listener")
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
    
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate initial empathetic response"""
        
        # Skip if in safety hold
        if state.stage == "safety_hold":
            return {}
        
        # Get user profile for personalization
        user_profile = context.get("user_profile", {})
        recent_summaries = context.get("recent_summaries", [])
        
        # Generate reflective response
        listener_response = await self._generate_listener_response(
            state, 
            user_profile, 
            recent_summaries
        )
        
        return {
            "listener_draft": listener_response,
            "stage": "listening"
        }
    
    async def _generate_listener_response(
        self, 
        state: TurnState, 
        user_profile: Dict[str, Any],
        recent_summaries: List[str]
    ) -> str:
        """Generate empathetic listening response"""
        
        # Build context from recent conversation
        conversation_context = "\n".join(recent_summaries[-3:]) if recent_summaries else "First interaction"
        
        # Get user preferences
        communication_style = user_profile.get("preferences", {}).get("communication_style", "empathetic")
        
        system_prompt = f"""You are a compassionate family law assistant trained in therapeutic communication.
Your role is to provide emotional support while helping users navigate legal challenges.

Communication style: {communication_style}
Current emotional state: {state.sentiment} (distress level: {state.distress_score}/10)

Guidelines:
1. Use active listening techniques (reflection, validation, summarization)
2. Acknowledge emotions before addressing practical matters
3. Be warm but professional
4. Keep initial responses concise (2-3 sentences)
5. Show you understand their specific situation
6. Avoid legal advice - focus on emotional support and process guidance

Recent context:
{conversation_context}"""

        user_prompt = f"""Respond empathetically to this message from someone dealing with family law issues:

"{state.user_text}"

Provide a brief, therapeutic response that shows understanding and validates their experience."""

        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.listener_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200,
                stream=True
            )
            
            # Collect the full response
            full_response = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
            
            return full_response.strip()
            
        except Exception as e:
            logger.error(f"Error generating listener response: {e}")
            return "I hear how difficult this is for you. Let me help you work through this step by step."
    
    def _get_therapeutic_techniques(self, state: TurnState) -> List[str]:
        """Select appropriate therapeutic techniques based on state"""
        techniques = []
        
        if state.distress_score >= 6:
            techniques.extend(["validation", "normalization", "grounding"])
        
        if state.engagement_level <= 3:
            techniques.extend(["open_questions", "curiosity", "choices"])
        
        if state.alliance_bond <= 4:
            techniques.extend(["empathy", "reflection", "collaborative_language"])
        
        if state.sentiment == "neg":
            techniques.extend(["hope", "strengths_focus", "reframing"])
        
        return techniques