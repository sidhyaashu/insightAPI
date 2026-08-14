from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Header, Request
from fastapi.responses import Response, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.crawls import CRAWL_SESSIONS
from app.core.database import get_db
from app.core.audit import AuditLogger
from app.repositories.crawl_repo import CrawlRepository
from app.services.openapi_exporter import OpenAPIExporter
from app.services.postman_exporter import PostmanExporter
from app.services.markdown_exporter import MarkdownExporter
from app.services.fuzzer import APIFuzzer

router = APIRouter()


def _clean_header(val: Any, default: str = "") -> str:
    if hasattr(val, "default"):
        return str(val.default or default)
    return str(val if val is not None else default)


@router.get("/{session_id}")
async def get_report_by_id(
    session_id: str,
    x_user_id: str = Header("default-user", alias="X-User-Id"),
    x_user_tier: str = Header("FREE", alias="X-User-Tier"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full generated documentation (OpenAPI, Postman, Markdown) for a crawl session with tenant isolation."""
    user_id = _clean_header(x_user_id, "default-user")
    tier = _clean_header(x_user_tier, "FREE").upper()
    # 1. Try DB
    try:
        repo = CrawlRepository(db)
        db_session = await repo.get_by_id(session_id)
        if db_session:
            if db_session.user_id != user_id and tier != "ADMIN":
                raise HTTPException(status_code=404, detail="Crawl session report not found.")
            return {
                "session_id": db_session.id,
                "openapi_spec": db_session.openapi_spec,
                "postman_collection": db_session.postman_collection,
                "markdown_docs": db_session.markdown_docs,
                "action_traces": db_session.action_traces or [],
            }
    except HTTPException:
        raise
    except Exception:
        pass

    # 2. Try memory store
    if session_id in CRAWL_SESSIONS:
        session = CRAWL_SESSIONS[session_id]
        if session.get("user_id") and session["user_id"] != user_id and tier != "ADMIN":
            raise HTTPException(status_code=404, detail="Crawl session report not found.")

        target_url = session.get("target_url", "https://example.com")
        sample_endpoints = session.get("captured_endpoints", [])
        return {
            "session_id": session_id,
            "openapi_spec": session.get("openapi_spec") or OpenAPIExporter.generate_spec(f"Session-{session_id}", target_url, sample_endpoints),
            "postman_collection": session.get("postman_collection") or PostmanExporter.generate_collection(f"Session-{session_id}", target_url, sample_endpoints),
            "markdown_docs": session.get("markdown_docs") or MarkdownExporter.generate_markdown(f"Session-{session_id}", target_url, sample_endpoints),
            "action_traces": session.get("action_traces", []),
        }

    raise HTTPException(status_code=404, detail="Crawl session report not found.")


@router.get("/{session_id}/export")
async def export_report(
    session_id: str,
    format: str = Query("openapi", enum=["openapi", "postman", "markdown", "playwright_python", "playwright_ts"]),
    http_request: Request = None,
    x_user_id: str = Header("default-user", alias="X-User-Id"),
    x_user_tier: str | None = Header(None, alias="X-User-Tier"),
    db: AsyncSession = Depends(get_db),
):
    """Export captured API documentation for a session in OpenAPI, Postman, Markdown, or Playwright test formats with tenant isolation."""
    user_id = _clean_header(x_user_id, "default-user")
    user_tier = _clean_header(x_user_tier, "FREE").upper()
    if format in ["postman", "markdown"] and user_tier == "FREE":
        raise HTTPException(
            status_code=403,
            detail=f"Exporting in {format.upper()} format requires STARTER tier or higher. Upgrade to unlock.",
        )

    # 1. Check memory store
    session = CRAWL_SESSIONS.get(session_id)
    if session and session.get("user_id") and session["user_id"] != user_id and user_tier != "ADMIN":
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    # 2. Check DB fallback if memory store misses
    if not session:
        try:
            repo = CrawlRepository(db)
            db_session = await repo.get_by_id(session_id)
            if db_session:
                if db_session.user_id != user_id and user_tier != "ADMIN":
                    raise HTTPException(status_code=404, detail="Crawl session not found.")
                session = {
                    "target_url": db_session.target_url,
                    "captured_endpoints": db_session.captured_endpoints or [],
                    "openapi_spec": db_session.openapi_spec,
                    "postman_collection": db_session.postman_collection,
                    "markdown_docs": db_session.markdown_docs,
                    "action_traces": db_session.action_traces or [],
                }
        except HTTPException:
            raise
        except Exception:
            pass

    if not session:
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    target_url = session.get("target_url", "https://example.com")
    sample_endpoints = session.get("captured_endpoints", [])
    action_traces = session.get("action_traces", [])

    # Record export download audit log
    await AuditLogger.log_event(
        db=db,
        user_id=x_user_id,
        action="export.download",
        target_id=session_id,
        request=http_request,
        metadata={"format": format},
    )

    if format == "openapi":
        spec = session.get("openapi_spec") or OpenAPIExporter.generate_spec(f"Session-{session_id}", target_url, sample_endpoints)
        return JSONResponse(content=spec)
    elif format == "postman":
        collection = session.get("postman_collection") or PostmanExporter.generate_collection(f"Session-{session_id}", target_url, sample_endpoints)
        return JSONResponse(content=collection)
    elif format == "markdown":
        md_text = session.get("markdown_docs") or MarkdownExporter.generate_markdown(f"Session-{session_id}", target_url, sample_endpoints)
        return Response(content=md_text, media_type="text/markdown")
    elif format == "playwright_ts":
        from app.generators.playwright_test_gen import PlaywrightTestGenerator
        ts_code = PlaywrightTestGenerator.generate_typescript_test(target_url, action_traces, session_id)
        return Response(content=ts_code, media_type="text/plain; charset=utf-8")
    else:
        from app.generators.playwright_test_gen import PlaywrightTestGenerator
        py_code = PlaywrightTestGenerator.generate_python_test(target_url, action_traces, session_id)
        return Response(content=py_code, media_type="text/plain; charset=utf-8")


@router.post("/{session_id}/fuzz")
async def fuzz_session_report(
    session_id: str,
    x_user_id: str = Header("default-user", alias="X-User-Id"),
    x_user_tier: str | None = Header(None, alias="X-User-Tier"),
    db: AsyncSession = Depends(get_db),
):
    """Run property-based API fuzzing on a session's OpenAPI spec."""
    user_tier = (x_user_tier or "FREE").upper()
    if user_tier in ("FREE", "PAYG"):
        raise HTTPException(
            status_code=403,
            detail="Automated fuzz testing is restricted to STARTER tier and above.",
        )

    session = CRAWL_SESSIONS.get(session_id)
    if session and session.get("user_id") and session["user_id"] != x_user_id and user_tier != "ADMIN":
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    if not session:
        try:
            repo = CrawlRepository(db)
            db_session = await repo.get_by_id(session_id)
            if db_session:
                if db_session.user_id != x_user_id and user_tier != "ADMIN":
                    raise HTTPException(status_code=404, detail="Crawl session not found.")
                session = {
                    "target_url": db_session.target_url,
                    "captured_endpoints": db_session.captured_endpoints or [],
                    "openapi_spec": db_session.openapi_spec,
                }
        except HTTPException:
            raise
        except Exception:
            pass

    if not session:
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    if user_tier == "FREE":
        raise HTTPException(
            status_code=403,
            detail="Property-based API fuzzing requires STARTER tier or higher.",
        )

    session = CRAWL_SESSIONS.get(session_id)
    if not session:
        try:
            repo = CrawlRepository(db)
            db_session = await repo.get_by_id(session_id)
            if db_session:
                session = {
                    "target_url": db_session.target_url,
                    "captured_endpoints": db_session.captured_endpoints or [],
                    "openapi_spec": db_session.openapi_spec,
                }
        except Exception:
            pass

    if not session:
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    target_url = session.get("target_url", "https://example.com")
    sample_endpoints = session.get("captured_endpoints", [])

    spec = session.get("openapi_spec") or OpenAPIExporter.generate_spec(f"Session-{session_id}", target_url, sample_endpoints)
    fuzz_results = APIFuzzer.fuzz_openapi_spec(spec)
    return JSONResponse(content=fuzz_results)
