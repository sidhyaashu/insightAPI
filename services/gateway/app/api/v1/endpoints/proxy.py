"""Gateway — httpx reverse proxy to downstream services."""
from __future__ import annotations

import logging
import httpx
from fastapi import APIRouter, Request, Response, HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Route table: prefix → upstream base URL
ROUTE_TABLE = {
    "/api/v1/auth": settings.CORE_SERVICE_URL,
    "/api/v1/users": settings.CORE_SERVICE_URL,
    "/api/v1/payments": settings.CORE_SERVICE_URL,
    "/api/v1/internal": settings.CORE_SERVICE_URL,
    "/api/auth": settings.CORE_SERVICE_URL,
    "/api/users": settings.CORE_SERVICE_URL,
    "/api/payments": settings.CORE_SERVICE_URL,
    "/api/internal": settings.CORE_SERVICE_URL,
    "/api/v1/chat": settings.AGENT_SERVICE_URL,
    "/api/chat": settings.AGENT_SERVICE_URL,
    "/api/v1": settings.AGENT_SERVICE_URL,
}

_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        # Disable follow_redirects so HTTP 307/302 OAuth redirects are passed directly to the user's browser
        _client = httpx.AsyncClient(timeout=120.0, follow_redirects=False)
    return _client


def _resolve_upstream(path: str) -> str | None:
    for prefix, base in ROUTE_TABLE.items():
        if path.startswith(prefix):
            remainder = path[len(prefix):]
            return f"{base}{prefix}{remainder}"
    return None


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def reverse_proxy(request: Request, path: str):
    """Proxy all REST API requests to the appropriate downstream service."""
    full_path = f"/{path}"
    upstream_url = _resolve_upstream(full_path)

    if not upstream_url:
        raise HTTPException(status_code=404, detail=f"No upstream route for: {full_path}")

    # Forward injected headers to downstream
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["x-forwarded-for"] = request.client.host if request.client else "unknown"

    body = await request.body()

    client = await get_http_client()
    try:
        upstream_resp = await client.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
        )
    except httpx.RequestError as e:
        logger.error(f"Upstream request error: {e}")
        raise HTTPException(status_code=502, detail="Upstream service unavailable.")

    # Filter out hop-by-hop and conflicting headers (e.g. transfer-encoding + content-length)
    res_headers = dict(upstream_resp.headers)
    res_headers.pop("server", None)
    res_headers.pop("date", None)
    res_headers.pop("transfer-encoding", None)
    res_headers.pop("content-length", None)
    res_headers.pop("set-cookie", None)

    response = Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=res_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )

    # Forward all Set-Cookie headers individually to preserve both access_token and refresh_token
    for cookie_header in upstream_resp.headers.get_list("set-cookie"):
        response.raw_headers.append((b"set-cookie", cookie_header.encode("latin-1")))

    return response
