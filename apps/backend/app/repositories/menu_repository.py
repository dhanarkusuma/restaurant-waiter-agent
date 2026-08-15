from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.app.models import MenuCategory, MenuItem


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
        result = await self.session.execute(select(MenuCategory))
        return list(result.scalars().all())

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
        return item
