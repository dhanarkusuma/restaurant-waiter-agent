import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent.agents.waiter_agent import create_waiter_agent
from agent.prompts.waiter_prompt import WAITER_SYSTEM_INSTRUCTION
from agent.tools.memory_tool import (
    add_customer_favorite,
    forget_customer_preference,
    get_customer_memory,
    remove_customer_favorite,
    save_customer_preference,
)
from agent.tools.menu_tool import reset_tool_session_factory, set_tool_session_factory
from apps.backend.app.models import Customer
from apps.backend.app.repositories import CustomerRepository, MenuRepository


class DummyToolContext:
    """Mock ToolContext holding state for tool tests."""
    def __init__(self, customer_id: int, dining_session_id: int = 1):
        self.state = {
            "customer_id": customer_id,
            "dining_session_id": dining_session_id,
            "table_number": "T-01",
        }


@pytest.fixture(autouse=True)
def setup_tools_db_session(db_session: AsyncSession):
    class TestSessionFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return db_session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    set_tool_session_factory(TestSessionFactory())
    yield
    reset_tool_session_factory()


@pytest.fixture
async def sample_customer(db_session: AsyncSession) -> Customer:
    repo = CustomerRepository(db_session)
    return await repo.create(telegram_id=777001, username="test_memory_user", first_name="Budi")


@pytest.fixture
async def sample_menu(db_session: AsyncSession):
    repo = MenuRepository(db_session)
    cat = await repo.create_category(name="Makanan Utama")
    item = await repo.create_item(name="Rawon Surabaya", price=42000, category_id=cat.id, is_available=True)
    return item


def test_waiter_agent_has_all_seven_tools_registered():
    """Verify that the root waiter agent has all 7 tools registered."""
    agent = create_waiter_agent()
    tool_names = [t.__name__ for t in agent.tools]
    assert len(agent.tools) >= 7
    assert "search_available_menu" in tool_names
    assert "get_menu_details" in tool_names
    assert "get_customer_memory" in tool_names
    assert "save_customer_preference" in tool_names
    assert "forget_customer_preference" in tool_names
    assert "add_customer_favorite" in tool_names
    assert "remove_customer_favorite" in tool_names


def test_system_prompt_mandates_memory_safety_and_personalization():
    """Verify prompt instructs agent on memory safety, distinguishing temporary vs persistent statements."""
    assert "get_customer_memory" in WAITER_SYSTEM_INSTRUCTION
    assert "save_customer_preference" in WAITER_SYSTEM_INSTRUCTION
    assert "forget_customer_preference" in WAITER_SYSTEM_INSTRUCTION
    assert "JANGAN mengklaim mengingat sesuatu kecuali data tersebut memang tersimpan" in WAITER_SYSTEM_INSTRUCTION
    assert "JANGAN simpan pernyataan konteks sementara sesi hari ini" in WAITER_SYSTEM_INSTRUCTION
    assert "Simpan preferensi permanen via `save_customer_preference` HANYA jika pelanggan menyatakan" in WAITER_SYSTEM_INSTRUCTION


@pytest.mark.asyncio
async def test_get_customer_memory_tool(sample_customer: Customer):
    """Test get_customer_memory tool reads profile from injected tool_context."""
    ctx = DummyToolContext(customer_id=sample_customer.id)
    # Save memory
    await save_customer_preference(
        memory_type="dislike",
        description="Tidak suka pedas",
        tool_context=ctx,
    )

    profile = await get_customer_memory(tool_context=ctx)
    assert profile["customer_id"] == sample_customer.id
    assert len(profile["memories"]["dislike"]) == 1
    assert profile["memories"]["dislike"][0]["description"] == "Tidak suka pedas"


@pytest.mark.asyncio
async def test_save_and_forget_preference_tools(sample_customer: Customer):
    """Test saving and forgetting customer preference tools."""
    ctx = DummyToolContext(customer_id=sample_customer.id)

    # Save preference
    save_res = await save_customer_preference(
        memory_type="preference",
        description="Suka makanan berkuah gurih",
        tool_context=ctx,
    )
    assert save_res["status"] == "created"

    # Forget preference
    forget_res = await forget_customer_preference(keyword="berkuah", tool_context=ctx)
    assert forget_res["status"] == "deleted"
    assert forget_res["count"] == 1

    profile = await get_customer_memory(tool_context=ctx)
    assert len(profile["memories"]["preference"]) == 0


@pytest.mark.asyncio
async def test_add_and_remove_favorite_tools(sample_customer: Customer, sample_menu):
    """Test adding and removing favorite tools."""
    ctx = DummyToolContext(customer_id=sample_customer.id)

    # Add favorite
    add_res = await add_customer_favorite(menu_name_or_id="Rawon Surabaya", tool_context=ctx)
    assert add_res["status"] == "added"
    assert add_res["name"] == "Rawon Surabaya"

    # Verify in profile
    profile = await get_customer_memory(tool_context=ctx)
    assert len(profile["favorites"]) == 1
    assert profile["favorites"][0]["name"] == "Rawon Surabaya"

    # Remove favorite
    rem_res = await remove_customer_favorite(menu_name_or_id="Rawon Surabaya", tool_context=ctx)
    assert rem_res["status"] == "removed"

    profile_after = await get_customer_memory(tool_context=ctx)
    assert len(profile_after["favorites"]) == 0
