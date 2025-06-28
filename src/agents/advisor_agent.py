from typing import Dict, Any, List, Optional
import asyncio
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
        
        # Check if we need location from user
        needs_location = False
        missing_info = context.get("match_info", {}).get("needed_info", [])
        if missing_info and "location" in missing_info and not state.facts.get("zip"):
            needs_location = True
        
        return {
            "assistant_response": final_response,
            "suggestions": suggestions,
            "show_cards": len(lawyer_cards) > 0 and state.distress_score < 7,
            "needs_location": needs_location
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

FORMATTING REQUIREMENTS:
- Use clear paragraph breaks between thoughts
- Keep paragraphs to 2-3 sentences maximum
- Use **bold** for important terms or next steps
- Use bullet points when listing multiple items:
  • Like this for options
  • Or steps to take
- Use numbered lists for sequential steps:
  1. First step
  2. Second step

CONTENT RULES:
- If missing information exists: Naturally ask about ONE piece of missing info (don't overwhelm)
- If distress >= 7: Focus on emotional support, minimal practical advice
- If engagement <= 3: Use open questions, offer choices, increase warmth
- If any alliance score <= 4: Rebuild connection before advice
- If reflection is needed: Incorporate one reflection prompt naturally
- Always end with an autonomy-preserving choice question

RESPONSE STRUCTURE:
1. Start with empathetic acknowledgment (use/adapt the listener draft)
2. {self._get_middle_section_guidance(strategy)}
3. If missing info exists, naturally weave in a question about it
4. End with choice-based question like:
   - "Would you like to explore [option A] or [option B]?"
   - "What feels most important to address first?"
   - "How can I best support you with this?"

TONE:
- Conversational and warm, not robotic
- Use "I" statements: "I understand this is difficult"
- Avoid passive voice
- Use simple, clear language

Keep response under 200 words unless explaining complex legal concepts."""

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
            response = await asyncio.wait_for(
                self.groq_client.chat.completions.create(
                    model=settings.advisor_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300
                ),
                timeout=10.0  # 10 second timeout
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
            
        except asyncio.TimeoutError:
            logger.error("Advisor response timed out after 10 seconds")
            return listener_draft + "\n\nHow would you like me to help you with this?"
            
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
        shown_suggestions = context.get("shown_suggestions", [])
        
        # Helper function to add suggestion if not recently shown
        def add_if_new(suggestion: str):
            if suggestion not in shown_suggestions:
                suggestions.append(suggestion)
        
        # Dynamic suggestions pool to ensure variety
        suggestion_pools = {
            "location_missing": [
                "I'm in [city, state]",
                "I live in [city name]",
                "My location is [state]",
                "I'm located in [city, state]"
            ],
            "budget_missing": [
                "My budget is around $[amount]",
                "I can afford $[amount] per month",
                "I'm looking for pro bono help",
                "What are typical lawyer fees?"
            ],
            "timeline_missing": [
                "I need help within [timeframe]",
                "This is urgent - I need help ASAP",
                "I have [number] weeks to respond",
                "When should I start this process?"
            ],
            "divorce_questions": [
                "What are the steps to file for divorce in my state?",
                "How is property divided in a divorce?",
                "What documents do I need to gather?",
                "How long does divorce typically take?",
                "Do I need a lawyer to file for divorce?",
                "What's the difference between contested and uncontested divorce?",
                "How much does divorce cost in my state?"
            ],
            "custody_questions": [
                "What factors determine child custody?",
                "How do I document my parenting time?",
                "What's the difference between legal and physical custody?",
                "Can I modify an existing custody order?",
                "How do courts decide what's best for children?",
                "What rights do grandparents have?",
                "How does relocation affect custody?"
            ],
            "emotional_support": [
                "I need help managing my anxiety about this",
                "Can you help me break this down into smaller steps?",
                "What support resources are available?",
                "How do others cope with this situation?",
                "I'm feeling overwhelmed - what should I focus on first?",
                "Are there support groups for people like me?",
                "How can I stay strong for my children?"
            ],
            "general_help": [
                "Find lawyers near me",
                "What are my legal options?",
                "How do I know if I need a lawyer?",
                "What questions should I ask a lawyer?",
                "What are my rights in this situation?"
            ]
        }
        
        # Check for missing info first
        missing_info = context.get("match_info", {}).get("needed_info", [])
        if missing_info:
            if "location" in missing_info and "location_missing" in suggestion_pools:
                # Pick suggestions not recently shown
                for sugg in suggestion_pools["location_missing"]:
                    if sugg not in shown_suggestions:
                        add_if_new(sugg)
                        break
            if "budget" in missing_info and "budget_missing" in suggestion_pools:
                for sugg in suggestion_pools["budget_missing"]:
                    if sugg not in shown_suggestions:
                        add_if_new(sugg)
                        break
            if "timeline" in missing_info and "timeline_missing" in suggestion_pools:
                for sugg in suggestion_pools["timeline_missing"]:
                    if sugg not in shown_suggestions:
                        add_if_new(sugg)
                        break
        
        # Add reflection prompts if available (prioritize these)
        if reflection_prompts and len(suggestions) < 3:
            for prompt in reflection_prompts[:2]:
                add_if_new(prompt)
        
        # Based on legal intent - select non-repeated suggestions
        if "divorce" in state.legal_intent:
            available_divorce_q = [q for q in suggestion_pools["divorce_questions"] if q not in shown_suggestions]
            if available_divorce_q:
                # Add up to 2 new divorce questions
                for q in available_divorce_q[:2]:
                    add_if_new(q)
        
        if "custody" in state.legal_intent:
            available_custody_q = [q for q in suggestion_pools["custody_questions"] if q not in shown_suggestions]
            if available_custody_q:
                # Add up to 2 new custody questions
                for q in available_custody_q[:2]:
                    add_if_new(q)
        
        # Based on emotional state
        if state.distress_score >= 6:
            available_emotional = [q for q in suggestion_pools["emotional_support"] if q not in shown_suggestions]
            if available_emotional:
                add_if_new(available_emotional[0])
        
        # General suggestions if we need more
        if len(suggestions) < 3:
            available_general = [q for q in suggestion_pools["general_help"] if q not in shown_suggestions]
            for q in available_general:
                add_if_new(q)
                if len(suggestions) >= 5:
                    break
        
        # If still not enough suggestions, add topic-specific follow-ups
        if len(suggestions) < 3:
            # Add contextual follow-ups based on conversation
            if state.facts.get("has_children"):
                add_if_new("How will this affect my children?")
            if state.facts.get("married_years"):
                add_if_new("Does length of marriage affect my case?")
            if any(word in state.user_text.lower() for word in ["scared", "afraid", "worried"]):
                add_if_new("What should I do if I feel unsafe?")
        
        # Limit to 5 suggestions
        return suggestions[:5]