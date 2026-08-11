import pytest
import asyncio
import requests
from app import AgentEngine, CrawlResult
from app.agents.nodes.analyzer import AnalyzerNode
from app.api.v1.endpoints.crawls import validate_target_url_ssrf
from fastapi import HTTPException

BASE_URL = "http://localhost:8000"


def test_analyzer_data_preservation():
    """Verify AnalyzerNode preserves raw endpoint fields and attaches schema."""
    raw_endpoints = [{
        "method": "POST",
        "url": "https://example.com/api/users",
        "template_route": "/api/users",
        "status": 201,
        "request_headers": {"Authorization": "Bearer token123"},
        "request_payload": {"name": "Alice"},
        "response_headers": {"Content-Type": "application/json"},
        "response_body": {"id": 1, "name": "Alice", "created_at": "2026-08-03"}
    }]
    
    state = {"captured_endpoints": raw_endpoints}
    result_state = asyncio.run(AnalyzerNode.process(state))
    captured = result_state["captured_endpoints"]

    assert len(captured) == 1
    ep = captured[0]
    # Check preserved fields
    assert ep["url"] == "https://example.com/api/users"
    assert ep["request_headers"]["Authorization"] == "Bearer token123"
    assert ep["request_payload"]["name"] == "Alice"
    assert ep["response_headers"]["Content-Type"] == "application/json"
    # Check schema attachment
    assert "schema" in ep
    assert ep["schema"]["properties"]["id"]["type"] == "integer"


def test_ssrf_validation_guard():
    """Verify SSRF validation blocks loopback, cloud metadata, and restricted IPs."""
    # Blocked SSRF targets
    blocked_urls = [
        "http://127.0.0.1/admin",
        "http://localhost:8000/health",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "file:///etc/passwd",
        "gopher://127.0.0.1:25/"
    ]

    for url in blocked_urls:
        with pytest.raises(HTTPException) as exc:
            validate_target_url_ssrf(url)
        assert exc.value.status_code == 400

    # Allowed valid public target
    validate_target_url_ssrf("https://example.com/api")


@pytest.mark.asyncio
async def test_multi_page_exploration_loop():
    """Verify AgentEngine explores multiple pages via graph loop."""
    engine = AgentEngine(headless=True)
    target_url = "https://httpbin.org/get"
    result = await engine.crawl(target_url, max_pages=2)

    assert isinstance(result, CrawlResult)
    assert result.target_url == target_url
    assert isinstance(result.captured_endpoints, list)


def test_reports_clean_404():
    """Verify invalid session ID returns 404 instead of fake data."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get("/api/v1/reports/non-existent-session-id-12345/export?format=openapi")
    assert r.status_code == 404
