from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.dependencies import get_current_admin
from apps.backend.app.database import get_db
from apps.backend.app.models import AdminUser, Customer
from apps.backend.app.repositories import CustomerRepository
from apps.backend.app.schemas.admin import CustomerMemoryViewerResponse
from apps.backend.app.services.customer_memory_service import CustomerMemoryService

router = APIRouter(prefix="/api/admin/customers", tags=["Admin Customer Memory Viewer"])


@router.get("", response_model=list[dict[str, Any]])
async def list_admin_customers(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all registered restaurant customers."""
    result = await db.execute(select(Customer).order_by(Customer.created_at.desc()))
    customers = result.scalars().all()
    return [
        {
            "id": c.id,
            "telegram_id": c.telegram_id,
            "username": c.username,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "created_at": c.created_at,
        }
        for c in customers
    ]


@router.get("/{customer_id}/memory", response_model=CustomerMemoryViewerResponse)
async def view_customer_memory(
    customer_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Read-only view of a customer's stored memory, preferences, and favorites."""
    cust_repo = CustomerRepository(db)
    customer = await cust_repo.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found",
        )

    memory_service = CustomerMemoryService(db)
    profile = await memory_service.get_customer_profile(customer_id)

    return CustomerMemoryViewerResponse(
        customer_id=customer.id,
        telegram_id=customer.telegram_id,
        username=customer.username,
        first_name=customer.first_name,
        last_name=customer.last_name,
        created_at=customer.created_at,
        memories=profile["memories"],
        favorites=profile["favorites"],
    )
