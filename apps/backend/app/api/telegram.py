import logging
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.config import settings
from apps.backend.app.database import get_db
from apps.backend.app.schemas.telegram import TelegramUpdate, TelegramWebhookResponse
from apps.backend.app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.post("/webhook", response_model=TelegramWebhookResponse | dict[str, str])
async def telegram_webhook(
    update: TelegramUpdate,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle incoming Telegram Webhook updates.
    Validates optional secret token and delegates business flow to TelegramService.
    """
    # Verify secret token if configured in settings
    if settings.TELEGRAM_WEBHOOK_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Invalid Telegram webhook secret token received.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Telegram webhook secret token",
            )

    telegram_service = TelegramService(db)
    response = await telegram_service.process_update(update)

    if response:
        return response

    return {"status": "ignored"}
