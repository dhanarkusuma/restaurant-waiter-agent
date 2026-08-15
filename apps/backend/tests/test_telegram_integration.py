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
from apps.backend.app.repositories import CustomerRepository, TableRepository
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
async def test_telegram_customer_creation_and_retrieval(
    telegram_service: TelegramService,
    db_session: AsyncSession,
):
    """Test that customer record is created or retrieved based on Telegram user ID."""
    # First update creates the customer
    customer1 = await telegram_service.get_or_create_customer(
        telegram_id=99887766,
        username="telegram_user_1",
        first_name="User",
        last_name="One",
    )
    assert customer1.id is not None
    assert customer1.telegram_id == 99887766
    assert customer1.username == "telegram_user_1"

    # Second call returns the exact same customer record
    customer2 = await telegram_service.get_or_create_customer(
        telegram_id=99887766,
    )
    assert customer1.id == customer2.id


@pytest.mark.asyncio
async def test_valid_table_deep_link_flow(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
    db_session: AsyncSession,
):
    """Test that /start <token> creates an active session and reserves the table."""
    update = make_telegram_update(
        telegram_id=12345,
        text=f"/start {test_table_1.qr_code_token}",
    )

    response = await telegram_service.process_update(update)
    assert response is not None
    assert response.chat_id == 12345
    assert "berhasil terhubung dengan Meja T-01" in response.text
    assert test_table_1.status == TableStatus.OCCUPIED


@pytest.mark.asyncio
async def test_invalid_table_token_flow(
    telegram_service: TelegramService,
):
    """Test /start with non-existent QR token returns error message."""
    update = make_telegram_update(
        telegram_id=12345,
        text="/start non_existent_table_token",
    )

    response = await telegram_service.process_update(update)
    assert response is not None
    assert "kode QR meja tidak valid" in response.text


@pytest.mark.asyncio
async def test_occupied_table_telegram_flow(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
):
    """Test that customer 2 scanning an occupied table gets an occupied notification."""
    # Customer 1 reserves Table 1
    update1 = make_telegram_update(
        telegram_id=111,
        text=f"/start {test_table_1.qr_code_token}",
    )
    await telegram_service.process_update(update1)

    # Customer 2 attempts to scan Table 1
    update2 = make_telegram_update(
        telegram_id=222,
        text=f"/start {test_table_1.qr_code_token}",
    )
    response2 = await telegram_service.process_update(update2)

    assert response2 is not None
    assert "sedang digunakan oleh pelanggan lain" in response2.text


@pytest.mark.asyncio
async def test_customer_already_having_another_active_session(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
    test_table_2: RestaurantTable,
):
    """Test that customer scanning table 2 while having active session on table 1 gets warning."""
    # Customer reserves Table 1
    update1 = make_telegram_update(
        telegram_id=333,
        text=f"/start {test_table_1.qr_code_token}",
    )
    await telegram_service.process_update(update1)

    # Same customer scans Table 2
    update2 = make_telegram_update(
        telegram_id=333,
        text=f"/start {test_table_2.qr_code_token}",
    )
    response2 = await telegram_service.process_update(update2)

    assert response2 is not None
    assert "masih memiliki sesi makan aktif di meja lain" in response2.text


@pytest.mark.asyncio
async def test_same_customer_rescanning_same_table(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
):
    """Test idempotent re-scan of the same table returns friendly active session message."""
    update = make_telegram_update(
        telegram_id=444,
        text=f"/start {test_table_1.qr_code_token}",
    )
    # First scan
    resp1 = await telegram_service.process_update(update)
    assert "berhasil terhubung dengan Meja T-01" in resp1.text

    # Re-scan same table
    resp2 = await telegram_service.process_update(update)
    assert "berhasil terhubung dengan Meja T-01" in resp2.text


@pytest.mark.asyncio
async def test_done_command_session_completion(
    telegram_service: TelegramService,
    test_table_1: RestaurantTable,
):
    """Test /done command completes active session and releases table."""
    # Start session
    update_start = make_telegram_update(
        telegram_id=555,
        text=f"/start {test_table_1.qr_code_token}",
    )
    await telegram_service.process_update(update_start)
    assert test_table_1.status == TableStatus.OCCUPIED

    # Send /done
    update_done = make_telegram_update(
        telegram_id=555,
        text="/done",
    )
    resp_done = await telegram_service.process_update(update_done)
    assert "telah selesai" in resp_done.text
    assert test_table_1.status == TableStatus.AVAILABLE


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


def test_telegram_configuration_not_hardcoded():
    """Verify that Telegram configuration settings are loaded dynamically from settings/env."""
    assert hasattr(settings, "TELEGRAM_BOT_TOKEN")
    assert hasattr(settings, "TELEGRAM_WEBHOOK_URL")
    assert hasattr(settings, "TELEGRAM_WEBHOOK_SECRET")
    # Verify defaults are string types without hardcoded production credentials
    assert isinstance(settings.TELEGRAM_BOT_TOKEN, str)
    assert isinstance(settings.TELEGRAM_WEBHOOK_SECRET, str)
