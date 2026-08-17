import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tasks import crawl_tasks
from app.api.v1.endpoints.crawls import start_crawl, CrawlRequest


@pytest.mark.asyncio
async def test_start_crawl_zero_workers_falls_back_to_background_tasks():
    """
    Verify F-45: When zero Celery workers are active, start_crawl falls back
    to BackgroundTasks immediately rather than silently pushing to a dead queue.
    """
    mock_db = AsyncMock()
    mock_bg = MagicMock()

    request = CrawlRequest(url="https://api.example.com", tos_accepted=True)

    with patch("app.api.v1.endpoints.crawls.DomainRepository") as mock_domain_repo_cls, \
         patch("app.api.v1.endpoints.crawls.CrawlRepository") as mock_crawl_repo_cls, \
         patch("app.tasks.crawl_tasks.is_celery_worker_active", return_value=False) as mock_liveness, \
         patch("app.tasks.crawl_tasks.run_crawl_task.delay") as mock_delay:

        mock_domain_repo = MagicMock()
        mock_domain_repo.is_domain_verified = AsyncMock(return_value=True)
        mock_domain_repo_cls.return_value = mock_domain_repo

        mock_crawl_repo = MagicMock()
        mock_crawl_repo.check_daily_quota = AsyncMock(return_value=(0, False))
        mock_session_obj = MagicMock()
        mock_session_obj.id = "session_fallback_123"
        mock_crawl_repo.create = AsyncMock(return_value=mock_session_obj)
        mock_crawl_repo.increment_daily_quota = AsyncMock()
        mock_crawl_repo_cls.return_value = mock_crawl_repo

        resp = await start_crawl(
            request=request,
            background_tasks=mock_bg,
            x_user_id="user_123",
            x_user_tier="FREE",
            x_user_allow_overage="false",
            db=mock_db,
        )

        assert resp.status == "running"
        assert resp.session_id == "session_fallback_123"

        # Celery task should NOT be delayed when no workers are active
        mock_delay.assert_not_called()

        # BackgroundTasks fallback MUST be added
        mock_bg.add_task.assert_called_once()
        added_fn = mock_bg.add_task.call_args[0][0]
        assert added_fn.__name__ == "run_background_crawl"
