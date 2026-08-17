import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.api.v1.endpoints.crawls import run_background_crawl, CRAWL_SESSIONS


@pytest.mark.asyncio
async def test_crawl_completion_with_failed_snapshots_marks_complete_no_snapshot():
    """
    Verify F-38: If snapshot persistence fails during crawl completion, the session
    is marked 'complete_no_snapshot' (instead of plain 'completed') and logs a warning.
    """
    session_id = "test-session-snap-fail"
    CRAWL_SESSIONS[session_id] = {
        "session_id": session_id,
        "user_id": "user-123",
        "status": "running",
        "target_url": "https://api.example.com",
    }

    mock_crawl_result = MagicMock()
    mock_crawl_result.captured_endpoints = [{"method": "GET", "url": "https://api.example.com/items"}]
    mock_crawl_result.action_traces = []
    mock_crawl_result.llm_metrics = {}
    mock_crawl_result.to_openapi.return_value = {"openapi": "3.0.0"}
    mock_crawl_result.to_postman.return_value = {"info": {}}
    mock_crawl_result.to_markdown.return_value = "# Docs"

    mock_engine = MagicMock()
    mock_engine.crawl = AsyncMock(return_value=mock_crawl_result)

    mock_db_session = MagicMock()
    mock_db_cm = MagicMock()
    mock_db_cm.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.api.v1.endpoints.crawls.AgentEngine", return_value=mock_engine), \
         patch("app.core.database.AsyncSessionLocal", return_value=mock_db_cm), \
         patch("app.api.v1.endpoints.crawls.SnapshotRepository") as mock_snap_repo_cls, \
         patch("app.api.v1.endpoints.crawls.CrawlRepository") as mock_crawl_repo_cls, \
         patch("app.api.v1.endpoints.crawls.publish_ws_event", new=AsyncMock()):

        # Force snapshot bulk_upsert to raise an error
        mock_snap_repo = MagicMock()
        mock_snap_repo.bulk_upsert_snapshots = AsyncMock(side_effect=RuntimeError("Database lock / constraint error"))
        mock_snap_repo_cls.return_value = mock_snap_repo

        mock_repo_instance = MagicMock()
        mock_repo_instance.update_status = AsyncMock()
        mock_crawl_repo_cls.return_value = mock_repo_instance

        await run_background_crawl(
            session_id=session_id,
            url="https://api.example.com",
            max_pages=5,
            headless=True,
            user_id="user-123",
            user_tier="FREE",
        )

        # In-memory status should reflect partial failure
        assert CRAWL_SESSIONS[session_id]["status"] == "complete_no_snapshot"
        assert "snapshot persistence failed" in CRAWL_SESSIONS[session_id]["error_message"]

        # Postgres repo update_status call should also reflect complete_no_snapshot
        mock_repo_instance.update_status.assert_called_once()
        called_status = mock_repo_instance.update_status.call_args[1]["status"]
        assert called_status == "complete_no_snapshot"
