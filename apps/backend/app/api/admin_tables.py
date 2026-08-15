from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.dependencies import get_current_admin
from apps.backend.app.database import get_db
from apps.backend.app.exceptions import (
    CannotDeactivateActiveTableError,
    TableAlreadyExistsError,
    TableNotFoundError,
)
from apps.backend.app.models.models import AdminUser
from apps.backend.app.schemas.table import (
    TableCreateRequest,
    TableDeleteResponse,
    TablePositionUpdateRequest,
    TableQRResponse,
    TableResponse,
    TableUpdateRequest,
)
from apps.backend.app.services.table_service import TableService

router = APIRouter(prefix="/api/admin/tables", tags=["Admin Tables"])


@router.get("", response_model=list[TableResponse])
async def list_tables(
    include_inactive: bool = True,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """List all tables with operational state, customer details, and visual layout coordinates."""
    service = TableService(db)
    return await service.list_tables_with_state(include_inactive=include_inactive)


@router.post("", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    payload: TableCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Create a new restaurant table with layout position."""
    service = TableService(db)
    try:
        return await service.create_table(
            table_number=payload.table_number,
            capacity=payload.capacity,
            position_x=payload.position_x,
            position_y=payload.position_y,
        )
    except TableAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/{table_id}", response_model=TableResponse)
async def update_table_metadata(
    table_id: int,
    payload: TableUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Update table metadata (table number, seating capacity)."""
    service = TableService(db)
    try:
        return await service.update_table_metadata(
            table_id=table_id,
            table_number=payload.table_number,
            capacity=payload.capacity,
        )
    except TableNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TableAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch("/{table_id}/position", response_model=TableResponse)
async def update_table_position(
    table_id: int,
    payload: TablePositionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Update visual floor layout coordinates after a drag-and-drop event."""
    service = TableService(db)
    try:
        return await service.update_table_position(
            table_id=table_id,
            position_x=payload.position_x,
            position_y=payload.position_y,
        )
    except TableNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{table_id}", response_model=TableDeleteResponse)
async def deactivate_or_delete_table(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Deactivate table (or delete if no historical transactions). Rejects if table has active session."""
    service = TableService(db)
    try:
        result = await service.deactivate_or_delete_table(table_id=table_id)
        return TableDeleteResponse(
            id=int(result["id"]),
            action=str(result["action"]),
            message=str(result["message"]),
        )
    except TableNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CannotDeactivateActiveTableError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{table_id}/qr", response_model=TableQRResponse)
async def get_table_qr(
    table_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Retrieve stable QR token and Telegram deep link for a table."""
    service = TableService(db)
    try:
        return await service.get_table_qr_info(table_id=table_id)
    except TableNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
