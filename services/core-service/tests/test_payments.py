import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from app.api.v1.endpoints.payments import report_usage_record, UsageRecordRequest


@pytest.mark.asyncio
async def test_report_usage_record_idor_mismatch_raises_403():
    """Verify that submitting a body.user_id different from x_user_id raises 403 Forbidden."""
    body = UsageRecordRequest(
        user_id="victim_user_456",
        crawl_id="crawl_123",
        quantity=1,
    )
    with pytest.raises(HTTPException) as exc_info:
        await report_usage_record(
            body=body,
            x_user_id="attacker_user_123",
        )

    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail


@pytest.mark.asyncio
async def test_report_usage_record_matching_or_omitted_user_id_succeeds():
    """Verify that when body.user_id matches x_user_id or is omitted, usage is billed to x_user_id."""
    body_matching = UsageRecordRequest(
        user_id="legit_user_123",
        crawl_id="crawl_123",
        quantity=1,
    )

    mock_user = MagicMock()
    mock_user.id = "legit_user_123"
    mock_user.email = "legit@example.com"
    mock_user.stripe_customer_id = "cus_test_123"

    with patch("app.api.v1.endpoints.payments.UserRepository") as mock_user_repo_cls, \
         patch("app.api.v1.endpoints.payments.settings") as mock_settings:
        mock_settings.STRIPE_SECRET_KEY = None
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_user)
        mock_user_repo_cls.return_value = mock_repo

        res = await report_usage_record(
            body=body_matching,
            x_user_id="legit_user_123",
        )
        assert res["status"] == "success"

        # Also test with body.user_id omitted (None)
        body_omitted = UsageRecordRequest(
            crawl_id="crawl_456",
            quantity=2,
        )
        res2 = await report_usage_record(
            body=body_omitted,
            x_user_id="legit_user_123",
        )
        assert res2["status"] == "success"
        assert res2["quantity"] == 2
