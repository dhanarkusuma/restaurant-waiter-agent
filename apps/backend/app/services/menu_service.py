from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.repositories.menu_repository import MenuRepository


class MenuService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.menu_repo = MenuRepository(db)

    async def search_menu(
        self,
        query: str | None = None,
        category_name: str | None = None,
        max_price: int | None = None,
        min_price: int | None = None,
        only_available: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Search available menu items with structured filtering (PostgreSQL source of truth).
        """
        items = await self.menu_repo.search(
            query=query,
            category_name=category_name,
            max_price=max_price,
            min_price=min_price,
            only_available=only_available,
        )

        return [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category.name if item.category else None,
                "price": item.price,
                "description": item.description,
                "is_available": item.is_available,
            }
            for item in items
        ]

    async def get_menu_details(self, item_id: int) -> dict[str, Any] | None:
        """
        Get single menu item details by ID.
        """
        item = await self.menu_repo.get_by_id(item_id)
        if not item:
            return None
        return {
            "id": item.id,
            "name": item.name,
            "category": item.category.name if item.category else None,
            "price": item.price,
            "description": item.description,
            "is_available": item.is_available,
        }

    async def list_categories(self) -> list[dict[str, Any]]:
        """
        List all menu categories.
        """
        categories = await self.menu_repo.list_categories()
        return [
            {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
            }
            for cat in categories
        ]
