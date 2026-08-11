"""
test_stagnation_and_resilience.py — Unit tests for StagnationDetector and repair_json_string
"""
import pytest
from unittest.mock import MagicMock
from app.engine.browser.stagnation_detector import StagnationDetector
from app.agents.nodes.llm_client import repair_json_string


def test_stagnation_detector_zero_yield_streak():
    """Verify zero-yield streak increments and deprioritizes selectors when threshold hit."""
    state = {
        "zero_yield_streak": 0,
        "last_endpoint_count": 5,
        "captured_endpoints": [{"ep": 1}, {"ep": 2}],
        "visited_state_hashes": ["hash1", "hash2"],
        "next_action": {"selector": "#stuck-btn", "parent_text": "Tab Section"},
        "deprioritized_modal_selectors": [],
    }

    # Action 1: 0 new endpoints
    state = StagnationDetector.record_action_yield(state, endpoints_before=5, endpoints_after=5, current_hash="hash1")
    assert state["zero_yield_streak"] == 1

    # Action 2: 0 new endpoints
    state = StagnationDetector.record_action_yield(state, endpoints_before=5, endpoints_after=5, current_hash="hash2")
    assert state["zero_yield_streak"] == 2

    # Action 3: 0 new endpoints -> hits THRESHOLD (3) -> deprioritizes selector
    state = StagnationDetector.record_action_yield(state, endpoints_before=5, endpoints_after=5, current_hash="hash3")
    assert state["zero_yield_streak"] == 3
    assert "#stuck-btn" in state["deprioritized_modal_selectors"]

    # Guidance text should now contain stagnation warning
    guidance = StagnationDetector.get_anti_loop_guidance(state)
    assert "STAGNATION WARNING" in guidance


def test_repair_json_string():
    """Verify repair_json_string cleans markdown fences and trailing commas."""
    raw_markdown = "```json\n[{\"index\": 0, \"reason\": \"good\",}]\n```"
    repaired = repair_json_string(raw_markdown)
    assert repaired == '[{"index": 0, "reason": "good"}]'

    raw_text = "Here is the response: {\"key\": \"value\",} hope this helps."
    repaired_text = repair_json_string(raw_text)
    assert repaired_text == '{"key": "value"}'
