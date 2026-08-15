from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.backend.app.models import DiningSession, SessionStatus


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, session_id: int, load_relations: bool = False) -> DiningSession | None:
        stmt = select(DiningSession).where(DiningSession.id == session_id)
        if load_relations:
            stmt = stmt.options(
                selectinload(DiningSession.table),
                selectinload(DiningSession.customer),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_customer_id(self, customer_id: int) -> DiningSession | None:
        result = await self.session.execute(
            select(DiningSession).where(
                DiningSession.customer_id == customer_id,
                DiningSession.status == SessionStatus.ACTIVE,
            ).options(selectinload(DiningSession.table))
        )
        return result.scalar_one_or_none()

    async def get_active_by_table_id(self, table_id: int) -> DiningSession | None:
        result = await self.session.execute(
            select(DiningSession).where(
                DiningSession.table_id == table_id,
                DiningSession.status == SessionStatus.ACTIVE,
            ).options(selectinload(DiningSession.table))
        )
        return result.scalar_one_or_none()

    async def get_all_active_sessions(self) -> list[DiningSession]:
        result = await self.session.execute(
            select(DiningSession).where(
                DiningSession.status == SessionStatus.ACTIVE
            ).options(selectinload(DiningSession.table))
        )
        return list(result.scalars().all())

    async def create(
        self,
        customer_id: int,
        table_id: int,
        started_at: datetime | None = None,
    ) -> DiningSession:
        now = started_at or datetime.now(timezone.utc)
        dining_session = DiningSession(
            customer_id=customer_id,
            table_id=table_id,
            status=SessionStatus.ACTIVE,
            started_at=now,
        )
        self.session.add(dining_session)
        await self.session.flush()
        return dining_session

    async def update(self, dining_session: DiningSession) -> DiningSession:
        await self.session.flush()
        return dining_session
