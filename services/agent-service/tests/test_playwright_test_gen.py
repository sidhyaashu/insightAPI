"""
Unit tests for Playwright Regression Test Generation from crawl action traces.
"""
import io
import zipfile
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.generators.playwright_test_gen import PlaywrightTestGenerator
from app.sdk import CrawlResult
from app.agents.nodes.executor import ExecutorNode
from app.api.v1.endpoints.crawls import generate_playwright_tests, CRAWL_SESSIONS


@pytest.fixture
def sample_action_traces():
    return [
        {
            "step": 1,
            "action_type": "type",
            "selector": "input#search-box",
            "value": "running shoes",
            "url_before": "https://shop.example.com",
            "url_after": "https://shop.example.com/search",
            "network_calls_triggered": [
                {
                    "method": "GET",
                    "url": "https://shop.example.com/api/v1/search?q=running+shoes",
                    "template_route": "/api/v1/search",
                    "status": 200,
                    "response_body": {
                        "total": 42,
                        "query": "running shoes",
                        "items": [{"id": 101, "title": "Nike Air Zoom"}],
                    },
                }
            ],
        },
        {
            "step": 2,
            "action_type": "click",
            "selector": "button.add-to-cart",
            "value": "",
            "url_before": "https://shop.example.com/search",
            "url_after": "https://shop.example.com/cart",
            "network_calls_triggered": [
                {
                    "method": "POST",
                    "url": "https://shop.example.com/api/v1/cart/items",
                    "template_route": "/api/v1/cart/items",
                    "status": 201,
                    "response_body": {
                        "cart_id": "cart_999",
                        "status": "success",
                        "item_count": 1,
                    },
                }
            ],
        },
    ]


def test_python_playwright_test_generation(sample_action_traces):
    """Verify generated Python test contains pytest fixtures, expect_response blocks, and contract assertions."""
    code = PlaywrightTestGenerator.generate_python_test(
        target_url="https://shop.example.com",
        action_traces=sample_action_traces,
        session_id="test-session-123",
    )

    assert "def test_api_regression_flow(page: Page):" in code
    assert 'page.goto("https://shop.example.com"' in code

    # Step 1 assertions
    assert 'with page.expect_response(lambda r: "/api/v1/search" in r.url and r.status == 200' in code
    assert 'page.fill("input#search-box", "running shoes")' in code
    assert "assert resp_1.status == 200" in code
    assert 'assert "total" in data_1' in code
    assert 'assert "query" in data_1' in code
    assert 'assert "items" in data_1' in code

    # Step 2 assertions
    assert 'with page.expect_response(lambda r: "/api/v1/cart/items" in r.url and r.status == 201' in code
    assert 'page.click("button.add-to-cart")' in code
    assert "assert resp_2.status == 201" in code
    assert 'assert "cart_id" in data_2' in code
    assert 'assert "status" in data_2' in code


def test_typescript_playwright_test_generation(sample_action_traces):
    """Verify generated TypeScript spec contains @playwright/test syntax and Promise.all patterns."""
    code = PlaywrightTestGenerator.generate_typescript_test(
        target_url="https://shop.example.com",
        action_traces=sample_action_traces,
        session_id="test-session-123",
    )

    assert "import { test, expect } from '@playwright/test';" in code
    assert "await page.goto('https://shop.example.com'" in code

    # Step 1 Promise.all pattern
    assert "const [response1] = await Promise.all([" in code
    assert "page.waitForResponse(res => res.url().includes('/api/v1/search') && res.status() === 200" in code
    assert "page.fill('input#search-box', 'running shoes')" in code
    assert "expect(response1.status()).toBe(200);" in code
    assert "expect(data1).toHaveProperty('total');" in code
    assert "expect(data1).toHaveProperty('items');" in code

    # Step 2
    assert "const [response2] = await Promise.all([" in code
    assert "page.waitForResponse(res => res.url().includes('/api/v1/cart/items') && res.status() === 201" in code
    assert "page.click('button.add-to-cart')" in code
    assert "expect(response2.status()).toBe(201);" in code
    assert "expect(data2).toHaveProperty('cart_id');" in code


def test_generate_test_suite_zip_packaging(sample_action_traces):
    """Verify in-memory zip archive contains test scripts, configs, dependencies, and README."""
    # 1. Python Zip
    py_zip_bytes = PlaywrightTestGenerator.generate_test_suite_zip(
        target_url="https://shop.example.com",
        action_traces=sample_action_traces,
        session_id="sess_py",
        format="python",
    )
    with zipfile.ZipFile(io.BytesIO(py_zip_bytes), "r") as zf:
        file_list = zf.namelist()
        assert "tests/test_api_regression.py" in file_list
        assert "pytest.ini" in file_list
        assert "requirements.txt" in file_list
        assert "README.md" in file_list

        reqs = zf.read("requirements.txt").decode()
        assert "pytest-playwright" in reqs

    # 2. TypeScript Zip
    ts_zip_bytes = PlaywrightTestGenerator.generate_test_suite_zip(
        target_url="https://shop.example.com",
        action_traces=sample_action_traces,
        session_id="sess_ts",
        format="typescript",
    )
    with zipfile.ZipFile(io.BytesIO(ts_zip_bytes), "r") as zf:
        file_list = zf.namelist()
        assert "tests/regression.spec.ts" in file_list
        assert "playwright.config.ts" in file_list
        assert "package.json" in file_list
        assert "README.md" in file_list

        pkg = zf.read("package.json").decode()
        assert "@playwright/test" in pkg


def test_crawl_result_to_playwright_test_helper(sample_action_traces):
    """Verify CrawlResult.to_playwright_test delegates correctly based on format."""
    result = CrawlResult(
        target_url="https://shop.example.com",
        captured_endpoints=[],
        action_traces=sample_action_traces,
    )

    py_code = result.to_playwright_test(format="python")
    assert "import pytest" in py_code

    ts_code = result.to_playwright_test(format="typescript")
    assert "@playwright/test" in ts_code


@pytest.mark.asyncio
async def test_generate_tests_endpoint(sample_action_traces):
    """Verify GET /api/v1/crawls/{id}/generate-tests returns test script or zip archive."""
    session_id = "test_gen_session_99"
    CRAWL_SESSIONS[session_id] = {
        "session_id": session_id,
        "target_url": "https://shop.example.com",
        "action_traces": sample_action_traces,
    }

    mock_db = AsyncMock()

    with patch("app.repositories.crawl_repo.CrawlRepository.get_by_id", new=AsyncMock(return_value=None)):
        # 1. Test Python script download
        resp_py = await generate_playwright_tests(
            session_id=session_id,
            format="python",
            as_zip=False,
            db=mock_db,
        )
        assert resp_py.media_type == "text/plain; charset=utf-8"
        assert "test_regression_test_gen_session_99.py" in resp_py.headers["Content-Disposition"]
        assert b"def test_api_regression_flow" in resp_py.body

        # 2. Test TypeScript script download
        resp_ts = await generate_playwright_tests(
            session_id=session_id,
            format="typescript",
            as_zip=False,
            db=mock_db,
        )
        assert resp_ts.media_type == "text/plain; charset=utf-8"
        assert "test_regression_test_gen_session_99.spec.ts" in resp_ts.headers["Content-Disposition"]
        assert b"@playwright/test" in resp_ts.body

        # 3. Test Zip download
        resp_zip = await generate_playwright_tests(
            session_id=session_id,
            format="python",
            as_zip=True,
            db=mock_db,
        )
        assert resp_zip.media_type == "application/zip"
        assert "insightapi_test_suite_test_gen_session_99.zip" in resp_zip.headers["Content-Disposition"]
        assert len(resp_zip.body) > 0


@pytest.mark.asyncio
async def test_executor_node_records_action_trace():
    """Verify ExecutorNode logs ordered action trace and captures triggered network endpoints."""
    mock_page = AsyncMock()
    mock_page.url = "https://app.example.com/results"
    mock_page.context.storage_state = AsyncMock(return_value={"cookies": [], "origins": []})

    mock_observer = MagicMock()
    mock_endpoint = MagicMock()
    mock_endpoint.to_dict.return_value = {
        "method": "GET",
        "url": "https://app.example.com/api/search",
        "status": 200,
    }
    mock_observer.captured_endpoints = []

    async def mock_execute_action(*args, **kwargs):
        mock_observer.captured_endpoints.append(mock_endpoint)
        return {"success": True}

    state = {
        "current_url": "https://app.example.com",
        "page_ref": mock_page,
        "next_action": {
            "action": "type",
            "selector": "input#query",
            "value": "search keyword",
        },
        "network_observer": mock_observer,
        "action_traces": [],
        "captured_endpoints": [],
        "interactive_elements": [],
        "visited_urls": [],
        "explored_count": 0,
        "max_pages": 5,
        "is_complete": False,
    }

    with patch("app.engine.executor.dynamic_executor.DynamicRuntimeExecutor.execute_action", new=AsyncMock(side_effect=mock_execute_action)), \
         patch("app.engine.browser.stabilizer.PageNetworkStabilizer.wait_until_stable", new=AsyncMock()), \
         patch("app.engine.browser.dom_distiller.DOMDistiller.detect_login_wall", new=AsyncMock(return_value=False)), \
         patch("app.engine.browser.dom_distiller.DOMDistiller.extract_interactive_snapshot", new=AsyncMock(return_value=[])):

        res_state = await ExecutorNode.process(state)

        traces = res_state.get("action_traces", [])
        assert len(traces) == 1
        trace = traces[0]
        assert trace["step"] == 1
        assert trace["action_type"] == "type"
        assert trace["selector"] == "input#query"
        assert trace["value"] == "search keyword"
        assert trace["url_before"] == "https://app.example.com"
        assert trace["url_after"] == "https://app.example.com/results"
        assert len(trace["network_calls_triggered"]) == 1
        assert trace["network_calls_triggered"][0]["url"] == "https://app.example.com/api/search"
