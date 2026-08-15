import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.config import settings
from apps.backend.app.exceptions import (
    CannotDeactivateActiveTableError,
    TableAlreadyExistsError,
    TableNotFoundError,
)
from apps.backend.app.models import (
    Customer,
    DiningSession,
    Order,
    RestaurantTable,
    SessionStatus,
    TableStatus,
)
from apps.backend.app.repositories.session_repository import SessionRepository
from apps.backend.app.repositories.table_repository import TableRepository
from apps.backend.app.schemas.table import (
    ActiveCustomerInfo,
    ActiveSessionInfo,
    TableQRResponse,
    TableResponse,
)


class TableService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.table_repo = TableRepository(db)
        self.session_repo = SessionRepository(db)

    def _build_deep_link(self, qr_code_token: str) -> str:
        bot_username = settings.TELEGRAM_BOT_USERNAME or "RestaurantWaiterBot"
        return f"https://t.me/{bot_username}?start={qr_code_token}"

    def _format_table_response(
        self,
        table: RestaurantTable,
        active_session: DiningSession | None = None,
    ) -> TableResponse:
        active_info: ActiveSessionInfo | None = None
        if active_session:
            cust_info: ActiveCustomerInfo | None = None
            if active_session.customer:
                cust_info = ActiveCustomerInfo(
                    customer_id=active_session.customer.id,
                    telegram_id=active_session.customer.telegram_id,
                    username=active_session.customer.username,
                    first_name=active_session.customer.first_name,
                    last_name=active_session.customer.last_name,
                )
            active_info = ActiveSessionInfo(
                session_id=active_session.id,
                started_at=active_session.started_at,
                last_order_completed_at=active_session.last_order_completed_at,
                customer=cust_info,
            )

        return TableResponse(
            id=table.id,
            table_number=table.table_number,
            status=table.status,
            capacity=table.capacity,
            position_x=table.position_x,
            position_y=table.position_y,
            is_active=table.is_active,
            qr_code_token=table.qr_code_token,
            deep_link_url=self._build_deep_link(table.qr_code_token),
            created_at=table.created_at,
            active_session=active_info,
        )

    async def list_tables_with_state(self, include_inactive: bool = True) -> list[TableResponse]:
        tables = await self.table_repo.list_all(include_inactive=include_inactive)
        results: list[TableResponse] = []
        for t in tables:
            active_session = await self.session_repo.get_active_by_table_id(t.id)
            results.append(self._format_table_response(t, active_session))
        return results

    async def create_table(
        self,
        table_number: str,
        capacity: int = 4,
        position_x: int = 0,
        position_y: int = 0,
    ) -> TableResponse:
        clean_number = table_number.strip()
        existing = await self.table_repo.get_by_table_number(clean_number)
        if existing:
            raise TableAlreadyExistsError(f"Meja dengan nomor '{clean_number}' sudah terdaftar")

        # Generate unique QR code token
        qr_token = f"qr_{uuid.uuid4().hex[:12]}"
        while await self.table_repo.get_by_qr_token(qr_token, only_active=False):
            qr_token = f"qr_{uuid.uuid4().hex[:12]}"

        table = await self.table_repo.create(
            table_number=clean_number,
            qr_code_token=qr_token,
            capacity=capacity,
            position_x=position_x,
            position_y=position_y,
            status=TableStatus.AVAILABLE,
        )
        return self._format_table_response(table, active_session=None)

    async def update_table_metadata(
        self,
        table_id: int,
        table_number: str | None = None,
        capacity: int | None = None,
    ) -> TableResponse:
        table = await self.table_repo.get_by_id(table_id)
        if not table:
            raise TableNotFoundError(f"Meja dengan ID {table_id} tidak ditemukan")

        if table_number is not None:
            clean_number = table_number.strip()
            if clean_number != table.table_number:
                existing = await self.table_repo.get_by_table_number(clean_number)
                if existing and existing.id != table_id:
                    raise TableAlreadyExistsError(f"Meja dengan nomor '{clean_number}' sudah terdaftar")

        updated_table = await self.table_repo.update(
            table,
            table_number=table_number,
            capacity=capacity,
        )
        active_session = await self.session_repo.get_active_by_table_id(table_id)
        return self._format_table_response(updated_table, active_session)

    async def update_table_position(
        self,
        table_id: int,
        position_x: int,
        position_y: int,
    ) -> TableResponse:
        table = await self.table_repo.get_by_id(table_id)
        if not table:
            raise TableNotFoundError(f"Meja dengan ID {table_id} tidak ditemukan")

        updated_table = await self.table_repo.update_position(
            table,
            position_x=position_x,
            position_y=position_y,
        )
        active_session = await self.session_repo.get_active_by_table_id(table_id)
        return self._format_table_response(updated_table, active_session)

    async def deactivate_or_delete_table(self, table_id: int) -> dict[str, str | int]:
        table = await self.table_repo.get_by_id(table_id)
        if not table:
            raise TableNotFoundError(f"Meja dengan ID {table_id} tidak ditemukan")

        # 1. Prevent deactivation if currently occupied or has active session
        active_session = await self.session_repo.get_active_by_table_id(table_id)
        if active_session or table.status == TableStatus.OCCUPIED:
            raise CannotDeactivateActiveTableError(
                f"Meja '{table.table_number}' sedang digunakan dan memiliki sesi aktif, tidak dapat dinonaktifkan."
            )

        # 2. Check if table has any historical dining sessions or orders
        history_session_check = await self.db.execute(
            select(DiningSession.id).where(DiningSession.table_id == table_id).limit(1)
        )
        history_order_check = await self.db.execute(
            select(Order.id).where(Order.table_id == table_id).limit(1)
        )
        has_history = (
            history_session_check.scalar_one_or_none() is not None
            or history_order_check.scalar_one_or_none() is not None
        )

        if has_history:
            # Soft-deactivate to protect relational data integrity
            await self.table_repo.update(table, is_active=False)
            return {
                "id": table_id,
                "action": "deactivated",
                "message": f"Meja {table.table_number} berhasil dinonaktifkan.",
            }
        else:
            # Hard delete if clean without history
            await self.table_repo.delete(table)
            return {
                "id": table_id,
                "action": "deleted",
                "message": f"Meja {table.table_number} berhasil dihapus permanen.",
            }

    async def get_table_qr_info(self, table_id: int) -> TableQRResponse:
        table = await self.table_repo.get_by_id(table_id)
        if not table:
            raise TableNotFoundError(f"Meja dengan ID {table_id} tidak ditemukan")

        return TableQRResponse(
            table_id=table.id,
            table_number=table.table_number,
            qr_code_token=table.qr_code_token,
            deep_link_url=self._build_deep_link(table.qr_code_token),
        )
