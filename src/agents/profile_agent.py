from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
from src.agents.base import BaseAgent
from src.models.conversation import TurnState
from src.models.user import UserProfile
from src.services.database import dynamodb_service, redis_service
from src.config.settings import settings
from src.utils.logger import get_logger
import json

logger = get_logger(__name__)


class ProfileAgent(BaseAgent):
    """Fetch and manage user profiles with caching"""
    
    def __init__(self):
        super().__init__("profile")
        self.cache_ttl = 300  # 5 minutes
    
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch user profile and inject into context"""
        user_id = state.user_id
        
        # Try cache first
        profile = await self._get_cached_profile(user_id)
        
        if not profile:
            # Fetch from database
            profile = await self._fetch_or_create_profile(user_id)
            
            # Cache the profile
            await self._cache_profile(user_id, profile)
        
        # Get recent conversation summaries
        summaries = await self._get_recent_summaries(user_id)
        
        # Calculate derived metrics
        metrics = self._calculate_user_metrics(profile)
        
        return {
            "user_profile": profile,
            "recent_summaries": summaries,
            "user_metrics": metrics,
            "preferences": profile.get("preferences", {})
        }
    
    async def _get_cached_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get profile from cache"""
        try:
            cached = await redis_service.get(f"profile:{user_id}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Cache error: {e}")
        return None
    
    async def _cache_profile(self, user_id: str, profile: Dict[str, Any]):
        """Cache profile with TTL"""
        try:
            await redis_service.set(
                f"profile:{user_id}",
                json.dumps(profile),
                ttl=self.cache_ttl
            )
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    async def _fetch_or_create_profile(self, user_id: str) -> Dict[str, Any]:
        """Fetch existing profile or create new one"""
        profile_data = await dynamodb_service.get_user_profile(user_id)
        
        if not profile_data:
            # Create new profile
            new_profile = UserProfile(user_id=user_id)
            profile_data = new_profile.dict()
            
            # Save to database
            await dynamodb_service.update_user_profile(user_id, profile_data)
            logger.info(f"Created new profile for user {user_id}")
        
        return profile_data
    
    async def _get_recent_summaries(self, user_id: str) -> List[str]:
        """Get recent conversation summaries"""
        # Fetch recent turns
        recent_turns = await dynamodb_service.get_recent_turns(user_id, limit=20)
        
        if not recent_turns:
            return []
        
        # Group by conversation and summarize
        summaries = []
        current_summary = []
        
        for turn in recent_turns:
            if turn.get("user_text") and turn.get("assistant_response"):
                summary_line = f"User: {turn['user_text'][:100]}... Assistant: {turn['assistant_response'][:100]}..."
                current_summary.append(summary_line)
                
                # Create summary every 5 turns
                if len(current_summary) >= 5:
                    summaries.append("\n".join(current_summary))
                    current_summary = []
        
        # Add remaining turns
        if current_summary:
            summaries.append("\n".join(current_summary))
        
        return summaries[-3:]  # Return last 3 summaries
    
    def _calculate_user_metrics(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived metrics from profile"""
        metrics = {
            "total_conversations": len(profile.get("conversation_summaries", [])),
            "days_since_first_interaction": 0,
            "average_distress_trend": "stable",
            "engagement_trend": "stable",
            "primary_concerns": [],
            "progress_percentage": 0,
            "milestones_completed": len(profile.get("milestones_completed", [])),
            "current_goals": profile.get("current_goals", [])
        }
        
        # Days since first interaction
        if profile.get("created_at"):
            created = datetime.fromisoformat(profile["created_at"])
            metrics["days_since_first_interaction"] = (datetime.utcnow() - created).days
        
        # Emotional trends
        timeline = profile.get("emotional_timeline", [])
        if len(timeline) >= 2:
            recent_distress = [e["distress_score"] for e in timeline[-5:]]
            older_distress = [e["distress_score"] for e in timeline[-10:-5]]
            
            if recent_distress and older_distress:
                recent_avg = sum(recent_distress) / len(recent_distress)
                older_avg = sum(older_distress) / len(older_distress)
                
                if recent_avg > older_avg + 1:
                    metrics["average_distress_trend"] = "increasing"
                elif recent_avg < older_avg - 1:
                    metrics["average_distress_trend"] = "decreasing"
        
        # Primary concerns from legal situation
        legal_situation = profile.get("legal_situation", {})
        if "case_type" in legal_situation:
            metrics["primary_concerns"] = legal_situation["case_type"]
        
        # Progress calculation - now using actual milestone count
        # Import milestone catalog to get accurate total
        from src.agents.progress_tracker import DIVORCE_MILESTONES
        
        milestones_completed = profile.get("milestones_completed", [])
        
        # Determine total milestones based on case type
        case_types = legal_situation.get("case_type", ["divorce"])
        if isinstance(case_types, str):
            case_types = [case_types]
        
        # For now, use divorce milestones as default
        total_milestones = len(DIVORCE_MILESTONES)
        
        # Calculate percentage more accurately
        if total_milestones > 0:
            metrics["progress_percentage"] = int((len(milestones_completed) / total_milestones) * 100)
        else:
            metrics["progress_percentage"] = 0
        
        return metrics
    
    async def update_profile_emotional_state(
        self, 
        user_id: str, 
        turn_state: TurnState
    ):
        """Update user profile with latest emotional state"""
        try:
            # Create emotional timeline entry
            emotional_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "sentiment": turn_state.sentiment,
                "enhanced_sentiment": turn_state.enhanced_sentiment,
                "distress_score": turn_state.distress_score,
                "engagement_level": turn_state.engagement_level,
                "context": turn_state.user_text[:50] + "..." if len(turn_state.user_text) > 50 else turn_state.user_text
            }
            
            # Create alliance history entry
            alliance_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "bond": turn_state.alliance_bond,
                "goal": turn_state.alliance_goal,
                "task": turn_state.alliance_task
            }
            
            # Get current profile
            profile = await dynamodb_service.get_user_profile(user_id)
            if not profile:
                profile = UserProfile(user_id=user_id).dict()
            
            # Update emotional timeline (keep last 100 entries)
            emotional_timeline = profile.get("emotional_timeline", [])
            emotional_timeline.append(emotional_entry)
            if len(emotional_timeline) > 100:
                emotional_timeline = emotional_timeline[-100:]
            
            # Update alliance history (keep last 50 entries)
            alliance_history = profile.get("alliance_history", [])
            alliance_history.append(alliance_entry)
            if len(alliance_history) > 50:
                alliance_history = alliance_history[-50:]
            
            # Calculate running averages
            recent_emotions = emotional_timeline[-10:]
            avg_distress = sum(e["distress_score"] for e in recent_emotions) / len(recent_emotions)
            avg_engagement = sum(e["engagement_level"] for e in recent_emotions) / len(recent_emotions)
            
            # Update milestones if progress markers present
            if turn_state.progress_markers:
                milestones_completed = profile.get("milestones_completed", [])
                # Add new milestones that aren't already in the list
                for marker in turn_state.progress_markers:
                    if marker not in milestones_completed:
                        milestones_completed.append(marker)
                profile["milestones_completed"] = milestones_completed
            
            # Update profile
            updates = {
                "emotional_timeline": emotional_timeline,
                "alliance_history": alliance_history,
                "average_distress_score": avg_distress,
                "average_engagement_level": avg_engagement,
                "last_interaction": datetime.utcnow().isoformat(),
                "milestones_completed": profile.get("milestones_completed", [])
            }
            
            await dynamodb_service.update_user_profile(user_id, updates)
            
            # Invalidate cache
            await redis_service.delete(f"profile:{user_id}")
            
        except Exception as e:
            logger.error(f"Error updating profile emotional state: {e}")