from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.security import create_access_token, get_password_hash, verify_password
from apps.backend.app.models import AdminUser
from apps.backend.app.repositories.admin_repository import AdminRepository


class AdminAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.admin_repo = AdminRepository(db)

    async def authenticate(self, username: str, password: str) -> tuple[AdminUser, str] | None:
        """Verify admin credentials securely and generate JWT access token."""
        admin = await self.admin_repo.get_by_username(username.strip())
        if not admin or not admin.is_active:
            return None

        if not verify_password(password, admin.hashed_password):
            return None

        token = create_access_token(data={"sub": admin.username, "user_id": admin.id, "role": "admin"})
        return admin, token

    async def create_admin_user(
        self,
        username: str,
        password: str,
        full_name: str | None = None,
        role: str = "admin",
    ) -> AdminUser:
        """Create a new admin user with hashed password."""
        hashed = get_password_hash(password)
        return await self.admin_repo.create(
            username=username,
            hashed_password=hashed,
            full_name=full_name,
        )
