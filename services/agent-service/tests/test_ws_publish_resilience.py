import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.api.v1.endpoints.crawls import (
    publish_ws_event,
    get_crawl_status,
    CRAWL_SESSIONS,
    CRAWL_WS_FAILURES,
    CRAWL_FALLBACK_EVENT_LOGS,
)


@pytest.mark.asyncio
async def test_publish_ws_event_retry_and_degraded_realtime_on_redis_failure():
    """
    Verify F-39: When Redis is unavailable, publish_ws_event retries, buffers the event
    in independent fallback storage, and sets degraded_realtime=True after 3 failures.
    """
    session_id = "test-resilience-session-1"
    CRAWL_SESSIONS[session_id] = {
        "session_id": session_id,
        "user_id": "test-user-1",
        "status": "running",
        "target_url": "https://example.com",
    }
    CRAWL_WS_FAILURES.pop(session_id, None)
    CRAWL_FALLBACK_EVENT_LOGS.pop(session_id, None)

    # Mock Redis client to always raise ConnectionError
    mock_redis = MagicMock()
    mock_redis.publish = AsyncMock(side_effect=ConnectionError("Redis connection refused"))

    with patch("app.api.v1.endpoints.crawls.get_redis_client", new=AsyncMock(return_value=mock_redis)):
        # Publish 3 events
        await publish_ws_event(session_id, {"type": "log", "message": "Step 1"})
        await publish_ws_event(session_id, {"type": "log", "message": "Step 2"})
        await publish_ws_event(session_id, {"type": "log", "message": "Step 3"})

        # Check failures counted
        assert CRAWL_WS_FAILURES[session_id] == 3

        # Check fallback event logs buffered all 3 events
        assert len(CRAWL_FALLBACK_EVENT_LOGS[session_id]) == 3
        assert CRAWL_FALLBACK_EVENT_LOGS[session_id][0]["message"] == "Step 1"

        # Complete the crawl
        CRAWL_SESSIONS[session_id]["status"] = "completed"
        CRAWL_SESSIONS[session_id]["captured_count"] = 5

        # Query GET /crawls/{session_id} status
        mock_db = AsyncMock()
        status_resp = await get_crawl_status(
            session_id=session_id,
            x_user_id="test-user-1",
            x_user_tier="FREE",
            db=mock_db,
        )

        assert status_resp["status"] == "completed"
        assert status_resp["degraded_realtime"] is True
        assert len(status_resp["event_logs"]) == 3
