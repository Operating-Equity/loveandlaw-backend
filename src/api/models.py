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