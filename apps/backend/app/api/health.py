from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.config import settings
from apps.backend.app.database import get_db
from apps.backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic system health status."""
    return HealthResponse(
        status="ok",
        app="restaurant-waiter-agent",
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        database="ready",
    )


@router.get("/health/db", response_model=HealthResponse)
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """Database connectivity health check."""
    try:
        await db.execute(text("SELECT 1"))
        return HealthResponse(
            status="ok",
            app="restaurant-waiter-agent",
            version="0.1.0",
            environment=settings.ENVIRONMENT,
            database="connected",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        ) from e
