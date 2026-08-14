"""
Integration tests for Multi-Tenant Data Isolation and Enterprise Audit Logging.
Validates that cross-tenant access attempts are strictly rejected with 404/403 and
that enterprise audit logs capture security and lifecycle operations.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException

from app.api.v1.endpoints.crawls import get_crawl_status, delete_crawl_session, generate_playwright_tests, CRAWL_SESSIONS
from app.api.v1.endpoints.reports import get_report_by_id, export_report
from app.api.v1.endpoints.auth_profiles import (
    get_auth_profile,
    update_auth_profile,
    delete_auth_profile,
    test_auth_profile as endpoint_test_auth_profile,
    UpdateAuthProfileRequest,
)
from app.api.v1.endpoints.audit_logs import get_audit_logs
from app.core.audit import AuditLogger
from app.repositories.audit_log_repo import AuditLogRepository
from app.models.crawl_session import CrawlSession


@pytest.mark.asyncio
async def test_cross_tenant_crawl_status_isolation():
    """Verify Tenant B cannot view or probe Tenant A's crawl sessions."""
    session_id = "crawl_user_a_123"
    mock_db_session = MagicMock(spec=CrawlSession)
    mock_db_session.id = session_id
    mock_db_session.user_id = "tenant_a"
    mock_db_session.target_url = "https://tenant-a-internal.com"
    mock_db_session.to_dict.return_value = {"session_id": session_id, "user_id": "tenant_a"}

    mock_db = AsyncMock()

    with patch("app.repositories.crawl_repo.CrawlRepository.get_by_id", new=AsyncMock(return_value=mock_db_session)):
        # 1. Tenant B attempt -> 404 Not Found (zero information disclosure)
        with pytest.raises(HTTPException) as exc_info:
            await get_crawl_status(
                session_id=session_id,
                x_user_id="tenant_b",
                x_user_tier="FREE",
                db=mock_db,
            )
        assert exc_info.value.status_code == 404

        # 2. Tenant A attempt -> 200 OK
        resp_a = await get_crawl_status(
            session_id=session_id,
            x_user_id="tenant_a",
            x_user_tier="FREE",
            db=mock_db,
        )
        assert resp_a["user_id"] == "tenant_a"

        # 3. Admin attempt -> 200 OK
        resp_admin = await get_crawl_status(
            session_id=session_id,
            x_user_id="super_admin",
            x_user_tier="ADMIN",
            db=mock_db,
        )
        assert resp_admin["user_id"] == "tenant_a"


@pytest.mark.asyncio
async def test_cross_tenant_crawl_deletion_isolation():
    """Verify Tenant B cannot delete Tenant A's crawl session."""
    session_id = "crawl_to_delete_999"
    mock_db_session = MagicMock(spec=CrawlSession)
    mock_db_session.id = session_id
    mock_db_session.user_id = "tenant_a"

    mock_db = AsyncMock()

    with patch("app.repositories.crawl_repo.CrawlRepository.get_by_id", new=AsyncMock(return_value=mock_db_session)):
        # Tenant B tries to delete Tenant A's session -> 404
        with pytest.raises(HTTPException) as exc_info:
            await delete_crawl_session(
                session_id=session_id,
                x_user_id="tenant_b",
                x_user_tier="FREE",
                db=mock_db,
            )
        assert exc_info.value.status_code == 404
        mock_db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_cross_tenant_report_and_export_isolation():
    """Verify Tenant B cannot access or export Tenant A's OpenAPI/Postman specs or Playwright tests."""
    session_id = "report_sess_456"
    mock_db_session = MagicMock(spec=CrawlSession)
    mock_db_session.id = session_id
    mock_db_session.user_id = "tenant_a"
    mock_db_session.target_url = "https://api.tenant-a.com"
    mock_db_session.openapi_spec = {"openapi": "3.0.3", "info": {"title": "Tenant A API"}}
    mock_db_session.postman_collection = {}
    mock_db_session.markdown_docs = "# Docs"
    mock_db_session.action_traces = []

    mock_db = AsyncMock()

    with patch("app.repositories.crawl_repo.CrawlRepository.get_by_id", new=AsyncMock(return_value=mock_db_session)):
        # 1. Report viewing
        with pytest.raises(HTTPException) as exc1:
            await get_report_by_id(
                session_id=session_id,
                x_user_id="tenant_b",
                x_user_tier="FREE",
                db=mock_db,
            )
        assert exc1.value.status_code == 404

        # 2. Spec export
        with pytest.raises(HTTPException) as exc2:
            await export_report(
                session_id=session_id,
                format="openapi",
                x_user_id="tenant_b",
                x_user_tier="STARTER",
                db=mock_db,
            )
        assert exc2.value.status_code == 404

        # 3. Test generation export
        with pytest.raises(HTTPException) as exc3:
            await generate_playwright_tests(
                session_id=session_id,
                format="python",
                x_user_id="tenant_b",
                x_user_tier="STARTER",
                db=mock_db,
            )
        assert exc3.value.status_code == 404


@pytest.mark.asyncio
async def test_cross_tenant_auth_profile_isolation():
    """Verify Tenant B cannot fetch, update, delete, or test Tenant A's AuthProfiles."""
    profile_id = "auth_prof_101"
    mock_db = AsyncMock()

    with patch("app.repositories.auth_profile_repo.AuthProfileRepository.get_profile", new=AsyncMock(return_value=None)), \
         patch("app.repositories.auth_profile_repo.AuthProfileRepository.update_profile", new=AsyncMock(return_value=None)), \
         patch("app.repositories.auth_profile_repo.AuthProfileRepository.delete_profile", new=AsyncMock(return_value=False)):

        # 1. GET
        with pytest.raises(HTTPException) as exc1:
            await get_auth_profile(profile_id=profile_id, x_user_id="tenant_b", db=mock_db)
        assert exc1.value.status_code == 404

        # 2. PATCH
        with pytest.raises(HTTPException) as exc2:
            await update_auth_profile(
                profile_id=profile_id,
                body=UpdateAuthProfileRequest(name="Hacked Name"),
                x_user_id="tenant_b",
                db=mock_db,
            )
        assert exc2.value.status_code == 404

        # 3. DELETE
        with pytest.raises(HTTPException) as exc3:
            await delete_auth_profile(profile_id=profile_id, x_user_id="tenant_b", db=mock_db)
        assert exc3.value.status_code == 404

        # 4. TEST
        with pytest.raises(HTTPException) as exc4:
            await endpoint_test_auth_profile(profile_id=profile_id, x_user_id="tenant_b", db=mock_db)
        assert exc4.value.status_code == 404


@pytest.mark.asyncio
async def test_audit_logs_tier_gating():
    """Verify GET /api/v1/audit-logs is strictly restricted to ENTERPRISE and ADMIN tiers."""
    mock_db = AsyncMock()

    # 1. FREE tier -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_free:
        await get_audit_logs(
            x_user_id="user_free",
            x_user_tier="FREE",
            db=mock_db,
        )
    assert exc_free.value.status_code == 403

    # 2. PRO tier -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_pro:
        await get_audit_logs(
            x_user_id="user_pro",
            x_user_tier="PRO",
            db=mock_db,
        )
    assert exc_pro.value.status_code == 403

    # 3. ENTERPRISE tier -> 200 OK
    mock_logs = [
        MagicMock(to_dict=lambda: {
            "id": "log_1",
            "user_id": "ent_user",
            "action": "crawl.create",
            "target_id": "sess_1",
            "ip": "10.0.0.1",
            "timestamp": "2026-08-14T23:50:00Z",
            "metadata": {"target_url": "https://example.com"},
        })
    ]
    with patch("app.repositories.audit_log_repo.AuditLogRepository.list_logs", new=AsyncMock(return_value=(mock_logs, 1))):
        res = await get_audit_logs(
            x_user_id="ent_user",
            x_user_tier="ENTERPRISE",
            db=mock_db,
        )
        assert res["total"] == 1
        assert len(res["items"]) == 1
        assert res["items"][0]["action"] == "crawl.create"


@pytest.mark.asyncio
async def test_audit_logger_records_event_safely():
    """Verify AuditLogger.log_event properly invokes AuditLogRepository without throwing on errors."""
    mock_db = AsyncMock()
    mock_repo = AsyncMock()

    with patch("app.repositories.audit_log_repo.AuditLogRepository.create_log", new=mock_repo.create_log):
        await AuditLogger.log_event(
            db=mock_db,
            user_id="enterprise_cust_1",
            action="export.download",
            target_id="sess_xyz",
            ip="192.168.1.50",
            metadata={"format": "playwright_python"},
        )
        mock_repo.create_log.assert_called_once()
