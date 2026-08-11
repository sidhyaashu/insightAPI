"""
test_cli_and_session_store.py — Unit tests for zero-dependency CLI session store,
auto-exporting crawl command, and database-free list & export CLI commands.
"""
import json
import pytest
from pathlib import Path
from typer.testing import CliRunner

from app.services.session_store import (
    save_session,
    get_session,
    list_sessions,
    get_sessions_dir,
    _prune_old_sessions,
)
from app.sdk import CrawlResult
from app.cli.main import app


runner = CliRunner()


@pytest.fixture
def temp_session_store(tmp_path, monkeypatch):
    """Redirect session store directory to a temporary folder during tests."""
    mock_dir = tmp_path / "sessions"
    mock_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.services.session_store.get_sessions_dir", lambda: mock_dir)
    return mock_dir


def test_session_store_save_get_list(temp_session_store):
    """Test saving, retrieving (exact + prefix + latest), and listing local session files."""
    eps = [
        {"method": "GET", "template_route": "/api/v1/users", "status": 200, "graphql_operation_name": None},
        {"method": "POST", "template_route": "/graphql", "status": 200, "graphql_operation_name": "GetUser"},
    ]

    sid1 = save_session("sess-1111-2222", "https://example.com", eps, explored_count=3, elapsed_time_seconds=1.5)
    sid2 = save_session("sess-3333-4444", "https://test.org", eps, explored_count=5, elapsed_time_seconds=2.8)

    assert sid1 == "sess-1111-2222"
    assert sid2 == "sess-3333-4444"

    # Get exact match
    s1 = get_session("sess-1111-2222")
    assert s1 is not None
    assert s1["target_url"] == "https://example.com"
    assert len(s1["captured_endpoints"]) == 2

    # Get prefix match
    s1_pref = get_session("sess-1111")
    assert s1_pref is not None
    assert s1_pref["session_id"] == "sess-1111-2222"

    # Get latest session
    latest = get_session()
    assert latest is not None
    assert latest["session_id"] == "sess-3333-4444"

    # List sessions
    all_sess = list_sessions()
    assert len(all_sess) == 2
    assert all_sess[0]["session_id"] == "sess-3333-4444"


def test_session_store_prune(temp_session_store, monkeypatch):
    """Test automatic pruning of old sessions when MAX_LOCAL_SESSIONS is exceeded."""
    monkeypatch.setattr("app.services.session_store.MAX_LOCAL_SESSIONS", 3)

    for i in range(5):
        save_session(f"sess-old-{i}", "https://example.com", [], explored_count=1)

    sessions = list_sessions()
    assert len(sessions) == 3
    session_ids = [s["session_id"] for s in sessions]
    assert "sess-old-4" in session_ids
    assert "sess-old-0" not in session_ids


def test_crawl_result_properties():
    """Test CrawlResult REST, GraphQL, and WebSocket counter properties."""
    captured = [
        {"method": "GET", "template_route": "/users", "graphql_operation_name": None},
        {"method": "POST", "template_route": "/posts", "graphql_operation_name": None},
        {"method": "POST", "template_route": "/graphql", "graphql_operation_name": "GetItems"},
        {"method": "WS", "template_route": "/ws", "graphql_operation_name": None},
    ]

    res = CrawlResult("https://example.com", captured, session_id="test-sid", explored_count=4, elapsed_time_seconds=3.2)

    assert res.rest_count == 2
    assert res.graphql_count == 1
    assert res.websocket_count == 1
    assert res.session_id == "test-sid"
    assert res.explored_count == 4
    assert res.elapsed_time_seconds == 3.2


def test_cli_export_command(temp_session_store, tmp_path):
    """Test `insightapi export` reading real session_store data without DB."""
    eps = [
        {"method": "GET", "template_route": "/api/v1/products", "status": 200, "schema": {"type": "object"}},
    ]
    sid = save_session("export-sess-123", "https://httpbin.org", eps, explored_count=2, elapsed_time_seconds=1.2)

    out_file = tmp_path / "spec.json"

    # Export OpenAPI
    result = runner.invoke(app, ["export", "--session-id", sid, "--format", "openapi", "--output", str(out_file)])
    assert result.exit_code == 0
    assert "Successfully exported OPENAPI" in result.output
    assert out_file.exists()
    spec_data = json.loads(out_file.read_text(encoding="utf-8"))
    assert spec_data["openapi"] == "3.0.3"

    # Export All
    out_dir = tmp_path / "output_all"
    result_all = runner.invoke(app, ["export", "--session-id", sid, "--format", "all", "--output", str(out_dir)])
    assert result_all.exit_code == 0
    assert (out_dir / "openapi.json").exists()
    assert (out_dir / "postman.json").exists()
    assert (out_dir / "API_DOCS.md").exists()


def test_cli_list_endpoints_command(temp_session_store):
    """Test `insightapi list-endpoints` command listing real endpoints from session store."""
    eps = [
        {"method": "GET", "template_route": "/api/v1/items", "status": 200, "confidence": 0.95, "graphql_operation_name": None},
        {"method": "POST", "template_route": "/graphql", "status": 200, "confidence": 0.90, "graphql_operation_name": "GetItems"},
    ]
    sid = save_session("list-sess-999", "https://example.com", eps, explored_count=3, elapsed_time_seconds=2.0)

    # List endpoints for session
    result = runner.invoke(app, ["list-endpoints", sid])
    assert result.exit_code == 0
    assert "/api/v1/items" in result.output
    assert "GraphQL" in result.output
    assert "REST" in result.output

    # List sessions table
    result_sessions = runner.invoke(app, ["list-endpoints", "--sessions"])
    assert result_sessions.exit_code == 0
    assert "Saved Crawl Sessions" in result_sessions.output
    assert "list-sess" in result_sessions.output
