import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.auth.security import create_access_token
from apps.backend.app.models import AdminUser
from apps.backend.app.services.admin_auth_service import AdminAuthService


@pytest.fixture
async def admin_auth_header(db_session: AsyncSession) -> dict[str, str]:
    service = AdminAuthService(db_session)
    admin = await service.create_admin_user(
        username="menu_admin",
        password="password123",
        role="admin",
    )
    token = create_access_token({"sub": admin.username, "user_id": admin.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_menu_unauthenticated_rejected(client: AsyncClient):
    """Test unauthenticated access to menu management is rejected with 401."""
    res = await client.get("/api/admin/menu/items")
    assert res.status_code == 401

    res_post = await client.post("/api/admin/menu/items", json={"name": "Test", "price": 10000})
    assert res_post.status_code == 401


@pytest.mark.asyncio
async def test_admin_category_and_menu_crud(client: AsyncClient, admin_auth_header: dict[str, str]):
    """Test full authenticated CRUD flow for categories and menu items."""
    # 1. Create Category
    res_cat = await client.post(
        "/api/admin/menu/categories",
        json={"name": "Hidangan Pembuka", "description": "Appetizer lezat"},
        headers=admin_auth_header,
    )
    assert res_cat.status_code == 200
    cat_id = res_cat.json()["id"]

    # 2. Create Menu Item
    res_item = await client.post(
        "/api/admin/menu/items",
        json={
            "name": "Lumpia Semarang",
            "price": 18000,
            "category_id": cat_id,
            "description": "Lumpia rebung gurih renyah",
            "is_available": True,
        },
        headers=admin_auth_header,
    )
    assert res_item.status_code == 200
    item_id = res_item.json()["id"]
    assert res_item.json()["name"] == "Lumpia Semarang"
    assert res_item.json()["category_name"] == "Hidangan Pembuka"

    # 3. List Menu Items
    res_list = await client.get("/api/admin/menu/items", headers=admin_auth_header)
    assert res_list.status_code == 200
    items = res_list.json()
    assert any(i["id"] == item_id for i in items)

    # 4. Update Menu Item
    res_upd = await client.put(
        f"/api/admin/menu/items/{item_id}",
        json={"price": 20000, "description": "Lumpia rebung spesial"},
        headers=admin_auth_header,
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["price"] == 20000
    assert res_upd.json()["description"] == "Lumpia rebung spesial"

    # 5. Quick Availability Toggle
    res_avail = await client.patch(
        f"/api/admin/menu/items/{item_id}/availability",
        json={"is_available": False},
        headers=admin_auth_header,
    )
    assert res_avail.status_code == 200
    assert res_avail.json()["is_available"] is False

    # 6. Delete or Deactivate Item
    res_del = await client.delete(
        f"/api/admin/menu/items/{item_id}",
        headers=admin_auth_header,
    )
    assert res_del.status_code == 200
    assert res_del.json()["action"] in ["deleted", "deactivated"]
