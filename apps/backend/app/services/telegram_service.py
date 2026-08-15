import logging
from typing import Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from agent.runner import WaiterAgentRunner, default_waiter_runner
from apps.backend.app.config import settings
from apps.backend.app.exceptions import (
    CustomerAlreadyHasActiveSessionError,
    TableAlreadyOccupiedError,
    TableNotFoundError,
)
from apps.backend.app.models import Customer, DiningSession
from apps.backend.app.repositories.customer_repository import CustomerRepository
from apps.backend.app.repositories.table_repository import TableRepository
from apps.backend.app.schemas.telegram import TelegramUpdate, TelegramWebhookResponse
from apps.backend.app.services.session_service import SessionService

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(
        self,
        db: AsyncSession,
        agent_runner: WaiterAgentRunner | None = None,
    ):
        self.db = db
        self.customer_repo = CustomerRepository(db)
        self.table_repo = TableRepository(db)
        self.session_service = SessionService(db)
        self.agent_runner = agent_runner or default_waiter_runner

    async def get_or_create_customer(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Customer:
        """Resolve or register customer record from Telegram identity."""
        return await self.customer_repo.get_or_create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

    def extract_deep_link_token(self, message_text: str) -> str | None:
        """
        Extract table QR token from a /start deep link.
        e.g., '/start qr_table_1' -> 'qr_table_1'
        e.g., '/start' -> None
        """
        if not message_text:
            return None
        parts = message_text.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0] == "/start":
            token = parts[1].strip()
            return token if token else None
        return None

    async def process_update(self, update: TelegramUpdate) -> TelegramWebhookResponse | None:
        """
        Process an incoming Telegram webhook update.
        Handles:
        - Customer resolution
        - QR deep-link table reservation flow (/start <qr_token>)
        - Session termination (/done)
        - ADK Waiter Agent conversation flow when session is active
        """
        message = update.message or update.edited_message
        if not message or not message.from_user or not message.text:
            return None

        telegram_user = message.from_user
        chat_id = message.chat.id
        raw_text = message.text.strip()

        # 1. Resolve / Create Customer from Telegram identity
        customer = await self.get_or_create_customer(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )

        response_text: str

        # 2. Check for /start deep link flow
        if raw_text.startswith("/start"):
            token = self.extract_deep_link_token(raw_text)
            if token:
                response_text = await self._handle_qr_deep_link(customer=customer, qr_token=token)
            else:
                # /start without QR deep-link token
                active_session = await self.session_service.get_active_session_for_customer(customer.id)
                if active_session:
                    table = await self.table_repo.get_by_id(active_session.table_id)
                    table_name = table.table_number if table else f"#{active_session.table_id}"
                    response_text = (
                        f"Selamat datang kembali! Anda saat ini terhubung dengan Meja {table_name}. "
                        "Sesi Anda sedang aktif. Ada yang bisa saya bantu?"
                    )
                else:
                    response_text = (
                        "Selamat datang di Restoran kami! "
                        "Silakan scan QR code yang tersedia di meja Anda untuk memulai pemesanan."
                    )

        # 3. Check for /done session termination flow
        elif raw_text == "/done":
            response_text = await self._handle_done_command(customer=customer)

        # 4. Conversational message flow with Google ADK Agent
        else:
            active_session = await self.session_service.get_active_session_for_customer(customer.id)
            if active_session:
                table = await self.table_repo.get_by_id(active_session.table_id)
                table_name = table.table_number if table else f"#{active_session.table_id}"
                response_text = await self.agent_runner.handle_customer_message(
                    customer_id=customer.id,
                    session_id=active_session.id,
                    message_text=raw_text,
                    table_number=table_name,
                )
            else:
                response_text = (
                    "Halo! Anda belum memiliki sesi makan yang aktif. "
                    "Silakan scan QR code di meja Anda terlebih dahulu untuk memulai pemesanan."
                )

        return TelegramWebhookResponse(chat_id=chat_id, text=response_text)

    async def _handle_qr_deep_link(self, customer: Customer, qr_token: str) -> str:
        """Handle QR scan deep link and table reservation."""
        try:
            session = await self.session_service.reserve_table_by_qr(
                customer_id=customer.id,
                qr_code_token=qr_token,
            )
            table = await self.table_repo.get_by_id(session.table_id)
            table_name = table.table_number if table else f"#{session.table_id}"
            return (
                f"Selamat datang di Restoran! Anda berhasil terhubung dengan Meja {table_name}. "
                "Sesi makan Anda telah aktif. Silakan tanyakan menu atau sampaikan apa yang ingin Anda pesan."
            )
        except TableNotFoundError:
            return "Maaf, kode QR meja tidak valid atau tidak terdaftar di sistem kami."
        except TableAlreadyOccupiedError:
            return "Maaf, meja ini sedang digunakan oleh pelanggan lain. Silakan gunakan meja yang masih tersedia atau hubungi staf restoran."
        except CustomerAlreadyHasActiveSessionError:
            return "Anda masih memiliki sesi makan aktif di meja lain. Selesaikan sesi tersebut terlebih dahulu atau hubungi staf restoran."

    async def _handle_done_command(self, customer: Customer) -> str:
        """Handle /done command to complete the customer's active session."""
        active_session = await self.session_service.get_active_session_for_customer(customer.id)
        if not active_session:
            return "Anda tidak memiliki sesi makan yang aktif saat ini."

        table = await self.table_repo.get_by_id(active_session.table_id)
        table_name = table.table_number if table else f"#{active_session.table_id}"

        await self.session_service.complete_session(active_session.id)
        return (
            f"Terima kasih! Sesi makan Anda di Meja {table_name} telah selesai. "
            "Meja telah dikosongkan. Sampai jumpa kembali!"
        )

    async def send_telegram_message(self, chat_id: int, text: str) -> bool:
        """
        Send outbound message via Telegram Bot API if bot token is configured.
        """
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            logger.debug("Telegram bot token not configured, skipping outbound HTTP call.")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.error("Failed to send Telegram message to chat %d: %s", chat_id, e)
            return False
