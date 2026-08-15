import pytest
from google.adk.agents import Agent
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent.agents.waiter_agent import create_waiter_agent, root_agent
from agent.prompts.waiter_prompt import WAITER_SYSTEM_INSTRUCTION
from agent.runner import WaiterAgentRunner


def test_waiter_agent_configuration():
    """Verify that root ADK agent is correctly configured with Waiter persona and language guidelines."""
    agent = create_waiter_agent()
    assert isinstance(agent, Agent)
    assert agent.name == "restaurant_waiter"
    assert "AI Waiter" in agent.instruction
    assert "Pelayan Restoran" in agent.instruction
    assert "Bahasa Indonesia adalah bahasa utama" in agent.instruction
    assert "alami, santun, hangat, dan ringkas" in agent.instruction
    assert "bahasa percakapan sehari-hari" in agent.instruction
    assert "bahasa lain" in agent.instruction
    assert agent.description == "AI Waiter Agent helping restaurant customers with their dining session"
    assert root_agent.name == "restaurant_waiter"


@pytest.mark.asyncio
async def test_waiter_runner_session_state_preservation():
    """
    Verify that WaiterAgentRunner preserves trusted context (customer_id, dining_session_id, table_number)
    in the ADK session state.
    """
    session_service = InMemorySessionService()
    runner = WaiterAgentRunner(
        agent=root_agent,
        app_name="test_app",
        session_service=session_service,
    )

    customer_id = 42
    session_id = 101
    table_number = "T-05"

    response = await runner.handle_customer_message(
        customer_id=customer_id,
        session_id=session_id,
        message_text="Halo, saya ingin melihat menu.",
        table_number=table_number,
    )

    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0

    # Verify that ADK session state was initialized with trusted context
    adk_session = await session_service.get_session(
        app_name="test_app",
        user_id=str(customer_id),
        session_id=f"dining_session_{session_id}",
    )

    assert adk_session is not None
    assert adk_session.state["customer_id"] == 42
    assert adk_session.state["dining_session_id"] == 101
    assert adk_session.state["table_number"] == "T-05"


@pytest.mark.asyncio
async def test_waiter_runner_mock_event_stream():
    """Verify that runner gathers text parts from event stream."""
    session_service = InMemorySessionService()
    agent = create_waiter_agent()
    runner = WaiterAgentRunner(
        agent=agent,
        app_name="test_app_mock",
        session_service=session_service,
    )

    # Mock runner.run_async to yield a predictable event stream
    async def mock_run_async(*args, **kwargs):
        yield Event(
            author=agent.name,
            content=types.Content(
                parts=[types.Part(text="Halo! Selamat datang di Meja T-01. Ada yang bisa saya bantu?")]
            ),
        )

    runner.runner.run_async = mock_run_async

    response = await runner.handle_customer_message(
        customer_id=1,
        session_id=1,
        message_text="Halo",
        table_number="T-01",
    )

    assert response == "Halo! Selamat datang di Meja T-01. Ada yang bisa saya bantu?"
