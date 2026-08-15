import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.security import create_access_token
from apps.backend.app.models import (
    Customer,
    DiningSession,
    RestaurantTable,
    SessionStatus,
    TableStatus,
)
from apps.backend.app.repositories import CustomerRepository, SessionRepository, TableRepository
from apps.backend.app.services.admin_auth_service import AdminAuthService
from apps.backend.app.services.session_service import SessionService


@pytest.fixture
async def admin_auth_header(db_session: AsyncSession) -> dict[str, str]:
    service = AdminAuthService(db_session)
    admin = await service.create_admin_user(
        username="table_admin",
        password="password123",
        role="admin",
    )
    token = create_access_token({"sub": admin.username, "user_id": admin.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_tables_unauthenticated_rejected(client: AsyncClient):
    """Test unauthenticated access to table endpoints is rejected with 401."""
    res_get = await client.get("/api/admin/tables")
    assert res_get.status_code == 401

    res_post = await client.post("/api/admin/tables", json={"table_number": "T-99", "capacity": 4})
    assert res_post.status_code == 401

    res_patch = await client.patch("/api/admin/tables/1/position", json={"position_x": 100, "position_y": 100})
    assert res_patch.status_code == 401

    res_del = await client.delete("/api/admin/tables/1")
    assert res_del.status_code == 401


@pytest.mark.asyncio
async def test_create_table_with_valid_position_and_unique_tokens(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
):
    """Test creating table with coordinates and verifying backend generates unique QR token and deep link."""
    payload = {
        "table_number": "Meja-VIP-1",
        "capacity": 6,
        "position_x": 120,
        "position_y": 240,
    }
    res = await client.post("/api/admin/tables", json=payload, headers=admin_auth_header)
    assert res.status_code == 201
    data = res.json()

    assert data["table_number"] == "Meja-VIP-1"
    assert data["capacity"] == 6
    assert data["position_x"] == 120
    assert data["position_y"] == 240
    assert data["status"] == "AVAILABLE"
    assert data["is_active"] is True
    assert data["qr_code_token"].startswith("qr_")
    assert "start=" in data["deep_link_url"]


@pytest.mark.asyncio
async def test_create_table_duplicate_number_rejected(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
):
    """Test duplicate table_number returns 409 Conflict."""
    payload = {"table_number": "T-DUP", "capacity": 4, "position_x": 0, "position_y": 0}
    res1 = await client.post("/api/admin/tables", json=payload, headers=admin_auth_header)
    assert res1.status_code == 201

    res2 = await client.post("/api/admin/tables", json=payload, headers=admin_auth_header)
    assert res2.status_code == 409
    assert "sudah terdaftar" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_update_table_position_and_persistence(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
):
    """Test updating table layout position via drag-and-drop endpoint and persisting in DB."""
    # 1. Create table
    res_create = await client.post(
        "/api/admin/tables",
        json={"table_number": "T-POS-1", "capacity": 2, "position_x": 10, "position_y": 20},
        headers=admin_auth_header,
    )
    table_id = res_create.json()["id"]

    # 2. Patch new position (simulate drag and drop release)
    res_patch = await client.patch(
        f"/api/admin/tables/{table_id}/position",
        json={"position_x": 350, "position_y": 480},
        headers=admin_auth_header,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["position_x"] == 350
    assert res_patch.json()["position_y"] == 480

    # 3. Retrieve list and verify persistence
    res_list = await client.get("/api/admin/tables", headers=admin_auth_header)
    assert res_list.status_code == 200
    tables = res_list.json()
    t = next(x for x in tables if x["id"] == table_id)
    assert t["position_x"] == 350
    assert t["position_y"] == 480
    assert t["status"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_update_table_metadata(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
):
    """Test updating table metadata (table number and capacity)."""
    res_create = await client.post(
        "/api/admin/tables",
        json={"table_number": "T-ORIGINAL", "capacity": 2},
        headers=admin_auth_header,
    )
    table_id = res_create.json()["id"]

    res_update = await client.put(
        f"/api/admin/tables/{table_id}",
        json={"table_number": "T-RENAMED", "capacity": 8},
        headers=admin_auth_header,
    )
    assert res_update.status_code == 200
    assert res_update.json()["table_number"] == "T-RENAMED"
    assert res_update.json()["capacity"] == 8


@pytest.mark.asyncio
async def test_get_table_qr_info_stable(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
):
    """Test QR endpoint returns stable token without regenerating every view."""
    res_create = await client.post(
        "/api/admin/tables",
        json={"table_number": "T-QR-TEST", "capacity": 4},
        headers=admin_auth_header,
    )
    table_id = res_create.json()["id"]
    initial_qr = res_create.json()["qr_code_token"]

    res_qr1 = await client.get(f"/api/admin/tables/{table_id}/qr", headers=admin_auth_header)
    assert res_qr1.status_code == 200
    assert res_qr1.json()["qr_code_token"] == initial_qr

    res_qr2 = await client.get(f"/api/admin/tables/{table_id}/qr", headers=admin_auth_header)
    assert res_qr2.status_code == 200
    assert res_qr2.json()["qr_code_token"] == initial_qr


@pytest.mark.asyncio
async def test_cannot_deactivate_table_with_active_session(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
    db_session: AsyncSession,
):
    """Test deactivation fails (400) if table currently has an active dining session."""
    # 1. Create table
    table_repo = TableRepository(db_session)
    table = await table_repo.create(table_number="T-ACTIVE-LOCK", qr_code_token="qr_lock_123", capacity=4)

    # 2. Create customer and active session
    cust_repo = CustomerRepository(db_session)
    customer = await cust_repo.create(telegram_id=987001, username="active_diner")
    session_service = SessionService(db_session)
    await session_service.reserve_table_by_qr(customer_id=customer.id, qr_code_token="qr_lock_123")

    # 3. Attempt to deactivate -> 400 Bad Request
    res_del = await client.delete(f"/api/admin/tables/{table.id}", headers=admin_auth_header)
    assert res_del.status_code == 400
    assert "memiliki sesi aktif" in res_del.json()["detail"]


@pytest.mark.asyncio
async def test_historical_table_soft_deactivation(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
    db_session: AsyncSession,
):
    """Test table with historical session is soft-deactivated (is_active=False) rather than hard-deleted."""
    # 1. Create table & session
    table_repo = TableRepository(db_session)
    table = await table_repo.create(table_number="T-HIST-1", qr_code_token="qr_hist_123", capacity=4)
    cust_repo = CustomerRepository(db_session)
    customer = await cust_repo.create(telegram_id=987002, username="past_diner")
    session_service = SessionService(db_session)
    session = await session_service.reserve_table_by_qr(customer_id=customer.id, qr_code_token="qr_hist_123")

    # 2. Complete session
    await session_service.complete_session(session.id)

    # 3. Deactivate table
    res_del = await client.delete(f"/api/admin/tables/{table.id}", headers=admin_auth_header)
    assert res_del.status_code == 200
    data = res_del.json()
    assert data["action"] == "deactivated"

    # 4. Check DB: table record remains with is_active = False
    refetched = await table_repo.get_by_id(table.id)
    assert refetched is not None
    assert refetched.is_active is False


@pytest.mark.asyncio
async def test_clean_table_without_history_hard_delete(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
    db_session: AsyncSession,
):
    """Test table without any historical data is hard-deleted from database."""
    table_repo = TableRepository(db_session)
    table = await table_repo.create(table_number="T-CLEAN-DELETE", qr_code_token="qr_clean_123", capacity=2)

    res_del = await client.delete(f"/api/admin/tables/{table.id}", headers=admin_auth_header)
    assert res_del.status_code == 200
    data = res_del.json()
    assert data["action"] == "deleted"

    refetched = await table_repo.get_by_id(table.id)
    assert refetched is None


@pytest.mark.asyncio
async def test_table_operational_status_controlled_by_session_lifecycle(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
    db_session: AsyncSession,
):
    """Test table status AVAILABLE/OCCUPIED is controlled by session lifecycle and not altered by position updates."""
    # 1. Create table -> AVAILABLE
    table_repo = TableRepository(db_session)
    table = await table_repo.create(table_number="T-LIFECYCLE", qr_code_token="qr_lifecycle_123", capacity=4)
    assert table.status == TableStatus.AVAILABLE

    # 2. Reserve -> OCCUPIED
    cust_repo = CustomerRepository(db_session)
    customer = await cust_repo.create(telegram_id=987003, username="lifecycle_diner", first_name="Budi")
    session_service = SessionService(db_session)
    session = await session_service.reserve_table_by_qr(customer_id=customer.id, qr_code_token="qr_lifecycle_123")

    # 3. Check admin table list sees OCCUPIED and active session details
    res_list = await client.get("/api/admin/tables", headers=admin_auth_header)
    t = next(x for x in res_list.json() if x["id"] == table.id)
    assert t["status"] == "OCCUPIED"
    assert t["active_session"] is not None
    assert t["active_session"]["customer"]["username"] == "lifecycle_diner"

    # 4. Drag and drop (update position) does NOT change OCCUPIED status
    res_patch = await client.patch(
        f"/api/admin/tables/{table.id}/position",
        json={"position_x": 500, "position_y": 300},
        headers=admin_auth_header,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "OCCUPIED"
    assert res_patch.json()["position_x"] == 500

    # 5. Complete session -> returns to AVAILABLE
    await session_service.complete_session(session.id)
    res_list_after = await client.get("/api/admin/tables", headers=admin_auth_header)
    t_after = next(x for x in res_list_after.json() if x["id"] == table.id)
    assert t_after["status"] == "AVAILABLE"
    assert t_after["active_session"] is None


@pytest.mark.asyncio
async def test_list_tables_no_missing_greenlet_regression(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
    db_session: AsyncSession,
):
    """
    Regression test for MissingGreenlet error on GET /api/admin/tables:
    Ensures that listing tables with active dining sessions and customer info
    does not trigger implicit lazy-loading IO when session objects are detached/expired.
    """
    # 1. Create table, customer, and active session
    table_repo = TableRepository(db_session)
    t1 = await table_repo.create(table_number="T-GREENLET-1", qr_code_token="qr_g1", capacity=4, position_x=50, position_y=60)
    t2_inactive = await table_repo.create(table_number="T-GREENLET-2", qr_code_token="qr_g2", capacity=2, position_x=150, position_y=160)
    await table_repo.update(t2_inactive, is_active=False)

    cust_repo = CustomerRepository(db_session)
    customer = await cust_repo.create(telegram_id=77712345, username="greenlet_user", first_name="Greenlet", last_name="Tester")

    session_service = SessionService(db_session)
    session = await session_service.reserve_table_by_qr(customer_id=customer.id, qr_code_token="qr_g1")

    # 2. Expire all objects from identity map to simulate fresh request / detached ORM state
    db_session.expire_all()

    # 3. Call GET /api/admin/tables?include_inactive=true
    res = await client.get("/api/admin/tables?include_inactive=true", headers=admin_auth_header)
    assert res.status_code == 200
    data = res.json()

    # Find table 1 (active session)
    table_item = next(t for t in data if t["id"] == t1.id)
    assert table_item["status"] == "OCCUPIED"
    assert table_item["position_x"] == 50
    assert table_item["position_y"] == 60
    assert table_item["is_active"] is True
    assert table_item["active_session"] is not None
    assert table_item["active_session"]["session_id"] == session.id
    assert table_item["active_session"]["customer"]["username"] == "greenlet_user"
    assert table_item["active_session"]["customer"]["telegram_id"] == 77712345
    assert table_item["active_session"]["customer"]["first_name"] == "Greenlet"
    assert table_item["active_session"]["customer"]["last_name"] == "Tester"

    # Find table 2 (inactive table listed when include_inactive=True)
    inactive_item = next(t for t in data if t["id"] == t2_inactive.id)
    assert inactive_item["is_active"] is False
    assert inactive_item["table_number"] == "T-GREENLET-2"

