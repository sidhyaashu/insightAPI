import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from app.api.v1.endpoints.drift import get_drift_report, trigger_drift_webhook, WebhookRequest


@pytest.mark.asyncio
async def test_drift_report_cross_tenant_access_raises_403():
    """Verify that user_A cannot fetch user_B's project drift report (expect 403 Forbidden)."""
    mock_db = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_drift_report(
            project_id="user_B_project",
            compare="crawl_B_2",
            base="crawl_B_1",
            x_user_id="user_A",
            x_user_tier="PRO",
            db=mock_db,
        )

    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail


@pytest.mark.asyncio
async def test_drift_webhook_cross_tenant_access_raises_403():
    """Verify that user_A cannot trigger a drift webhook on user_B's project (expect 403 Forbidden)."""
    mock_db = AsyncMock()
    body = WebhookRequest(
        compare_crawl_id="crawl_B_2",
        webhook_url="https://ci.example.com/webhook",
        base_crawl_id="crawl_B_1",
    )

    with pytest.raises(HTTPException) as exc_info:
        await trigger_drift_webhook(
            project_id="user_B_project",
            body=body,
            x_user_id="user_A",
            x_user_tier="PRO",
            db=mock_db,
        )

    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail


@pytest.mark.asyncio
async def test_drift_report_unauthorized_crawl_snapshots_raises_404():
    """Verify that if a user queries their own project but provides another tenant's crawl ID, it raises 404."""
    mock_db = AsyncMock()

    with patch("app.api.v1.endpoints.drift.compare_snapshots") as mock_compare:
        mock_compare.side_effect = HTTPException(
            status_code=404,
            detail="Crawl snapshot 'crawl_other_tenant' not found for project 'user_A'."
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_drift_report(
                project_id="user_A",
                compare="crawl_other_tenant",
                base="crawl_user_A_1",
                x_user_id="user_A",
                x_user_tier="PRO",
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "not found for project" in exc_info.value.detail
