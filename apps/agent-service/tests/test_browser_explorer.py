"""Unit tests for the Playwright browser exploration tool."""
import pytest
from app.tools.browser_explorer import explore_web_app_browser, _is_safe_element_to_click


def test_safe_element_detection():
    # Dangerous actions should be rejected
    assert not _is_safe_element_to_click("Logout", "button")
    assert not _is_safe_element_to_click("Sign Out", "a")
    assert not _is_safe_element_to_click("Delete Account", "button")
    assert not _is_safe_element_to_click("Cancel Subscription", "button")
    assert not _is_safe_element_to_click("Pay Invoice", "button")

    # Harmless discovery actions should be approved
    assert _is_safe_element_to_click("View Profile", "button")
    assert _is_safe_element_to_click("Analytics Tab", "a")
    assert _is_safe_element_to_click("Filter by Date", "select")
    assert _is_safe_element_to_click("Next Page", "button")
    assert _is_safe_element_to_click("Settings", "a")


@pytest.mark.asyncio
async def test_browser_exploration_execution():
    # Test against public httpbin
    result = await explore_web_app_browser("https://httpbin.org/html", max_clicks=3)
    assert result.status == "success"
    assert result.data["target_url"] == "https://httpbin.org/html"
    assert "endpoints" in result.data
    assert "actions_executed" in result.data
