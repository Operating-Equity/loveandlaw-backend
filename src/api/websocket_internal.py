"""
Internal endpoints for Lambda WebSocket proxy
These endpoints are only accessible from within the VPC
"""
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import json
from datetime import datetime

from src.core.therapeutic_engine import therapeutic_engine
from src.services.pii_redaction import pii_service
from src.utils.logger import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

# Router for internal WebSocket endpoints
router = APIRouter(prefix="/internal/websocket", tags=["internal", "websocket"])

# Models for internal communication
class WebSocketMessage(BaseModel):
    connectionId: str
    type: str
    cid: Optional[str] = None
    text: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    requestContext: Optional[Dict[str, Any]] = None

class WebSocketDisconnect(BaseModel):
    connectionId: str

class WebSocketResponse(BaseModel):
    messages: Optional[List[Dict[str, Any]]] = None
    message: Optional[Dict[str, Any]] = None

# In-memory storage for active connections (for development)
# In production, this should use Redis or DynamoDB
active_connections: Dict[str, Dict[str, Any]] = {}

@router.post("/message", response_model=WebSocketResponse)
async def handle_websocket_message(message: WebSocketMessage) -> WebSocketResponse:
    """Handle WebSocket message forwarded from Lambda"""
    
    connection_id = message.connectionId
    messages_to_send = []
    
    try:
        # Handle authentication
        if message.type == "auth":
            user_id = message.user_id
            if not user_id:
                return WebSocketResponse(message={
                    "type": "error",
                    "message": "User ID required"
                })
            
            # Store connection info
            active_connections[connection_id] = {
                "user_id": user_id,
                "conversation_id": message.conversation_id,
                "authenticated": True
            }
            
            return WebSocketResponse(message={
                "type": "auth_success",
                "user_id": user_id,
                "conversation_id": message.conversation_id
            })
        
        # Handle user messages
        elif message.type == "user_msg":
            # Check authentication
            conn_info = active_connections.get(connection_id, {})
            
            if not conn_info.get("authenticated") and not settings.debug:
                return WebSocketResponse(message={
                    "type": "error",
                    "message": "Not authenticated"
                })
            
            # Auto-authenticate in debug mode
            if settings.debug and not conn_info.get("authenticated"):
                conn_info = {
                    "user_id": "debug_user",
                    "conversation_id": message.conversation_id or "debug_conversation",
                    "authenticated": True
                }
                active_connections[connection_id] = conn_info
            
            user_text = message.text or ""
            if not user_text.strip():
                return WebSocketResponse(message={
                    "type": "error",
                    "message": "Empty message"
                })
            
            # Acknowledge receipt
            messages_to_send.append({
                "type": "message_received",
                "cid": message.cid
            })
            
            # Redact PII
            redacted_text, found_pii = await pii_service.redact_text(user_text)
            
            if found_pii:
                logger.info(f"PII detected and redacted: {list(found_pii.keys())}")
            
            # Process through therapeutic engine
            result = await therapeutic_engine.process_turn(
                user_id=conn_info["user_id"],
                user_text=redacted_text,
                conversation_id=conn_info["conversation_id"]
            )
            
            # Format response messages
            response_text = result["assistant_response"]
            chunk_size = 20
            
            # Stream response in chunks
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                messages_to_send.append({
                    "type": "ai_chunk",
                    "cid": message.cid,
                    "text_fragment": chunk
                })
            
            # Send completion marker
            messages_to_send.append({
                "type": "ai_complete",
                "cid": message.cid
            })
            
            # Send lawyer cards if available
            if result.get("lawyer_cards") and result["metrics"]["distress_score"] < 7:
                messages_to_send.append({
                    "type": "cards",
                    "cid": message.cid,
                    "cards": result["lawyer_cards"]
                })
            
            # Send reflection data if needed
            if result.get("reflection", {}).get("needs_reflection"):
                messages_to_send.append({
                    "type": "reflection",
                    "cid": message.cid,
                    "reflection_type": result["reflection"]["reflection_type"],
                    "reflection_insights": result["reflection"]["reflection_insights"]
                })
            
            # Send suggestions
            if result.get("suggestions"):
                messages_to_send.append({
                    "type": "suggestions",
                    "cid": message.cid,
                    "suggestions": result["suggestions"]
                })
            
            # Send metrics in debug mode
            if settings.debug:
                messages_to_send.append({
                    "type": "metrics",
                    "cid": message.cid,
                    "metrics": jsonable_encoder(result["metrics"])
                })
            
            # Ensure all messages are JSON-serializable
            messages_to_send = jsonable_encoder(messages_to_send)
            return WebSocketResponse(messages=messages_to_send)
        
        # Handle heartbeat
        elif message.type == "heartbeat":
            return WebSocketResponse(message={"type": "heartbeat"})
        
        else:
            return WebSocketResponse(message={
                "type": "error",
                "message": f"Unknown message type: {message.type}"
            })
            
    except Exception as e:
        logger.error(f"Error processing WebSocket message: {e}")
        return WebSocketResponse(message={
            "type": "error",
            "message": "Error processing message"
        })

@router.post("/disconnect")
async def handle_websocket_disconnect(disconnect: WebSocketDisconnect):
    """Handle WebSocket disconnection notification from Lambda"""
    
    connection_id = disconnect.connectionId
    
    # Clean up connection info
    if connection_id in active_connections:
        del active_connections[connection_id]
        logger.info(f"Cleaned up connection: {connection_id}")
    
    return {"status": "ok"}

@router.get("/health")
async def websocket_health():
    """Health check for WebSocket internal endpoints"""
    return {
        "status": "healthy",
        "active_connections": len(active_connections)
    }