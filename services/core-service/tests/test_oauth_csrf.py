import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from fastapi.responses import Response
from app.api.v1.endpoints.auth import github_login, google_login, oauth_callback
from app.repositories.session_repo import SessionRepository


@pytest.mark.asyncio
async def test_oauth_login_generates_and_attaches_state_token():
    """Verify that /auth/github/login and /auth/google/login generate and attach a state param."""
    with patch.object(SessionRepository, "store_oauth_state", new=AsyncMock(return_value="mock_state_123")):
        gh_resp = await github_login()
        assert gh_resp.status_code == 307
        assert "state=mock_state_123" in gh_resp.headers["location"]

        google_resp = await google_login()
        assert google_resp.status_code == 307
        assert "state=mock_state_123" in google_resp.headers["location"]


@pytest.mark.asyncio
async def test_oauth_callback_missing_or_invalid_state_raises_400():
    """Verify that /auth/callback without a valid state parameter raises 400 Bad Request."""
    mock_response = Response()

    # Case 1: Missing state
    with patch.object(SessionRepository, "verify_and_consume_oauth_state", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc_info:
            await oauth_callback(
                response=mock_response,
                code="mock_oauth_code",
                provider="github",
                state=None,
            )
        assert exc_info.value.status_code == 400
        assert "CSRF protection failed" in exc_info.value.detail

    # Case 2: Forged / invalid state
    with patch.object(SessionRepository, "verify_and_consume_oauth_state", new=AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc_info:
            await oauth_callback(
                response=mock_response,
                code="mock_oauth_code",
                provider="github",
                state="attacker_forged_state",
            )
        assert exc_info.value.status_code == 400
        assert "CSRF protection failed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_oauth_callback_valid_state_exchanges_code():
    """Verify that /auth/callback with valid state consumes state and completes authentication."""
    mock_response = Response()
    mock_user = MagicMock()
    mock_user.id = "user_oauth_123"
    mock_user.email = "oauth@example.com"
    mock_user.name = "OAuth User"
    mock_user.avatar_url = "https://example.com/avatar.png"
    mock_user.tier = "FREE"
    mock_user.role = "user"
    mock_user.is_verified = True

    mock_profile = {
        "provider": "github",
        "sub": "gh_123",
        "email": "oauth@example.com",
        "name": "OAuth User",
        "avatar_url": "https://example.com/avatar.png",
    }

    with patch.object(SessionRepository, "verify_and_consume_oauth_state", new=AsyncMock(return_value=True)), \
         patch("app.api.v1.endpoints.auth.exchange_github_code", new=AsyncMock(return_value=mock_profile)), \
         patch("app.api.v1.endpoints.auth.UserRepository") as mock_user_repo_cls, \
         patch("app.api.v1.endpoints.auth.TokenService") as mock_token_svc_cls:

        mock_user_repo = MagicMock()
        mock_user_repo.upsert_oauth_user = AsyncMock(return_value=mock_user)
        mock_user_repo_cls.return_value = mock_user_repo

        mock_token_svc = MagicMock()
        mock_token_svc.issue_token_pair = AsyncMock(return_value={
            "access_token": "acc_tok_123",
            "refresh_token": "ref_tok_123",
        })
        mock_token_svc_cls.return_value = mock_token_svc

        res = await oauth_callback(
            response=mock_response,
            code="valid_code",
            provider="github",
            state="valid_state_123",
        )

        assert res["access_token"] == "acc_tok_123"
        assert res["user"]["id"] == "user_oauth_123"
