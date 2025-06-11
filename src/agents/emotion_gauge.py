from typing import Dict, Any, Tuple
import asyncio
from groq import AsyncGroq
from src.agents.base import BaseAgent
from src.models.conversation import TurnState
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmotionGauge(BaseAgent):
    """Analyze emotional state and engagement level"""
    
    def __init__(self):
        super().__init__("emotion_gauge")
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
    
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze emotional indicators"""
        
        # Run sentiment and engagement analysis in parallel
        sentiment_task = self._analyze_sentiment(state.user_text)
        engagement_task = self._analyze_engagement(state.user_text, context)
        
        (sentiment, enhanced_sentiment), engagement_level = await asyncio.gather(
            sentiment_task,
            engagement_task
        )
        
        return {
            "sentiment": sentiment,
            "enhanced_sentiment": enhanced_sentiment,
            "engagement_level": engagement_level
        }
    
    async def _analyze_sentiment(self, text: str) -> Tuple[str, str]:
        """Analyze basic and enhanced sentiment"""
        prompt = f"""Analyze the emotional sentiment of this message.

First, classify as: pos, neu, or neg

Then identify the specific emotion from this list:
admiration, amusement, anger, annoyance, approval, caring, confusion, curiosity, 
desire, disappointment, disapproval, disgust, embarrassment, excitement, fear, 
gratitude, grief, joy, love, nervousness, optimism, pride, realization, relief, 
remorse, sadness, surprise, neutral

Message: {text}

Format your response EXACTLY as:
Basic: [pos/neu/neg]
Enhanced: [specific emotion]"""

        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.emotion_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=50
            )
            
            result = response.choices[0].message.content.strip()
            lines = result.split('\n')
            
            basic = "neu"
            enhanced = "neutral"
            
            for line in lines:
                if line.startswith("Basic:"):
                    basic = line.split(":")[1].strip()
                elif line.startswith("Enhanced:"):
                    enhanced = line.split(":")[1].strip()
            
            # Validate enhanced sentiment
            valid_emotions = [
                "admiration", "amusement", "anger", "annoyance", "approval", "caring",
                "confusion", "curiosity", "desire", "disappointment", "disapproval",
                "disgust", "embarrassment", "excitement", "fear", "gratitude", "grief",
                "joy", "love", "nervousness", "optimism", "pride", "realization",
                "relief", "remorse", "sadness", "surprise", "neutral"
            ]
            
            # Clean up the enhanced sentiment
            enhanced = enhanced.lower().strip()
            
            # If the emotion contains extra text, try to extract the valid emotion
            if enhanced not in valid_emotions:
                # Try to find a valid emotion in the response
                for emotion in valid_emotions:
                    if emotion in enhanced:
                        enhanced = emotion
                        break
                else:
                    # Map common variations
                    emotion_map = {
                        "worry": "nervousness",
                        "worried": "nervousness", 
                        "concern": "nervousness",
                        "concerned": "nervousness",
                        "frustration": "annoyance",
                        "frustrated": "annoyance",
                        "sympathy": "caring",
                        "empathy": "caring",
                        "regret": "remorse",
                        "confidence": "optimism",
                        "confident": "optimism",
                        "anxious": "nervousness",
                        "anxiety": "nervousness",
                        "stress": "nervousness",
                        "stressed": "nervousness"
                    }
                    
                    # Check if any mapped emotion is in the response
                    for key, value in emotion_map.items():
                        if key in enhanced:
                            enhanced = value
                            break
                    else:
                        # Default to neutral if we can't map it
                        logger.warning(f"Unknown emotion '{enhanced}', defaulting to neutral")
                        enhanced = "neutral"
            
            return basic, enhanced
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return "neu", "neutral"
    
    async def _analyze_engagement(self, text: str, context: Dict[str, Any]) -> float:
        """Analyze user engagement level"""
        
        # Get conversation history
        turn_count = len(context.get("conversation_history", []))
        
        prompt = f"""Rate the user's engagement level from 0-10 based on their message.

Consider:
- Length and detail of response
- Questions asked
- Emotional investment
- Willingness to share information
- Response to previous guidance

This is turn {turn_count} of the conversation.

Message: {text}

Return ONLY a number from 0-10:"""

        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.emotion_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            
            score = float(response.choices[0].message.content.strip())
            return min(max(score, 0), 10)  # Ensure 0-10 range
            
        except Exception as e:
            logger.error(f"Error in engagement analysis: {e}")
            
            # Fallback heuristic
            word_count = len(text.split())
            if word_count < 10:
                return 3.0
            elif word_count < 30:
                return 5.0
            elif word_count < 100:
                return 7.0
            else:
                return 8.0