import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.config import settings
from apps.backend.app.models import (
    Customer,
    DiningSession,
    RestaurantTable,
    SessionStatus,
    TableStatus,
)
from apps.backend.app.repositories import CustomerRepository, SessionRepository, TableRepository
from apps.backend.app.schemas.telegram import (
    TelegramChat,
    TelegramMessage,
    TelegramUpdate,
    TelegramUser,
)
from apps.backend.app.services.telegram_service import TelegramService


@pytest.fixture
async def telegram_service(db_session: AsyncSession) -> TelegramService:
    return TelegramService(db_session)


@pytest.fixture
async def test_table_1(db_session: AsyncSession) -> RestaurantTable:
    repo = TableRepository(db_session)
    return await repo.create(table_number="T-01", qr_code_token="qr_table_01", capacity=4)


@pytest.fixture
async def test_table_2(db_session: AsyncSession) -> RestaurantTable:
    repo = TableRepository(db_session)
    return await repo.create(table_number="T-02", qr_code_token="qr_table_02", capacity=2)


def make_telegram_update(
    telegram_id: int,
    text: str,
    username: str = "john_doe",
    first_name: str = "John",
    update_id: int = 1,
    message_id: int = 100,
) -> TelegramUpdate:
    """Helper to construct TelegramUpdate objects for tests."""
    return TelegramUpdate(
        update_id=update_id,
        message=TelegramMessage(
            message_id=message_id,
            from_user=TelegramUser(
                id=telegram_id,
                is_bot=False,
                first_name=first_name,
                username=username,
            ),
            chat=TelegramChat(id=telegram_id, type="private"),
            text=text,
        ),
    )


@pytest.mark.asyncio
async def test_customer_creation_from_telegram_identity(
    telegram_service: TelegramService,
    db_session: AsyncSession,
):
    """Test that customer record is created on first interaction."""
    update = make_telegram_update(
        telegram_id=123456789,
        username="test_user",
        first_name="Alice",
        text="/start",
    )

    response = await telegram_service.process_update(update)
    assert response is not None
    assert response.chat_id == 123456789
    assert "Silakan scan QR code" in response.text

    # Verify customer in DB
    customer_repo = CustomerRepository(db_session)
    customer = await customer_repo.get_by_telegram_id(123456789)
    assert customer is not None
    assert customer.username == "test_user"
    assert customer.first_name == "Alice"


@pytest.mark.asyncio
async def test_customer_retrieval_existing_telegram_identity(
    telegram_service: TelegramService,
    db_session: AsyncSession,
):
    """Test retrieving existing customer without duplicate record creation."""
    customer_repo = CustomerRepository(db_session)
    created = await customer_repo.create(
        telegram_id=987654321,
        username="existing_user",
        first_name="Bob",
    )

    update = make_telegram_update(
        telegram_id=987654321,
        username="existing_user",
        text="/start",
    )
    await telegram_service.process_update(update)

    fetched = await customer_repo.get_by_telegram_id(987654321)
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_deep_link_qr_table_reservation(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
    db_session: AsyncSession,
):
    """Test /start <qr_token> successfully reserves an available table."""
    update = make_telegram_update(
        telegram_id=111222,
        text=f"/start {test_table_1.qr_code_token}",
    )

    response = await telegram_service.process_update(update)
    assert response is not None
    assert "berhasil terhubung dengan Meja T-01" in response.text
    assert "Sesi makan Anda telah aktif" in response.text

    # Verify table is now OCCUPIED
    table_repo = TableRepository(db_session)
    table = await table_repo.get_by_id(test_table_1.id)
    assert table.status == TableStatus.OCCUPIED


@pytest.mark.asyncio
async def test_deep_link_invalid_qr_token(
    telegram_service: TelegramService,
):
    """Test /start <invalid_token> returns error message."""
    update = make_telegram_update(
        telegram_id=333444,
        text="/start invalid_nonexistent_qr",
    )

    response = await telegram_service.process_update(update)
    assert response is not None
    assert "tidak valid atau tidak terdaftar" in response.text


@pytest.mark.asyncio
async def test_deep_link_occupied_table(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
    db_session: AsyncSession,
):
    """Test /start on already occupied table is rejected."""
    # User 1 reserves table 1
    update1 = make_telegram_update(
        telegram_id=101010,
        text=f"/start {test_table_1.qr_code_token}",
    )
    await telegram_service.process_update(update1)

    # User 2 tries to reserve same table 1
    update2 = make_telegram_update(
        telegram_id=202020,
        text=f"/start {test_table_1.qr_code_token}",
    )
    response2 = await telegram_service.process_update(update2)
    assert response2 is not None
    assert "sedang digunakan oleh pelanggan lain" in response2.text


@pytest.mark.asyncio
async def test_user_already_has_active_session_on_other_table(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
    test_table_2: RestaurantTable,
):
    """Test that customer cannot reserve a second table while first session is active."""
    # Reserve Table 1
    update1 = make_telegram_update(
        telegram_id=555666,
        text=f"/start {test_table_1.qr_code_token}",
    )
    await telegram_service.process_update(update1)

    # Try to reserve Table 2
    update2 = make_telegram_update(
        telegram_id=555666,
        text=f"/start {test_table_2.qr_code_token}",
    )
    response2 = await telegram_service.process_update(update2)
    assert response2 is not None
    assert "masih memiliki sesi makan aktif di meja lain" in response2.text


@pytest.mark.asyncio
async def test_re_entering_same_table_deep_link_resumes_session(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
):
    """Test that scanning same table QR when customer is already at that table resumes session."""
    update = make_telegram_update(
        telegram_id=777888,
        text=f"/start {test_table_1.qr_code_token}",
    )
    # First entry
    res1 = await telegram_service.process_update(update)
    assert "berhasil terhubung dengan Meja T-01" in res1.text

    # Re-scan same QR
    res2 = await telegram_service.process_update(update)
    assert "berhasil terhubung dengan Meja T-01" in res2.text


@pytest.mark.asyncio
async def test_start_without_token_when_session_active(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
):
    """Test /start without token when session is already active informs user of their table."""
    # First reserve
    await telegram_service.process_update(
        make_telegram_update(telegram_id=999111, text=f"/start {test_table_1.qr_code_token}")
    )

    # Now send plain /start
    res = await telegram_service.process_update(
        make_telegram_update(telegram_id=999111, text="/start")
    )
    assert res is not None
    assert "Selamat datang kembali" in res.text
    assert "Meja T-01" in res.text


@pytest.mark.asyncio
async def test_done_command_completes_session_and_releases_table(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
    db_session: AsyncSession,
):
    """Test /done completes active session and marks table AVAILABLE."""
    # Reserve
    await telegram_service.process_update(
        make_telegram_update(telegram_id=444555, text=f"/start {test_table_1.qr_code_token}")
    )

    # Terminate
    res = await telegram_service.process_update(
        make_telegram_update(telegram_id=444555, text="/done")
    )
    assert res is not None
    assert "telah selesai" in res.text
    assert "Meja telah dikosongkan" in res.text

    # Verify table AVAILABLE
    table_repo = TableRepository(db_session)
    table = await table_repo.get_by_id(test_table_1.id)
    assert table.status == TableStatus.AVAILABLE


@pytest.mark.asyncio
async def test_done_command_without_active_session(
    telegram_service: TelegramService,
):
    """Test /done when user has no active session."""
    res = await telegram_service.process_update(
        make_telegram_update(telegram_id=121212, text="/done")
    )
    assert res is not None
    assert "tidak memiliki sesi makan yang aktif" in res.text


@pytest.mark.asyncio
async def test_webhook_endpoint_handling(
    client: AsyncClient,
    test_table_1: RestaurantTable,
):
    """Test FastAPI HTTP webhook endpoint handling."""
    payload = {
        "update_id": 999,
        "message": {
            "message_id": 101,
            "from": {
                "id": 777888,
                "is_bot": False,
                "first_name": "WebhookUser",
            },
            "chat": {
                "id": 777888,
                "type": "private",
            },
            "text": f"/start {test_table_1.qr_code_token}",
        },
    }

    response = await client.post("/api/telegram/webhook", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "sendMessage"
    assert data["chat_id"] == 777888
    assert "berhasil terhubung dengan Meja T-01" in data["text"]


@pytest.mark.asyncio
async def test_webhook_secret_token_verification(
    client: AsyncClient,
    test_table_1: RestaurantTable,
    monkeypatch,
):
    """Test that Telegram webhook validates secret token when configured in settings."""
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "super_secret_token_123")

    payload = {
        "update_id": 1000,
        "message": {
            "message_id": 102,
            "from": {"id": 888999, "is_bot": False},
            "chat": {"id": 888999, "type": "private"},
            "text": "/start",
        },
    }

    # 1. Missing secret header -> 403 Forbidden
    res_missing = await client.post("/api/telegram/webhook", json=payload)
    assert res_missing.status_code == 403

    # 2. Invalid secret header -> 403 Forbidden
    res_invalid = await client.post(
        "/api/telegram/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"},
    )
    assert res_invalid.status_code == 403

    # 3. Valid secret header -> 200 OK
    res_valid = await client.post(
        "/api/telegram/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "super_secret_token_123"},
    )
    assert res_valid.status_code == 200


@pytest.mark.asyncio
async def test_no_missing_greenlet_on_lazy_relationship_access(
    telegram_service: TelegramService,
    db_session: AsyncSession,
    test_table_1: RestaurantTable,
):
    """
    Regression test for MissingGreenlet error:
    Ensure that processing incoming messages for a session with un-loaded table relationship
    uses TableRepository explicitly rather than lazy-loading `session.table`.
    """
    cust_repo = CustomerRepository(db_session)
    session_repo = SessionRepository(db_session)

    # 1. Create customer and active session directly without loaded table relationship
    cust = await cust_repo.create(telegram_id=999888777, username="greenlet_test_user")
    session = await session_repo.create(customer_id=cust.id, table_id=test_table_1.id)
    # Expire session instance so relationships are not loaded
    db_session.expire(session)

    # 2. Plain /start with active session (previously triggered lazy loading)
    res_start = await telegram_service.process_update(
        make_telegram_update(telegram_id=999888777, text="/start")
    )
    assert res_start is not None
    assert "Meja T-01" in res_start.text

    # 3. Conversational message with active session
    res_msg = await telegram_service.process_update(
        make_telegram_update(telegram_id=999888777, text="Halo apa kabar?")
    )
    assert res_msg is not None

    # 4. /done with active session
    res_done = await telegram_service.process_update(
        make_telegram_update(telegram_id=999888777, text="/done")
    )
    assert res_done is not None
    assert "Meja T-01" in res_done.text


def test_telegram_configuration_not_hardcoded():
    """Verify that Telegram configuration settings are loaded dynamically from settings/env."""
    assert hasattr(settings, "TELEGRAM_BOT_TOKEN")
    assert hasattr(settings, "TELEGRAM_WEBHOOK_URL")
    assert hasattr(settings, "TELEGRAM_WEBHOOK_SECRET")
    # Verify defaults are string types without hardcoded production credentials
    assert isinstance(settings.TELEGRAM_BOT_TOKEN, str)
    assert isinstance(settings.TELEGRAM_WEBHOOK_SECRET, str)
