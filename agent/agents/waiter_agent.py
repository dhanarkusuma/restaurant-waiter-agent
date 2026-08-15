from google.adk.agents import Agent

from agent.prompts.waiter_prompt import WAITER_SYSTEM_INSTRUCTION
from agent.tools.memory_tool import (
    add_customer_favorite,
    forget_customer_preference,
    get_customer_memory,
    remove_customer_favorite,
    save_customer_preference,
)
from agent.tools.menu_tool import get_menu_details, search_available_menu
from agent.tools.order_tool import (
    add_item_to_order_draft,
    confirm_and_place_order,
    remove_item_from_order_draft,
    update_draft_item_quantity,
    view_order_draft,
)


def create_waiter_agent(model_name: str = "gemini-2.5-flash") -> Agent:
    """
    Factory function to create the Google ADK Restaurant Waiter Agent with menu, memory, and ordering tools.
    """
    return Agent(
        name="restaurant_waiter",
        model=model_name,
        instruction=WAITER_SYSTEM_INSTRUCTION,
        description="AI Waiter Agent helping restaurant customers with menu discovery, recommendations, memory personalization, order drafting, and dining session",
        tools=[
            search_available_menu,
            get_menu_details,
            get_customer_memory,
            save_customer_preference,
            forget_customer_preference,
            add_customer_favorite,
            remove_customer_favorite,
            add_item_to_order_draft,
            update_draft_item_quantity,
            remove_item_from_order_draft,
            view_order_draft,
            confirm_and_place_order,
        ],
    )


# Default root agent instance
root_agent = create_waiter_agent()
