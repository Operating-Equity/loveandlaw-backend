#!/usr/bin/env python3
"""
Minimal startup script for LoveAndLaw backend
This bypasses some dependencies to get the API running quickly
"""
import asyncio
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set minimal required environment variables if not present
if not os.getenv("GROQ_API_KEY"):
    print("Warning: GROQ_API_KEY not set. Using placeholder.")
    os.environ["GROQ_API_KEY"] = "placeholder_key"

if not os.getenv("JWT_SECRET_KEY"):
    print("Warning: JWT_SECRET_KEY not set. Using development key.")
    os.environ["JWT_SECRET_KEY"] = "development_secret_key_not_for_production"

# Disable some optional services
os.environ["SKIP_AWS_INIT"] = "true"
os.environ["SKIP_REDIS_INIT"] = "true"

async def main():
    """Run only the FastAPI server"""
    print("Starting LoveAndLaw Backend in minimal mode...")
    print("This will run only the REST API on port 8000")
    print("WebSocket service and some features will be disabled")
    print("\nTo test the API:")
    print("- Health check: http://localhost:8000/")
    print("- API docs: http://localhost:8000/docs")
    
    # Run only the FastAPI server
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )

if __name__ == "__main__":
    asyncio.run(main())