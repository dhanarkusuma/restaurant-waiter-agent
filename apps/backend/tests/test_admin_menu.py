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
    assert res_cat.status_code in [200, 201]
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


@pytest.mark.asyncio
async def test_admin_category_management_and_deletion_safety(
    client: AsyncClient,
    admin_auth_header: dict[str, str],
):
    """
    Test Category Management API:
    - List categories
    - Create category
    - Update category name & description
    - Duplicate category rejection
    - Category deletion rejected if referenced by menu items
    - Category deletion allowed if unreferenced
    - Unauthenticated rejection
    """
    # 1. Unauthenticated access rejected
    res_unauth = await client.get("/api/admin/categories")
    assert res_unauth.status_code == 401

    res_post_unauth = await client.post("/api/admin/categories", json={"name": "Test Cat"})
    assert res_post_unauth.status_code == 401

    # 2. Create category
    res_create = await client.post(
        "/api/admin/categories",
        json={"name": "Minuman Tradisional", "description": "Minuman herbal khas nusantara"},
        headers=admin_auth_header,
    )
    assert res_create.status_code == 201
    cat_data = res_create.json()
    cat_id = cat_data["id"]
    assert cat_data["name"] == "Minuman Tradisional"
    assert cat_data["description"] == "Minuman herbal khas nusantara"

    # 3. Duplicate category rejection
    res_dup = await client.post(
        "/api/admin/categories",
        json={"name": "Minuman Tradisional", "description": "Duplikat"},
        headers=admin_auth_header,
    )
    assert res_dup.status_code == 400
    assert "sudah ada" in res_dup.json()["detail"].lower()

    # 4. List categories includes newly created
    res_list = await client.get("/api/admin/categories", headers=admin_auth_header)
    assert res_list.status_code == 200
    cats = res_list.json()
    assert any(c["id"] == cat_id and c["name"] == "Minuman Tradisional" for c in cats)

    # 5. Update category
    res_upd = await client.put(
        f"/api/admin/categories/{cat_id}",
        json={"name": "Minuman Nusantara", "description": "Aneka minuman rempah"},
        headers=admin_auth_header,
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["name"] == "Minuman Nusantara"
    assert res_upd.json()["description"] == "Aneka minuman rempah"

    # 6. Create Menu Item referencing this category
    res_item = await client.post(
        "/api/admin/menu/items",
        json={
            "name": "Wedang Jahe",
            "price": 12000,
            "category_id": cat_id,
            "description": "Hangat dan segar",
            "is_available": True,
        },
        headers=admin_auth_header,
    )
    assert res_item.status_code == 200
    item_id = res_item.json()["id"]

    # 7. Attempt to delete category referenced by menu item -> REJECTED with 400
    res_del_ref = await client.delete(f"/api/admin/categories/{cat_id}", headers=admin_auth_header)
    assert res_del_ref.status_code == 400
    assert "masih digunakan" in res_del_ref.json()["detail"].lower()

    # 8. Delete the menu item, then category deletion must succeed
    await client.delete(f"/api/admin/menu/items/{item_id}", headers=admin_auth_header)

    res_del_ok = await client.delete(f"/api/admin/categories/{cat_id}", headers=admin_auth_header)
    assert res_del_ok.status_code == 200
    assert res_del_ok.json()["action"] == "deleted"

    # 9. Verify category no longer in list
    res_list_after = await client.get("/api/admin/categories", headers=admin_auth_header)
    assert not any(c["id"] == cat_id for c in res_list_after.json())

