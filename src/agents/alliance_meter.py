from typing import Dict, Any
from groq import AsyncGroq
from src.agents.base import BaseAgent
from src.models.conversation import TurnState
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AllianceMeter(BaseAgent):
    """Measure therapeutic alliance (bond, goal, task) metrics"""
    
    def __init__(self):
        super().__init__("alliance_meter")
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
    
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Measure alliance components"""
        
        # Get conversation history for context
        recent_turns = context.get("recent_turns", [])
        
        # Analyze alliance components
        alliance_scores = await self._analyze_alliance(
            state.user_text,
            state.assistant_draft,
            recent_turns
        )
        
        return alliance_scores
    
    async def _analyze_alliance(
        self, 
        user_text: str, 
        assistant_response: str,
        recent_turns: list
    ) -> Dict[str, float]:
        """Analyze therapeutic alliance components"""
        
        # Build conversation context
        context = self._build_context(recent_turns[-3:]) if recent_turns else ""
        
        prompt = f"""Analyze the therapeutic alliance in this conversation exchange.

Rate each component from 0-10:

1. BOND (0-10): Emotional connection, trust, feeling understood
   - Does the user feel heard and validated?
   - Is there warmth and rapport?
   - Signs of trust or mistrust?

2. GOAL (0-10): Agreement on what they're working toward
   - Clear shared understanding of objectives?
   - User buy-in to suggested direction?
   - Alignment on priorities?

3. TASK (0-10): Agreement on how to achieve goals
   - User engagement with suggested steps?
   - Willingness to follow guidance?
   - Active participation vs resistance?

Recent context:
{context}

Current exchange:
User: {user_text}
Assistant: {assistant_response}

Respond with ONLY three numbers:
Bond: [0-10]
Goal: [0-10]
Task: [0-10]"""

        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.alliance_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=50
            )
            
            result = response.choices[0].message.content.strip()
            scores = self._parse_scores(result)
            
            return scores
            
        except Exception as e:
            logger.error(f"Error in alliance analysis: {e}")
            # Return neutral scores on error
            return {
                "alliance_bond": 5.0,
                "alliance_goal": 5.0,
                "alliance_task": 5.0
            }
    
    def _build_context(self, recent_turns: list) -> str:
        """Build conversation context from recent turns"""
        context_lines = []
        for turn in recent_turns:
            context_lines.append(f"User: {turn.get('user_text', '')[:100]}...")
            context_lines.append(f"Assistant: {turn.get('assistant_response', '')[:100]}...")
        return "\n".join(context_lines)
    
    def _parse_scores(self, result: str) -> Dict[str, float]:
        """Parse alliance scores from LLM response"""
        scores = {
            "alliance_bond": 5.0,
            "alliance_goal": 5.0,
            "alliance_task": 5.0
        }
        
        lines = result.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("Bond:"):
                try:
                    scores["alliance_bond"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("Goal:"):
                try:
                    scores["alliance_goal"] = float(line.split(":")[1].strip())
                except:
                    pass
            elif line.startswith("Task:"):
                try:
                    scores["alliance_task"] = float(line.split(":")[1].strip())
                except:
                    pass
        
        # Ensure scores are in valid range
        for key in scores:
            scores[key] = min(max(scores[key], 0), 10)
        
        return scores