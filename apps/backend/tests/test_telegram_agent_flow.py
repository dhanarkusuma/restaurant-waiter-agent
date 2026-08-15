import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from agent.runner import WaiterAgentRunner
from apps.backend.app.models import Customer, RestaurantTable, TableStatus
from apps.backend.app.repositories import CustomerRepository, TableRepository
from apps.backend.app.schemas.telegram import (
    TelegramChat,
    TelegramMessage,
    TelegramUpdate,
    TelegramUser,
)
from apps.backend.app.services.session_service import SessionService
from apps.backend.app.services.telegram_service import TelegramService


class MockAgentRunner(WaiterAgentRunner):
    """Test double for WaiterAgentRunner recording invocations."""

    def __init__(self):
        self.invocations = []

    async def handle_customer_message(
        self,
        customer_id: int,
        session_id: int,
        message_text: str,
        table_number: str | None = None,
    ) -> str:
        self.invocations.append({
            "customer_id": customer_id,
            "session_id": session_id,
            "message_text": message_text,
            "table_number": table_number,
        })
        return f"[AI Waiter]: Halo! Anda sedang di Meja {table_number}. Pesan Anda: '{message_text}'"


@pytest.fixture
async def test_table(db_session: AsyncSession) -> RestaurantTable:
    repo = TableRepository(db_session)
    return await repo.create(table_number="T-07", qr_code_token="qr_table_07", capacity=4)


@pytest.mark.asyncio
async def test_telegram_message_routed_to_adk_agent_when_session_active(
    db_session: AsyncSession,
    test_table: RestaurantTable,
):
    """
    Test that conversational messages from a customer with an active session
    are routed to the ADK Waiter Agent with trusted context.
    """
    mock_runner = MockAgentRunner()
    telegram_service = TelegramService(db=db_session, agent_runner=mock_runner)

    telegram_id = 999111
    # 1. Customer reserves table via QR flow
    update_start = TelegramUpdate(
        update_id=1,
        message=TelegramMessage(
            message_id=10,
            from_user=TelegramUser(id=telegram_id, username="foodie_alice"),
            chat=TelegramChat(id=telegram_id),
            text=f"/start {test_table.qr_code_token}",
        ),
    )
    resp_start = await telegram_service.process_update(update_start)
    assert resp_start is not None
    assert "berhasil terhubung dengan Meja T-07" in resp_start.text

    # 2. Customer sends a conversational message
    update_msg = TelegramUpdate(
        update_id=2,
        message=TelegramMessage(
            message_id=11,
            from_user=TelegramUser(id=telegram_id, username="foodie_alice"),
            chat=TelegramChat(id=telegram_id),
            text="Permisi, apakah ada rekomendasi makanan yang enak?",
        ),
    )
    resp_msg = await telegram_service.process_update(update_msg)
    assert resp_msg is not None
    assert "[AI Waiter]: Halo! Anda sedang di Meja T-07" in resp_msg.text

    # 3. Verify mock runner received trusted backend context
    assert len(mock_runner.invocations) == 1
    inv = mock_runner.invocations[0]
    assert inv["table_number"] == "T-07"
    assert inv["message_text"] == "Permisi, apakah ada rekomendasi makanan yang enak?"
    assert inv["customer_id"] is not None
    assert inv["session_id"] is not None


@pytest.mark.asyncio
async def test_telegram_message_without_active_session_prompts_qr_scan(
    db_session: AsyncSession,
):
    """
    Test that conversational message from a customer without active session
    prompts them to scan QR code first before chatting with AI waiter.
    """
    mock_runner = MockAgentRunner()
    telegram_service = TelegramService(db=db_session, agent_runner=mock_runner)

    update = TelegramUpdate(
        update_id=3,
        message=TelegramMessage(
            message_id=12,
            from_user=TelegramUser(id=888222, username="new_user"),
            chat=TelegramChat(id=888222),
            text="Halo, saya mau pesan makanan.",
        ),
    )
    response = await telegram_service.process_update(update)

    assert response is not None
    assert "belum memiliki sesi makan yang aktif" in response.text
    assert "Silakan scan QR code" in response.text
    # Agent was NOT invoked because no active dining session exists
    assert len(mock_runner.invocations) == 0
