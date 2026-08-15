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

    async def get_by_qr_token(self, qr_token: str) -> RestaurantTable | None:
        result = await self.session.execute(
            select(RestaurantTable).where(RestaurantTable.qr_code_token == qr_token)
        )
        return result.scalar_one_or_none()

    async def get_by_table_number(self, table_number: str) -> RestaurantTable | None:
        result = await self.session.execute(
            select(RestaurantTable).where(RestaurantTable.table_number == table_number)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        table_number: str,
        qr_code_token: str,
        capacity: int = 4,
        status: TableStatus = TableStatus.AVAILABLE,
    ) -> RestaurantTable:
        table = RestaurantTable(
            table_number=table_number,
            qr_code_token=qr_code_token,
            capacity=capacity,
            status=status,
        )
        self.session.add(table)
        await self.session.flush()
        return table

    async def update_status(self, table: RestaurantTable, status: TableStatus) -> RestaurantTable:
        table.status = status
        await self.session.flush()
        return table
