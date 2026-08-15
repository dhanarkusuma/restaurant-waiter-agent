import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.models import (
    Customer,
    OrderStatus,
    PaymentStatus,
    RestaurantTable,
    SessionStatus,
)
from apps.backend.app.repositories import (
    CustomerRepository,
    MenuRepository,
    OrderRepository,
    SessionRepository,
    TableRepository,
)
from apps.backend.app.services.order_service import OrderDraftManager, OrderService


@pytest.fixture
async def setup_order_env(db_session: AsyncSession):
    cust_repo = CustomerRepository(db_session)
    table_repo = TableRepository(db_session)
    session_repo = SessionRepository(db_session)
    menu_repo = MenuRepository(db_session)

    # Customers
    cust1 = await cust_repo.create(telegram_id=10101, username="order_alice", first_name="Alice")
    cust2 = await cust_repo.create(telegram_id=20202, username="order_bob", first_name="Bob")

    # Tables
    table1 = await table_repo.create(table_number="T-01", qr_code_token="qr_t1", capacity=4)
    table2 = await table_repo.create(table_number="T-02", qr_code_token="qr_t2", capacity=2)

    # Sessions
    session1 = await session_repo.create(customer_id=cust1.id, table_id=table1.id)
    session2 = await session_repo.create(customer_id=cust2.id, table_id=table2.id)

    # Menu items
    cat = await menu_repo.create_category(name="Makanan Utama")
    item_nasi_goreng = await menu_repo.create_item(
        name="Nasi Goreng Kampung",
        price=30000,
        category_id=cat.id,
        is_available=True,
    )
    item_es_teh = await menu_repo.create_item(
        name="Es Teh Manis",
        price=8000,
        category_id=cat.id,
        is_available=True,
    )
    item_habis = await menu_repo.create_item(
        name="Ikan Bakar Rica",
        price=60000,
        category_id=cat.id,
        is_available=False,
    )

    draft_manager = OrderDraftManager()

    return {
        "cust1": cust1,
        "cust2": cust2,
        "session1": session1,
        "session2": session2,
        "table1": table1,
        "item_nasi_goreng": item_nasi_goreng,
        "item_es_teh": item_es_teh,
        "item_habis": item_habis,
        "draft_manager": draft_manager,
    }


@pytest.mark.asyncio
async def test_add_available_menu_items_to_draft(
    db_session: AsyncSession,
    setup_order_env,
):
    """Test adding available items with quantity and notes to order draft."""
    env = setup_order_env
    service = OrderService(db_session, draft_manager=env["draft_manager"])

    res = await service.add_item_to_draft(
        customer_id=env["cust1"].id,
        session_id=env["session1"].id,
        menu_name_or_id="Nasi Goreng Kampung",
        quantity=2,
        notes="pedas sedang, telur ceplok",
    )

    assert res["status"] == "added"
    assert res["added_item"] == "Nasi Goreng Kampung"
    assert res["quantity"] == 2
    assert res["draft"]["total_amount"] == 60000
    assert len(res["draft"]["items"]) == 1
    assert res["draft"]["items"][0]["notes"] == "pedas sedang, telur ceplok"


@pytest.mark.asyncio
async def test_reject_unavailable_and_nonexistent_menu_items(
    db_session: AsyncSession,
    setup_order_env,
):
    """Test that unavailable and non-existent menu items cannot be added to draft."""
    env = setup_order_env
    service = OrderService(db_session, draft_manager=env["draft_manager"])

    # Unavailable item
    res_unavail = await service.add_item_to_draft(
        customer_id=env["cust1"].id,
        session_id=env["session1"].id,
        menu_name_or_id="Ikan Bakar Rica",
        quantity=1,
    )
    assert res_unavail["status"] == "error"
    assert "sedang tidak tersedia" in res_unavail["message"]

    # Non-existent item
    res_missing = await service.add_item_to_draft(
        customer_id=env["cust1"].id,
        session_id=env["session1"].id,
        menu_name_or_id="Burger Keju Mewah",
        quantity=1,
    )
    assert res_missing["status"] == "error"
    assert "tidak ditemukan" in res_missing["message"]


@pytest.mark.asyncio
async def test_update_quantity_and_remove_from_draft(
    db_session: AsyncSession,
    setup_order_env,
):
    """Test updating item quantity and removing items from draft."""
    env = setup_order_env
    service = OrderService(db_session, draft_manager=env["draft_manager"])

    cid = env["cust1"].id
    sid = env["session1"].id

    await service.add_item_to_draft(cid, sid, "Nasi Goreng Kampung", quantity=1)
    await service.add_item_to_draft(cid, sid, "Es Teh Manis", quantity=1)

    # Update quantity
    update_res = await service.update_item_quantity(cid, sid, "Es Teh Manis", quantity=3)
    assert update_res["status"] == "updated"
    assert update_res["draft"]["total_amount"] == 30000 + (8000 * 3)  # 54000

    # Remove item
    rem_res = await service.remove_item_from_draft(cid, sid, "Nasi Goreng Kampung")
    assert rem_res["status"] == "removed"
    assert rem_res["draft"]["total_amount"] == 24000
    assert len(rem_res["draft"]["items"]) == 1


@pytest.mark.asyncio
async def test_draft_isolation_between_customers(
    db_session: AsyncSession,
    setup_order_env,
):
    """Test that drafts are strictly isolated per (customer_id, session_id)."""
    env = setup_order_env
    service = OrderService(db_session, draft_manager=env["draft_manager"])

    # Customer 1 adds Nasi Goreng
    await service.add_item_to_draft(env["cust1"].id, env["session1"].id, "Nasi Goreng Kampung", quantity=2)

    # Customer 2's draft should be empty
    c2_draft = await service.get_draft_summary(env["cust2"].id, env["session2"].id)
    assert c2_draft["is_empty"] is True
    assert c2_draft["total_amount"] == 0


@pytest.mark.asyncio
async def test_confirm_and_create_order_persists_in_db(
    db_session: AsyncSession,
    setup_order_env,
):
    """
    Test that explicit confirmation creates Order and OrderItem records in PostgreSQL
    with status=ORDERED and payment_status=UNPAID, and clears the draft.
    """
    env = setup_order_env
    service = OrderService(db_session, draft_manager=env["draft_manager"])
    order_repo = OrderRepository(db_session)

    cid = env["cust1"].id
    sid = env["session1"].id

    # Add items to draft
    await service.add_item_to_draft(cid, sid, "Nasi Goreng Kampung", quantity=2, notes="pedas")
    await service.add_item_to_draft(cid, sid, "Es Teh Manis", quantity=1)

    # Confirm and place order
    order_res = await service.confirm_and_create_order(cid, sid)
    assert order_res["status"] == "created"
    assert order_res["order_id"] is not None
    assert order_res["total_amount"] == (30000 * 2) + (8000 * 1)  # 68000
    assert order_res["order_status"] == OrderStatus.ORDERED.value
    assert order_res["payment_status"] == PaymentStatus.UNPAID.value

    # Verify persisted in PostgreSQL
    order_in_db = await order_repo.get_by_id(order_res["order_id"])
    assert order_in_db is not None
    assert order_in_db.customer_id == cid
    assert order_in_db.dining_session_id == sid
    assert order_in_db.table_id == env["table1"].id
    assert order_in_db.total_amount == 68000
    assert order_in_db.status == OrderStatus.ORDERED
    assert order_in_db.payment_status == PaymentStatus.UNPAID
    assert len(order_in_db.items) == 2

    # Verify draft is cleared
    draft_after = await service.get_draft_summary(cid, sid)
    assert draft_after["is_empty"] is True


@pytest.mark.asyncio
async def test_prevent_order_creation_from_empty_draft(
    db_session: AsyncSession,
    setup_order_env,
):
    """Test that attempting to confirm an empty draft fails cleanly."""
    env = setup_order_env
    service = OrderService(db_session, draft_manager=env["draft_manager"])

    res = await service.confirm_and_create_order(env["cust1"].id, env["session1"].id)
    assert res["status"] == "error"
    assert "masih kosong" in res["message"]
