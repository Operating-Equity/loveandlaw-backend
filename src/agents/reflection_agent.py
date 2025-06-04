from typing import Dict, Any, List
import asyncio
from datetime import datetime, timedelta
from openai import AsyncOpenAI
from groq import AsyncGroq

from src.models.conversation import TurnState
from src.agents.base import BaseAgent
from src.utils.logger import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


class ReflectionAgent(BaseAgent):
    """
    Agent that helps users reflect on their journey, emotional progress,
    and decisions made. Promotes self-awareness and growth.
    """
    
    def __init__(self):
        super().__init__()
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def process(self, turn_state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine if reflection is appropriate and generate reflection prompts.
        
        Returns:
            Dict containing:
            - needs_reflection: bool indicating if reflection should be triggered
            - reflection_type: type of reflection (journey, emotional, decision, milestone)
            - reflection_prompts: List of reflection questions/prompts
            - reflection_insights: Insights about user's progress
        """
        
        # Get user profile data
        user_profile = context.get("user_profile", {})
        conversation_history = context.get("conversation_summary", [])
        emotional_timeline = user_profile.get("emotional_timeline", [])
        milestones = turn_state.progress_markers
        
        # Check if reflection is appropriate
        should_reflect, reflection_type = await self._should_trigger_reflection(
            turn_state, user_profile, conversation_history
        )
        
        if not should_reflect:
            return {
                "needs_reflection": False,
                "reflection_type": None,
                "reflection_prompts": [],
                "reflection_insights": []
            }
        
        # Generate appropriate reflection content
        reflection_prompts = await self._generate_reflection_prompts(
            reflection_type, turn_state, user_profile, conversation_history
        )
        
        # Generate insights about progress
        reflection_insights = await self._analyze_journey_progress(
            turn_state, emotional_timeline, milestones
        )
        
        return {
            "needs_reflection": True,
            "reflection_type": reflection_type,
            "reflection_prompts": reflection_prompts,
            "reflection_insights": reflection_insights
        }
    
    async def _should_trigger_reflection(
        self, 
        turn_state: TurnState, 
        user_profile: Dict[str, Any],
        conversation_history: List[str]
    ) -> tuple[bool, str]:
        """
        Determine if reflection should be triggered and what type.
        
        Reflection triggers:
        1. Milestone reached - reflect on achievement
        2. Emotional shift - significant change in distress/engagement
        3. Decision point - user considering major action
        4. Time-based - periodic check-ins on journey
        5. Low alliance - when therapeutic relationship needs strengthening
        """
        
        # Check for milestone completion
        recent_milestones = user_profile.get("recent_milestones", [])
        if recent_milestones:
            return True, "milestone"
        
        # Check for emotional shifts
        emotional_timeline = user_profile.get("emotional_timeline", [])
        if len(emotional_timeline) >= 3:
            recent_emotions = emotional_timeline[-3:]
            avg_recent_distress = sum(e.get("distress_score", 5) for e in recent_emotions) / 3
            current_distress = turn_state.distress_score
            
            # Significant improvement
            if current_distress < avg_recent_distress - 2:
                return True, "emotional_progress"
            
            # Significant worsening
            if current_distress > avg_recent_distress + 2:
                return True, "emotional_support"
        
        # Check for decision points
        user_text_lower = turn_state.user_text.lower()
        decision_keywords = [
            "should i", "thinking about", "considering", "not sure if",
            "what do you think", "need to decide", "torn between"
        ]
        if any(keyword in user_text_lower for keyword in decision_keywords):
            return True, "decision"
        
        # Check for low alliance scores
        if (turn_state.alliance_bond < 5 or 
            turn_state.alliance_goal < 5 or 
            turn_state.alliance_task < 5):
            return True, "alliance"
        
        # Time-based reflection (every 10 turns or weekly)
        turn_count = user_profile.get("turn_count", 0)
        if turn_count > 0 and turn_count % 10 == 0:
            return True, "journey"
        
        # Check last reflection time
        last_reflection = user_profile.get("last_reflection_date")
        if last_reflection:
            last_date = datetime.fromisoformat(last_reflection)
            if datetime.utcnow() - last_date > timedelta(days=7):
                return True, "journey"
        
        return False, None
    
    async def _generate_reflection_prompts(
        self,
        reflection_type: str,
        turn_state: TurnState,
        user_profile: Dict[str, Any],
        conversation_history: List[str]
    ) -> List[str]:
        """Generate reflection prompts based on type and context."""
        
        prompt = f"""
        Generate 3-4 thoughtful reflection questions for a user going through family law challenges.
        
        Reflection Type: {reflection_type}
        Current Emotional State: {turn_state.sentiment} (distress: {turn_state.distress_score}/10)
        Recent Context: {turn_state.user_text}
        User Journey Summary: {' '.join(conversation_history[-3:])}
        
        Guidelines for {reflection_type} reflection:
        """
        
        if reflection_type == "milestone":
            prompt += """
            - Celebrate the achievement
            - Help them recognize their strength and progress
            - Connect this milestone to their larger goals
            - Encourage self-compassion
            """
        elif reflection_type == "emotional_progress":
            prompt += """
            - Acknowledge the emotional improvement
            - Help them identify what's been helpful
            - Explore what they've learned about themselves
            - Build confidence in their coping abilities
            """
        elif reflection_type == "emotional_support":
            prompt += """
            - Validate their struggle without minimizing
            - Gently explore what might be contributing to increased distress
            - Help them identify their support systems
            - Encourage self-care without being prescriptive
            """
        elif reflection_type == "decision":
            prompt += """
            - Help them clarify their values and priorities
            - Explore what matters most to them
            - Consider different perspectives without pushing
            - Connect decisions to their long-term wellbeing
            """
        elif reflection_type == "alliance":
            prompt += """
            - Check in on how supported they feel
            - Explore what would be most helpful right now
            - Clarify goals and expectations
            - Strengthen the therapeutic relationship
            """
        elif reflection_type == "journey":
            prompt += """
            - Help them see the bigger picture of their progress
            - Identify patterns of growth or challenge
            - Recognize their resilience
            - Connect past progress to future possibilities
            """
        
        prompt += """
        
        Generate questions that are:
        - Open-ended and inviting
        - Strengths-focused while acknowledging challenges
        - Respectful of their autonomy
        - Promoting self-awareness without being intrusive
        
        Format: Return only the questions, one per line.
        """
        
        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.emotion_model,  # Using emotion_model for reflection
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
            )
            
            questions = response.choices[0].message.content.strip().split('\n')
            return [q.strip() for q in questions if q.strip()][:4]
            
        except Exception as e:
            logger.error(f"Error generating reflection prompts: {e}")
            # Fallback questions
            return self._get_fallback_prompts(reflection_type)
    
    async def _analyze_journey_progress(
        self,
        turn_state: TurnState,
        emotional_timeline: List[Dict],
        milestones: List[str]
    ) -> List[str]:
        """Analyze and generate insights about user's journey progress."""
        
        if len(emotional_timeline) < 2:
            return []
        
        prompt = f"""
        Analyze this user's journey through their family law situation and provide 2-3 brief, 
        supportive insights about their progress.
        
        Emotional Journey:
        - Starting point: {emotional_timeline[0] if emotional_timeline else 'Unknown'}
        - Current state: Distress {turn_state.distress_score}/10, {turn_state.sentiment}
        - Milestones achieved: {', '.join(milestones) if milestones else 'Starting their journey'}
        
        Recent emotional trends:
        {self._format_emotional_trends(emotional_timeline[-5:])}
        
        Generate insights that:
        - Acknowledge both progress and ongoing challenges
        - Are specific to their journey (not generic)
        - Build hope while staying realistic
        - Are brief (1-2 sentences each)
        
        Format: One insight per line.
        """
        
        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.emotion_model,  # Using emotion_model for reflection
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=200
            )
            
            insights = response.choices[0].message.content.strip().split('\n')
            return [i.strip() for i in insights if i.strip()][:3]
            
        except Exception as e:
            logger.error(f"Error generating journey insights: {e}")
            return []
    
    def _format_emotional_trends(self, timeline: List[Dict]) -> str:
        """Format emotional timeline for analysis."""
        if not timeline:
            return "No emotional data available"
        
        trends = []
        for entry in timeline:
            date = entry.get("timestamp", "Unknown time")
            distress = entry.get("distress_score", "?")
            sentiment = entry.get("sentiment", "unknown")
            trends.append(f"- {date}: Distress {distress}/10, {sentiment}")
        
        return '\n'.join(trends)
    
    def _get_fallback_prompts(self, reflection_type: str) -> List[str]:
        """Fallback reflection prompts by type."""
        
        prompts = {
            "milestone": [
                "How does it feel to have reached this point in your journey?",
                "What strengths helped you get here?",
                "What have you learned about yourself through this process?"
            ],
            "emotional_progress": [
                "What's been helpful in managing your emotions lately?",
                "How are you feeling compared to when we started talking?",
                "What coping strategies have you discovered work best for you?"
            ],
            "emotional_support": [
                "What's feeling most challenging right now?",
                "Who in your life offers you support during difficult times?",
                "What would help you feel more grounded today?"
            ],
            "decision": [
                "What values are most important to you as you consider this decision?",
                "How do you typically make important decisions?",
                "What would you need to know to feel more confident moving forward?"
            ],
            "alliance": [
                "How can I best support you right now?",
                "What's working well in our conversations?",
                "Is there anything you'd like to approach differently?"
            ],
            "journey": [
                "Looking back, what surprises you most about your journey so far?",
                "What are you most proud of accomplishing?",
                "How has this experience changed your perspective?"
            ]
        }
        
        return prompts.get(reflection_type, [
            "How are you feeling about your progress?",
            "What's on your mind today?",
            "What would be most helpful to explore?"
        ])