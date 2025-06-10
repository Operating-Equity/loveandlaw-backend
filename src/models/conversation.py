from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import uuid4


class TurnState(BaseModel):
    turn_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    stage: Literal["listening", "advising", "matching", "safety_hold"] = "listening"
    user_text: str
    assistant_draft: str = ""
    sentiment: Literal["pos", "neu", "neg"] = "neu"
    enhanced_sentiment: Literal[
        "admiration", "amusement", "anger", "annoyance", "approval", "caring",
        "confusion", "curiosity", "desire", "disappointment", "disapproval",
        "disgust", "embarrassment", "excitement", "fear", "gratitude", "grief",
        "joy", "love", "nervousness", "optimism", "pride", "realization",
        "relief", "remorse", "sadness", "surprise", "neutral"
    ] = "neutral"
    distress_score: float = Field(ge=0, le=10, default=0)
    engagement_level: float = Field(ge=0, le=10, default=5)
    
    alliance_bond: float = Field(ge=0, le=10, default=5)
    alliance_goal: float = Field(ge=0, le=10, default=5)
    alliance_task: float = Field(ge=0, le=10, default=5)
    
    legal_intent: List[str] = Field(default_factory=list)
    facts: Dict[str, Any] = Field(default_factory=dict)
    progress_markers: List[str] = Field(default_factory=list)
    memory_short: Optional[str] = None
    memory_long: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class LawyerCard(BaseModel):
    id: str
    name: str
    firm: str
    match_score: float = Field(ge=0, le=1)
    blurb: str
    link: str
    practice_areas: List[str] = Field(default_factory=list)
    location: Dict[str, Any] = Field(default_factory=dict)
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    budget_range: Optional[str] = None


class WebSocketMessage(BaseModel):
    type: Literal["user_msg", "ai_chunk", "cards", "suggestions", "heartbeat", "error", "session_end"]
    cid: Optional[str] = None
    text: Optional[str] = None
    text_fragment: Optional[str] = None
    cards: Optional[List[LawyerCard]] = None
    suggestions: Optional[List[str]] = None
    code: Optional[str] = None
    message: Optional[str] = None


class ConversationState(BaseModel):
    user_id: str
    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    turns: List[TurnState] = Field(default_factory=list)
    current_stage: Literal["listening", "advising", "matching", "safety_hold"] = "listening"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }