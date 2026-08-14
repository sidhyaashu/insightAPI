"""
Unit tests for Domain Ownership Verification, DNS/HTTP Challenges, and ToS Gating.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from app.core.domain_verifier import DomainVerifier, generate_verification_token, normalize_domain
from app.api.v1.endpoints.crawls import start_crawl, CrawlRequest


def test_normalize_domain():
    """Verify domain normalization handles schemes, ports, and subpaths."""
    assert normalize_domain("https://api.example.com/v1/users") == "api.example.com"
    assert normalize_domain("http://example.com:8080/path") == "example.com"
    assert normalize_domain("MY-API.ORG") == "my-api.org"
    assert normalize_domain("  staging.app.io  ") == "staging.app.io"


def test_generate_verification_token():
    """Verify collision-resistant token format."""
    token1 = generate_verification_token()
    token2 = generate_verification_token()
    assert token1.startswith("insightapi-verify-")
    assert token2.startswith("insightapi-verify-")
    assert token1 != token2


@pytest.mark.asyncio
async def test_dns_txt_verification_success_and_failure():
    """Verify DoH DNS TXT verification checks token in answer records."""
    verifier = DomainVerifier(timeout=5.0)

    # 1. Success case: DoH returns matching TXT record
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "Answer": [
                {"name": "_insightapi-challenge.example.com", "type": 16, "data": '"insightapi-verify-12345"'}
            ]
        })
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        is_verified = await verifier.verify_dns_txt("example.com", "insightapi-verify-12345")
        assert is_verified is True

    # 2. Failure case: DoH returns non-matching TXT record
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={
            "Answer": [
                {"name": "_insightapi-challenge.example.com", "type": 16, "data": '"v=spf1 include:_spf.google.com ~all"'}
            ]
        })
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        is_verified = await verifier.verify_dns_txt("example.com", "insightapi-verify-99999")
        assert is_verified is False


@pytest.mark.asyncio
async def test_well_known_file_verification_success_and_failure():
    """Verify well-known HTTP file challenge checks token in body."""
    verifier = DomainVerifier(timeout=5.0)

    # 1. Success case: HTTP 200 with token in body
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "insightapi-verify-abcdef"
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        is_verified = await verifier.verify_well_known_file("example.com", "insightapi-verify-abcdef")
        assert is_verified is True

    # 2. Failure case: HTTP 404
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        is_verified = await verifier.verify_well_known_file("example.com", "insightapi-verify-abcdef")
        assert is_verified is False


@pytest.mark.asyncio
async def test_start_crawl_unverified_domain_without_tos_returns_403():
    """Verify attempting to crawl an unverified target without ToS acceptance raises 403 Forbidden."""
    mock_db = AsyncMock()
    mock_bg = MagicMock()
    mock_req = MagicMock()
    mock_req.headers = {}
    mock_req.client.host = "192.0.2.1"

    request = CrawlRequest(url="https://unverified-api.io", tos_accepted=False)

    with patch("app.api.v1.endpoints.crawls.DomainRepository") as mock_domain_repo_cls:
        mock_domain_repo = MagicMock()
        mock_domain_repo.is_domain_verified = AsyncMock(return_value=False)
        mock_domain_repo_cls.return_value = mock_domain_repo

        with pytest.raises(HTTPException) as exc_info:
            await start_crawl(
                request=request,
                background_tasks=mock_bg,
                http_request=mock_req,
                x_user_id="user_test_1",
                x_user_tier="FREE",
                db=mock_db,
            )

        assert exc_info.value.status_code == 403
        assert "not verified for your account" in exc_info.value.detail
        assert "Terms of Service" in exc_info.value.detail


@pytest.mark.asyncio
async def test_start_crawl_unverified_domain_with_tos_logs_acceptance_and_succeeds():
    """Verify crawling an unverified target with tos_accepted=True logs an audit record and proceeds."""
    mock_db = AsyncMock()
    mock_bg = MagicMock()
    mock_req = MagicMock()
    mock_req.headers = {"x-forwarded-for": "203.0.113.45"}
    mock_req.client.host = "127.0.0.1"

    request = CrawlRequest(url="https://unverified-api.io", tos_accepted=True)

    with patch("app.api.v1.endpoints.crawls.DomainRepository") as mock_domain_repo_cls, \
         patch("app.api.v1.endpoints.crawls.CrawlRepository") as mock_crawl_repo_cls:

        mock_domain_repo = MagicMock()
        mock_domain_repo.is_domain_verified = AsyncMock(return_value=False)
        mock_domain_repo.record_tos_acceptance = AsyncMock()
        mock_domain_repo_cls.return_value = mock_domain_repo

        mock_crawl_repo = MagicMock()
        mock_crawl_repo.check_daily_quota = AsyncMock(return_value=(0, False))
        mock_session_obj = MagicMock()
        mock_session_obj.id = "session_tos_pass"
        mock_crawl_repo.create = AsyncMock(return_value=mock_session_obj)
        mock_crawl_repo.increment_daily_quota = AsyncMock()
        mock_crawl_repo_cls.return_value = mock_crawl_repo

        resp = await start_crawl(
            request=request,
            background_tasks=mock_bg,
            http_request=mock_req,
            x_user_id="user_test_1",
            x_user_tier="FREE",
            db=mock_db,
        )

        assert resp.status == "running"
        assert resp.session_id == "session_tos_pass"

        # Verify ToS audit record was saved with user IP and domain
        mock_domain_repo.record_tos_acceptance.assert_called_once()
        _, tos_kwargs = mock_domain_repo.record_tos_acceptance.call_args
        assert tos_kwargs["user_id"] == "user_test_1"
        assert tos_kwargs["domain"] == "unverified-api.io"
        assert tos_kwargs["user_ip"] == "203.0.113.45"


@pytest.mark.asyncio
async def test_start_crawl_verified_domain_succeeds_without_tos_checkbox():
    """Verify crawling a pre-verified domain succeeds directly without requiring tos_accepted."""
    mock_db = AsyncMock()
    mock_bg = MagicMock()
    mock_req = MagicMock()
    mock_req.headers = {}
    mock_req.client.host = "10.0.0.1"

    request = CrawlRequest(url="https://verified-company.com", tos_accepted=False)

    with patch("app.api.v1.endpoints.crawls.DomainRepository") as mock_domain_repo_cls, \
         patch("app.api.v1.endpoints.crawls.CrawlRepository") as mock_crawl_repo_cls:

        mock_domain_repo = MagicMock()
        mock_domain_repo.is_domain_verified = AsyncMock(return_value=True)
        mock_domain_repo_cls.return_value = mock_domain_repo

        mock_crawl_repo = MagicMock()
        mock_crawl_repo.check_daily_quota = AsyncMock(return_value=(0, False))
        mock_session_obj = MagicMock()
        mock_session_obj.id = "session_verified_direct"
        mock_crawl_repo.create = AsyncMock(return_value=mock_session_obj)
        mock_crawl_repo.increment_daily_quota = AsyncMock()
        mock_crawl_repo_cls.return_value = mock_crawl_repo

        resp = await start_crawl(
            request=request,
            background_tasks=mock_bg,
            http_request=mock_req,
            x_user_id="user_test_1",
            x_user_tier="FREE",
            db=mock_db,
        )

        assert resp.status == "running"
        assert resp.session_id == "session_verified_direct"
        # Since domain is verified, ToS record does not need to be written
        mock_domain_repo.record_tos_acceptance.assert_not_called()
