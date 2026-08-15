import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.security import create_access_token
from apps.backend.app.models import AdminUser, OrderStatus, PaymentStatus
from apps.backend.app.repositories import (
    CustomerRepository,
    MenuRepository,
    SessionRepository,
    TableRepository,
)
from apps.backend.app.services import AdminAuthService, OrderDraftManager, OrderService


@pytest.fixture
async def admin_auth_header(db_session: AsyncSession) -> dict[str, str]:
    service = AdminAuthService(db_session)
    admin = await service.create_admin_user(
        username="orders_admin",
        password="password123",
        role="admin",
    )
    token = create_access_token({"sub": admin.username, "user_id": admin.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_order(db_session: AsyncSession):
    cust_repo = CustomerRepository(db_session)
    table_repo = TableRepository(db_session)
    session_repo = SessionRepository(db_session)
    menu_repo = MenuRepository(db_session)

    cust = await cust_repo.create(telegram_id=881122, username="api_admin_user")
    table = await table_repo.create(table_number="T-99", qr_code_token="qr_t99")
    session = await session_repo.create(customer_id=cust.id, table_id=table.id)

    cat = await menu_repo.create_category(name="Makanan")
    item = await menu_repo.create_item(name="Soto Ayam", price=20000, category_id=cat.id)

    draft_mgr = OrderDraftManager()
    order_service = OrderService(db_session, draft_manager=draft_mgr)

    await order_service.add_item_to_draft(cust.id, session.id, "Soto Ayam", quantity=1)
    order_data = await order_service.confirm_and_create_order(cust.id, session.id)

    return {
        "order_id": order_data["order_id"],
        "cust": cust,
        "table": table,
        "session": session,
    }


@pytest.mark.asyncio
async def test_admin_list_and_get_orders(client: AsyncClient, admin_auth_header: dict[str, str], sample_order):
    """Test listing all orders and getting a single order via authenticated admin API."""
    order_id = sample_order["order_id"]

    # List orders
    res_list = await client.get("/api/admin/orders", headers=admin_auth_header)
    assert res_list.status_code == 200
    orders = res_list.json()
    assert len(orders) >= 1
    assert any(o["id"] == order_id for o in orders)

    # Get single order
    res_get = await client.get(f"/api/admin/orders/{order_id}", headers=admin_auth_header)
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["id"] == order_id
    assert data["status"] == OrderStatus.ORDERED.value
    assert data["payment_status"] == PaymentStatus.UNPAID.value


@pytest.mark.asyncio
async def test_admin_update_order_status_api(client: AsyncClient, admin_auth_header: dict[str, str], sample_order):
    """Test valid and invalid status updates via authenticated admin API."""
    order_id = sample_order["order_id"]

    # Valid: ORDERED -> IN_PROGRESS
    res_prog = await client.patch(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=admin_auth_header,
    )
    assert res_prog.status_code == 200
    assert res_prog.json()["status"] == OrderStatus.IN_PROGRESS.value

    # Invalid: IN_PROGRESS -> ORDERED (backward transition)
    res_invalid = await client.patch(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "ORDERED"},
        headers=admin_auth_header,
    )
    assert res_invalid.status_code == 400
    assert "Cannot transition" in res_invalid.json()["detail"]

    # Valid: IN_PROGRESS -> DONE
    res_done = await client.patch(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "DONE"},
        headers=admin_auth_header,
    )
    assert res_done.status_code == 200
    assert res_done.json()["status"] == OrderStatus.DONE.value
    assert res_done.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_admin_manual_payment_api(client: AsyncClient, admin_auth_header: dict[str, str], sample_order):
    """Test marking order as PAID via authenticated admin API."""
    order_id = sample_order["order_id"]

    res_pay = await client.post(f"/api/admin/orders/{order_id}/pay", headers=admin_auth_header)
    assert res_pay.status_code == 200
    assert res_pay.json()["payment_status"] == PaymentStatus.PAID.value

    # Idempotent second pay
    res_pay_again = await client.post(f"/api/admin/orders/{order_id}/pay", headers=admin_auth_header)
    assert res_pay_again.status_code == 200
    assert res_pay_again.json()["payment_status"] == PaymentStatus.PAID.value
