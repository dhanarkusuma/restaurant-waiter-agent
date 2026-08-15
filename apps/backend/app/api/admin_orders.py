from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.dependencies import get_current_admin
from apps.backend.app.database import get_db
from apps.backend.app.exceptions import (
    InvalidOrderStatusTransitionError,
    OrderNotFoundError,
)
from apps.backend.app.models import AdminUser, OrderStatus, PaymentStatus
from apps.backend.app.schemas.order import OrderResponse, OrderStatusUpdateRequest
from apps.backend.app.services.order_service import OrderService

router = APIRouter(prefix="/api/admin/orders", tags=["Admin Orders"])


@router.get("", response_model=list[OrderResponse])
async def list_admin_orders(
    status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List orders with optional status/payment filters for admin staff."""
    service = OrderService(db)
    orders = await service.list_orders(status=status, payment_status=payment_status)
    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_admin_order(
    order_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get single order details."""
    service = OrderService(db)
    order = await service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_admin_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Advance order status (ORDERED -> IN_PROGRESS -> DONE).
    Rejects invalid state transitions.
    """
    service = OrderService(db)
    try:
        updated_order = await service.update_order_status(
            order_id=order_id,
            new_status=payload.status,
        )
        return updated_order
    except OrderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidOrderStatusTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{order_id}/pay", response_model=OrderResponse)
async def mark_admin_order_paid(
    order_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually mark an order as PAID by admin staff.
    Operation is idempotent.
    """
    service = OrderService(db)
    try:
        paid_order = await service.mark_order_as_paid(order_id=order_id)
        return paid_order
    except OrderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
