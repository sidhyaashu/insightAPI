import pytest
import asyncio
from app import AgentEngine, CrawlResult


@pytest.mark.asyncio
async def test_e2e_crawl_pipeline():
    """
    End-to-end test of the full InsightAPI AI pipeline:
    1. BrowserManager starts stealth Chromium
    2. Page navigation & NetworkObserver interception
    3. DOMDistiller interactive snapshot extraction
    4. LangGraph StateGraph execution (Planner -> Risk Evaluator -> Analyzer)
    5. CrawlResult schema generation & triple exporters (OpenAPI, Postman, Markdown)
    """
    engine = AgentEngine(headless=True)
    
    # Run crawl on a fast reliable target
    target_url = "https://httpbin.org/get"
    result = await engine.crawl(target_url, max_pages=2)

    assert isinstance(result, CrawlResult)
    assert result.target_url == target_url
    assert isinstance(result.captured_endpoints, list)

    # Test exporters on CrawlResult
    openapi_spec = result.to_openapi()
    assert '"openapi": "3.0.3"' in openapi_spec
    
    postman_coll = result.to_postman()
    assert '"schema"' in postman_coll
    
    markdown_docs = result.to_markdown()
    assert "# API Documentation" in markdown_docs
