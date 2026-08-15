from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.repositories.analytics_repository import AnalyticsRepository


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_repo = AnalyticsRepository(db)

    async def get_popular_menu(self, limit: int = 10) -> list[dict[str, Any]]:
        return await self.analytics_repo.get_most_popular_menu_items(limit=limit)

    async def get_table_usage(self) -> list[dict[str, Any]]:
        return await self.analytics_repo.get_table_usage()
