from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    full_name: str | None = None


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str = "admin"
    full_name: str | None = None
    is_active: bool


class MenuCategoryCreateRequest(BaseModel):
    name: str
    description: str | None = None


class MenuCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class MenuItemCreateRequest(BaseModel):
    name: str
    price: int
    category_id: int | None = None
    description: str | None = None
    is_available: bool = True


class MenuItemUpdateRequest(BaseModel):
    name: str | None = None
    price: int | None = None
    category_id: int | None = None
    description: str | None = None
    is_available: bool | None = None


class MenuItemAvailabilityRequest(BaseModel):
    is_available: bool


class MenuItemAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int | None = None
    category_name: str | None = None
    name: str
    description: str | None = None
    price: int
    is_available: bool
    created_at: datetime
    updated_at: datetime | None = None


class CustomerMemoryViewerResponse(BaseModel):
    customer_id: int
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    created_at: datetime
    memories: dict[str, list[dict[str, Any]]]
    favorites: list[dict[str, Any]]


class PopularMenuItemResponse(BaseModel):
    menu_item_id: int
    name: str
    category: str | None = None
    total_quantity_ordered: int
    total_revenue: int


class TableUsageResponse(BaseModel):
    table_id: int
    table_number: str
    capacity: int
    total_sessions: int
