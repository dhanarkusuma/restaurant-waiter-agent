from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.models import RestaurantTable, TableStatus


class TableRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, table_id: int) -> RestaurantTable | None:
        result = await self.session.execute(
            select(RestaurantTable).where(RestaurantTable.id == table_id)
        )
        return result.scalar_one_or_none()

    async def get_by_qr_token(self, qr_token: str, only_active: bool = True) -> RestaurantTable | None:
        stmt = select(RestaurantTable).where(RestaurantTable.qr_code_token == qr_token)
        if only_active:
            stmt = stmt.where(RestaurantTable.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_table_number(self, table_number: str) -> RestaurantTable | None:
        result = await self.session.execute(
            select(RestaurantTable).where(RestaurantTable.table_number == table_number)
        )
        return result.scalar_one_or_none()

    async def list_all(self, include_inactive: bool = True) -> list[RestaurantTable]:
        stmt = select(RestaurantTable).order_by(RestaurantTable.table_number)
        if not include_inactive:
            stmt = stmt.where(RestaurantTable.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        table_number: str,
        qr_code_token: str,
        capacity: int = 4,
        position_x: int = 0,
        position_y: int = 0,
        status: TableStatus = TableStatus.AVAILABLE,
    ) -> RestaurantTable:
        table = RestaurantTable(
            table_number=table_number,
            qr_code_token=qr_code_token,
            capacity=capacity,
            position_x=position_x,
            position_y=position_y,
            status=status,
            is_active=True,
        )
        self.session.add(table)
        await self.session.flush()
        return table

    async def update(
        self,
        table: RestaurantTable,
        table_number: str | None = None,
        capacity: int | None = None,
        position_x: int | None = None,
        position_y: int | None = None,
        is_active: bool | None = None,
    ) -> RestaurantTable:
        if table_number is not None:
            table.table_number = table_number.strip()
        if capacity is not None:
            table.capacity = capacity
        if position_x is not None:
            table.position_x = position_x
        if position_y is not None:
            table.position_y = position_y
        if is_active is not None:
            table.is_active = is_active
        await self.session.flush()
        return table

    async def update_status(self, table: RestaurantTable, status: TableStatus) -> RestaurantTable:
        table.status = status
        await self.session.flush()
        return table

    async def update_position(
        self,
        table: RestaurantTable,
        position_x: int,
        position_y: int,
    ) -> RestaurantTable:
        table.position_x = position_x
        table.position_y = position_y
        await self.session.flush()
        return table

    async def delete(self, table: RestaurantTable) -> None:
        await self.session.delete(table)
        await self.session.flush()
