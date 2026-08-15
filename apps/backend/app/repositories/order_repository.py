from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.app.models import Order, OrderItem, OrderStatus, PaymentStatus


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: int) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.menu_item),
                selectinload(Order.table),
                selectinload(Order.customer),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_session(self, session_id: int) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.dining_session_id == session_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.menu_item),
            )
            .order_by(Order.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_order(
        self,
        customer_id: int,
        dining_session_id: int,
        table_id: int,
        total_amount: int,
        items: list[dict[str, Any]],
    ) -> Order:
        order = Order(
            customer_id=customer_id,
            dining_session_id=dining_session_id,
            table_id=table_id,
            status=OrderStatus.ORDERED,
            payment_status=PaymentStatus.UNPAID,
            total_amount=total_amount,
        )
        self.session.add(order)
        await self.session.flush()

        for item_data in items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data["menu_item_id"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                subtotal=item_data["subtotal"],
                notes=item_data.get("notes"),
            )
            self.session.add(order_item)

        await self.session.flush()
        return order
