from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import csv
import io
import json
import asyncio
from typing import Dict, Any, List
from uuid import uuid4
from datetime import datetime

from src.config.settings import settings
from src.services.database import initialize_databases, close_databases, elasticsearch_service, dynamodb_service
from src.api.models import MatchRequest, LawyerUploadResponse, ProfileResponse, ProfileUpdateRequest, LawyerDetailsResponse
from src.api.auth import get_current_user
from src.api.websocket_internal import router as websocket_internal_router
from src.utils.logger import get_logger
from src.core.therapeutic_engine import therapeutic_engine
from src.services.pii_redaction import pii_service

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

# Include internal WebSocket router
app.include_router(websocket_internal_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "healthy",
        "service": "Love & Law Backend",
        "version": "1.0.0",
        "environment": settings.environment
    }


@app.get("/health")
async def health():
    """Health check endpoint for ALB/ECS"""
    return {
        "status": "healthy",
        "service": "Love & Law Backend",
        "version": "1.0.0",
        "environment": settings.environment
    }


@app.get(f"/api/{settings.api_version}/health")
async def api_health():
    """API health check endpoint"""
    # Check database connectivity
    health_status = {
        "status": "healthy",
        "service": "Love & Law Backend API",
        "version": "1.0.0",
        "environment": settings.environment,
        "checks": {
            "elasticsearch": "unknown",
            "dynamodb": "unknown",
            "redis": "unknown"
        }
    }
    
    # Check Elasticsearch
    try:
        if elasticsearch_service.client:
            await elasticsearch_service.client.ping()
            health_status["checks"]["elasticsearch"] = "healthy"
        else:
            health_status["checks"]["elasticsearch"] = "not_configured"
    except Exception as e:
        health_status["checks"]["elasticsearch"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check DynamoDB
    try:
        if dynamodb_service.conversations_table and dynamodb_service.profiles_table:
            health_status["checks"]["dynamodb"] = "healthy"
        else:
            health_status["checks"]["dynamodb"] = "not_configured"
    except Exception as e:
        health_status["checks"]["dynamodb"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Redis is optional
    health_status["checks"]["redis"] = "not_implemented"
    
    return health_status


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
            "name": profile.get("name"),
            "email": profile.get("email"),
            "preferred_avatar": profile.get("preferred_avatar"),
            "saved_lawyers": profile.get("saved_lawyers", []),
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


@app.put(f"/api/{settings.api_version}/profile/{{user_id}}")
async def update_profile(
    user_id: str,
    profile_update: ProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ProfileResponse:
    """Update user profile"""
    
    # Check authorization
    if current_user["user_id"] != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    try:
        # Get existing profile first
        existing_profile = await dynamodb_service.get_user_profile(user_id)
        
        if not existing_profile:
            # Create new profile if it doesn't exist
            existing_profile = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        
        # Prepare updates (only include non-None values)
        updates = {k: v for k, v in profile_update.dict().items() if v is not None}
        updates["user_id"] = user_id  # Ensure user_id is set
        
        # Update the profile
        await dynamodb_service.update_user_profile(user_id, updates)
        
        # Fetch the updated profile
        updated_profile = await dynamodb_service.get_user_profile(user_id)
        
        if not updated_profile:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated profile")
        
        # Sanitize sensitive data
        sanitized_profile = {
            "user_id": updated_profile["user_id"],
            "created_at": updated_profile["created_at"],
            "updated_at": updated_profile["updated_at"],
            "name": updated_profile.get("name"),
            "email": updated_profile.get("email"),
            "preferred_avatar": updated_profile.get("preferred_avatar"),
            "saved_lawyers": updated_profile.get("saved_lawyers", []),
            "legal_situation": updated_profile.get("legal_situation", {}),
            "milestones_completed": updated_profile.get("milestones_completed", []),
            "current_goals": updated_profile.get("current_goals", []),
            "preferences": updated_profile.get("preferences", {}),
            "average_distress_score": updated_profile.get("average_distress_score", 5.0),
            "average_engagement_level": updated_profile.get("average_engagement_level", 5.0)
        }
        
        return ProfileResponse(profile=sanitized_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Error updating profile")


@app.get(f"/api/{settings.api_version}/lawyers/{{lawyer_id}}")
async def get_lawyer_details(
    lawyer_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> LawyerDetailsResponse:
    """Get detailed information about a specific lawyer by ID"""
    try:
        # Fetch lawyer data from Elasticsearch
        lawyer_data = await elasticsearch_service.get_lawyer_by_id(lawyer_id)
        
        if not lawyer_data:
            raise HTTPException(status_code=404, detail="Lawyer not found")
        
        # Convert to response model
        response = LawyerDetailsResponse(
            id=lawyer_data.get("id"),
            name=lawyer_data.get("name", ""),
            firm=lawyer_data.get("firm"),
            profile_summary=lawyer_data.get("profile_summary"),
            city=lawyer_data.get("city"),
            state=lawyer_data.get("state"),
            location=lawyer_data.get("location"),
            practice_areas=lawyer_data.get("practice_areas", []),
            specialties=lawyer_data.get("specialties", []),
            education=lawyer_data.get("education", []),
            professional_experience=lawyer_data.get("professional_experience"),
            years_of_experience=lawyer_data.get("years_of_experience"),
            languages=lawyer_data.get("languages", []),
            payment_methods=lawyer_data.get("payment_methods", []),
            ratings=lawyer_data.get("ratings"),
            reviews=lawyer_data.get("reviews", []),
            phone_numbers=lawyer_data.get("phone_numbers", []),
            email=lawyer_data.get("email"),
            website=lawyer_data.get("website"),
            awards=lawyer_data.get("awards", []),
            associations=lawyer_data.get("associations", []),
            fee_structure=lawyer_data.get("fee_structure"),
            budget_range=lawyer_data.get("budget_range"),
            active=lawyer_data.get("active", True)
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lawyer details: {e}")
        raise HTTPException(status_code=500, detail="Error fetching lawyer details")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat interactions"""
    connection_id = str(uuid4())
    user_id = None
    conversation_id = None
    authenticated = False
    
    await websocket.accept()
    logger.info(f"New WebSocket connection: {connection_id}")
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection_established",
            "connection_id": connection_id,
            "message": "Connected to Love & Law Assistant"
        })
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
        
        while True:
            try:
                # Receive message
                message = await websocket.receive_json()
                msg_type = message.get("type")
                
                # Handle authentication
                if msg_type == "auth":
                    user_id = message.get("user_id")
                    if not user_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "User ID required"
                        })
                        continue
                    
                    authenticated = True
                    conversation_id = message.get("conversation_id") or str(uuid4())
                    
                    await websocket.send_json({
                        "type": "auth_success",
                        "user_id": user_id,
                        "conversation_id": conversation_id
                    })
                
                # Handle user messages
                elif msg_type == "user_msg":
                    if not authenticated and not settings.debug:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Not authenticated"
                        })
                        continue
                    
                    # In debug mode, auto-authenticate
                    if settings.debug and not authenticated:
                        user_id = "debug_user"
                        conversation_id = str(uuid4())
                        authenticated = True
                    
                    cid = message.get("cid", str(uuid4()))
                    user_text = message.get("text", "").strip()
                    
                    if not user_text:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Empty message"
                        })
                        continue
                    
                    # Acknowledge receipt
                    await websocket.send_json({
                        "type": "message_received",
                        "cid": cid
                    })
                    
                    # Redact PII
                    redacted_text, found_pii = await pii_service.redact_text(user_text)
                    
                    if found_pii:
                        logger.info(f"PII detected and redacted: {list(found_pii.keys())}")
                    
                    # Process through therapeutic engine
                    result = await therapeutic_engine.process_turn(
                        user_id=user_id,
                        user_text=redacted_text,
                        conversation_id=conversation_id
                    )
                    
                    # Stream response
                    await stream_response(websocket, cid, result)
                
                # Handle heartbeat
                elif msg_type == "heartbeat":
                    await websocket.send_json({"type": "heartbeat"})
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}"
                    })
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)
                error_msg = str(e) if settings.debug else "Error processing message"
                await websocket.send_json({
                    "type": "error",
                    "message": error_msg
                })
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Cancel heartbeat
        heartbeat_task.cancel()
        logger.info(f"WebSocket connection closed: {connection_id}")


async def send_heartbeat(websocket: WebSocket):
    """Send periodic heartbeat messages"""
    try:
        while True:
            await asyncio.sleep(settings.ws_heartbeat_interval)
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")


async def stream_response(websocket: WebSocket, cid: str, result: Dict[str, Any]):
    """Stream AI response to client"""
    
    # Simulate streaming by chunking the response
    response_text = result["assistant_response"]
    chunk_size = 20  # Characters per chunk
    
    # Send response in chunks
    for i in range(0, len(response_text), chunk_size):
        chunk = response_text[i:i + chunk_size]
        await websocket.send_json({
            "type": "ai_chunk",
            "cid": cid,
            "text_fragment": chunk
        })
        await asyncio.sleep(0.05)  # Simulate typing
    
    # Send completion marker
    await websocket.send_json({
        "type": "ai_complete",
        "cid": cid
    })
    
    # Send lawyer cards if available
    logger.info(f"Lawyer cards check: has_cards={bool(result.get('lawyer_cards'))}, "
                f"distress_score={result['metrics']['distress_score']}, "
                f"num_cards={len(result.get('lawyer_cards', []))}")
    
    if result.get("lawyer_cards") and result["metrics"]["distress_score"] < 7:
        await websocket.send_json({
            "type": "cards",
            "cid": cid,
            "cards": result["lawyer_cards"]
        })
    
    # Send reflection data if needed
    if result.get("reflection", {}).get("needs_reflection"):
        await websocket.send_json({
            "type": "reflection",
            "cid": cid,
            "reflection_type": result["reflection"]["reflection_type"],
            "reflection_insights": result["reflection"]["reflection_insights"]
        })
    
    # Send suggestions
    if result.get("suggestions"):
        await websocket.send_json({
            "type": "suggestions",
            "cid": cid,
            "suggestions": result["suggestions"]
        })
    
    # Send metrics (for debugging/monitoring)
    if settings.debug:
        metrics = result["metrics"].copy()
        # Add legal routing info
        if result.get("legal_intent"):
            metrics["legal_intent"] = result["legal_intent"]
        if result.get("active_legal_specialist"):
            metrics["active_legal_specialist"] = result["active_legal_specialist"]
            
        await websocket.send_json({
            "type": "metrics",
            "cid": cid,
            "metrics": metrics
        })


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )