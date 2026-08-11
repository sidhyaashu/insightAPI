"""
test_session_injection.py — Unit tests for authenticated session support.

Tests:
  1. storage_state is forwarded to Playwright's new_context() when provided.
  2. storage_state is NOT stored in CRAWL_SESSIONS after a crawl.
  3. New CSRF/XSRF/session header names are redacted by NetworkFilter.
  4. New body fields (id_token, session_id, etc.) are redacted by NetworkFilter.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# 1. BrowserManager passes storage_state to new_context()
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_storage_state_injected_into_context():
    """BrowserManager.start() must pass storage_state to browser.new_context()."""
    from app.engine.browser.manager import BrowserManager

    fake_storage = {
        "cookies": [{"name": "session", "value": "abc123", "domain": "example.com"}],
        "origins": []
    }

    mock_context = AsyncMock()
    mock_context.add_init_script = AsyncMock()
    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_chromium = MagicMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium
    mock_pw.stop = AsyncMock()

    mock_pw_ctx = MagicMock()
    mock_pw_ctx.start = AsyncMock(return_value=mock_pw)

    with patch("app.engine.browser.manager.async_playwright", return_value=mock_pw_ctx):
        manager = BrowserManager(headless=True, storage_state=fake_storage)
        await manager.start()

    mock_browser.new_context.assert_called_once()
    call_kwargs = mock_browser.new_context.call_args.kwargs
    assert "storage_state" in call_kwargs, "storage_state must be passed to new_context()"
    assert call_kwargs["storage_state"] == fake_storage
    assert "user_agent" not in call_kwargs, "user_agent must be omitted when storage_state is provided"


@pytest.mark.asyncio
async def test_no_storage_state_sets_user_agent():
    """Without storage_state BrowserManager should set a custom user_agent."""
    from app.engine.browser.manager import BrowserManager

    mock_context = AsyncMock()
    mock_context.add_init_script = AsyncMock()
    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)

    mock_chromium = MagicMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium
    mock_pw.stop = AsyncMock()

    mock_pw_ctx = MagicMock()
    mock_pw_ctx.start = AsyncMock(return_value=mock_pw)

    with patch("app.engine.browser.manager.async_playwright", return_value=mock_pw_ctx):
        manager = BrowserManager(headless=True, storage_state=None)
        await manager.start()

    call_kwargs = mock_browser.new_context.call_args.kwargs
    assert "user_agent" in call_kwargs, "user_agent must be set when no storage_state is provided"
    assert "storage_state" not in call_kwargs


# ---------------------------------------------------------------------------
# 2. session_state is never stored in CRAWL_SESSIONS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_crawl_sessions_does_not_store_session_state():
    """
    After run_background_crawl completes, CRAWL_SESSIONS[session_id] must not
    contain a 'session_state' key (credential leakage prevention).
    """
    from app.api.v1.endpoints.crawls import run_background_crawl, CRAWL_SESSIONS

    fake_session = {"cookies": [{"name": "auth", "value": "secret"}], "origins": []}
    session_id = "test-session-leak-check"
    CRAWL_SESSIONS[session_id] = {"session_id": session_id, "status": "running", "captured_endpoints": []}

    mock_result = MagicMock()
    mock_result.captured_endpoints = []
    mock_result.to_openapi.return_value = "{}"
    mock_result.to_postman.return_value = "{}"
    mock_result.to_markdown.return_value = ""

    with patch("app.api.v1.endpoints.crawls.AgentEngine") as MockEngine:
        instance = AsyncMock()
        instance.crawl = AsyncMock(return_value=mock_result)
        MockEngine.return_value = instance

        await run_background_crawl(
            session_id=session_id,
            url="https://example.com",
            max_pages=1,
            headless=True,
            session_state=fake_session,
        )

    stored = CRAWL_SESSIONS[session_id]
    assert "session_state" not in stored, (
        "session_state must NEVER be stored in CRAWL_SESSIONS (credential leakage risk)"
    )

    # Cleanup
    del CRAWL_SESSIONS[session_id]


# ---------------------------------------------------------------------------
# 3. New auth-session header names are redacted
# ---------------------------------------------------------------------------
def test_redact_new_auth_headers():
    """NetworkFilter must redact the extended set of auth-related request headers."""
    from app.engine.network.filter import NetworkFilter

    headers = {
        "x-csrf-token": "csrf_abc123",
        "x-xsrf-token": "xsrf_xyz",
        "x-request-token": "req_tok",
        "x-session-token": "sess_tok",
        "x-session-id": "sess_id_val",
        "session-id": "id_val",
        "bearer": "Bearer eyJhbGci...",
        "Content-Type": "application/json",   # must NOT be redacted
        "Accept": "application/json",          # must NOT be redacted
    }

    result = NetworkFilter.redact_sensitive_headers(headers)

    sensitive = [
        "x-csrf-token", "x-xsrf-token", "x-request-token",
        "x-session-token", "x-session-id", "session-id", "bearer",
    ]
    for key in sensitive:
        assert result[key] == "[REDACTED]", f"Header '{key}' was not redacted"

    # Safe headers should pass through unchanged
    assert result["Content-Type"] == "application/json"
    assert result["Accept"] == "application/json"


# ---------------------------------------------------------------------------
# 4. New body fields are redacted
# ---------------------------------------------------------------------------
def test_redact_new_auth_body_fields():
    """NetworkFilter must redact the extended set of auth-related body fields."""
    from app.engine.network.filter import NetworkFilter

    body = {
        "username": "alice",          # safe
        "id_token": "eyJhbGci...",    # redact
        "auth_token": "tok_abc",      # redact
        "bearer_token": "brr_xyz",    # redact
        "csrf_token": "csrfval",      # redact
        "xsrf_token": "xsrfval",     # redact
        "session_id": "s123",         # redact
        "session_token": "stok",      # redact
        "data": {
            "client_secret": "secret!", # redact (nested)
            "name": "Bob",              # safe (nested)
        }
    }

    result = NetworkFilter.redact_sensitive_body(body)

    assert result["username"] == "alice", "Non-sensitive field must not be redacted"
    for field in ["id_token", "auth_token", "bearer_token", "csrf_token", "xsrf_token", "session_id", "session_token"]:
        assert result[field] == "[REDACTED]", f"Body field '{field}' was not redacted"
    assert result["data"]["client_secret"] == "[REDACTED]", "Nested sensitive field was not redacted"
    assert result["data"]["name"] == "Bob", "Nested non-sensitive field must not be redacted"
