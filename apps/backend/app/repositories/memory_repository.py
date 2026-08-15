from typing import Any
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.app.models import CustomerFavorite, CustomerMemory, MenuItem


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Customer Memory ---

    async def list_memories(
        self,
        customer_id: int,
        memory_type: str | None = None,
    ) -> list[CustomerMemory]:
        stmt = select(CustomerMemory).where(CustomerMemory.customer_id == customer_id)
        if memory_type:
            stmt = stmt.where(CustomerMemory.type == memory_type)
        stmt = stmt.order_by(CustomerMemory.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_memory_by_id(self, memory_id: int, customer_id: int) -> CustomerMemory | None:
        result = await self.session.execute(
            select(CustomerMemory).where(
                and_(
                    CustomerMemory.id == memory_id,
                    CustomerMemory.customer_id == customer_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def find_equivalent_memory(
        self,
        customer_id: int,
        description: str,
        memory_type: str | None = None,
    ) -> CustomerMemory | None:
        """Find if a substantially similar memory already exists for this customer."""
        cleaned_desc = description.strip().lower()
        memories = await self.list_memories(customer_id=customer_id, memory_type=memory_type)
        for m in memories:
            existing_desc = m.description.strip().lower()
            if existing_desc == cleaned_desc or cleaned_desc in existing_desc or existing_desc in cleaned_desc:
                return m
        return None

    async def create_memory(
        self,
        customer_id: int,
        memory_type: str,
        description: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> CustomerMemory:
        memory = CustomerMemory(
            customer_id=customer_id,
            type=memory_type,
            description=description.strip(),
            metadata_json=metadata_json,
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def update_memory(
        self,
        memory: CustomerMemory,
        description: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> CustomerMemory:
        memory.description = description.strip()
        if metadata_json is not None:
            memory.metadata_json = metadata_json
        await self.session.flush()
        return memory

    async def delete_memory(self, memory: CustomerMemory) -> None:
        await self.session.delete(memory)
        await self.session.flush()

    async def delete_memories_by_keyword(self, customer_id: int, keyword: str) -> list[CustomerMemory]:
        """Delete memories matching a keyword for a customer."""
        memories = await self.list_memories(customer_id)
        deleted: list[CustomerMemory] = []
        kw = keyword.strip().lower()
        for m in memories:
            if kw in m.description.lower() or kw in m.type.lower():
                await self.session.delete(m)
                deleted.append(m)
        if deleted:
            await self.session.flush()
        return deleted

    # --- Customer Favorites ---

    async def list_favorites(self, customer_id: int) -> list[CustomerFavorite]:
        stmt = (
            select(CustomerFavorite)
            .where(CustomerFavorite.customer_id == customer_id)
            .options(
                selectinload(CustomerFavorite.menu_item).selectinload(MenuItem.category)
            )
            .order_by(CustomerFavorite.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_favorite(self, customer_id: int, menu_item_id: int) -> CustomerFavorite | None:
        result = await self.session.execute(
            select(CustomerFavorite).where(
                and_(
                    CustomerFavorite.customer_id == customer_id,
                    CustomerFavorite.menu_item_id == menu_item_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def add_favorite(self, customer_id: int, menu_item_id: int) -> CustomerFavorite:
        fav = CustomerFavorite(customer_id=customer_id, menu_item_id=menu_item_id)
        self.session.add(fav)
        await self.session.flush()
        return fav

    async def remove_favorite(self, customer_id: int, menu_item_id: int) -> bool:
        fav = await self.get_favorite(customer_id, menu_item_id)
        if fav:
            await self.session.delete(fav)
            await self.session.flush()
            return True
        return False
