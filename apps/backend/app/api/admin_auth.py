from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.dependencies import get_current_admin
from apps.backend.app.database import get_db
from apps.backend.app.models import AdminUser
from apps.backend.app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUserResponse,
)
from apps.backend.app.services.admin_auth_service import AdminAuthService

router = APIRouter(prefix="/api/admin/auth", tags=["Admin Auth"])


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    payload: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Admin staff login endpoint generating JWT access token."""
    service = AdminAuthService(db)
    result = await service.authenticate(
        username=payload.username,
        password=payload.password,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin, token = result
    return AdminLoginResponse(
        access_token=token,
        token_type="bearer",
        username=admin.username,
        role=getattr(admin, "role", "admin"),
        full_name=admin.full_name,
    )


@router.get("/me", response_model=AdminUserResponse)
async def get_current_admin_profile(
    admin: AdminUser = Depends(get_current_admin),
):
    """Get current authenticated admin user profile."""
    return admin
