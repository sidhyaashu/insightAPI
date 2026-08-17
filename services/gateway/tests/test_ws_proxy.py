import pytest
from app.api.v1.endpoints.ws import build_upstream_ws_url


def test_build_upstream_ws_url_http():
    """Verify that http:// AGENT_SERVICE_URL maps to ws:// scheme."""
    url = build_upstream_ws_url("http://agent-service:8002", "crawls/session-123/stream")
    assert url == "ws://agent-service:8002/ws/crawls/session-123/stream"

    # With redundant leading ws/
    url_leading = build_upstream_ws_url("http://agent-service:8002", "ws/crawls/session-123/stream")
    assert url_leading == "ws://agent-service:8002/ws/crawls/session-123/stream"

    # With query string
    url_query = build_upstream_ws_url("http://agent-service:8002", "chat/sess-1", query_string="token=jwt123")
    assert url_query == "ws://agent-service:8002/ws/chat/sess-1?token=jwt123"


def test_build_upstream_ws_url_https():
    """Verify that https:// AGENT_SERVICE_URL maps to wss:// scheme."""
    url = build_upstream_ws_url("https://agent.production.insightapi.com", "crawls/session-123/stream")
    assert url == "wss://agent.production.insightapi.com/ws/crawls/session-123/stream"

    # With custom port
    url_port = build_upstream_ws_url("https://agent.production.insightapi.com:8443", "chat/sess-1")
    assert url_port == "wss://agent.production.insightapi.com:8443/ws/chat/sess-1"

    # With query string
    url_query = build_upstream_ws_url("https://agent.production.insightapi.com", "crawls/session-123/stream", query_string="token=jwt123")
    assert url_query == "wss://agent.production.insightapi.com/ws/crawls/session-123/stream?token=jwt123"
