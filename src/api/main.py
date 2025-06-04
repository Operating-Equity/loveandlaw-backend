from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import csv
import io
from typing import Dict, Any, List

from src.config.settings import settings
from src.services.database import initialize_databases, close_databases, elasticsearch_service, dynamodb_service
from src.api.models import MatchRequest, LawyerUploadResponse, ProfileResponse
from src.api.auth import get_current_user
from src.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting up Love & Law Backend...")
    await initialize_databases()
    logger.info("Databases initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await close_databases()
    logger.info("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Love & Law Conversational API",
    version="1.0.0",
    description="Therapeutic family law assistant backend",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Love & Law Backend",
        "version": "1.0.0",
        "environment": settings.environment
    }


@app.post(f"/api/{settings.api_version}/match")
async def match_lawyers(
    request: MatchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Match lawyers based on user criteria"""
    try:
        # Build search query
        query = {
            "zip": request.facts.get("zip"),
            "practice_areas": request.facts.get("practice_areas", []),
            "budget_range": request.facts.get("budget_range"),
            "text": request.facts.get("search_text", "")
        }
        
        # Remove None values
        query = {k: v for k, v in query.items() if v is not None}
        
        # Search lawyers
        lawyers = await elasticsearch_service.search_lawyers(query, size=request.limit)
        
        # Format response
        cards = []
        for lawyer in lawyers:
            cards.append({
                "id": lawyer["id"],
                "name": lawyer["name"],
                "firm": lawyer["firm"],
                "match_score": lawyer["match_score"],
                "blurb": lawyer.get("description", "")[:200],
                "link": f"/lawyer/{lawyer['id']}",
                "practice_areas": lawyer.get("practice_areas", []),
                "location": lawyer.get("location", {}),
                "rating": lawyer.get("rating"),
                "reviews_count": lawyer.get("reviews_count"),
                "budget_range": lawyer.get("budget_range")
            })
        
        return {"cards": cards}
        
    except Exception as e:
        logger.error(f"Error matching lawyers: {e}")
        raise HTTPException(status_code=500, detail="Error matching lawyers")


@app.post(f"/api/{settings.api_version}/lawyers/upload")
async def upload_lawyers(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> LawyerUploadResponse:
    """Upload lawyers via CSV file (admin only)"""
    
    # Check admin permissions
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")
    
    try:
        # Read CSV
        contents = await file.read()
        csv_data = io.StringIO(contents.decode('utf-8'))
        reader = csv.DictReader(csv_data)
        
        # Process lawyers
        indexed_count = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Validate required fields
                required_fields = ["id", "name", "firm"]
                missing_fields = [f for f in required_fields if not row.get(f)]
                
                if missing_fields:
                    errors.append(f"Row {row_num}: Missing fields {missing_fields}")
                    continue
                
                # Build lawyer document
                lawyer = {
                    "id": row["id"],
                    "name": row["name"],
                    "firm": row["firm"],
                    "practice_areas": [a.strip() for a in row.get("practice_areas", "").split(",") if a.strip()],
                    "location": {
                        "zip": row.get("zip", ""),
                        "city": row.get("city", ""),
                        "state": row.get("state", "")
                    },
                    "description": row.get("description", ""),
                    "budget_range": row.get("budget_range", ""),
                    "rating": float(row.get("rating", 0)) if row.get("rating") else None,
                    "reviews_count": int(row.get("reviews_count", 0)) if row.get("reviews_count") else None
                }
                
                # Index in Elasticsearch
                await elasticsearch_service.index_lawyer(lawyer)
                indexed_count += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        return LawyerUploadResponse(
            status="completed",
            indexed_count=indexed_count,
            errors=errors[:10]  # Limit errors in response
        )
        
    except Exception as e:
        logger.error(f"Error uploading lawyers: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


@app.get(f"/api/{settings.api_version}/profile/{{user_id}}")
async def get_profile(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ProfileResponse:
    """Get user profile"""
    
    # Check authorization
    if current_user["user_id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        profile = await dynamodb_service.get_user_profile(user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Sanitize sensitive data
        sanitized_profile = {
            "user_id": profile["user_id"],
            "created_at": profile["created_at"],
            "updated_at": profile["updated_at"],
            "legal_situation": profile.get("legal_situation", {}),
            "milestones_completed": profile.get("milestones_completed", []),
            "current_goals": profile.get("current_goals", []),
            "preferences": profile.get("preferences", {}),
            "average_distress_score": profile.get("average_distress_score", 5.0),
            "average_engagement_level": profile.get("average_engagement_level", 5.0)
        }
        
        return ProfileResponse(profile=sanitized_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail="Error fetching profile")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )