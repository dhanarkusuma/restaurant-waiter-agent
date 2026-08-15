import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.config import settings
from apps.backend.app.database import AsyncSessionLocal
from apps.backend.app.models import AdminUser
from apps.backend.app.repositories.admin_repository import AdminRepository
from apps.backend.app.services.admin_auth_service import AdminAuthService


async def seed_admin(
    session: AsyncSession | None = None,
    username: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
) -> tuple[AdminUser | None, bool]:
    """
    Idempotently seed the initial admin account.

    - Reads credentials from arguments or centralized application settings (ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_FULL_NAME).
    - Explicit parameters override settings.
    - Uses existing AdminAuthService and password hashing.
    - If admin user already exists, skips creation without duplicating.
    - Never logs or exposes plaintext password.

    Returns:
        tuple[AdminUser | None, bool]: (admin_user, created)
    """
    admin_username = (username if username is not None else settings.ADMIN_USERNAME).strip()
    admin_password = password if password is not None else settings.ADMIN_PASSWORD
    admin_full_name = full_name if full_name is not None else (settings.ADMIN_FULL_NAME or "System Administrator")

    if not admin_username:
        raise ValueError("ADMIN_USERNAME configuration or parameter is required.")

    if not admin_password:
        raise ValueError("ADMIN_PASSWORD configuration or parameter is required.")

    async def _execute(db_session: AsyncSession) -> tuple[AdminUser, bool]:
        admin_repo = AdminRepository(db_session)
        existing = await admin_repo.get_by_username(admin_username)
        if existing:
            return existing, False

        auth_service = AdminAuthService(db_session)
        new_admin = await auth_service.create_admin_user(
            username=admin_username,
            password=admin_password,
            full_name=admin_full_name,
            role="admin",
        )
        await db_session.commit()
        return new_admin, True

    if session is not None:
        return await _execute(session)

    async with AsyncSessionLocal() as db:
        return await _execute(db)


async def main() -> None:
    try:
        admin, created = await seed_admin()
        if created:
            print(f"[SUCCESS] Admin user '{admin.username}' created successfully.")
        else:
            print(f"[INFO] Admin user '{admin.username}' already exists. No changes made.")
    except ValueError as e:
        print(f"[ERROR] Seeding failed: {e}", file=sys.stderr)
        print(
            "\nUsage:\n"
            "  Set ADMIN_USERNAME and ADMIN_PASSWORD in .env or environment before running:\n"
            "    ADMIN_USERNAME=admin ADMIN_PASSWORD=your_secure_password uv run python -m apps.backend.scripts.seed_admin\n",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error during admin seeding: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
