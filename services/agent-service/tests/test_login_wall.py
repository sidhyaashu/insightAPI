import pytest
from playwright.async_api import async_playwright
from app.agents.nodes.executor import ExecutorNode
from app.agents.state import CrawlState
from app.engine.browser.dom_distiller import DOMDistiller


@pytest.mark.asyncio
async def test_login_wall_detection():
    """
    Simulates a login wall containing password inputs without session cookies.
    Verifies ExecutorNode sets is_complete=True with error_message='auth_required'
    and records auth_required_url.
    
    Fixes failure mode: Agent wasting resources attempting blind credential entries.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Login Wall Test</title></head>
        <body>
            <h2>Sign In Required</h2>
            <form id="login-form">
                <input type="text" id="username" placeholder="Username">
                <input type="password" id="password" placeholder="Password">
                <button type="submit">Log In</button>
            </form>
        </body>
        </html>
        """
        await page.set_content(html_content)

        snapshot = await DOMDistiller.extract_interactive_snapshot(page)
        assert any(el.get("type") == "password" for el in snapshot)

        state: CrawlState = {
            "target_url": page.url,
            "current_url": page.url,
            "visited_urls": [],
            "visited_state_hashes": [],
            "visited_selectors": [],
            "interactive_elements": snapshot,
            "captured_endpoints": [],
            "next_action": {"selector": "#password", "tag": "input"},
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
            "network_observer": None,
            "page_ref": page
        }

        updated_state = await ExecutorNode.process(state)

        assert updated_state["is_complete"] is True
        assert updated_state["error_message"] == "auth_required"
        assert updated_state["auth_required_url"] == page.url

        await browser.close()
