from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.config import settings
from apps.backend.app.exceptions import (
    CustomerAlreadyHasActiveSessionError,
    SessionNotActiveError,
    SessionNotFoundError,
    TableAlreadyOccupiedError,
    TableNotFoundError,
)
from apps.backend.app.models import (
    Customer,
    DiningSession,
    RestaurantTable,
    SessionStatus,
    TableStatus,
)
from apps.backend.app.repositories import CustomerRepository, TableRepository
from apps.backend.app.services import SessionService


@pytest.fixture
async def session_service(db_session: AsyncSession) -> SessionService:
    return SessionService(db_session)


@pytest.fixture
async def sample_customer(db_session: AsyncSession) -> Customer:
    repo = CustomerRepository(db_session)
    return await repo.create(telegram_id=1001, username="test_customer", first_name="Alice")


@pytest.fixture
async def sample_customer_2(db_session: AsyncSession) -> Customer:
    repo = CustomerRepository(db_session)
    return await repo.create(telegram_id=1002, username="test_customer_2", first_name="Bob")


@pytest.fixture
async def sample_table(db_session: AsyncSession) -> RestaurantTable:
    repo = TableRepository(db_session)
    return await repo.create(table_number="T1", qr_code_token="qr_table_1", capacity=4)


@pytest.fixture
async def sample_table_2(db_session: AsyncSession) -> RestaurantTable:
    repo = TableRepository(db_session)
    return await repo.create(table_number="T2", qr_code_token="qr_table_2", capacity=2)


@pytest.mark.asyncio
async def test_available_table_can_be_reserved(
    session_service: SessionService,
    sample_customer: Customer,
    sample_table: RestaurantTable,
):
    """Test that a customer can successfully reserve an AVAILABLE table via valid QR token."""
    session = await session_service.reserve_table_by_qr(
        customer_id=sample_customer.id,
        qr_code_token=sample_table.qr_code_token,
    )

    assert session is not None
    assert session.customer_id == sample_customer.id
    assert session.table_id == sample_table.id
    assert session.status == SessionStatus.ACTIVE
    assert sample_table.status == TableStatus.OCCUPIED


@pytest.mark.asyncio
async def test_invalid_qr_token_raises_not_found(
    session_service: SessionService,
    sample_customer: Customer,
):
    """Test that an invalid QR token raises TableNotFoundError."""
    with pytest.raises(TableNotFoundError):
        await session_service.reserve_table_by_qr(
            customer_id=sample_customer.id,
            qr_code_token="non_existent_token",
        )


@pytest.mark.asyncio
async def test_occupied_table_cannot_be_reserved(
    session_service: SessionService,
    sample_customer: Customer,
    sample_customer_2: Customer,
    sample_table: RestaurantTable,
):
    """Test that an already occupied table cannot be reserved by another customer."""
    # Customer 1 reserves Table 1
    await session_service.reserve_table_by_qr(
        customer_id=sample_customer.id,
        qr_code_token=sample_table.qr_code_token,
    )

    # Customer 2 attempts to reserve Table 1
    with pytest.raises(TableAlreadyOccupiedError):
        await session_service.reserve_table_by_qr(
            customer_id=sample_customer_2.id,
            qr_code_token=sample_table.qr_code_token,
        )


@pytest.mark.asyncio
async def test_customer_cannot_have_multiple_active_sessions(
    session_service: SessionService,
    sample_customer: Customer,
    sample_table: RestaurantTable,
    sample_table_2: RestaurantTable,
):
    """Test that a customer with an active session cannot reserve a second different table."""
    # Customer reserves Table 1
    await session_service.reserve_table_by_qr(
        customer_id=sample_customer.id,
        qr_code_token=sample_table.qr_code_token,
    )

    # Customer attempts to reserve Table 2 while still active on Table 1
    with pytest.raises(CustomerAlreadyHasActiveSessionError):
        await session_service.reserve_table_by_qr(
            customer_id=sample_customer.id,
            qr_code_token=sample_table_2.qr_code_token,
        )


@pytest.mark.asyncio
async def test_customer_rescan_same_table_returns_existing_active_session(
    session_service: SessionService,
    sample_customer: Customer,
    sample_table: RestaurantTable,
):
    """Test that re-scanning the same table by the same customer returns their existing active session."""
    session1 = await session_service.reserve_table_by_qr(
        customer_id=sample_customer.id,
        qr_code_token=sample_table.qr_code_token,
    )

    session2 = await session_service.reserve_table_by_qr(
        customer_id=sample_customer.id,
        qr_code_token=sample_table.qr_code_token,
    )

    assert session1.id == session2.id
    assert session2.status == SessionStatus.ACTIVE


@pytest.mark.asyncio
async def test_session_completion_releases_table(
    session_service: SessionService,
    sample_customer: Customer,
    sample_customer_2: Customer,
    sample_table: RestaurantTable,
):
    """Test that completing a dining session sets session COMPLETED and table AVAILABLE again."""
    session = await session_service.reserve_table_by_qr(
        customer_id=sample_customer.id,
        qr_code_token=sample_table.qr_code_token,
    )
    assert sample_table.status == TableStatus.OCCUPIED

    # Complete the session
    completed_session = await session_service.complete_session(session.id)

    assert completed_session.status == SessionStatus.COMPLETED
    assert completed_session.completed_at is not None
    assert sample_table.status == TableStatus.AVAILABLE

    # Now Customer 2 can reserve the released table
    session_customer_2 = await session_service.reserve_table_by_qr(
        customer_id=sample_customer_2.id,
        qr_code_token=sample_table.qr_code_token,
    )
    assert session_customer_2.customer_id == sample_customer_2.id
    assert sample_table.status == TableStatus.OCCUPIED


@pytest.mark.asyncio
async def test_completing_already_completed_session_raises_error(
    session_service: SessionService,
    sample_customer: Customer,
    sample_table: RestaurantTable,
):
    """Test that attempting to complete an already completed session raises SessionNotActiveError."""
    session = await session_service.reserve_table_by_qr(
        customer_id=sample_customer.id,
        qr_code_token=sample_table.qr_code_token,
    )
    await session_service.complete_session(session.id)

    with pytest.raises(SessionNotActiveError):
        await session_service.complete_session(session.id)


@pytest.mark.asyncio
async def test_completing_non_existent_session_raises_error(
    session_service: SessionService,
):
    """Test that completing a non-existent session raises SessionNotFoundError."""
    with pytest.raises(SessionNotFoundError):
        await session_service.complete_session(99999)


@pytest.mark.asyncio
async def test_zero_order_session_timeout(
    session_service: SessionService,
    sample_customer: Customer,
    sample_table: RestaurantTable,
):
    """
    Test zero-order session timeout:
    Timeout anchor is session.started_at.
    Default timeout is 30 minutes.
    """
    now = datetime.now(timezone.utc)
    started_at = now - timedelta(minutes=31)

    # Directly create session started 31 minutes ago with no orders
    session = await session_service.session_repo.create(
        customer_id=sample_customer.id,
        table_id=sample_table.id,
        started_at=started_at,
    )
    await session_service.table_repo.update_status(sample_table, TableStatus.OCCUPIED)

    # At 29 minutes, it shouldn't be expired
    time_29m = started_at + timedelta(minutes=29)
    assert not session_service.is_session_expired(session, current_time=time_29m)

    # At 30+ minutes, it should be expired
    time_31m = started_at + timedelta(minutes=31)
    assert session_service.is_session_expired(session, current_time=time_31m)

    # Process timeouts
    expired = await session_service.process_session_timeouts(current_time=now)
    assert len(expired) == 1
    assert expired[0].id == session.id
    assert expired[0].status == SessionStatus.COMPLETED
    assert sample_table.status == TableStatus.AVAILABLE


@pytest.mark.asyncio
async def test_session_timeout_after_latest_completed_order(
    session_service: SessionService,
    sample_customer: Customer,
    sample_table: RestaurantTable,
):
    """
    Test timeout anchor when orders exist:
    Even if session started 2 hours ago, if last order completed 15 mins ago,
    session should NOT be expired.
    If last order completed 35 mins ago, session SHOULD be expired.
    """
    now = datetime.now(timezone.utc)
    session_start = now - timedelta(hours=2)

    session = await session_service.session_repo.create(
        customer_id=sample_customer.id,
        table_id=sample_table.id,
        started_at=session_start,
    )
    await session_service.table_repo.update_status(sample_table, TableStatus.OCCUPIED)

    # Order completed 15 minutes ago
    session.last_order_completed_at = now - timedelta(minutes=15)
    await session_service.session_repo.update(session)

    # With 30-min timeout, 15 minutes elapsed -> NOT expired
    assert not session_service.is_session_expired(session, current_time=now)

    # Simulate now advancing to 35 minutes after order completion
    later_time = session.last_order_completed_at + timedelta(minutes=35)
    assert session_service.is_session_expired(session, current_time=later_time)

    # Process timeout at later time
    expired = await session_service.process_session_timeouts(current_time=later_time)
    assert len(expired) == 1
    assert expired[0].id == session.id
    assert expired[0].status == SessionStatus.COMPLETED
    assert sample_table.status == TableStatus.AVAILABLE


@pytest.mark.asyncio
async def test_configurable_timeout_behavior(
    session_service: SessionService,
    sample_customer: Customer,
    sample_table: RestaurantTable,
):
    """Test that timeout duration is configurable (e.g. 15 minutes instead of 30 minutes)."""
    now = datetime.now(timezone.utc)
    started_at = now - timedelta(minutes=20)

    session = await session_service.session_repo.create(
        customer_id=sample_customer.id,
        table_id=sample_table.id,
        started_at=started_at,
    )

    # With default 30-min timeout, 20 mins elapsed -> NOT expired
    assert not session_service.is_session_expired(session, timeout_minutes=30, current_time=now)

    # With custom 15-min timeout, 20 mins elapsed -> EXPIRED
    assert session_service.is_session_expired(session, timeout_minutes=15, current_time=now)
