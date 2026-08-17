import pytest
from app.api.v1.endpoints.proxy import _resolve_upstream, ROUTE_TABLE


def test_internal_routes_not_in_gateway_route_table():
    """
    Verify F-9: Gateway ROUTE_TABLE does NOT expose internal endpoints.
    Public requests to /api/v1/internal/* or /api/internal/* must fail upstream resolution.
    """
    assert "/api/v1/internal" not in ROUTE_TABLE
    assert "/api/internal" not in ROUTE_TABLE

    assert _resolve_upstream("/api/v1/internal/users/user_123/session") is None
    assert _resolve_upstream("/api/internal/users/user_123/tier") is None
