import json
import asyncio
from typing import Dict, Any, Optional, Set
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol
from uuid import uuid4

from src.core.therapeutic_engine import therapeutic_engine
from src.services.pii_redaction import pii_service
from src.models.conversation import WebSocketMessage
from src.utils.logger import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


class WebSocketConnection:
    """Manages a single WebSocket connection"""
    
    def __init__(self, websocket: WebSocketServerProtocol, connection_id: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id: Optional[str] = None
        self.conversation_id: Optional[str] = None
        self.authenticated: bool = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.last_activity: datetime = datetime.utcnow()
    
    async def start_heartbeat(self):
        """Start heartbeat to keep connection alive"""
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        try:
            while True:
                await asyncio.sleep(settings.ws_heartbeat_interval)
                await self.send_message({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message to client"""
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def close(self):
        """Clean up connection"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        await self.websocket.close()


class ChatEdgeService:
    """WebSocket server for chat interactions"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        connection_id = str(uuid4())
        connection = WebSocketConnection(websocket, connection_id)
        self.connections[connection_id] = connection
        
        logger.info(f"New connection: {connection_id}")
        
        try:
            # Start heartbeat
            await connection.start_heartbeat()
            
            # Send welcome message
            await connection.send_message({
                "type": "connection_established",
                "connection_id": connection_id,
                "message": "Connected to Love & Law Assistant"
            })
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(connection, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            await connection.send_message({
                "type": "error",
                "message": "An error occurred processing your request"
            })
        finally:
            # Clean up
            await self._cleanup_connection(connection)
    
    async def _handle_message(self, connection: WebSocketConnection, raw_message: str):
        """Process incoming message"""
        try:
            message = json.loads(raw_message)
            msg_type = message.get("type")
            
            # Update last activity
            connection.last_activity = datetime.utcnow()
            
            # Route based on message type
            if msg_type == "auth":
                await self._handle_auth(connection, message)
            elif msg_type == "user_msg":
                await self._handle_user_message(connection, message)
            elif msg_type == "heartbeat":
                # Echo heartbeat
                await connection.send_message({"type": "heartbeat"})
            else:
                await connection.send_message({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
                
        except json.JSONDecodeError:
            await connection.send_message({
                "type": "error",
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await connection.send_message({
                "type": "error",
                "message": "Error processing message"
            })
    
    async def _handle_auth(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """Handle authentication"""
        # For now, simple auth - in production would validate JWT
        user_id = message.get("user_id")
        if not user_id:
            await connection.send_message({
                "type": "error",
                "message": "User ID required"
            })
            return
        
        connection.user_id = user_id
        connection.authenticated = True
        connection.conversation_id = message.get("conversation_id") or str(uuid4())
        
        # Track user connection
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection.connection_id)
        
        await connection.send_message({
            "type": "auth_success",
            "user_id": user_id,
            "conversation_id": connection.conversation_id
        })
    
    async def _handle_user_message(self, connection: WebSocketConnection, message: Dict[str, Any]):
        """Handle user chat message"""
        # In development mode, auto-authenticate if not authenticated
        if settings.environment == "development" and not connection.authenticated:
            # Auto-authenticate with a default user_id
            connection.user_id = message.get("user_id", "dev-user-" + connection.connection_id[:8])
            connection.authenticated = True
            connection.conversation_id = str(uuid4())
            logger.info(f"Development mode: Auto-authenticated user {connection.user_id}")
        
        if not connection.authenticated:
            await connection.send_message({
                "type": "error",
                "message": "Not authenticated"
            })
            return
        
        cid = message.get("cid", str(uuid4()))
        user_text = message.get("text", "").strip()
        
        if not user_text:
            await connection.send_message({
                "type": "error",
                "message": "Empty message"
            })
            return
        
        try:
            # Acknowledge receipt
            await connection.send_message({
                "type": "message_received",
                "cid": cid
            })
            
            # Redact PII
            redacted_text, found_pii = await pii_service.redact_text(user_text)
            
            # Log PII detection
            if found_pii:
                logger.info(f"PII detected and redacted: {list(found_pii.keys())}")
            
            # Process through therapeutic engine
            result = await therapeutic_engine.process_turn(
                user_id=connection.user_id,
                user_text=redacted_text,
                conversation_id=connection.conversation_id
            )
            
            # Validate result structure
            if not result or not isinstance(result, dict):
                raise ValueError("Invalid response from therapeutic engine")
            
            # Log the result for debugging
            logger.info(f"Therapeutic engine result keys: {list(result.keys())}")
            logger.info(f"Assistant response present: {'assistant_response' in result}")
            if "assistant_response" in result:
                logger.info(f"Assistant response length: {len(result['assistant_response'])}")
                logger.info(f"Assistant response preview: {result['assistant_response'][:100]}...")
            
            # The therapeutic engine should ALWAYS provide a response
            # If it doesn't, there's a bug that needs fixing
            if "assistant_response" not in result:
                logger.error("Therapeutic engine did not provide assistant_response")
                raise ValueError("Therapeutic engine failed to generate response")
            
            if "metrics" not in result:
                logger.error("Therapeutic engine did not provide metrics")
                raise ValueError("Therapeutic engine failed to generate metrics")
            
            # Stream response
            await self._stream_response(connection, cid, result)
            
        except Exception as e:
            logger.error(f"Error processing user message: {e}", exc_info=True)
            error_msg = str(e) if settings.debug else "Error processing your message. Please try again."
            await connection.send_message({
                "type": "error",
                "cid": cid,
                "message": error_msg
            })
    
    async def _stream_response(self, connection: WebSocketConnection, cid: str, result: Dict[str, Any]):
        """Stream AI response to client"""
        
        # Simulate streaming by chunking the response
        response_text = result.get("assistant_response", "")
        logger.info(f"Streaming response of length {len(response_text)}")
        
        if not response_text:
            logger.error("No assistant_response to stream!")
            return
            
        chunk_size = 20  # Characters per chunk
        
        # Send response in chunks
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            logger.debug(f"Sending chunk {i//chunk_size + 1}: {chunk}")
            await connection.send_message({
                "type": "ai_chunk",
                "cid": cid,
                "text": chunk
            })
            await asyncio.sleep(0.05)  # Simulate typing
        
        # Send completion marker
        await connection.send_message({
            "type": "ai_complete",
            "cid": cid
        })
        
        # Send lawyer cards if available
        if result.get("lawyer_cards") and result["metrics"]["distress_score"] < 7:
            await connection.send_message({
                "type": "cards",
                "cid": cid,
                "cards": result["lawyer_cards"]
            })
        
        # Send reflection data if needed
        if result.get("reflection", {}).get("needs_reflection"):
            await connection.send_message({
                "type": "reflection",
                "cid": cid,
                "reflection_type": result["reflection"]["reflection_type"],
                "reflection_insights": result["reflection"]["reflection_insights"]
            })
        
        # Send suggestions
        if result.get("suggestions"):
            await connection.send_message({
                "type": "suggestions",
                "cid": cid,
                "suggestions": result["suggestions"]
            })
        
        # Send metrics (for debugging/monitoring)
        if settings.debug:
            await connection.send_message({
                "type": "metrics",
                "cid": cid,
                "metrics": result["metrics"]
            })
    
    async def _cleanup_connection(self, connection: WebSocketConnection):
        """Clean up disconnected connection"""
        connection_id = connection.connection_id
        
        # Remove from connections
        if connection_id in self.connections:
            del self.connections[connection_id]
        
        # Remove from user connections
        if connection.user_id and connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]
        
        # Cancel heartbeat
        if connection.heartbeat_task:
            connection.heartbeat_task.cancel()
        
        logger.info(f"Cleaned up connection: {connection_id}")


# Global instance
chat_edge_service = ChatEdgeService()