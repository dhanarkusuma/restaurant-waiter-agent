import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "restaurant-waiter-agent"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_api_health_check_endpoint(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_db_health_check_endpoint(client: AsyncClient):
    response = await client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["database"] == "connected"
