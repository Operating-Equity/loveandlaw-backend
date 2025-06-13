"""
Groq API client with retry logic and better error handling
"""
import asyncio
from typing import Optional
from groq import AsyncGroq
import httpx

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GroqClientWithRetry(AsyncGroq):
    """Groq client wrapper with retry logic and connection pooling"""
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, timeout: float = 30.0):
        # Initialize parent with custom settings
        super().__init__(
            api_key=api_key or settings.groq_api_key,
            timeout=httpx.Timeout(timeout, connect=10.0),
            max_retries=max_retries,  # Use built-in retry mechanism
            default_headers={
                "User-Agent": "loveandlaw-backend/1.0"
            }
        )
        
        # Override the httpx client to add custom retry logic for connection errors
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            transport=httpx.AsyncHTTPTransport(retries=3)
        )


# Global instance for reuse
_groq_client: Optional[GroqClientWithRetry] = None


def get_groq_client() -> GroqClientWithRetry:
    """Get or create a global Groq client instance"""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClientWithRetry()
    return _groq_client


async def test_groq_connection() -> bool:
    """Test if Groq API is accessible"""
    try:
        client = get_groq_client()
        response = await client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=[{"role": "user", "content": "Say 'test'"}],
            max_tokens=5,
            temperature=0
        )
        return response is not None
    except Exception as e:
        logger.error(f"Groq connection test failed: {e}")
        return False