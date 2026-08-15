from agent.agents.waiter_agent import create_waiter_agent
from agent.prompts.waiter_prompt import WAITER_SYSTEM_INSTRUCTION


def test_customer_agent_does_not_have_admin_payment_or_status_tools():
    """Verify that customer-facing ADK agent cannot mark orders as paid or advance lifecycle status."""
    agent = create_waiter_agent()
    tool_names = [t.__name__ for t in agent.tools]

    # Must NOT have admin tools
    forbidden_tools = [
        "mark_order_as_paid",
        "update_order_status",
        "advance_order_status",
        "set_order_done",
        "pay_order",
    ]

    for tool in forbidden_tools:
        assert tool not in tool_names, f"Customer agent should NOT have {tool}"


def test_system_prompt_instructs_manual_payment_at_cashier():
    """Verify system instruction explicitly instructs waiter that payment is manual with staff/cashier."""
    assert "Pembayaran dilakukan secara manual ke kasir/staf restoran" in WAITER_SYSTEM_INSTRUCTION
    assert "AI Waiter tidak dapat memproses pembayaran" in WAITER_SYSTEM_INSTRUCTION
