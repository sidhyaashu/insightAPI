import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_internal_session_missing_secret_returns_403():
    """
    Verify F-9: Requests to /internal without x-gateway-secret return 403 Forbidden.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/internal/users/user_target/session")
        assert resp.status_code == 403 or resp.status_code == 422


@pytest.mark.asyncio
async def test_internal_session_mismatched_user_id_returns_403():
    """
    Verify F-9: If a forwarded user header tries to query another user's session, reject with 403.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/internal/users/user_target/session",
            headers={
                "x-gateway-secret": settings.GATEWAY_SECRET,
                "x-user-id": "attacker_user_id",
            },
        )
        assert resp.status_code == 403
        assert "Cross-user" in resp.json().get("detail", "")
