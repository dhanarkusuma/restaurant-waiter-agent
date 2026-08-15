import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.security import verify_password
from apps.backend.app.config import settings
from apps.backend.app.models import AdminUser
from apps.backend.app.repositories import AdminRepository
from apps.backend.app.services import AdminAuthService
from apps.backend.scripts.seed_admin import seed_admin


@pytest.fixture(autouse=True)
def clean_admin_settings():
    """Ensure settings are cleanly configured before and after tests."""
    orig_username = settings.ADMIN_USERNAME
    orig_password = settings.ADMIN_PASSWORD
    orig_full_name = settings.ADMIN_FULL_NAME
    settings.ADMIN_USERNAME = ""
    settings.ADMIN_PASSWORD = ""
    settings.ADMIN_FULL_NAME = "System Administrator"
    yield
    settings.ADMIN_USERNAME = orig_username
    settings.ADMIN_PASSWORD = orig_password
    settings.ADMIN_FULL_NAME = orig_full_name


@pytest.mark.asyncio
async def test_seed_admin_creates_new_admin_with_hashed_password(db_session: AsyncSession):
    """Test creating a new admin account with explicit parameters and verifying password is saved as hash."""
    admin, created = await seed_admin(
        session=db_session,
        username="super_seed_admin",
        password="MySecurePassword!123",
        full_name="Master Seeder",
    )

    assert created is True
    assert admin is not None
    assert admin.username == "super_seed_admin"
    assert admin.full_name == "Master Seeder"
    assert admin.is_active is True

    # 1. Plaintext password MUST NOT be stored in database
    assert admin.hashed_password != "MySecurePassword!123"
    assert ":" in admin.hashed_password  # Salt:Hash format

    # 2. Hash can be verified with auth security
    assert verify_password("MySecurePassword!123", admin.hashed_password) is True
    assert verify_password("WrongPassword", admin.hashed_password) is False

    # 3. Can authenticate successfully through AdminAuthService
    auth_service = AdminAuthService(db_session)
    result = await auth_service.authenticate("super_seed_admin", "MySecurePassword!123")
    assert result is not None
    authed_admin, token = result
    assert authed_admin.username == "super_seed_admin"
    assert token is not None


@pytest.mark.asyncio
async def test_seed_admin_idempotency_running_twice_does_not_duplicate(db_session: AsyncSession):
    """Test running seed_admin multiple times returns existing user without duplicates."""
    # First execution: created
    admin1, created1 = await seed_admin(
        session=db_session,
        username="idempotent_admin",
        password="FirstPassword123",
        full_name="Idempotent Admin",
    )
    assert created1 is True

    # Second execution: not created, returns existing
    admin2, created2 = await seed_admin(
        session=db_session,
        username="idempotent_admin",
        password="DifferentPassword456",
    )
    assert created2 is False
    assert admin2.id == admin1.id
    assert admin2.username == admin1.username

    # Total count in database for this username must be exactly 1
    count_res = await db_session.execute(
        select(func.count(AdminUser.id)).where(AdminUser.username == "idempotent_admin")
    )
    assert count_res.scalar() == 1

    # Original password remains valid and unchanged
    assert verify_password("FirstPassword123", admin2.hashed_password) is True


@pytest.mark.asyncio
async def test_seed_admin_reads_from_application_settings(db_session: AsyncSession):
    """Test seed_admin reads ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_FULL_NAME from application settings."""
    settings.ADMIN_USERNAME = "settings_admin_user"
    settings.ADMIN_PASSWORD = "SettingsSecretPass789"
    settings.ADMIN_FULL_NAME = "Settings Admin"

    admin, created = await seed_admin(session=db_session)
    assert created is True
    assert admin.username == "settings_admin_user"
    assert admin.full_name == "Settings Admin"
    assert verify_password("SettingsSecretPass789", admin.hashed_password) is True


@pytest.mark.asyncio
async def test_seed_admin_explicit_arguments_override_settings(db_session: AsyncSession):
    """Test that explicit function arguments override values configured in application settings."""
    settings.ADMIN_USERNAME = "default_settings_user"
    settings.ADMIN_PASSWORD = "DefaultSettingsPass123"

    admin, created = await seed_admin(
        session=db_session,
        username="overridden_user",
        password="OverriddenPass456",
    )
    assert created is True
    assert admin.username == "overridden_user"
    assert verify_password("OverriddenPass456", admin.hashed_password) is True
    assert verify_password("DefaultSettingsPass123", admin.hashed_password) is False


@pytest.mark.asyncio
async def test_seed_admin_missing_credentials_raises_error(db_session: AsyncSession):
    """Test that missing username or password raises ValueError safely."""
    settings.ADMIN_USERNAME = ""
    settings.ADMIN_PASSWORD = ""

    with pytest.raises(ValueError, match="ADMIN_USERNAME"):
        await seed_admin(session=db_session, username="", password="some_password")

    with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
        await seed_admin(session=db_session, username="valid_user", password="")
