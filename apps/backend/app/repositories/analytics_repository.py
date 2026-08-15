from typing import Any
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.models import DiningSession, MenuCategory, MenuItem, OrderItem, RestaurantTable


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_most_popular_menu_items(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Aggregate most frequently ordered menu items using PostgreSQL SUM(quantity).
        """
        stmt = (
            select(
                MenuItem.id.label("menu_item_id"),
                MenuItem.name.label("name"),
                MenuCategory.name.label("category"),
                func.coalesce(func.sum(OrderItem.quantity), 0).label("total_quantity_ordered"),
                func.coalesce(func.sum(OrderItem.subtotal), 0).label("total_revenue"),
            )
            .join(OrderItem, MenuItem.id == OrderItem.menu_item_id, isouter=True)
            .join(MenuCategory, MenuItem.category_id == MenuCategory.id, isouter=True)
            .group_by(MenuItem.id, MenuItem.name, MenuCategory.name)
            .order_by(desc("total_quantity_ordered"), MenuItem.name)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "menu_item_id": row.menu_item_id,
                "name": row.name,
                "category": row.category,
                "total_quantity_ordered": int(row.total_quantity_ordered),
                "total_revenue": int(row.total_revenue),
            }
            for row in result.all()
        ]

    async def get_table_usage(self) -> list[dict[str, Any]]:
        """
        Aggregate table usage frequency using PostgreSQL COUNT(DiningSession.id).
        """
        stmt = (
            select(
                RestaurantTable.id.label("table_id"),
                RestaurantTable.table_number.label("table_number"),
                RestaurantTable.capacity.label("capacity"),
                func.count(DiningSession.id).label("total_sessions"),
            )
            .join(DiningSession, RestaurantTable.id == DiningSession.table_id, isouter=True)
            .group_by(RestaurantTable.id, RestaurantTable.table_number, RestaurantTable.capacity)
            .order_by(desc("total_sessions"), RestaurantTable.table_number)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "table_id": row.table_id,
                "table_number": row.table_number,
                "capacity": row.capacity,
                "total_sessions": int(row.total_sessions),
            }
            for row in result.all()
        ]
