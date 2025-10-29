"""
Health check endpoint for monitoring and load balancer integration.
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: datetime
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.

    Returns health status of the API service.

    Returns:
        Dictionary containing health status, timestamp, service name, and version
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "aurora-trader-api",
        "version": "0.1.0",
    }
