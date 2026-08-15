from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.models import Customer


class CustomerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, customer_id: int) -> Customer | None:
        result = await self.session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Customer | None:
        result = await self.session.execute(
            select(Customer).where(Customer.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Customer:
        customer = Customer(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        self.session.add(customer)
        await self.session.flush()
        return customer

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Customer:
        customer = await self.get_by_telegram_id(telegram_id)
        if not customer:
            customer = await self.create(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
        return customer
