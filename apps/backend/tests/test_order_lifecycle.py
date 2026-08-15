from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.exceptions import InvalidOrderStatusTransitionError
from apps.backend.app.models import (
    Customer,
    DiningSession,
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
from apps.backend.app.services.session_service import SessionService


@pytest.fixture
async def lifecycle_env(db_session: AsyncSession):
    cust_repo = CustomerRepository(db_session)
    table_repo = TableRepository(db_session)
    session_repo = SessionRepository(db_session)
    menu_repo = MenuRepository(db_session)

    cust = await cust_repo.create(telegram_id=30303, username="lifecycle_user", first_name="Charlie")
    table = await table_repo.create(table_number="T-12", qr_code_token="qr_t12", capacity=4)
    session = await session_repo.create(customer_id=cust.id, table_id=table.id)

    cat = await menu_repo.create_category(name="Makanan Utama")
    item = await menu_repo.create_item(name="Ayam Geprek", price=25000, category_id=cat.id, is_available=True)

    draft_mgr = OrderDraftManager()
    order_service = OrderService(db_session, draft_manager=draft_mgr)

    # Add item and create order
    await order_service.add_item_to_draft(cust.id, session.id, "Ayam Geprek", quantity=2)
    order_dict = await order_service.confirm_and_create_order(cust.id, session.id)

    return {
        "cust": cust,
        "table": table,
        "session": session,
        "item": item,
        "order_id": order_dict["order_id"],
        "order_service": order_service,
    }


@pytest.mark.asyncio
async def test_order_status_transitions_ordered_to_in_progress_to_done(
    db_session: AsyncSession,
    lifecycle_env,
):
    """Test valid forward transitions: ORDERED -> IN_PROGRESS -> DONE."""
    service: OrderService = lifecycle_env["order_service"]
    order_id = lifecycle_env["order_id"]

    # 1. ORDERED -> IN_PROGRESS
    order_in_prog = await service.update_order_status(order_id, OrderStatus.IN_PROGRESS)
    assert order_in_prog.status == OrderStatus.IN_PROGRESS
    assert order_in_prog.completed_at is None

    # 2. IN_PROGRESS -> DONE
    done_time = datetime(2026, 8, 15, 12, 30, tzinfo=timezone.utc)
    order_done = await service.update_order_status(order_id, OrderStatus.DONE, completed_at=done_time)
    assert order_done.status == OrderStatus.DONE
    assert order_done.completed_at == done_time

    # 3. Verify session last_order_completed_at is updated
    session_repo = SessionRepository(db_session)
    session = await session_repo.get_by_id(lifecycle_env["session"].id)
    assert session.last_order_completed_at == done_time


@pytest.mark.asyncio
async def test_invalid_order_status_transitions(
    db_session: AsyncSession,
    lifecycle_env,
):
    """Test that invalid and backward transitions raise InvalidOrderStatusTransitionError."""
    service: OrderService = lifecycle_env["order_service"]
    order_id = lifecycle_env["order_id"]

    # 1. Skipping IN_PROGRESS (ORDERED -> DONE) is invalid
    with pytest.raises(InvalidOrderStatusTransitionError):
        await service.update_order_status(order_id, OrderStatus.DONE)

    # Advance to IN_PROGRESS
    await service.update_order_status(order_id, OrderStatus.IN_PROGRESS)

    # 2. Backward to ORDERED (IN_PROGRESS -> ORDERED) is invalid
    with pytest.raises(InvalidOrderStatusTransitionError):
        await service.update_order_status(order_id, OrderStatus.ORDERED)

    # Advance to DONE
    await service.update_order_status(order_id, OrderStatus.DONE)

    # 3. Double completion (DONE -> DONE) or backward (DONE -> IN_PROGRESS) is invalid
    with pytest.raises(InvalidOrderStatusTransitionError):
        await service.update_order_status(order_id, OrderStatus.DONE)

    with pytest.raises(InvalidOrderStatusTransitionError):
        await service.update_order_status(order_id, OrderStatus.IN_PROGRESS)


@pytest.mark.asyncio
async def test_admin_manual_payment_and_idempotency(
    db_session: AsyncSession,
    lifecycle_env,
):
    """Test admin marking order as PAID and idempotent behavior."""
    service: OrderService = lifecycle_env["order_service"]
    order_id = lifecycle_env["order_id"]

    # Initial payment_status is UNPAID
    order = await service.get_order_by_id(order_id)
    assert order.payment_status == PaymentStatus.UNPAID

    # Mark PAID
    paid_order = await service.mark_order_as_paid(order_id)
    assert paid_order.payment_status == PaymentStatus.PAID
    assert paid_order.is_overdue is False

    # Second mark PAID is idempotent
    paid_order_again = await service.mark_order_as_paid(order_id)
    assert paid_order_again.payment_status == PaymentStatus.PAID


@pytest.mark.asyncio
async def test_payment_timeout_overdue_calculation(
    db_session: AsyncSession,
    lifecycle_env,
):
    """Test that unpaid order passes payment_due_at and becomes overdue."""
    service: OrderService = lifecycle_env["order_service"]
    order_id = lifecycle_env["order_id"]

    order = await service.get_order_by_id(order_id)
    assert order.payment_due_at is not None

    # Before 10 minutes: not overdue
    t_before = order.created_at + timedelta(minutes=5)
    assert service.is_order_overdue(order, current_time=t_before) is False

    # After 10 minutes: overdue
    t_after = order.created_at + timedelta(minutes=11)
    assert service.is_order_overdue(order, current_time=t_after) is True

    # Process timeouts
    overdue_orders = await service.process_payment_timeouts(current_time=t_after)
    assert len(overdue_orders) == 1
    assert overdue_orders[0].id == order_id
    assert overdue_orders[0].is_overdue is True


@pytest.mark.asyncio
async def test_session_timeout_anchored_to_latest_completed_order(
    db_session: AsyncSession,
    lifecycle_env,
):
    """
    Test that session auto-termination uses latest completed order timestamp
    as anchor for the 30-minute timeout.
    """
    order_service: OrderService = lifecycle_env["order_service"]
    session_service = SessionService(db_session)
    order_id = lifecycle_env["order_id"]
    session_id = lifecycle_env["session"].id

    order_done_time = datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)
    # Move order to IN_PROGRESS then DONE at 10:00
    await order_service.update_order_status(order_id, OrderStatus.IN_PROGRESS)
    await order_service.update_order_status(order_id, OrderStatus.DONE, completed_at=order_done_time)

    session_repo = SessionRepository(db_session)
    session = await session_repo.get_by_id(session_id)
    assert session.last_order_completed_at == order_done_time

    # At 10:20 (20 min after order completed): session is NOT expired
    t_20min = datetime(2026, 8, 15, 10, 20, tzinfo=timezone.utc)
    assert session_service.is_session_expired(session, current_time=t_20min) is False

    # At 10:31 (31 min after order completed): session IS expired
    t_31min = datetime(2026, 8, 15, 10, 31, tzinfo=timezone.utc)
    assert session_service.is_session_expired(session, current_time=t_31min) is True

    # Process session timeouts
    expired_sessions = await session_service.process_session_timeouts(current_time=t_31min)
    assert len(expired_sessions) == 1
    assert expired_sessions[0].id == session_id
    assert expired_sessions[0].status == SessionStatus.COMPLETED
