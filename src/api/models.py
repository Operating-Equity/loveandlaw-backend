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