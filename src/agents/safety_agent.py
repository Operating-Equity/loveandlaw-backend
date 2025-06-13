from typing import Dict, Any, List
import re
from src.agents.base import BaseAgent
from src.models.conversation import TurnState
from src.config.settings import settings
from src.utils.logger import get_logger
from src.utils.groq_client import get_groq_client

logger = get_logger(__name__)


class SafetyAgent(BaseAgent):
    """Detect distress and safety concerns in user messages"""
    
    def __init__(self):
        super().__init__("safety")
        self.groq_client = get_groq_client()
        
        # Crisis keywords and patterns
        self.crisis_keywords = [
            "suicide", "kill myself", "end it all", "not worth living",
            "harm myself", "self harm", "want to die", "better off dead",
            "no point in living", "can't go on", "ending my life"
        ]
        
        self.crisis_patterns = [
            r"\b(want|going|plan) to (die|kill|harm|hurt) (myself|my self)\b",
            r"\blife.{0,20}not worth\b",
            r"\bno reason to (live|go on)\b",
            r"\b(thinking|thought) (of|about) (suicide|dying|death)\b"
        ]
        
        # Distress indicators
        self.distress_indicators = {
            "high": ["devastated", "desperate", "hopeless", "can't cope", "falling apart", 
                    "breaking down", "lost everything", "ruined my life"],
            "medium": ["overwhelmed", "stressed", "anxious", "scared", "confused", 
                      "frustrated", "angry", "upset", "crying"],
            "low": ["worried", "concerned", "unsure", "nervous", "sad"]
        }
    
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess safety and distress level"""
        text = state.user_text.lower()
        
        # Check for immediate crisis
        crisis_detected = await self._detect_crisis(text)
        
        # Calculate distress score
        distress_score = await self._calculate_distress_score(text, state)
        
        # Determine if safety hold is needed
        needs_safety_hold = crisis_detected or distress_score >= settings.crisis_threshold
        
        updates = {
            "distress_score": distress_score,
            "crisis_detected": crisis_detected,
            "needs_safety_hold": needs_safety_hold
        }
        
        if needs_safety_hold:
            updates["stage"] = "safety_hold"
            updates["safety_response"] = await self._generate_safety_response(state, crisis_detected)
            
            # Log for human review
            logger.warning(f"Safety hold triggered for user {state.user_id}: distress={distress_score}, crisis={crisis_detected}")
        
        return updates
    
    async def _detect_crisis(self, text: str) -> bool:
        """Detect crisis keywords and patterns"""
        # Check keywords
        for keyword in self.crisis_keywords:
            if keyword in text:
                return True
        
        # Check patterns
        for pattern in self.crisis_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Use LLM for nuanced detection
        try:
            prompt = f"""Analyze this message for suicide risk or self-harm intent. 
Return ONLY 'YES' if there are clear indicators, 'NO' otherwise.

Message: {text}

Answer:"""

            response = await self.groq_client.chat.completions.create(
                model=settings.safety_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            
            answer = response.choices[0].message.content.strip().upper()
            return answer == "YES"
            
        except Exception as e:
            logger.error(f"Error in crisis detection: {e}")
            # Err on the side of caution
            return False
    
    async def _calculate_distress_score(self, text: str, state: TurnState) -> float:
        """Calculate distress score from 0-10"""
        score = 0.0
        
        # Check distress indicators
        for level, indicators in self.distress_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    if level == "high":
                        score += 3.0
                    elif level == "medium":
                        score += 2.0
                    else:
                        score += 1.0
        
        # Factor in sentiment
        if state.sentiment == "neg":
            score += 1.0
        
        # Use LLM for nuanced assessment
        try:
            prompt = f"""Rate the emotional distress level in this message from 0-10.
0 = No distress
5 = Moderate distress
10 = Severe distress/crisis

Consider: emotional language, hopelessness, overwhelm, coping ability.

Message: {text}

Return ONLY a number from 0-10:"""

            response = await self.groq_client.chat.completions.create(
                model=settings.safety_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            
            llm_score = float(response.choices[0].message.content.strip())
            
            # Combine scores (weighted average)
            final_score = (score * 0.3 + llm_score * 0.7)
            
        except Exception as e:
            logger.error(f"Error in distress scoring: {e}")
            final_score = min(score, 10.0)
        
        return min(final_score, 10.0)
    
    async def _generate_safety_response(self, state: TurnState, crisis: bool) -> str:
        """Generate appropriate safety response"""
        if crisis:
            return """I'm deeply concerned about what you're sharing. Your life has value, and there is help available.

**Please reach out for immediate support:**
• National Suicide Prevention Lifeline: 988 or 1-800-273-8255
• Crisis Text Line: Text HOME to 741741
• Or go to your nearest emergency room

Would you like me to connect you with a crisis counselor right now? I'm here to support you through this."""
        
        else:
            return """I can see you're going through an incredibly difficult time. It's okay to feel overwhelmed - divorce and family legal issues are among life's most stressful experiences.

**Here are some immediate coping strategies:**
• Take slow, deep breaths (4 counts in, 6 counts out)
• Call a trusted friend or family member
• Consider speaking with a counselor who specializes in family transitions

I'm here to help you navigate this step by step. Would you like to focus on one specific concern right now, or would you prefer to talk about how you're feeling?"""