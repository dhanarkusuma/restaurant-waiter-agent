from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.config import settings
from apps.backend.app.exceptions import (
    CustomerAlreadyHasActiveSessionError,
    SessionNotActiveError,
    SessionNotFoundError,
    TableAlreadyOccupiedError,
    TableNotFoundError,
)
from apps.backend.app.models import DiningSession, SessionStatus, TableStatus
from apps.backend.app.repositories.customer_repository import CustomerRepository
from apps.backend.app.repositories.session_repository import SessionRepository
from apps.backend.app.repositories.table_repository import TableRepository


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.table_repo = TableRepository(db)
        self.session_repo = SessionRepository(db)
        self.customer_repo = CustomerRepository(db)

    async def reserve_table_by_qr(
        self,
        customer_id: int,
        qr_code_token: str,
    ) -> DiningSession:
        """
        Validate table from QR token and reserve table by creating an active dining session.
        Enforces:
        - Table must exist.
        - Table must not already be OCCUPIED.
        - Customer must not have another active session on a different table.
        - Idempotent re-scan on the same table returns the existing active session.
        """
        table = await self.table_repo.get_by_qr_token(qr_code_token)
        if not table:
            raise TableNotFoundError(f"Table with QR code token '{qr_code_token}' does not exist")

        # Check if customer already has an active session
        active_customer_session = await self.session_repo.get_active_by_customer_id(customer_id)
        if active_customer_session:
            if active_customer_session.table_id == table.id:
                # Idempotent re-scan on the same table returns the active session
                return active_customer_session
            raise CustomerAlreadyHasActiveSessionError(
                f"Customer already has an active dining session on another table"
            )

        # Check if table already has an active session or is OCCUPIED
        active_table_session = await self.session_repo.get_active_by_table_id(table.id)
        if table.status == TableStatus.OCCUPIED or active_table_session is not None:
            raise TableAlreadyOccupiedError(f"Table '{table.table_number}' is currently occupied")

        # Transactionally transition table to OCCUPIED and create session
        await self.table_repo.update_status(table, TableStatus.OCCUPIED)
        dining_session = await self.session_repo.create(
            customer_id=customer_id,
            table_id=table.id,
        )

        return dining_session

    async def get_active_session_for_customer(self, customer_id: int) -> DiningSession | None:
        return await self.session_repo.get_active_by_customer_id(customer_id)

    async def get_active_session_for_table(self, table_id: int) -> DiningSession | None:
        return await self.session_repo.get_active_by_table_id(table_id)

    async def complete_session(
        self,
        session_id: int,
        completed_at: datetime | None = None,
    ) -> DiningSession:
        """
        Complete an active dining session and release the table back to AVAILABLE.
        """
        dining_session = await self.session_repo.get_by_id(session_id, load_relations=True)
        if not dining_session:
            raise SessionNotFoundError(f"Dining session with ID {session_id} not found")

        if dining_session.status != SessionStatus.ACTIVE:
            raise SessionNotActiveError(f"Dining session {session_id} is not active")

        now = completed_at or datetime.now(timezone.utc)
        dining_session.status = SessionStatus.COMPLETED
        dining_session.completed_at = now
        await self.session_repo.update(dining_session)

        # Release table back to AVAILABLE
        table = await self.table_repo.get_by_id(dining_session.table_id)
        if table:
            await self.table_repo.update_status(table, TableStatus.AVAILABLE)

        return dining_session

    def is_session_expired(
        self,
        dining_session: DiningSession,
        timeout_minutes: int | None = None,
        current_time: datetime | None = None,
    ) -> bool:
        """
        Check if an active session is expired based on:
        - last_order_completed_at (if orders exist and completed)
        - session.started_at / created_at (if no orders completed yet)
        """
        if dining_session.status != SessionStatus.ACTIVE:
            return False

        timeout_mins = (
            timeout_minutes
            if timeout_minutes is not None
            else settings.SESSION_AUTO_TERMINATE_MINUTES
        )

        # Timeout anchor per approved spec
        anchor = (
            dining_session.last_order_completed_at
            if dining_session.last_order_completed_at is not None
            else dining_session.started_at
        )

        if anchor is None:
            anchor = dining_session.created_at

        # Ensure datetime is timezone-aware
        now = current_time or datetime.now(timezone.utc)
        if anchor.tzinfo is None and now.tzinfo is not None:
            anchor = anchor.replace(tzinfo=timezone.utc)
        elif anchor.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        expiration_time = anchor + timedelta(minutes=timeout_mins)
        return now >= expiration_time

    async def process_session_timeouts(
        self,
        timeout_minutes: int | None = None,
        current_time: datetime | None = None,
    ) -> list[DiningSession]:
        """
        Identify all expired active dining sessions and complete them idempotently.
        """
        active_sessions = await self.session_repo.get_all_active_sessions()
        expired_sessions: list[DiningSession] = []

        now = current_time or datetime.now(timezone.utc)

        for session in active_sessions:
            if self.is_session_expired(session, timeout_minutes=timeout_minutes, current_time=now):
                completed_session = await self.complete_session(session.id, completed_at=now)
                expired_sessions.append(completed_session)

        return expired_sessions
