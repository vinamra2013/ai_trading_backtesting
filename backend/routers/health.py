# Health check router for FastAPI backend

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = "ok"


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for service monitoring.

    Returns:
        HealthResponse: Service health status
    """
    return HealthResponse(status="ok")
