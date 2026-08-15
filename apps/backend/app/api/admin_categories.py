from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.dependencies import get_current_admin
from apps.backend.app.database import get_db
from apps.backend.app.exceptions import (
    CategoryAlreadyExistsError,
    CategoryInUseError,
    CategoryNotFoundError,
)
from apps.backend.app.models import AdminUser
from apps.backend.app.schemas.admin import (
    CategoryDeleteResponse,
    MenuCategoryCreateRequest,
    MenuCategoryResponse,
    MenuCategoryUpdateRequest,
)
from apps.backend.app.services.menu_service import MenuService

router = APIRouter(prefix="/api/admin/categories", tags=["Admin Categories"])


@router.get("", response_model=list[MenuCategoryResponse])
async def list_categories(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all menu categories."""
    service = MenuService(db)
    return await service.list_categories()


@router.get("/{category_id}", response_model=MenuCategoryResponse)
async def get_category(
    category_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get single menu category details."""
    service = MenuService(db)
    cat = await service.get_category_by_id(category_id)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found",
        )
    return cat


@router.post("", response_model=MenuCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: MenuCategoryCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new menu category."""
    service = MenuService(db)
    try:
        return await service.create_category(name=payload.name, description=payload.description)
    except CategoryAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{category_id}", response_model=MenuCategoryResponse)
async def update_category(
    category_id: int,
    payload: MenuCategoryUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing menu category."""
    service = MenuService(db)
    try:
        return await service.update_category(
            category_id=category_id,
            name=payload.name,
            description=payload.description,
        )
    except CategoryNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CategoryAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{category_id}", response_model=CategoryDeleteResponse)
async def delete_category(
    category_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a menu category if not referenced by any menu items."""
    service = MenuService(db)
    try:
        return await service.delete_category(category_id=category_id)
    except CategoryNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CategoryInUseError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
