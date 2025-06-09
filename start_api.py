#!/usr/bin/env python3
"""Simple API startup script"""
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from src.config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        log_level="info",
        reload=False  # Disable reload to avoid thread issues
    )