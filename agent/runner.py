import logging
import os
from typing import Any
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from apps.backend.app.config import settings

logger = logging.getLogger(__name__)


class WaiterAgentRunner:
    """
    Orchestrates execution of the Google ADK Waiter Agent for incoming customer messages.
    Maintains session state and trusted context (customer_id, dining_session_id).
    """

    def __init__(
        self,
        agent: Agent | None = None,
        app_name: str = "restaurant_waiter_app",
        session_service: InMemorySessionService | None = None,
    ):
        if agent is None:
            from agent.agents.waiter_agent import root_agent
            agent = root_agent
        self.agent = agent
        self.app_name = app_name
        self.session_service = session_service or InMemorySessionService()
        self.runner = Runner(
            agent=self.agent,
            app_name=self.app_name,
            session_service=self.session_service,
        )

    async def handle_customer_message(
        self,
        customer_id: int,
        session_id: int,
        message_text: str,
        table_number: str | None = None,
    ) -> str:
        """
        Handle a customer conversational message through the Google ADK Agent.
        Preserves trusted customer_id and dining_session_id context in session state.
        """
        # Ensure API key from settings is accessible to google-genai client
        if settings.GEMINI_API_KEY and "GEMINI_API_KEY" not in os.environ:
            os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

        user_id_str = str(customer_id)
        session_id_str = f"dining_session_{session_id}"

        # 1. Ensure ADK Session exists with trusted state context
        adk_session = await self.session_service.get_session(
            app_name=self.app_name,
            user_id=user_id_str,
            session_id=session_id_str,
        )

        trusted_state = {
            "customer_id": customer_id,
            "dining_session_id": session_id,
            "table_number": table_number,
        }

        if not adk_session:
            await self.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id_str,
                session_id=session_id_str,
                state=trusted_state,
            )

        # 2. Prepare message content
        new_message = types.Content(
            parts=[types.Part(text=message_text)],
            role="user",
        )

        response_chunks: list[str] = []

        try:
            async for event in self.runner.run_async(
                user_id=user_id_str,
                session_id=session_id_str,
                new_message=new_message,
                state_delta=trusted_state,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_chunks.append(part.text)
        except Exception as e:
            logger.warning(
                "ADK Agent runner call encountered exception: %s. Using graceful response.",
                e,
                exc_info=True,
            )
            table_info = f" di Meja {table_number}" if table_number else ""
            return (
                f"Halo! Saya adalah AI Waiter Anda{table_info}. "
                "Ada yang bisa saya bantu untuk menemani waktu santap Anda?"
            )

        if response_chunks:
            return "".join(response_chunks).strip()

        table_info = f" di Meja {table_number}" if table_number else ""
        return f"Halo! Ada yang bisa saya bantu untuk pesanan Anda{table_info}?"


_default_waiter_runner: WaiterAgentRunner | None = None


def get_default_waiter_runner() -> WaiterAgentRunner:
    global _default_waiter_runner
    if _default_waiter_runner is None:
        _default_waiter_runner = WaiterAgentRunner()
    return _default_waiter_runner


def __getattr__(name: str) -> Any:
    if name == "default_waiter_runner":
        return get_default_waiter_runner()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
