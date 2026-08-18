import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_cors_allowed_origin_receives_headers():
    """Verify that a request from an allowed origin receives proper Access-Control-Allow-Origin headers."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Pre-flight OPTIONS request from allowed origin
        resp = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://app.insightapi.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code in (200, 204)
        assert resp.headers.get("access-control-allow-origin") == "https://app.insightapi.com"
        assert resp.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_disallowed_origin_does_not_receive_headers():
    """Verify that a request from an untrusted origin does NOT receive allow-origin header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://malicious-site.attacker.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != "https://malicious-site.attacker.com"
