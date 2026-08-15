import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.security import create_access_token
from apps.backend.app.models import AdminUser
from apps.backend.app.repositories import (
    CustomerRepository,
    MenuRepository,
    OrderRepository,
    SessionRepository,
    TableRepository,
)
from apps.backend.app.services import AdminAuthService, OrderDraftManager, OrderService


@pytest.fixture
async def admin_auth_header(db_session: AsyncSession) -> dict[str, str]:
    service = AdminAuthService(db_session)
    admin = await service.create_admin_user(
        username="analytics_admin",
        password="password123",
        role="admin",
    )
    token = create_access_token({"sub": admin.username, "user_id": admin.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seed_analytics_data(db_session: AsyncSession):
    cust_repo = CustomerRepository(db_session)
    table_repo = TableRepository(db_session)
    session_repo = SessionRepository(db_session)
    menu_repo = MenuRepository(db_session)

    cust = await cust_repo.create(telegram_id=667788, username="stats_user")
    table1 = await table_repo.create(table_number="T-01", qr_code_token="qr_stat_1", capacity=4)
    table2 = await table_repo.create(table_number="T-02", qr_code_token="qr_stat_2", capacity=2)

    session1 = await session_repo.create(customer_id=cust.id, table_id=table1.id)

    cat = await menu_repo.create_category(name="Makanan")
    item1 = await menu_repo.create_item(name="Nasi Uduk", price=20000, category_id=cat.id)
    item2 = await menu_repo.create_item(name="Es Jeruk", price=8000, category_id=cat.id)

    draft_mgr = OrderDraftManager()
    order_service = OrderService(db_session, draft_manager=draft_mgr)

    # Order 1: 3x Nasi Uduk, 2x Es Jeruk
    await order_service.add_item_to_draft(cust.id, session1.id, "Nasi Uduk", quantity=3)
    await order_service.add_item_to_draft(cust.id, session1.id, "Es Jeruk", quantity=2)
    await order_service.confirm_and_create_order(cust.id, session1.id)


@pytest.mark.asyncio
async def test_popular_menu_and_table_usage_analytics(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
    seed_analytics_data,
):
    """Test popular menu items and table usage aggregation analytics."""
    # 1. Popular Menu
    res_menu = await client.get("/api/admin/analytics/popular-menu", headers=admin_auth_header)
    assert res_menu.status_code == 200
    pop_items = res_menu.json()
    assert len(pop_items) >= 2
    top_item = pop_items[0]
    assert top_item["name"] == "Nasi Uduk"
    assert top_item["total_quantity_ordered"] == 3
    assert top_item["total_revenue"] == 60000

    # 2. Table Usage
    res_tables = await client.get("/api/admin/analytics/table-usage", headers=admin_auth_header)
    assert res_tables.status_code == 200
    tables = res_tables.json()
    assert len(tables) >= 2
    t1 = next(t for t in tables if t["table_number"] == "T-01")
    assert t1["total_sessions"] == 1


@pytest.mark.asyncio
async def test_analytics_unauthenticated_rejected(client: AsyncClient):
    """Test unauthenticated access to analytics endpoints returns 401."""
    res = await client.get("/api/admin/analytics/popular-menu")
    assert res.status_code == 401

    res_tables = await client.get("/api/admin/analytics/table-usage")
    assert res_tables.status_code == 401
