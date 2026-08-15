import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.security import create_access_token
from apps.backend.app.models import AdminUser
from apps.backend.app.services.admin_auth_service import AdminAuthService


@pytest.fixture
async def seeded_admin(db_session: AsyncSession) -> AdminUser:
    service = AdminAuthService(db_session)
    return await service.create_admin_user(
        username="superadmin",
        password="correct_password_123",
        full_name="Super Administrator",
        role="admin",
    )


@pytest.mark.asyncio
async def test_valid_admin_login(client: AsyncClient, seeded_admin: AdminUser):
    """Test valid admin login returns JWT token and user info."""
    response = await client.post(
        "/api/admin/auth/login",
        json={"username": "superadmin", "password": "correct_password_123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "superadmin"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_invalid_admin_login(client: AsyncClient, seeded_admin: AdminUser):
    """Test invalid credentials return 401 Unauthorized."""
    # Wrong password
    res_wrong_pwd = await client.post(
        "/api/admin/auth/login",
        json={"username": "superadmin", "password": "wrong_password"},
    )
    assert res_wrong_pwd.status_code == 401

    # Nonexistent user
    res_missing_user = await client.post(
        "/api/admin/auth/login",
        json={"username": "nonexistent", "password": "password123"},
    )
    assert res_missing_user.status_code == 401


@pytest.mark.asyncio
async def test_missing_and_invalid_jwt_rejected(client: AsyncClient):
    """Test protected admin endpoint rejects missing and invalid tokens."""
    # Missing token
    res_missing = await client.get("/api/admin/auth/me")
    assert res_missing.status_code == 401

    # Invalid token
    res_invalid = await client.get(
        "/api/admin/auth/me",
        headers={"Authorization": "Bearer invalid_garbage_token_123"},
    )
    assert res_invalid.status_code == 401


@pytest.mark.asyncio
async def test_protected_admin_profile_access(client: AsyncClient, seeded_admin: AdminUser):
    """Test accessing protected /api/admin/auth/me with valid JWT."""
    token = create_access_token({"sub": seeded_admin.username, "user_id": seeded_admin.id})
    response = await client.get(
        "/api/admin/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "superadmin"
    assert data["role"] == "admin"
    assert data["is_active"] is True
    # Password hash must NEVER be exposed
    assert "password" not in data
    assert "password_hash" not in data
