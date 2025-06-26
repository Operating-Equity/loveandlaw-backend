from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    """Request model for lawyer matching"""
    facts: Dict[str, Any] = Field(
        ..., 
        description="Search criteria including zip, practice_areas, budget_range, etc."
    )
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of results")


class LawyerUploadResponse(BaseModel):
    """Response model for lawyer CSV upload"""
    status: str
    indexed_count: int
    errors: List[str] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    """Response model for user profile"""
    profile: Dict[str, Any]


class ProfileUpdateRequest(BaseModel):
    """Request model for updating user profile"""
    name: Optional[str] = None
    email: Optional[str] = None
    preferred_avatar: Optional[str] = None
    saved_lawyers: Optional[List[str]] = None
    legal_situation: Optional[Dict[str, Any]] = None
    current_goals: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None


class LawyerDetailsResponse(BaseModel):
    """Response model for lawyer details"""
    id: str
    name: str
    firm: Optional[str] = None
    profile_summary: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    practice_areas: List[str] = Field(default_factory=list)
    specialties: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    professional_experience: Optional[str] = None
    years_of_experience: Optional[int] = None
    languages: List[str] = Field(default_factory=list)
    payment_methods: List[str] = Field(default_factory=list)
    ratings: Optional[Dict[str, Any]] = None
    reviews: List[Dict[str, Any]] = Field(default_factory=list)
    phone_numbers: List[str] = Field(default_factory=list)
    email: Optional[str] = None
    website: Optional[str] = None
    awards: List[str] = Field(default_factory=list)
    associations: List[str] = Field(default_factory=list)
    fee_structure: Optional[Dict[str, Any]] = None
    budget_range: Optional[str] = None
    active: bool = True


class AuthRequest(BaseModel):
    """Authentication request"""
    user_id: str
    password: Optional[str] = None  # For future implementation
    session_token: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response"""
    user_id: str
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LawyerCreateRequest(BaseModel):
    """Request model for creating a new lawyer"""
    name: str = Field(..., description="Lawyer's full name")
    firm: str = Field(..., description="Law firm name")
    profile_summary: Optional[str] = Field(None, description="Brief professional summary")
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    practice_areas: List[str] = Field(default_factory=list, description="List of practice areas")
    specialties: List[Dict[str, Any]] = Field(default_factory=list, description="Specialized areas of expertise")
    education: List[Dict[str, Any]] = Field(default_factory=list, description="Educational background")
    professional_experience: Optional[str] = None
    years_of_experience: Optional[int] = None
    languages: List[str] = Field(default_factory=list, description="Languages spoken")
    payment_methods: List[str] = Field(default_factory=list, description="Accepted payment methods")
    phone_numbers: List[str] = Field(default_factory=list, description="Contact phone numbers")
    email: Optional[str] = None
    website: Optional[str] = None
    awards: List[str] = Field(default_factory=list, description="Professional awards and recognitions")
    associations: List[str] = Field(default_factory=list, description="Professional associations")
    fee_structure: Optional[Dict[str, Any]] = None
    budget_range: Optional[str] = Field(None, description="Budget range (e.g., '$', '$$', '$$$')")
    active: bool = Field(default=True, description="Whether the lawyer is actively practicing")


class LawyerCreateResponse(BaseModel):
    """Response model for lawyer creation"""
    id: str
    message: str = "Lawyer created successfully"


class CreateConversationRequest(BaseModel):
    """Request model for creating a new conversation"""
    initial_message: Optional[str] = Field(None, description="Optional initial message to start the conversation")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata about the conversation")


class CreateConversationResponse(BaseModel):
    """Response model for conversation creation"""
    conversation_id: str
    created_at: str
    message: str = "Conversation created successfully"
    websocket_url: Optional[str] = Field(None, description="WebSocket URL to connect to for this conversation")


class ConversationSummary(BaseModel):
    """Summary of a conversation"""
    conversation_id: str
    user_id: str
    created_at: str
    updated_at: str
    status: str = Field(default="active", description="active or archived")
    last_message: Optional[str] = None
    summary: Optional[str] = None
    message_count: int = 0
    average_distress_score: float = 5.0
    legal_topics: List[str] = Field(default_factory=list)


class ConversationsListResponse(BaseModel):
    """Response model for conversations list"""
    conversations: List[ConversationSummary]
    total: int
    limit: int
    offset: int


class ConversationMessage(BaseModel):
    """A single message in a conversation"""
    message_id: str
    turn_id: str
    timestamp: str
    role: str  # "user" or "assistant"
    content: str
    redacted: bool = False


class ConversationMessagesResponse(BaseModel):
    """Response model for conversation messages"""
    conversation_id: str
    messages: List[ConversationMessage]
    total: int
    limit: int
    offset: int