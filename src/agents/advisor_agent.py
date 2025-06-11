from typing import Dict, Any, List, Optional
from groq import AsyncGroq
from src.agents.base import BaseAgent
from src.models.conversation import TurnState, LawyerCard
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AdvisorAgent(BaseAgent):
    """Compose final response with adaptive empathy and guidance"""
    
    def __init__(self):
        super().__init__("advisor")
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
    
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
        
        # Check if matcher needs more info
        match_info = context.get("match_info", {})
        missing_info = match_info.get("needed_info", [])
        
        # Get reflection data
        needs_reflection = context.get("needs_reflection", False)
        reflection_type = context.get("reflection_type")
        reflection_prompts = context.get("reflection_prompts", [])
        reflection_insights = context.get("reflection_insights", [])
        
        suggestions = await self._generate_suggestions(
            state, 
            context,
            reflection_prompts=reflection_prompts if needs_reflection else []
        )
        
        # Compose adaptive response
        final_response = await self._compose_adaptive_response(
            state,
            listener_draft,
            legal_guidance,
            lawyer_cards,
            context,
            reflection_data={
                "needs_reflection": needs_reflection,
                "reflection_type": reflection_type,
                "reflection_prompts": reflection_prompts,
                "reflection_insights": reflection_insights
            }
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
        context: Dict[str, Any],
        reflection_data: Dict[str, Any]
    ) -> str:
        """Compose response with adaptive empathy"""
        
        # Determine response strategy based on alliance and state
        strategy = self._determine_response_strategy(state)
        
        # Check if we need more info for matching
        missing_info = context.get("match_info", {}).get("needed_info", [])
        
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
4. Missing information for matching: {missing_info if missing_info else 'None'}
5. Reflection needed: {reflection_data['needs_reflection']} (type: {reflection_data.get('reflection_type', 'none')})

Adaptive Empathy Rules:
- If missing information exists: Naturally ask about ONE piece of missing info (don't overwhelm)
- If distress >= 7: Focus on emotional support, minimal practical advice
- If engagement <= 3: Use open questions, offer choices, increase warmth
- If any alliance score <= 4: Rebuild connection before advice
- If reflection is needed: Incorporate one reflection prompt naturally into the response
- Always end with autonomy-preserving choice (what they'd like to focus on)

Response structure:
1. Start with empathetic acknowledgment (use/adapt the listener draft)
2. {self._get_middle_section_guidance(strategy)}
3. If missing info exists, naturally weave in a question about it
4. End with choice-based question

Keep response under 200 words."""

        # Add reflection context if needed
        reflection_context = ""
        if reflection_data['needs_reflection'] and reflection_data.get('reflection_prompts'):
            reflection_context = f"""

Reflection prompts to potentially incorporate:
{chr(10).join(f"- {prompt}" for prompt in reflection_data['reflection_prompts'][:2])}

Reflection insights about their journey:
{chr(10).join(f"- {insight}" for insight in reflection_data.get('reflection_insights', [])[:2])}
"""

        user_prompt = f"""Create the final response for this situation:

User said: "{state.user_text}"

{"Missing information needed: " + ", ".join(missing_info) if missing_info else ""}
{reflection_context}

Craft a response following the adaptive empathy rules and structure above.
- If missing info exists, ask about ONE item naturally (e.g., "To find the best match for your situation, could you tell me about your budget?" or "What area are you located in?")
- If reflection is needed, naturally weave in ONE reflection prompt
- Don't mention lawyers yet if we're still gathering information"""

        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.advisor_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            final_response = response.choices[0].message.content.strip()
            
            # Clean up any meta-text from the response
            if "Here's a response" in final_response or "following the adaptive empathy" in final_response:
                # Extract just the actual response content
                if '"' in final_response:
                    # Find content between quotes
                    parts = final_response.split('"')
                    if len(parts) >= 3:
                        # Get the content between the first pair of quotes after any preamble
                        for i, part in enumerate(parts):
                            if i > 0 and i % 2 == 1 and len(part) > 50:  # Odd indices are between quotes
                                final_response = part
                                break
                elif '\n\n' in final_response:
                    # If no quotes, try splitting by double newline
                    parts = final_response.split('\n\n', 1)
                    if len(parts) > 1:
                        final_response = parts[1]
            
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
    
    async def _generate_suggestions(
        self, 
        state: TurnState, 
        context: Dict[str, Any],
        reflection_prompts: List[str] = []
    ) -> List[str]:
        """Generate contextual suggestions for user"""
        
        suggestions = []
        
        # Check for missing info first
        missing_info = context.get("match_info", {}).get("needed_info", [])
        if missing_info:
            # Add questions about missing info
            if "location" in missing_info:
                suggestions.append("I'm in [city, state]")
            if "budget" in missing_info:
                suggestions.append("My budget is around $[amount]")
            if "timeline" in missing_info:
                suggestions.append("I need help within [timeframe]")
            if "family details" in missing_info:
                suggestions.append("I have [number] children")
        
        # Add reflection prompts if available (prioritize these)
        if reflection_prompts and len(suggestions) < 3:
            suggestions.extend(reflection_prompts[:2])
        
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