import asyncio
import uvicorn
import websockets
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from src.config.settings import settings
from src.core.websocket_handler import chat_edge_service
from src.api.main import app
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def start_websocket_server():
    """Start the WebSocket server"""
    logger.info(f"Starting WebSocket server on port {settings.api_port + 1}")
    
    async with websockets.serve(
        chat_edge_service.handle_connection,
        "0.0.0.0",
        settings.api_port + 1,
        ping_interval=20,
        ping_timeout=10
    ):
        await asyncio.Future()  # Run forever


def run_api_server():
    """Run the FastAPI server"""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        log_level="info" if not settings.debug else "debug",
        reload=settings.debug
    )


async def main():
    """Main application entry point"""
    logger.info("Starting Love & Law Backend Services...")
    
    # Start WebSocket server in the background
    ws_task = asyncio.create_task(start_websocket_server())
    
    # Run API server in a thread (uvicorn handles its own event loop)
    import threading
    api_thread = threading.Thread(target=run_api_server)
    api_thread.start()
    
    # Keep WebSocket server running
    try:
        await ws_task
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    # Run the application
    asyncio.run(main())