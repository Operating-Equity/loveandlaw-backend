import uvicorn
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Main application entry point"""
    logger.info("Starting Love & Law Backend Services...")
    logger.info(f"API will be available at http://localhost:{settings.api_port}")
    logger.info(f"REST endpoints: http://localhost:{settings.api_port}/api/{settings.api_version}/")
    logger.info(f"WebSocket endpoint: ws://localhost:{settings.api_port}/ws")
    
    # Run the FastAPI server (which now includes WebSocket support)
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        log_level="info" if not settings.debug else "debug",
        reload=settings.debug
    )


if __name__ == "__main__":
    main()