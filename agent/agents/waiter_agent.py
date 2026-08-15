from google.adk.agents import Agent

from agent.prompts.waiter_prompt import WAITER_SYSTEM_INSTRUCTION
from agent.tools.menu_tool import get_menu_details, search_available_menu


def create_waiter_agent(model_name: str = "gemini-2.5-flash") -> Agent:
    """
    Factory function to create the Google ADK Restaurant Waiter Agent with menu retrieval tools.
    """
    return Agent(
        name="restaurant_waiter",
        model=model_name,
        instruction=WAITER_SYSTEM_INSTRUCTION,
        description="AI Waiter Agent helping restaurant customers with menu discovery, recommendations, and dining session",
        tools=[search_available_menu, get_menu_details],
    )


# Default root agent instance
root_agent = create_waiter_agent()
