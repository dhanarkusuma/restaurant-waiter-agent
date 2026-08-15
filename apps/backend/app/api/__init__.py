from fastapi import APIRouter

from apps.backend.app.api.admin_analytics import router as admin_analytics_router
from apps.backend.app.api.admin_auth import router as admin_auth_router
from apps.backend.app.api.admin_customers import router as admin_customers_router
from apps.backend.app.api.admin_menu import router as admin_menu_router
from apps.backend.app.api.admin_orders import router as admin_orders_router
from apps.backend.app.api.health import router as health_router
from apps.backend.app.api.telegram import router as telegram_router

api_router = APIRouter()
# Health
api_router.include_router(health_router)
# Telegram webhook (customer channel)
api_router.include_router(telegram_router)
# Admin routers (JWT protected)
api_router.include_router(admin_auth_router)
api_router.include_router(admin_menu_router)
api_router.include_router(admin_orders_router)
api_router.include_router(admin_customers_router)
api_router.include_router(admin_analytics_router)

__all__ = ["api_router"]
