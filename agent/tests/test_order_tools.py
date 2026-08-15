import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agent.agents.waiter_agent import create_waiter_agent, root_agent
from agent.prompts.waiter_prompt import WAITER_SYSTEM_INSTRUCTION
from agent.tools.menu_tool import reset_tool_session_factory, set_tool_session_factory
from agent.tools.order_tool import (
    add_item_to_order_draft,
    confirm_and_place_order,
    remove_item_from_order_draft,
    update_draft_item_quantity,
    view_order_draft,
)
from apps.backend.app.models import Customer, DiningSession, RestaurantTable
from apps.backend.app.repositories import (
    CustomerRepository,
    MenuRepository,
    SessionRepository,
    TableRepository,
)


class DummyToolContext:
    def __init__(self, customer_id: int, dining_session_id: int, table_number: str = "T-01"):
        self.state = {
            "customer_id": customer_id,
            "dining_session_id": dining_session_id,
            "table_number": table_number,
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
async def sample_order_fixture(db_session: AsyncSession):
    cust_repo = CustomerRepository(db_session)
    table_repo = TableRepository(db_session)
    session_repo = SessionRepository(db_session)
    menu_repo = MenuRepository(db_session)

    cust = await cust_repo.create(telegram_id=990011, username="order_agent_user", first_name="Dono")
    table = await table_repo.create(table_number="T-09", qr_code_token="qr_t9", capacity=4)
    session = await session_repo.create(customer_id=cust.id, table_id=table.id)

    cat = await menu_repo.create_category(name="Makanan Utama")
    item1 = await menu_repo.create_item(name="Bebek Goreng Madura", price=40000, category_id=cat.id, is_available=True)
    item2 = await menu_repo.create_item(name="Es Jeruk Segar", price=10000, category_id=cat.id, is_available=True)

    return {
        "cust": cust,
        "table": table,
        "session": session,
        "item1": item1,
        "item2": item2,
    }


def test_waiter_agent_has_all_twelve_tools_registered():
    """Verify that root agent has all 12 tools registered across menu, memory, and ordering."""
    agent = create_waiter_agent()
    tool_names = [t.__name__ for t in agent.tools]
    assert len(agent.tools) == 12
    # Menu tools
    assert "search_available_menu" in tool_names
    assert "get_menu_details" in tool_names
    # Memory tools
    assert "get_customer_memory" in tool_names
    assert "save_customer_preference" in tool_names
    assert "forget_customer_preference" in tool_names
    assert "add_customer_favorite" in tool_names
    assert "remove_customer_favorite" in tool_names
    # Order tools
    assert "add_item_to_order_draft" in tool_names
    assert "update_draft_item_quantity" in tool_names
    assert "remove_item_from_order_draft" in tool_names
    assert "view_order_draft" in tool_names
    assert "confirm_and_place_order" in tool_names


def test_system_prompt_mandates_order_draft_summary_and_explicit_confirmation():
    """Verify prompt instructs agent on drafting, summarizing, and requiring explicit customer confirmation."""
    assert "add_item_to_order_draft" in WAITER_SYSTEM_INSTRUCTION
    assert "view_order_draft" in WAITER_SYSTEM_INSTRUCTION
    assert "confirm_and_place_order" in WAITER_SYSTEM_INSTRUCTION
    assert "ATURAN KONFIRMASI MUTLAK" in WAITER_SYSTEM_INSTRUCTION
    assert "DILARANG KERAS memanggil `confirm_and_place_order` sebelum pelanggan memberikan konfirmasi eksplisit" in WAITER_SYSTEM_INSTRUCTION
    assert "status ORDERED" in WAITER_SYSTEM_INSTRUCTION


@pytest.mark.asyncio
async def test_order_drafting_and_confirmation_tool_flow(sample_order_fixture):
    """Test full ordering tool flow from drafting to review to confirmation."""
    fx = sample_order_fixture
    ctx = DummyToolContext(customer_id=fx["cust"].id, dining_session_id=fx["session"].id)

    # 1. Add Bebek Goreng (qty 2) and Es Jeruk (qty 2) to draft
    res1 = await add_item_to_order_draft(
        menu_item="Bebek Goreng Madura",
        quantity=2,
        notes="sambal banyak",
        tool_context=ctx,
    )
    assert res1["status"] == "added"
    assert res1["draft"]["total_amount"] == 80000

    res2 = await add_item_to_order_draft(
        menu_item="Es Jeruk Segar",
        quantity=2,
        notes="kurangi gula",
        tool_context=ctx,
    )
    assert res2["status"] == "added"
    assert res2["draft"]["total_amount"] == 100000

    # 2. View draft summary
    draft_view = await view_order_draft(tool_context=ctx)
    assert draft_view["item_count"] == 4
    assert draft_view["total_amount"] == 100000
    assert len(draft_view["items"]) == 2

    # 3. Update quantity of Es Jeruk to 1
    update_res = await update_draft_item_quantity(
        menu_item="Es Jeruk Segar",
        quantity=1,
        tool_context=ctx,
    )
    assert update_res["status"] == "updated"
    assert update_res["draft"]["total_amount"] == 90000

    # 4. Explicitly confirm and place order
    confirm_res = await confirm_and_place_order(tool_context=ctx)
    assert confirm_res["status"] == "created"
    assert confirm_res["order_id"] is not None
    assert confirm_res["total_amount"] == 90000
    assert confirm_res["order_status"] == "ORDERED"
    assert confirm_res["payment_status"] == "UNPAID"

    # 5. Verify draft is now empty
    draft_after = await view_order_draft(tool_context=ctx)
    assert draft_after["is_empty"] is True
