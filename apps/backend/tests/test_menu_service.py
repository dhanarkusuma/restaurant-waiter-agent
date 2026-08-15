import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.models import MenuCategory, MenuItem
from apps.backend.app.repositories import MenuRepository
from apps.backend.app.services import MenuService


@pytest.fixture
async def sample_menu_data(db_session: AsyncSession):
    """Seed sample categories and menu items for testing."""
    repo = MenuRepository(db_session)

    # Categories
    cat_food = await repo.create_category(name="Makanan Utama", description="Hidangan utama lezat")
    cat_beverage = await repo.create_category(name="Minuman", description="Minuman segar dan hangat")
    cat_dessert = await repo.create_category(name="Dessert", description="Hidangan penutup manis")

    # Available items
    item_nasi_goreng = await repo.create_item(
        name="Nasi Goreng Spesial",
        category_id=cat_food.id,
        price=35000,
        description="Nasi goreng dengan ayam suwir, telur mata sapi, dan acar pedas gurih",
        is_available=True,
    )
    item_ayam_bakar = await repo.create_item(
        name="Ayam Bakar Madu",
        category_id=cat_food.id,
        price=45000,
        description="Ayam bakar bumbu madu manis gurih disajikan dengan sambal terasi",
        is_available=True,
    )
    item_es_teh = await repo.create_item(
        name="Es Teh Manis",
        category_id=cat_beverage.id,
        price=8000,
        description="Teh melati dingin dengan gula asli yang menyegarkan",
        is_available=True,
    )
    item_jus_alpukat = await repo.create_item(
        name="Jus Alpukat",
        category_id=cat_beverage.id,
        price=20000,
        description="Jus buah alpukat segar dengan kental manis cokelat",
        is_available=True,
    )
    item_pisang_goreng = await repo.create_item(
        name="Pisang Goreng Keju",
        category_id=cat_dessert.id,
        price=18000,
        description="Pisang raja goreng krispi dengan taburan keju parut dan cokelat",
        is_available=True,
    )

    # Unavailable items (sold out)
    item_sop_buntut = await repo.create_item(
        name="Sop Buntut Sapi",
        category_id=cat_food.id,
        price=75000,
        description="Sop buntut empuk berkuah rempah gurih (Habis)",
        is_available=False,
    )
    item_es_kopi = await repo.create_item(
        name="Es Kopi Susu Aren",
        category_id=cat_beverage.id,
        price=22000,
        description="Kopi susu gula aren spesial (Habis)",
        is_available=False,
    )

    return {
        "categories": [cat_food, cat_beverage, cat_dessert],
        "available_items": [item_nasi_goreng, item_ayam_bakar, item_es_teh, item_jus_alpukat, item_pisang_goreng],
        "unavailable_items": [item_sop_buntut, item_es_kopi],
    }


@pytest.mark.asyncio
async def test_retrieve_all_available_menu_items(
    db_session: AsyncSession,
    sample_menu_data,
):
    """Test retrieving all available menu items by default."""
    service = MenuService(db_session)
    results = await service.search_menu()

    assert len(results) == 5
    names = [item["name"] for item in results]
    assert "Nasi Goreng Spesial" in names
    assert "Ayam Bakar Madu" in names
    assert "Es Teh Manis" in names
    assert "Jus Alpukat" in names
    assert "Pisang Goreng Keju" in names


@pytest.mark.asyncio
async def test_exclude_unavailable_menu_items(
    db_session: AsyncSession,
    sample_menu_data,
):
    """Test that unavailable (sold out) items are strictly excluded by default."""
    service = MenuService(db_session)
    results = await service.search_menu(only_available=True)

    names = [item["name"] for item in results]
    assert "Sop Buntut Sapi" not in names
    assert "Es Kopi Susu Aren" not in names
    for item in results:
        assert item["is_available"] is True


@pytest.mark.asyncio
async def test_category_filtering(
    db_session: AsyncSession,
    sample_menu_data,
):
    """Test searching menu items filtered by category."""
    service = MenuService(db_session)

    # Filter beverages
    beverages = await service.search_menu(category_name="Minuman")
    assert len(beverages) == 2
    for b in beverages:
        assert b["category"] == "Minuman"

    # Filter desserts
    desserts = await service.search_menu(category_name="Dessert")
    assert len(desserts) == 1
    assert desserts[0]["name"] == "Pisang Goreng Keju"


@pytest.mark.asyncio
async def test_price_filtering(
    db_session: AsyncSession,
    sample_menu_data,
):
    """Test filtering menu items within price range."""
    service = MenuService(db_session)

    # Items under 20,000 IDR
    cheap_items = await service.search_menu(max_price=20000)
    assert len(cheap_items) == 3
    for item in cheap_items:
        assert item["price"] <= 20000

    # Items between 20,000 and 40,000 IDR
    mid_items = await service.search_menu(min_price=20000, max_price=40000)
    assert len(mid_items) == 2
    names = [item["name"] for item in mid_items]
    assert "Jus Alpukat" in names
    assert "Nasi Goreng Spesial" in names


@pytest.mark.asyncio
async def test_keyword_search_name_and_description(
    db_session: AsyncSession,
    sample_menu_data,
):
    """Test search matching keyword in name or description."""
    service = MenuService(db_session)

    # Search by ingredient in description ('madu')
    honey_items = await service.search_menu(query="madu")
    assert len(honey_items) == 1
    assert honey_items[0]["name"] == "Ayam Bakar Madu"

    # Search by taste attribute ('manis')
    sweet_items = await service.search_menu(query="manis")
    assert len(sweet_items) >= 2
    names = [item["name"] for item in sweet_items]
    assert "Es Teh Manis" in names


@pytest.mark.asyncio
async def test_menu_details_lookup(
    db_session: AsyncSession,
    sample_menu_data,
):
    """Test single item lookup by ID."""
    service = MenuService(db_session)
    first_item = sample_menu_data["available_items"][0]

    details = await service.get_menu_details(first_item.id)
    assert details is not None
    assert details["id"] == first_item.id
    assert details["name"] == "Nasi Goreng Spesial"
    assert details["price"] == 35000

    # Non-existent ID lookup
    non_existent = await service.get_menu_details(99999)
    assert non_existent is None


@pytest.mark.asyncio
async def test_no_suitable_menu_result(
    db_session: AsyncSession,
    sample_menu_data,
):
    """Test empty results when no menu matches criteria."""
    service = MenuService(db_session)

    # Search for dish not in restaurant
    results = await service.search_menu(query="Pizza Pepperoni Super")
    assert results == []

    # Search with impossible price filter
    results_price = await service.search_menu(min_price=500000)
    assert results_price == []
