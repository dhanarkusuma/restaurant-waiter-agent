import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent.agents.waiter_agent import create_waiter_agent, root_agent
from agent.prompts.waiter_prompt import WAITER_SYSTEM_INSTRUCTION
from agent.tools.menu_tool import (
    get_menu_details,
    reset_tool_session_factory,
    search_available_menu,
    set_tool_session_factory,
)
from apps.backend.app.repositories import MenuRepository


@pytest.fixture(autouse=True)
def setup_menu_tool_session(db_session: AsyncSession):
    """Set test db session factory for ADK tools."""
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
async def seed_menu_items(db_session: AsyncSession):
    repo = MenuRepository(db_session)
    cat = await repo.create_category(name="Makanan Utama")
    item1 = await repo.create_item(
        name="Sate Ayam Madura",
        price=30000,
        description="Sate daging ayam empuk dengan bumbu kacang gurih manis",
        category_id=cat.id,
        is_available=True,
    )
    item2 = await repo.create_item(
        name="Soto Betawi",
        price=40000,
        description="Soto daging sapi kuah santan gurih kaya rempah",
        category_id=cat.id,
        is_available=True,
    )
    item3 = await repo.create_item(
        name="Gulai Kambing",
        price=50000,
        description="Gulai kambing rempah spesial (Habis)",
        category_id=cat.id,
        is_available=False,
    )
    return {"cat": cat, "item1": item1, "item2": item2, "item3": item3}


def test_waiter_agent_has_menu_tools_registered():
    """Verify that root agent has menu tools registered."""
    agent = create_waiter_agent()
    tool_names = [t.__name__ for t in agent.tools]
    assert "search_available_menu" in tool_names
    assert "get_menu_details" in tool_names
    assert len(agent.tools) == 2


def test_system_prompt_mandates_tool_grounding_and_forbids_hallucination():
    """Verify prompt instructs agent to use tools, forbids hallucination, and guides recommendation."""
    assert "search_available_menu" in WAITER_SYSTEM_INSTRUCTION
    assert "get_menu_details" in WAITER_SYSTEM_INSTRUCTION
    assert "DILARANG KERAS mengarang, berhalusinasi" in WAITER_SYSTEM_INSTRUCTION
    assert "Hanya rekomendasikan menu yang statusnya TERSEDIA" in WAITER_SYSTEM_INSTRUCTION
    assert "sampaikan secara jujur dan sopan bahwa menu tersebut tidak tersedia" in WAITER_SYSTEM_INSTRUCTION


@pytest.mark.asyncio
async def test_search_available_menu_tool_execution(seed_menu_items):
    """Test search_available_menu ADK tool execution."""
    results = await search_available_menu(query="sate")
    assert len(results) == 1
    assert results[0]["name"] == "Sate Ayam Madura"
    assert results[0]["price"] == 30000
    assert "bumbu kacang" in results[0]["description"]
    assert results[0]["is_available"] is True


@pytest.mark.asyncio
async def test_tool_excludes_unavailable_items(seed_menu_items):
    """Test that search_available_menu tool strictly excludes unavailable items."""
    results = await search_available_menu(query="gulai")
    assert results == []


@pytest.mark.asyncio
async def test_get_menu_details_tool_execution(seed_menu_items):
    """Test get_menu_details ADK tool execution."""
    item1 = seed_menu_items["item1"]
    details = await get_menu_details(item1.id)
    assert details["name"] == "Sate Ayam Madura"
    assert details["price"] == 30000

    # Non-existent item
    missing = await get_menu_details(99999)
    assert "error" in missing
