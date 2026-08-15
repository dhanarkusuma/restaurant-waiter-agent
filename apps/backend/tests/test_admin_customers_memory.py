import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.security import create_access_token
from apps.backend.app.models import AdminUser, Customer
from apps.backend.app.repositories import CustomerRepository, MenuRepository
from apps.backend.app.services import AdminAuthService, CustomerMemoryService


@pytest.fixture
async def admin_auth_header(db_session: AsyncSession) -> dict[str, str]:
    service = AdminAuthService(db_session)
    admin = await service.create_admin_user(
        username="cust_viewer_admin",
        password="password123",
        role="admin",
    )
    token = create_access_token({"sub": admin.username, "user_id": admin.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def customer_with_data(db_session: AsyncSession) -> Customer:
    cust_repo = CustomerRepository(db_session)
    menu_repo = MenuRepository(db_session)
    memory_service = CustomerMemoryService(db_session)

    cust = await cust_repo.create(telegram_id=987654, username="john_doe", first_name="John")
    cat = await menu_repo.create_category(name="Minuman")
    item = await menu_repo.create_item(name="Kopi Tubruk", price=12000, category_id=cat.id)

    # Add memory and favorite
    await memory_service.save_memory(cust.id, "preference", "Suka kopi hitam tanpa gula")
    await memory_service.save_memory(cust.id, "dietary", "Tidak bisa konsumsi susu sapi (lactose intolerant)")
    await memory_service.add_favorite(cust.id, menu_id=item.id)

    return cust


@pytest.mark.asyncio
async def test_admin_customer_memory_viewer(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
    customer_with_data: Customer,
):
    """Test authenticated customer listing and memory viewer."""
    # 1. List customers
    res_list = await client.get("/api/admin/customers", headers=admin_auth_header)
    assert res_list.status_code == 200
    custs = res_list.json()
    assert any(c["id"] == customer_with_data.id for c in custs)

    # 2. View customer memory profile
    res_mem = await client.get(
        f"/api/admin/customers/{customer_with_data.id}/memory",
        headers=admin_auth_header,
    )
    assert res_mem.status_code == 200
    data = res_mem.json()
    assert data["customer_id"] == customer_with_data.id
    assert data["telegram_id"] == 987654
    assert len(data["memories"]["preference"]) == 1
    assert data["memories"]["preference"][0]["description"] == "Suka kopi hitam tanpa gula"
    assert len(data["memories"]["dietary"]) == 1
    assert len(data["favorites"]) == 1
    assert data["favorites"][0]["name"] == "Kopi Tubruk"


@pytest.mark.asyncio
async def test_customer_memory_viewer_unauthenticated_rejected(
    client: AsyncClient,
    customer_with_data: Customer,
):
    """Test unauthenticated access to customer memory is rejected."""
    res = await client.get(f"/api/admin/customers/{customer_with_data.id}/memory")
    assert res.status_code == 401
