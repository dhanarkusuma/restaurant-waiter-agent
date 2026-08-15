from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.repositories.memory_repository import MemoryRepository
from apps.backend.app.repositories.menu_repository import MenuRepository


class CustomerMemoryService:
    VALID_MEMORY_TYPES = {"preference", "dislike", "dietary", "note"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_repo = MemoryRepository(db)
        self.menu_repo = MenuRepository(db)

    async def get_customer_profile(self, customer_id: int) -> dict[str, Any]:
        """
        Retrieve all persistent memory and favorites for a customer.
        """
        memories = await self.memory_repo.list_memories(customer_id)
        favorites = await self.memory_repo.list_favorites(customer_id)

        categorized_memories: dict[str, list[dict[str, Any]]] = {
            "preference": [],
            "dislike": [],
            "dietary": [],
            "note": [],
        }

        for m in memories:
            m_type = m.type.lower() if m.type.lower() in self.VALID_MEMORY_TYPES else "note"
            categorized_memories[m_type].append({
                "id": m.id,
                "description": m.description,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })

        formatted_favorites = [
            {
                "menu_id": f.menu_item_id,
                "name": f.menu_item.name if f.menu_item else "Unknown",
                "price": f.menu_item.price if f.menu_item else 0,
                "category": f.menu_item.category.name if f.menu_item and f.menu_item.category else None,
                "is_available": f.menu_item.is_available if f.menu_item else False,
                "description": f.menu_item.description if f.menu_item else None,
            }
            for f in favorites
        ]

        return {
            "customer_id": customer_id,
            "memories": categorized_memories,
            "favorites": formatted_favorites,
        }

    async def save_memory(
        self,
        customer_id: int,
        memory_type: str,
        description: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Save or update a customer memory while preventing duplicate equivalent entries.
        """
        cleaned_type = memory_type.strip().lower()
        if cleaned_type not in self.VALID_MEMORY_TYPES:
            cleaned_type = "note"

        cleaned_desc = description.strip()

        # Check if an equivalent memory already exists
        existing = await self.memory_repo.find_equivalent_memory(
            customer_id=customer_id,
            description=cleaned_desc,
            memory_type=cleaned_type,
        )

        if existing:
            updated = await self.memory_repo.update_memory(
                existing,
                description=cleaned_desc,
                metadata_json=metadata_json,
            )
            return {
                "status": "updated",
                "id": updated.id,
                "type": updated.type,
                "description": updated.description,
            }

        created = await self.memory_repo.create_memory(
            customer_id=customer_id,
            memory_type=cleaned_type,
            description=cleaned_desc,
            metadata_json=metadata_json,
        )
        return {
            "status": "created",
            "id": created.id,
            "type": created.type,
            "description": created.description,
        }

    async def forget_memory(self, customer_id: int, keyword: str) -> dict[str, Any]:
        """
        Delete customer memories matching a keyword or description.
        """
        deleted = await self.memory_repo.delete_memories_by_keyword(
            customer_id=customer_id,
            keyword=keyword,
        )
        return {
            "status": "deleted" if deleted else "not_found",
            "count": len(deleted),
            "deleted_descriptions": [m.description for m in deleted],
        }

    async def get_favorites(self, customer_id: int) -> list[dict[str, Any]]:
        """
        Retrieve the customer's persistent favorite menu items.
        """
        favorites = await self.memory_repo.list_favorites(customer_id)
        return [
            {
                "menu_id": f.menu_item_id,
                "name": f.menu_item.name if f.menu_item else "Unknown",
                "price": f.menu_item.price if f.menu_item else 0,
                "category": f.menu_item.category.name if f.menu_item and f.menu_item.category else None,
                "is_available": f.menu_item.is_available if f.menu_item else False,
                "description": f.menu_item.description if f.menu_item else None,
            }
            for f in favorites
        ]

    async def add_favorite(
        self,
        customer_id: int,
        menu_id: int | None = None,
        menu_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Add a menu item to the customer's favorites.
        Menu item is identifiable even if currently unavailable.
        """
        menu_item = None
        if menu_id is not None:
            menu_item = await self.menu_repo.get_by_id(menu_id)
        elif menu_name:
            menu_item = await self.menu_repo.get_by_name(menu_name)

        if not menu_item:
            target = f"'{menu_name}'" if menu_name else f"ID {menu_id}"
            return {"status": "error", "message": f"Menu {target} tidak ditemukan di daftar menu"}

        existing_fav = await self.memory_repo.get_favorite(customer_id, menu_item.id)
        if existing_fav:
            return {
                "status": "already_favorite",
                "menu_id": menu_item.id,
                "name": menu_item.name,
                "is_available": menu_item.is_available,
            }

        await self.memory_repo.add_favorite(customer_id, menu_item.id)
        return {
            "status": "added",
            "menu_id": menu_item.id,
            "name": menu_item.name,
            "is_available": menu_item.is_available,
        }

    async def remove_favorite(
        self,
        customer_id: int,
        menu_id: int | None = None,
        menu_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Remove a menu item from the customer's favorites.
        """
        menu_item = None
        if menu_id is not None:
            menu_item = await self.menu_repo.get_by_id(menu_id)
        elif menu_name:
            menu_item = await self.menu_repo.get_by_name(menu_name)

        if not menu_item:
            target = f"'{menu_name}'" if menu_name else f"ID {menu_id}"
            return {"status": "error", "message": f"Menu {target} tidak ditemukan di daftar menu"}

        removed = await self.memory_repo.remove_favorite(customer_id, menu_item.id)
        if removed:
            return {
                "status": "removed",
                "menu_id": menu_item.id,
                "name": menu_item.name,
            }
        return {
            "status": "not_in_favorites",
            "message": f"Menu '{menu_item.name}' tidak ada di daftar favorit Anda",
        }
