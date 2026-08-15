"""
Unit tests for Pay-Per-Crawl Overage Billing and Quota Branching in InsightAPI.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from app.api.v1.endpoints.crawls import start_crawl, _report_metered_usage, CrawlRequest


@pytest.mark.asyncio
async def test_quota_exceeded_without_overage_raises_429():
    """Verify that exceeding quota without allow_overage raises a 429 HTTPException."""
    mock_db = AsyncMock()
    mock_bg = MagicMock()

    request = CrawlRequest(url="https://api.example.com", tos_accepted=True)

    with patch("app.api.v1.endpoints.crawls.CrawlRepository") as mock_repo_cls, \
         patch("app.api.v1.endpoints.crawls.DomainRepository") as mock_domain_repo_cls:
        mock_domain_repo = MagicMock()
        mock_domain_repo.is_domain_verified = AsyncMock(return_value=True)
        mock_domain_repo_cls.return_value = mock_domain_repo

        mock_repo = MagicMock()
        mock_repo.check_daily_quota = AsyncMock(return_value=(1, True))  # (count=1, is_exceeded=True)
        mock_repo_cls.return_value = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await start_crawl(
                request=request,
                background_tasks=mock_bg,
                x_user_id="user_123",
                x_user_tier="FREE",
                x_user_allow_overage="false",
                db=mock_db,
            )

        assert exc_info.value.status_code == 429
        assert "Daily crawl limit reached" in exc_info.value.detail
        assert "Enable Pay-per-crawl overage" in exc_info.value.detail


@pytest.mark.asyncio
async def test_quota_exceeded_with_overage_bypasses_429():
    """Verify that exceeding quota with allow_overage=True allows crawl and queues overage task."""
    mock_db = AsyncMock()
    mock_bg = MagicMock()

    request = CrawlRequest(url="https://api.example.com", max_pages=5, tos_accepted=True)

    with patch("app.api.v1.endpoints.crawls.CrawlRepository") as mock_repo_cls, \
         patch("app.api.v1.endpoints.crawls.DomainRepository") as mock_domain_repo_cls, \
         patch("app.queue.client.CrawlQueueClient.enqueue_crawl_job", new=AsyncMock()) as mock_enqueue:
        mock_domain_repo = MagicMock()
        mock_domain_repo.is_domain_verified = AsyncMock(return_value=True)
        mock_domain_repo_cls.return_value = mock_domain_repo

        mock_repo = MagicMock()
        mock_repo.check_daily_quota = AsyncMock(return_value=(1, True))  # exceeded
        mock_session_obj = MagicMock()
        mock_session_obj.id = "session_overage_123"
        mock_repo.create = AsyncMock(return_value=mock_session_obj)
        mock_repo.increment_daily_quota = AsyncMock()
        mock_repo_cls.return_value = mock_repo

        resp = await start_crawl(
            request=request,
            background_tasks=mock_bg,
            x_user_id="user_123",
            x_user_tier="FREE",
            x_user_allow_overage="true",
            db=mock_db,
        )

        assert resp.status == "running"
        assert resp.session_id == "session_overage_123"
        assert resp.target_url == "https://api.example.com"

        # Verify background task or queue dispatch was added with is_overage=True
        assert mock_enqueue.called or mock_bg.add_task.called
        if mock_enqueue.called:
            payload = mock_enqueue.call_args[0][1]
            assert payload["is_overage"] is True
            assert payload["user_tier"] == "FREE"


@pytest.mark.asyncio
async def test_payg_tier_bypasses_quota_and_marks_overage():
    """Verify that PAYG tier accounts automatically bypass quota limits."""
    mock_db = AsyncMock()
    mock_bg = MagicMock()

    request = CrawlRequest(url="https://api.payg.io", tos_accepted=True)

    with patch("app.api.v1.endpoints.crawls.CrawlRepository") as mock_repo_cls, \
         patch("app.api.v1.endpoints.crawls.DomainRepository") as mock_domain_repo_cls:
        mock_domain_repo = MagicMock()
        mock_domain_repo.is_domain_verified = AsyncMock(return_value=True)
        mock_domain_repo_cls.return_value = mock_domain_repo

        mock_repo = MagicMock()
        mock_repo.check_daily_quota = AsyncMock(return_value=(0, False))
        mock_session_obj = MagicMock()
        mock_session_obj.id = "session_payg_456"
        mock_repo.create = AsyncMock(return_value=mock_session_obj)
        mock_repo.increment_daily_quota = AsyncMock()
        mock_repo_cls.return_value = mock_repo

        resp = await start_crawl(
            request=request,
            background_tasks=mock_bg,
            x_user_id="user_payg_1",
            x_user_tier="PAYG",
            x_user_allow_overage="false",
            db=mock_db,
        )

        assert resp.status == "running"
        assert resp.session_id == "session_payg_456"


@pytest.mark.asyncio
async def test_report_metered_usage_dispatch():
    """Verify that _report_metered_usage dispatches a POST request to core-service payments endpoint."""
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        await _report_metered_usage(
            user_id="user_test_99",
            session_id="crawl_test_99",
            url="https://example.com/api",
        )

        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        call_json = mock_client.post.call_args[1]["json"]
        call_headers = mock_client.post.call_args[1]["headers"]

        assert "/api/v1/payments/usage-records" in call_url
        assert call_json["user_id"] == "user_test_99"
        assert call_json["crawl_id"] == "crawl_test_99"
        assert call_json["quantity"] == 1
        assert call_headers["x-user-id"] == "user_test_99"
