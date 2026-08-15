from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.models import AdminUser


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> AdminUser | None:
        result = await self.session.execute(
            select(AdminUser).where(AdminUser.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, admin_id: int) -> AdminUser | None:
        result = await self.session.execute(
            select(AdminUser).where(AdminUser.id == admin_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        username: str,
        hashed_password: str,
        full_name: str | None = None,
    ) -> AdminUser:
        admin = AdminUser(
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
        )
        self.session.add(admin)
        await self.session.flush()
        return admin
