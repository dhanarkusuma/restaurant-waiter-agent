from google.adk.agents import Agent

from agent.prompts.waiter_prompt import WAITER_SYSTEM_INSTRUCTION


def create_waiter_agent(model_name: str = "gemini-2.5-flash") -> Agent:
    """
    Factory function to create the Google ADK Restaurant Waiter Agent.
    """
    return Agent(
        name="restaurant_waiter",
        model=model_name,
        instruction=WAITER_SYSTEM_INSTRUCTION,
        description="AI Waiter Agent helping restaurant customers with their dining session",
        tools=[],
    )


# Default root agent instance
root_agent = create_waiter_agent()
