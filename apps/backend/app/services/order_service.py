from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.config import settings
from apps.backend.app.exceptions import (
    InvalidOrderStatusTransitionError,
    OrderNotFoundError,
    SessionNotFoundError,
    TableNotFoundError,
)
from apps.backend.app.models import Order, OrderStatus, PaymentStatus, SessionStatus
from apps.backend.app.repositories.menu_repository import MenuRepository
from apps.backend.app.repositories.order_repository import OrderRepository
from apps.backend.app.repositories.session_repository import SessionRepository


class OrderDraftManager:
    """
    In-memory storage for unconfirmed order drafts, isolated per (customer_id, session_id).
    """
    def __init__(self):
        self._drafts: dict[tuple[int, int], list[dict[str, Any]]] = {}

    def get_items(self, customer_id: int, session_id: int) -> list[dict[str, Any]]:
        return self._drafts.get((customer_id, session_id), [])

    def set_items(self, customer_id: int, session_id: int, items: list[dict[str, Any]]) -> None:
        self._drafts[(customer_id, session_id)] = items

    def clear(self, customer_id: int, session_id: int) -> None:
        self._drafts.pop((customer_id, session_id), None)

    def clear_all(self) -> None:
        self._drafts.clear()


# Global draft manager instance
_global_draft_manager = OrderDraftManager()


class OrderService:
    # Valid forward state transitions
    VALID_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
        OrderStatus.ORDERED: [OrderStatus.IN_PROGRESS],
        OrderStatus.IN_PROGRESS: [OrderStatus.DONE],
        OrderStatus.DONE: [],
    }

    def __init__(
        self,
        db: AsyncSession,
        draft_manager: OrderDraftManager | None = None,
    ):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.menu_repo = MenuRepository(db)
        self.session_repo = SessionRepository(db)
        self.draft_manager = draft_manager or _global_draft_manager

    async def _resolve_menu_item(self, menu_name_or_id: str):
        if menu_name_or_id.isdigit():
            return await self.menu_repo.get_by_id(int(menu_name_or_id))
        return await self.menu_repo.get_by_name(menu_name_or_id)

    async def get_draft_summary(self, customer_id: int, session_id: int) -> dict[str, Any]:
        """
        Get the current unconfirmed order draft with fresh prices and subtotals from database.
        """
        raw_items = self.draft_manager.get_items(customer_id, session_id)
        if not raw_items:
            return {
                "items": [],
                "item_count": 0,
                "total_amount": 0,
                "is_empty": True,
            }

        verified_items: list[dict[str, Any]] = []
        total_amount = 0

        for it in raw_items:
            menu_item = await self.menu_repo.get_by_id(it["menu_item_id"])
            if not menu_item:
                continue

            unit_price = menu_item.price
            subtotal = unit_price * it["quantity"]
            total_amount += subtotal

            verified_items.append({
                "menu_item_id": menu_item.id,
                "name": menu_item.name,
                "unit_price": unit_price,
                "quantity": it["quantity"],
                "subtotal": subtotal,
                "notes": it.get("notes") or "",
                "is_available": menu_item.is_available,
            })

        return {
            "items": verified_items,
            "item_count": sum(i["quantity"] for i in verified_items),
            "total_amount": total_amount,
            "is_empty": len(verified_items) == 0,
        }

    async def add_item_to_draft(
        self,
        customer_id: int,
        session_id: int,
        menu_name_or_id: str,
        quantity: int = 1,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Add an available menu item to the customer's active order draft.
        """
        if quantity <= 0:
            return {"status": "error", "message": "Jumlah pesanan harus minimal 1"}

        menu_item = await self._resolve_menu_item(menu_name_or_id)
        if not menu_item:
            return {"status": "error", "message": f"Menu '{menu_name_or_id}' tidak ditemukan"}

        if not menu_item.is_available:
            return {
                "status": "error",
                "message": f"Maaf, menu '{menu_item.name}' sedang tidak tersedia (habis)",
            }

        items = self.draft_manager.get_items(customer_id, session_id)
        existing = next((i for i in items if i["menu_item_id"] == menu_item.id), None)

        if existing:
            existing["quantity"] += quantity
            if notes:
                existing["notes"] = notes
        else:
            items.append({
                "menu_item_id": menu_item.id,
                "quantity": quantity,
                "notes": notes or "",
            })

        self.draft_manager.set_items(customer_id, session_id, items)
        summary = await self.get_draft_summary(customer_id, session_id)
        return {
            "status": "added",
            "added_item": menu_item.name,
            "quantity": quantity,
            "draft": summary,
        }

    async def update_item_quantity(
        self,
        customer_id: int,
        session_id: int,
        menu_name_or_id: str,
        quantity: int,
    ) -> dict[str, Any]:
        """
        Update the quantity of an item in the draft. If quantity <= 0, item is removed.
        """
        menu_item = await self._resolve_menu_item(menu_name_or_id)
        if not menu_item:
            return {"status": "error", "message": f"Menu '{menu_name_or_id}' tidak ditemukan"}

        if quantity <= 0:
            return await self.remove_item_from_draft(customer_id, session_id, menu_name_or_id)

        items = self.draft_manager.get_items(customer_id, session_id)
        existing = next((i for i in items if i["menu_item_id"] == menu_item.id), None)
        if not existing:
            return {
                "status": "error",
                "message": f"Menu '{menu_item.name}' belum ada di draft pesanan Anda",
            }

        existing["quantity"] = quantity
        self.draft_manager.set_items(customer_id, session_id, items)
        summary = await self.get_draft_summary(customer_id, session_id)
        return {
            "status": "updated",
            "updated_item": menu_item.name,
            "new_quantity": quantity,
            "draft": summary,
        }

    async def remove_item_from_draft(
        self,
        customer_id: int,
        session_id: int,
        menu_name_or_id: str,
    ) -> dict[str, Any]:
        """
        Remove an item completely from the customer's draft.
        """
        menu_item = await self._resolve_menu_item(menu_name_or_id)
        if not menu_item:
            return {"status": "error", "message": f"Menu '{menu_name_or_id}' tidak ditemukan"}

        items = self.draft_manager.get_items(customer_id, session_id)
        remaining = [i for i in items if i["menu_item_id"] != menu_item.id]

        if len(remaining) == len(items):
            return {
                "status": "not_in_draft",
                "message": f"Menu '{menu_item.name}' tidak ada di draft pesanan Anda",
            }

        self.draft_manager.set_items(customer_id, session_id, remaining)
        summary = await self.get_draft_summary(customer_id, session_id)
        return {
            "status": "removed",
            "removed_item": menu_item.name,
            "draft": summary,
        }

    async def confirm_and_create_order(
        self,
        customer_id: int,
        session_id: int,
        payment_timeout_minutes: int | None = None,
    ) -> dict[str, Any]:
        """
        Confirm customer draft, persist Order and OrderItem records in PostgreSQL.
        Server calculates subtotals and total using trusted database prices.
        """
        # 1. Validate session
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.status != SessionStatus.ACTIVE or session.customer_id != customer_id:
            return {
                "status": "error",
                "message": "Sesi makan tidak valid atau sudah tidak aktif.",
            }

        # 2. Validate draft
        raw_items = self.draft_manager.get_items(customer_id, session_id)
        if not raw_items:
            return {
                "status": "error",
                "message": "Draft pesanan Anda masih kosong. Silakan pilih menu terlebih dahulu.",
            }

        # 3. Verify prices and availability from PostgreSQL
        verified_items: list[dict[str, Any]] = []
        total_amount = 0

        for it in raw_items:
            menu_item = await self.menu_repo.get_by_id(it["menu_item_id"])
            if not menu_item:
                return {
                    "status": "error",
                    "message": f"Menu dengan ID {it['menu_item_id']} tidak valid.",
                }
            if not menu_item.is_available:
                return {
                    "status": "error",
                    "message": f"Maaf, menu '{menu_item.name}' saat ini sedang habis.",
                }

            unit_price = menu_item.price
            subtotal = unit_price * it["quantity"]
            total_amount += subtotal

            verified_items.append({
                "menu_item_id": menu_item.id,
                "name": menu_item.name,
                "unit_price": unit_price,
                "quantity": it["quantity"],
                "subtotal": subtotal,
                "notes": it.get("notes") or "",
            })

        # 4. Create Order & OrderItems
        order = await self.order_repo.create_order(
            customer_id=customer_id,
            dining_session_id=session.id,
            table_id=session.table_id,
            total_amount=total_amount,
            items=verified_items,
            payment_timeout_minutes=payment_timeout_minutes,
        )

        # 5. Clear draft upon successful creation
        self.draft_manager.clear(customer_id, session_id)

        return {
            "status": "created",
            "order_id": order.id,
            "table_id": session.table_id,
            "total_amount": total_amount,
            "order_status": order.status.value,
            "payment_status": order.payment_status.value,
            "items": verified_items,
        }

    # --- Order Lifecycle (Admin / Kitchen Actions) ---

    async def get_order_by_id(self, order_id: int) -> Order | None:
        return await self.order_repo.get_by_id(order_id)

    async def list_orders(
        self,
        status: OrderStatus | None = None,
        payment_status: PaymentStatus | None = None,
    ) -> list[Order]:
        return await self.order_repo.list_all(status=status, payment_status=payment_status)

    async def update_order_status(
        self,
        order_id: int,
        new_status: OrderStatus,
        completed_at: datetime | None = None,
    ) -> Order:
        """
        Advance order status strictly forward:
        ORDERED -> IN_PROGRESS -> DONE.
        Updates dining session's last_order_completed_at when order becomes DONE.
        """
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFoundError(f"Order with ID {order_id} not found")

        current_status = order.status
        allowed_targets = self.VALID_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_targets:
            raise InvalidOrderStatusTransitionError(
                f"Cannot transition order {order_id} from {current_status.value} to {new_status.value}"
            )

        order.status = new_status
        now = completed_at or datetime.now(timezone.utc)

        if new_status == OrderStatus.DONE:
            order.completed_at = now
            # Update dining session's last_order_completed_at anchor
            session = await self.session_repo.get_by_id(order.dining_session_id)
            if session:
                session.last_order_completed_at = now
                await self.session_repo.update(session)

        await self.order_repo.update(order)
        return order

    # --- Manual Payment (Admin Action) ---

    async def mark_order_as_paid(self, order_id: int) -> Order:
        """
        Admin marks an order as PAID manually.
        Operation is idempotent.
        """
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFoundError(f"Order with ID {order_id} not found")

        if order.payment_status == PaymentStatus.PAID:
            return order

        order.payment_status = PaymentStatus.PAID
        order.is_overdue = False  # Paid orders are no longer overdue
        await self.order_repo.update(order)
        return order

    # --- Payment Timeout Processing ---

    def is_order_overdue(
        self,
        order: Order,
        current_time: datetime | None = None,
    ) -> bool:
        """
        Check if an unpaid order has passed its payment_due_at timestamp.
        """
        if order.payment_status == PaymentStatus.PAID:
            return False

        if not order.payment_due_at:
            return False

        now = current_time or datetime.now(timezone.utc)
        due_at = order.payment_due_at

        # Match timezone awareness
        if due_at.tzinfo is None and now.tzinfo is not None:
            due_at = due_at.replace(tzinfo=timezone.utc)
        elif due_at.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        return now >= due_at

    async def process_payment_timeouts(
        self,
        current_time: datetime | None = None,
    ) -> list[Order]:
        """
        Identify unpaid orders that have passed payment_due_at and mark is_overdue = True.
        Does NOT cancel order or mark PAID.
        """
        unpaid_orders = await self.order_repo.list_all(payment_status=PaymentStatus.UNPAID)
        newly_overdue: list[Order] = []

        now = current_time or datetime.now(timezone.utc)

        for order in unpaid_orders:
            if not order.is_overdue and self.is_order_overdue(order, current_time=now):
                order.is_overdue = True
                await self.order_repo.update(order)
                newly_overdue.append(order)

        return newly_overdue
