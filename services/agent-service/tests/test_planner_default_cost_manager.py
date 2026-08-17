import pytest
from unittest.mock import patch, MagicMock
from app.agents.nodes.planner import LLMPlannerStrategy
from app.agents.state import CrawlState


@pytest.mark.asyncio
async def test_planner_enforces_budget_even_when_cost_manager_is_none():
    """
    Verify F-35: When state['cost_manager'] is None (SDK/CLI direct run),
    LLMPlannerStrategy constructs a default CostManager and enforces budget caps,
    rather than skipping budget enforcement and allowing unbounded spend.
    """
    # Create state with NO cost_manager
    state: CrawlState = {
        "target_url": "https://example.com",
        "current_url": "https://example.com/login",
        "visited_urls": ["https://example.com"],
        "visited_state_hashes": [],
        "visited_selectors": [],
        "interactive_elements": [],
        "captured_endpoints": [],
        "next_action": None,
        "is_safe_action": True,
        "risk_reason": None,
        "frontier": [
            {
                "element": {"tag": "button", "text": "Submit", "selector": "#btn-1"},
                "selector_key": "#btn-1",
                "score": 10,
                "source_url": "https://example.com",
            }
        ],
        "explored_count": 1,
        "max_pages": 5,
        "is_complete": False,
        "error_message": None,
        "auth_required_url": None,
        "modal_action_count": 0,
        "deprioritized_modal_selectors": [],
        "last_endpoint_count": 0,
        "network_observer": None,
        "page_ref": None,
        "rate_limit_ms": 500,
        "humanize_interactions": False,
        "crawl_id": "sdk_test_crawl_1",
        "user_id": None,
        "cost_manager": None,  # Explicitly None
    }

    mock_cost_manager = MagicMock()
    # Simulate exhausted default budget
    mock_cost_manager.is_budget_exhausted.return_value = True
    mock_cost_manager.is_planner_budget_exhausted.return_value = False

    with patch("app.core.config.settings.LLM_PLANNER_ENABLED", True), \
         patch("app.agents.nodes.llm_client.make_cost_manager", return_value=mock_cost_manager) as mock_make_cm:

        res = await LLMPlannerStrategy.select_action(state, state["frontier"])

        # Cost manager MUST have been initialized
        mock_make_cm.assert_called_once()
        # Planner should reject LLM execution because budget is exhausted
        assert res is None
        # State should now contain the cost manager
        assert state["cost_manager"] is mock_cost_manager
