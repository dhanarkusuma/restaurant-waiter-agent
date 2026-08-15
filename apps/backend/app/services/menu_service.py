from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.models import MenuItem
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

    # --- Admin Operations ---

    async def list_all_admin(self, category_id: int | None = None) -> list[dict[str, Any]]:
        items = await self.menu_repo.list_all_admin(category_id=category_id)
        return [
            {
                "id": it.id,
                "category_id": it.category_id,
                "category_name": it.category.name if it.category else None,
                "name": it.name,
                "description": it.description,
                "price": it.price,
                "is_available": it.is_available,
                "created_at": it.created_at,
                "updated_at": it.updated_at,
            }
            for it in items
        ]

    async def create_category(self, name: str, description: str | None = None) -> dict[str, Any]:
        cat = await self.menu_repo.create_category(name=name, description=description)
        return {"id": cat.id, "name": cat.name, "description": cat.description}

    async def create_menu_item(
        self,
        name: str,
        price: int,
        category_id: int | None = None,
        description: str | None = None,
        is_available: bool = True,
    ) -> dict[str, Any]:
        item = await self.menu_repo.create_item(
            name=name,
            price=price,
            category_id=category_id,
            description=description,
            is_available=is_available,
        )
        return {
            "id": item.id,
            "category_id": item.category_id,
            "category_name": item.category.name if item.category else None,
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "is_available": item.is_available,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    async def update_menu_item(
        self,
        item_id: int,
        name: str | None = None,
        price: int | None = None,
        category_id: int | None = None,
        description: str | None = None,
        is_available: bool | None = None,
    ) -> dict[str, Any] | None:
        item = await self.menu_repo.get_by_id(item_id)
        if not item:
            return None

        updated = await self.menu_repo.update_item(
            item,
            name=name,
            price=price,
            category_id=category_id,
            description=description,
            is_available=is_available,
        )
        return {
            "id": updated.id,
            "category_id": updated.category_id,
            "category_name": updated.category.name if updated.category else None,
            "name": updated.name,
            "description": updated.description,
            "price": updated.price,
            "is_available": updated.is_available,
            "created_at": updated.created_at,
            "updated_at": updated.updated_at,
        }

    async def set_item_availability(self, item_id: int, is_available: bool) -> dict[str, Any] | None:
        return await self.update_menu_item(item_id=item_id, is_available=is_available)

    async def delete_or_deactivate_item(self, item_id: int) -> dict[str, Any] | None:
        item = await self.menu_repo.get_by_id(item_id)
        if not item:
            return None
        action = await self.menu_repo.delete_or_deactivate_item(item)
        return {"id": item_id, "action": action}
