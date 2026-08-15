from fastapi import APIRouter

from apps.backend.app.api.admin_orders import router as admin_orders_router
from apps.backend.app.api.health import router as health_router
from apps.backend.app.api.telegram import router as telegram_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(telegram_router)
api_router.include_router(admin_orders_router)

__all__ = ["api_router"]
