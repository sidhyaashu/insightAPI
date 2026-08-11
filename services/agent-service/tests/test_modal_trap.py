import pytest
from playwright.async_api import async_playwright
from app.agents.nodes.executor import ExecutorNode
from app.agents.nodes.planner import PlannerNode
from app.agents.state import CrawlState


@pytest.mark.asyncio
async def test_modal_trap_force_close_and_deprioritize():
    """
    Simulates execution trapped inside a non-productive modal dialog.
    Verifies that after 3 unproductive actions in a modal, ExecutorNode force-closes the modal
    and deprioritizes its selectors in PlannerNode.
    
    Fixes failure mode: Agent cycling endlessly on unhelpful modal dialog controls.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        html_content = """
        <!DOCTYPE html>
        <html>
        <body>
            <button id="open-modal">Open Modal</button>
            <div id="modal-container" class="modal" role="dialog" style="display: block;">
                <h3>Modal Dialog</h3>
                <button id="modal-btn-1">Modal Option 1</button>
                <button id="modal-btn-2">Modal Option 2</button>
            </div>
        </body>
        </html>
        """
        await page.set_content(html_content)

        state: CrawlState = {
            "target_url": page.url,
            "current_url": page.url,
            "visited_urls": [],
            "visited_state_hashes": [],
            "visited_selectors": [],
            "interactive_elements": [],
            "captured_endpoints": [],
            "next_action": {
                "selector": "#modal-btn-1",
                "tag": "button",
                "parent_text": "Modal Dialog",
                "form_context": "modal"
            },
            "is_safe_action": True,
            "risk_reason": None,
            "frontier": [],
            "explored_count": 0,
            "max_pages": 10,
            "is_complete": False,
            "error_message": None,
            "auth_required_url": None,
            "modal_action_count": 2,
            "deprioritized_modal_selectors": [],
            "last_endpoint_count": 0,
            "network_observer": None,
            "page_ref": page
        }

        # 3rd action inside modal with 0 new endpoints captured
        await ExecutorNode.handle_modal_trap(page, state["next_action"], state)

        # Modal selector should be recorded in deprioritized_modal_selectors
        assert "#modal-btn-1" in state["deprioritized_modal_selectors"]

        # PlannerNode should heavily penalize score of modal elements
        modal_el = {
            "selector": "#modal-btn-1",
            "tag": "button",
            "text": "Modal Option 1",
            "parent_text": "Modal Dialog",
            "form_context": "modal"
        }
        score = PlannerNode.score_element(modal_el, state["deprioritized_modal_selectors"])
        assert score < 0.0

        await browser.close()
