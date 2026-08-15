from datetime import datetime
from pydantic import BaseModel, Field

from apps.backend.app.models.models import TableStatus


class TableCreateRequest(BaseModel):
    table_number: str = Field(..., min_length=1, max_length=50, description="Unique table identifier/number")
    capacity: int = Field(default=4, ge=1, le=50, description="Seating capacity of the table")
    position_x: int = Field(default=0, description="X coordinate on visual floor layout")
    position_y: int = Field(default=0, description="Y coordinate on visual floor layout")


class TableUpdateRequest(BaseModel):
    table_number: str | None = Field(default=None, min_length=1, max_length=50)
    capacity: int | None = Field(default=None, ge=1, le=50)


class TablePositionUpdateRequest(BaseModel):
    position_x: int = Field(..., description="X coordinate on visual floor layout")
    position_y: int = Field(..., description="Y coordinate on visual floor layout")


class ActiveCustomerInfo(BaseModel):
    customer_id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class ActiveSessionInfo(BaseModel):
    session_id: int
    started_at: datetime
    last_order_completed_at: datetime | None = None
    customer: ActiveCustomerInfo | None = None


class TableResponse(BaseModel):
    id: int
    table_number: str
    status: TableStatus
    capacity: int
    position_x: int
    position_y: int
    is_active: bool
    qr_code_token: str
    deep_link_url: str
    created_at: datetime
    active_session: ActiveSessionInfo | None = None


class TableQRResponse(BaseModel):
    table_id: int
    table_number: str
    qr_code_token: str
    deep_link_url: str


class TableDeleteResponse(BaseModel):
    id: int
    action: str  # 'deactivated' or 'deleted'
    message: str
