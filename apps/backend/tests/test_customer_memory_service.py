import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.app.models import Customer, MenuItem
from apps.backend.app.repositories import CustomerRepository, MenuRepository
from apps.backend.app.services import CustomerMemoryService


@pytest.fixture
async def customer_1(db_session: AsyncSession) -> Customer:
    repo = CustomerRepository(db_session)
    return await repo.create(telegram_id=5001, username="user_one", first_name="User1")


@pytest.fixture
async def customer_2(db_session: AsyncSession) -> Customer:
    repo = CustomerRepository(db_session)
    return await repo.create(telegram_id=5002, username="user_two", first_name="User2")


@pytest.fixture
async def menu_items_sample(db_session: AsyncSession):
    repo = MenuRepository(db_session)
    cat = await repo.create_category(name="Makanan Utama")
    item1 = await repo.create_item(name="Nasi Liwet", price=35000, category_id=cat.id, is_available=True)
    item2 = await repo.create_item(name="Sate Kambing", price=55000, category_id=cat.id, is_available=False)
    return {"item1": item1, "item2": item2}


@pytest.mark.asyncio
async def test_create_and_read_customer_memory(
    db_session: AsyncSession,
    customer_1: Customer,
):
    """Test creating memories of different types and reading them back in customer profile."""
    service = CustomerMemoryService(db_session)

    # Save dislike
    res1 = await service.save_memory(
        customer_id=customer_1.id,
        memory_type="dislike",
        description="Tidak suka makanan yang terlalu pedas",
    )
    assert res1["status"] == "created"
    assert res1["type"] == "dislike"

    # Save dietary
    res2 = await service.save_memory(
        customer_id=customer_1.id,
        memory_type="dietary",
        description="Alergi seafood dan udang",
    )
    assert res2["status"] == "created"
    assert res2["type"] == "dietary"

    # Read profile
    profile = await service.get_customer_profile(customer_1.id)
    assert profile["customer_id"] == customer_1.id
    assert len(profile["memories"]["dislike"]) == 1
    assert profile["memories"]["dislike"][0]["description"] == "Tidak suka makanan yang terlalu pedas"
    assert len(profile["memories"]["dietary"]) == 1
    assert profile["memories"]["dietary"][0]["description"] == "Alergi seafood dan udang"


@pytest.mark.asyncio
async def test_prevent_duplicate_equivalent_memories(
    db_session: AsyncSession,
    customer_1: Customer,
):
    """Test that creating a substantially similar memory updates the existing one rather than duplicating."""
    service = CustomerMemoryService(db_session)

    res1 = await service.save_memory(
        customer_id=customer_1.id,
        memory_type="preference",
        description="Suka teh manis dingin",
    )
    assert res1["status"] == "created"

    # Save similar/duplicate memory
    res2 = await service.save_memory(
        customer_id=customer_1.id,
        memory_type="preference",
        description="Suka teh manis dingin",
    )
    assert res2["status"] == "updated"
    assert res2["id"] == res1["id"]

    profile = await service.get_customer_profile(customer_1.id)
    assert len(profile["memories"]["preference"]) == 1


@pytest.mark.asyncio
async def test_explicitly_forget_memory_by_keyword(
    db_session: AsyncSession,
    customer_1: Customer,
):
    """Test that customer can explicitly ask to forget a memory by keyword."""
    service = CustomerMemoryService(db_session)

    await service.save_memory(
        customer_id=customer_1.id,
        memory_type="dislike",
        description="Tidak suka makanan pedas cabai rawit",
    )
    await service.save_memory(
        customer_id=customer_1.id,
        memory_type="preference",
        description="Suka jus alpukat manis",
    )

    # Forget pedas
    forget_res = await service.forget_memory(customer_id=customer_1.id, keyword="pedas")
    assert forget_res["status"] == "deleted"
    assert forget_res["count"] == 1
    assert "Tidak suka makanan pedas cabai rawit" in forget_res["deleted_descriptions"]

    # Verify profile now only contains the other memory
    profile = await service.get_customer_profile(customer_1.id)
    assert len(profile["memories"]["dislike"]) == 0
    assert len(profile["memories"]["preference"]) == 1


@pytest.mark.asyncio
async def test_add_and_retrieve_favorites(
    db_session: AsyncSession,
    customer_1: Customer,
    menu_items_sample,
):
    """Test adding favorite menu items and retrieving them."""
    service = CustomerMemoryService(db_session)
    item1 = menu_items_sample["item1"]

    res = await service.add_favorite(customer_id=customer_1.id, menu_id=item1.id)
    assert res["status"] == "added"
    assert res["name"] == "Nasi Liwet"

    favs = await service.get_favorites(customer_1.id)
    assert len(favs) == 1
    assert favs[0]["name"] == "Nasi Liwet"
    assert favs[0]["is_available"] is True


@pytest.mark.asyncio
async def test_favorite_available_even_when_item_is_unavailable(
    db_session: AsyncSession,
    customer_1: Customer,
    menu_items_sample,
):
    """Test that a menu item can be favorited and identified even if currently unavailable."""
    service = CustomerMemoryService(db_session)
    item2 = menu_items_sample["item2"]  # is_available = False

    res = await service.add_favorite(customer_id=customer_1.id, menu_id=item2.id)
    assert res["status"] == "added"
    assert res["name"] == "Sate Kambing"
    assert res["is_available"] is False

    favs = await service.get_favorites(customer_1.id)
    assert len(favs) == 1
    assert favs[0]["name"] == "Sate Kambing"
    assert favs[0]["is_available"] is False


@pytest.mark.asyncio
async def test_prevent_duplicate_favorites(
    db_session: AsyncSession,
    customer_1: Customer,
    menu_items_sample,
):
    """Test adding the same favorite twice is idempotent and does not create duplicate."""
    service = CustomerMemoryService(db_session)
    item1 = menu_items_sample["item1"]

    res1 = await service.add_favorite(customer_id=customer_1.id, menu_id=item1.id)
    assert res1["status"] == "added"

    res2 = await service.add_favorite(customer_id=customer_1.id, menu_id=item1.id)
    assert res2["status"] == "already_favorite"

    favs = await service.get_favorites(customer_1.id)
    assert len(favs) == 1


@pytest.mark.asyncio
async def test_remove_favorite(
    db_session: AsyncSession,
    customer_1: Customer,
    menu_items_sample,
):
    """Test removing a favorite item."""
    service = CustomerMemoryService(db_session)
    item1 = menu_items_sample["item1"]

    await service.add_favorite(customer_id=customer_1.id, menu_id=item1.id)
    assert len(await service.get_favorites(customer_1.id)) == 1

    rem_res = await service.remove_favorite(customer_id=customer_1.id, menu_id=item1.id)
    assert rem_res["status"] == "removed"
    assert len(await service.get_favorites(customer_1.id)) == 0


@pytest.mark.asyncio
async def test_memory_and_favorite_isolation_between_customers(
    db_session: AsyncSession,
    customer_1: Customer,
    customer_2: Customer,
    menu_items_sample,
):
    """Test that customer memories and favorites are strictly scoped to the correct customer."""
    service = CustomerMemoryService(db_session)
    item1 = menu_items_sample["item1"]

    # Customer 1 has memory & favorite
    await service.save_memory(customer_id=customer_1.id, memory_type="preference", description="Suka manis")
    await service.add_favorite(customer_id=customer_1.id, menu_id=item1.id)

    # Customer 2 should have empty profile
    profile_2 = await service.get_customer_profile(customer_2.id)
    assert len(profile_2["memories"]["preference"]) == 0
    assert len(profile_2["favorites"]) == 0
