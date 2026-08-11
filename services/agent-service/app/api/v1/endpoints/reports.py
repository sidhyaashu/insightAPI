from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import Response, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.crawls import CRAWL_SESSIONS
from app.core.database import get_db
from app.repositories.crawl_repo import CrawlRepository
from app.services.openapi_exporter import OpenAPIExporter
from app.services.postman_exporter import PostmanExporter
from app.services.markdown_exporter import MarkdownExporter

router = APIRouter()


@router.get("/{session_id}")
async def get_report_by_id(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full generated documentation (OpenAPI, Postman, Markdown) for a crawl session."""
    # 1. Try DB
    try:
        repo = CrawlRepository(db)
        db_session = await repo.get_by_id(session_id)
        if db_session:
            return {
                "session_id": db_session.id,
                "openapi_spec": db_session.openapi_spec,
                "postman_collection": db_session.postman_collection,
                "markdown_docs": db_session.markdown_docs,
            }
    except Exception:
        pass

    # 2. Try memory store
    if session_id in CRAWL_SESSIONS:
        session = CRAWL_SESSIONS[session_id]
        target_url = session.get("target_url", "https://example.com")
        sample_endpoints = session.get("captured_endpoints", [])
        return {
            "session_id": session_id,
            "openapi_spec": session.get("openapi_spec") or OpenAPIExporter.generate_spec(f"Session-{session_id}", target_url, sample_endpoints),
            "postman_collection": session.get("postman_collection") or PostmanExporter.generate_collection(f"Session-{session_id}", target_url, sample_endpoints),
            "markdown_docs": session.get("markdown_docs") or MarkdownExporter.generate_markdown(f"Session-{session_id}", target_url, sample_endpoints),
        }

    raise HTTPException(status_code=404, detail="Crawl session report not found.")


@router.get("/{session_id}/export")
async def export_report(
    session_id: str,
    format: str = Query("openapi", enum=["openapi", "postman", "markdown"])
):
    """Export captured API documentation for a session in OpenAPI, Postman, or Markdown format."""
    if session_id not in CRAWL_SESSIONS:
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    session = CRAWL_SESSIONS[session_id]
    target_url = session.get("target_url", "https://example.com")
    sample_endpoints = session.get("captured_endpoints", [])

    if format == "openapi":
        spec = OpenAPIExporter.generate_spec(f"Session-{session_id}", target_url, sample_endpoints)
        return JSONResponse(content=spec)
    elif format == "postman":
        collection = PostmanExporter.generate_collection(f"Session-{session_id}", target_url, sample_endpoints)
        return JSONResponse(content=collection)
    else:
        md_text = MarkdownExporter.generate_markdown(f"Session-{session_id}", target_url, sample_endpoints)
        return Response(content=md_text, media_type="text/markdown")


@router.post("/{session_id}/fuzz")
async def fuzz_session_report(session_id: str):
    """Run property-based API fuzzing on a session's OpenAPI spec."""
    if session_id not in CRAWL_SESSIONS:
        raise HTTPException(status_code=404, detail="Crawl session not found.")

    session = CRAWL_SESSIONS[session_id]
    target_url = session.get("target_url", "https://example.com")
    sample_endpoints = session.get("captured_endpoints", [])

    spec = OpenAPIExporter.generate_spec(f"Session-{session_id}", target_url, sample_endpoints)
    from app.services.fuzzer import APIFuzzer
    fuzz_results = APIFuzzer.fuzz_openapi_spec(spec)
    return JSONResponse(content=fuzz_results)
