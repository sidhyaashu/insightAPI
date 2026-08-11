import pytest
from unittest.mock import MagicMock
from playwright.async_api import async_playwright
from app.agents.nodes.executor import ExecutorNode
from app.agents.state import CrawlState


@pytest.mark.asyncio
async def test_popup_navigation_handling():
    """
    Simulates clicking a target="_blank" link opening a popup / new tab.
    Verifies ExecutorNode attaches NetworkObserver to the popup page, captures traffic,
    closes the popup page, and preserves focus on the primary crawling page.
    
    Fixes failure mode: Planner wandering into popup/new-tab windows and getting stranded.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <a id="popup-link" href="about:blank" target="_blank">Open Popup</a>
        </body>
        </html>
        """
        await page.set_content(html_content)

        mock_observer = MagicMock()
        mock_observer.attach_to_page = MagicMock()

        state: CrawlState = {
            "target_url": page.url,
            "current_url": page.url,
            "visited_urls": [],
            "visited_state_hashes": [],
            "visited_selectors": [],
            "interactive_elements": [],
            "captured_endpoints": [],
            "next_action": {"selector": "#popup-link", "tag": "a"},
            "is_safe_action": True,
            "risk_reason": None,
            "frontier": [],
            "explored_count": 0,
            "max_pages": 10,
            "is_complete": False,
            "error_message": None,
            "auth_required_url": None,
            "modal_action_count": 0,
            "deprioritized_modal_selectors": [],
            "last_endpoint_count": 0,
            "network_observer": mock_observer,
            "page_ref": page
        }

        async def click_popup_action():
            await page.click("#popup-link")
            return {"success": True}

        res = await ExecutorNode.handle_popup_navigation(page, state, click_popup_action())

        assert res["success"] is True
        # Verify NetworkObserver was attached to popup page
        assert mock_observer.attach_to_page.called
        # Verify main page remains open and context has only 1 page active (popup closed)
        assert len(context.pages) == 1
        assert context.pages[0] == page

        await browser.close()
