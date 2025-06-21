from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4


class EmotionalTimelineEntry(BaseModel):
    timestamp: datetime
    sentiment: str
    distress_score: float
    engagement_level: float
    context: Optional[str] = None


class UserPreferences(BaseModel):
    communication_style: Literal["formal", "casual", "empathetic"] = "empathetic"
    language: str = "en"
    timezone: str = "UTC"
    notification_preferences: Dict[str, bool] = Field(default_factory=lambda: {
        "email": True,
        "sms": False,
        "in_app": True
    })


class UserProfile(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # User information
    name: Optional[str] = None
    email: Optional[str] = None
    preferred_avatar: Optional[str] = None  # Avatar URL or identifier
    
    # Demographics (optional, privacy-conscious)
    location: Optional[Dict[str, str]] = None  # {zip, state, country}
    
    # Legal situation
    legal_situation: Dict[str, Any] = Field(default_factory=dict)
    case_type: Optional[List[str]] = None
    important_dates: Dict[str, datetime] = Field(default_factory=dict)
    
    # Progress tracking
    milestones_completed: List[str] = Field(default_factory=list)
    current_goals: List[str] = Field(default_factory=list)
    
    # Emotional profile
    emotional_timeline: List[EmotionalTimelineEntry] = Field(default_factory=list)
    average_distress_score: float = 5.0
    average_engagement_level: float = 5.0
    
    # Alliance metrics history
    alliance_history: List[Dict[str, float]] = Field(default_factory=list)
    
    # Conversation summaries
    conversation_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Preferences
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    
    # Matched lawyers history
    lawyers_viewed: List[str] = Field(default_factory=list)
    lawyers_contacted: List[str] = Field(default_factory=list)
    saved_lawyers: List[str] = Field(default_factory=list)  # Saved/favorited lawyers
    
    # Safety flags
    crisis_interventions: List[Dict[str, Any]] = Field(default_factory=list)
    requires_human_review: bool = False