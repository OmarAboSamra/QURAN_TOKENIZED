"""
Metadata and health check routes.

Provides lightweight endpoints for monitoring and service discovery:
    GET /meta/health  – Returns 200 if the server is running
    GET /meta/info    – Returns API title, version, description
"""
from fastapi import APIRouter, status
from pydantic import BaseModel

from backend.config import get_settings

router = APIRouter(prefix="/meta", tags=["Meta"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    message: str


class InfoResponse(BaseModel):
    """API information response model."""

    title: str
    version: str
    description: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        Health status information
    """
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.api_version,
        message="Qur'an Analysis API is running",
    )


@router.get(
    "/info",
    response_model=InfoResponse,
    status_code=status.HTTP_200_OK,
)
async def api_info() -> InfoResponse:
    """
    Get API information.
    
    Returns:
        API metadata and description
    """
    settings = get_settings()
    return InfoResponse(
        title=settings.api_title,
        version=settings.api_version,
        description=(
            "Production-ready backend for Qur'an analysis with tokenization, "
            "root extraction, and reference linking"
        ),
    )
