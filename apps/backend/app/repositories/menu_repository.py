from typing import Any
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.app.models import MenuCategory, MenuItem, OrderItem


class MenuRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, item_id: int) -> MenuItem | None:
        result = await self.session.execute(
            select(MenuItem)
            .where(MenuItem.id == item_id)
            .options(selectinload(MenuItem.category))
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> MenuItem | None:
        result = await self.session.execute(
            select(MenuItem)
            .where(MenuItem.name.ilike(f"%{name}%"))
            .options(selectinload(MenuItem.category))
        )
        return result.scalar_one_or_none()

    async def list_categories(self) -> list[MenuCategory]:
        result = await self.session.execute(select(MenuCategory).order_by(MenuCategory.name))
        return list(result.scalars().all())

    async def get_category_by_id(self, category_id: int) -> MenuCategory | None:
        result = await self.session.execute(
            select(MenuCategory).where(MenuCategory.id == category_id)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str | None = None,
        category_name: str | None = None,
        max_price: int | None = None,
        min_price: int | None = None,
        only_available: bool = True,
    ) -> list[MenuItem]:
        """
        Structured PostgreSQL query for menu items based on keyword, category, price, and availability.
        """
        stmt = select(MenuItem).options(selectinload(MenuItem.category))

        filters = []

        if only_available:
            filters.append(MenuItem.is_available == True)  # noqa: E712

        if query:
            search_term = f"%{query.strip()}%"
            filters.append(
                (MenuItem.name.ilike(search_term)) | (MenuItem.description.ilike(search_term))
            )

        if category_name:
            stmt = stmt.join(MenuItem.category)
            filters.append(MenuCategory.name.ilike(f"%{category_name.strip()}%"))

        if max_price is not None:
            filters.append(MenuItem.price <= max_price)

        if min_price is not None:
            filters.append(MenuItem.price >= min_price)

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(MenuItem.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all_admin(self, category_id: int | None = None) -> list[MenuItem]:
        """List all menu items for admin management (including unavailable)."""
        stmt = select(MenuItem).options(selectinload(MenuItem.category)).order_by(MenuItem.name)
        if category_id is not None:
            stmt = stmt.where(MenuItem.category_id == category_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_category(self, name: str, description: str | None = None) -> MenuCategory:
        category = MenuCategory(name=name, description=description)
        self.session.add(category)
        await self.session.flush()
        return category

    async def create_item(
        self,
        name: str,
        price: int,
        description: str | None = None,
        category_id: int | None = None,
        is_available: bool = True,
    ) -> MenuItem:
        item = MenuItem(
            name=name,
            price=price,
            description=description,
            category_id=category_id,
            is_available=is_available,
        )
        self.session.add(item)
        await self.session.flush()
        # Re-fetch with category loaded
        return await self.get_by_id(item.id) or item

    async def update_item(
        self,
        item: MenuItem,
        name: str | None = None,
        price: int | None = None,
        description: str | None = None,
        category_id: int | None = None,
        is_available: bool | None = None,
    ) -> MenuItem:
        if name is not None:
            item.name = name.strip()
        if price is not None:
            item.price = price
        if description is not None:
            item.description = description
        if category_id is not None:
            item.category_id = category_id
        if is_available is not None:
            item.is_available = is_available
        await self.session.flush()
        return await self.get_by_id(item.id) or item

    async def delete_or_deactivate_item(self, item: MenuItem) -> str:
        """
        Delete if never ordered, otherwise deactivate (is_available=False)
        to protect historical order integrity.
        """
        result = await self.session.execute(
            select(OrderItem).where(OrderItem.menu_item_id == item.id).limit(1)
        )
        has_orders = result.scalar_one_or_none() is not None

        if has_orders:
            item.is_available = False
            await self.session.flush()
            return "deactivated"
        else:
            await self.session.delete(item)
            await self.session.flush()
            return "deleted"
