from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.dependencies import get_current_admin
from apps.backend.app.database import get_db
from apps.backend.app.models import AdminUser
from apps.backend.app.schemas.admin import (
    MenuCategoryCreateRequest,
    MenuCategoryResponse,
    MenuItemAdminResponse,
    MenuItemAvailabilityRequest,
    MenuItemCreateRequest,
    MenuItemUpdateRequest,
)
from apps.backend.app.services.menu_service import MenuService

router = APIRouter(prefix="/api/admin/menu", tags=["Admin Menu Management"])


@router.get("/categories", response_model=list[MenuCategoryResponse])
async def list_categories(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all menu categories."""
    service = MenuService(db)
    return await service.list_categories()


@router.post("/categories", response_model=MenuCategoryResponse)
async def create_category(
    payload: MenuCategoryCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new menu category."""
    service = MenuService(db)
    return await service.create_category(name=payload.name, description=payload.description)


@router.get("/items", response_model=list[MenuItemAdminResponse])
async def list_menu_items(
    category_id: int | None = None,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all menu items (including unavailable items) for admin management."""
    service = MenuService(db)
    return await service.list_all_admin(category_id=category_id)


@router.post("/items", response_model=MenuItemAdminResponse)
async def create_menu_item(
    payload: MenuItemCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new menu item."""
    service = MenuService(db)
    return await service.create_menu_item(
        name=payload.name,
        price=payload.price,
        category_id=payload.category_id,
        description=payload.description,
        is_available=payload.is_available,
    )


@router.put("/items/{item_id}", response_model=MenuItemAdminResponse)
async def update_menu_item(
    item_id: int,
    payload: MenuItemUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing menu item."""
    service = MenuService(db)
    updated = await service.update_menu_item(
        item_id=item_id,
        name=payload.name,
        price=payload.price,
        category_id=payload.category_id,
        description=payload.description,
        is_available=payload.is_available,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu item {item_id} not found",
        )
    return updated


@router.patch("/items/{item_id}/availability", response_model=MenuItemAdminResponse)
async def set_menu_item_availability(
    item_id: int,
    payload: MenuItemAvailabilityRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Quick toggle for menu item availability."""
    service = MenuService(db)
    updated = await service.set_item_availability(item_id=item_id, is_available=payload.is_available)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu item {item_id} not found",
        )
    return updated


@router.delete("/items/{item_id}")
async def delete_menu_item(
    item_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete or deactivate menu item.
    Deactivates if historical orders reference this item to preserve audit trail.
    """
    service = MenuService(db)
    result = await service.delete_or_deactivate_item(item_id=item_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Menu item {item_id} not found",
        )
    return result
