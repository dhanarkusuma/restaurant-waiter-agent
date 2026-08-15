from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.exceptions import SessionNotFoundError, TableNotFoundError
from apps.backend.app.models import OrderStatus, PaymentStatus, SessionStatus
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
