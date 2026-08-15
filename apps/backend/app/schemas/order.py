from datetime import datetime
from pydantic import BaseModel, ConfigDict

from apps.backend.app.models import OrderStatus, PaymentStatus


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    menu_item_id: int
    quantity: int
    unit_price: int
    subtotal: int
    notes: str | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    dining_session_id: int
    table_id: int
    status: OrderStatus
    payment_status: PaymentStatus
    total_amount: int
    is_overdue: bool
    payment_due_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    items: list[OrderItemResponse] = []
