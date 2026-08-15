import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from agent.agents.waiter_agent import create_waiter_agent
from apps.backend.app.models import Customer
from apps.backend.app.repositories import CustomerRepository
from apps.backend.app.schemas.telegram import (
    TelegramChat,
    TelegramMessage,
    TelegramUpdate,
    TelegramUser,
)


@pytest.mark.asyncio
async def test_telegram_channel_operates_without_admin_jwt(client: AsyncClient):
    """
    Verify customer Telegram webhook endpoint is accessible without admin JWT token.
    Customer interactions use Telegram ID, not admin JWT.
    """
    update_payload = {
        "update_id": 99999,
        "message": {
            "message_id": 1,
            "from": {"id": 1234567, "username": "customer_sam"},
            "chat": {"id": 1234567},
            "text": "/start",
        },
    }
    response = await client.post("/api/telegram/webhook", json=update_payload)
    # Webhook responds 200 without requiring Admin JWT
    assert response.status_code == 200
    assert "Silakan scan QR code" in response.json()["text"]


@pytest.mark.asyncio
async def test_admin_endpoints_strictly_reject_non_admin(client: AsyncClient):
    """Verify all admin routes strictly reject requests without JWT."""
    admin_routes = [
        ("GET", "/api/admin/auth/me"),
        ("GET", "/api/admin/menu/items"),
        ("POST", "/api/admin/menu/items"),
        ("GET", "/api/admin/orders"),
        ("POST", "/api/admin/orders/1/pay"),
        ("GET", "/api/admin/customers"),
        ("GET", "/api/admin/customers/1/memory"),
        ("GET", "/api/admin/analytics/popular-menu"),
        ("GET", "/api/admin/analytics/table-usage"),
    ]

    for method, path in admin_routes:
        if method == "GET":
            res = await client.get(path)
        elif method == "POST":
            res = await client.post(path, json={})
        assert res.status_code == 401, f"{method} {path} should return 401 without JWT"


def test_customer_facing_agent_tools_isolation():
    """Verify customer-facing ADK agent cannot access admin operations."""
    agent = create_waiter_agent()
    tool_names = [t.__name__ for t in agent.tools]

    admin_tool_keywords = ["admin", "pay_order", "delete_menu", "create_menu", "analytics"]
    for tool_name in tool_names:
        for kw in admin_tool_keywords:
            assert kw not in tool_name.lower(), f"Customer agent tool {tool_name} violates boundary"
