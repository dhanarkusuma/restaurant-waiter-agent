from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.dependencies import get_current_admin
from apps.backend.app.database import get_db
from apps.backend.app.models import AdminUser
from apps.backend.app.schemas.admin import PopularMenuItemResponse, TableUsageResponse
from apps.backend.app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/admin/analytics", tags=["Admin Analytics"])


@router.get("/popular-menu", response_model=list[PopularMenuItemResponse])
async def get_popular_menu(
    limit: int = 10,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get most frequently ordered menu items with quantities and revenues."""
    service = AnalyticsService(db)
    return await service.get_popular_menu(limit=limit)


@router.get("/table-usage", response_model=list[TableUsageResponse])
async def get_table_usage(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get table usage frequencies and dining session counts."""
    service = AnalyticsService(db)
    return await service.get_table_usage()
