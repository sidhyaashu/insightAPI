"""Crawl Review & Approval Gate — REST endpoints

GET  /api/v1/crawls/{crawl_id}/endpoints
     — List all captured endpoints sorted by confidence ASC.
       Reads from crawl_snapshots; overlays any reviewed_endpoints overrides.

PATCH /api/v1/crawls/{crawl_id}/endpoints/{endpoint_key}
     Body: { schema?: dict, is_excluded?: bool }
     — Merge-patch this endpoint's reviewed override into CrawlSession.reviewed_endpoints.

POST /api/v1/crawls/{crawl_id}/approve
     Body: { confidence_threshold?: float }
     — Merges reviewed overrides over raw snapshots, filters excluded, runs exporters,
       transitions CrawlSession to 'completed'.

All endpoints require x-user-id == session.user_id (ownership guard).
No tier gate — review is available on all plans.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional
from urllib.parse import urlparse
import re

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.crawl_repo import CrawlRepository
from app.repositories.snapshot_repo import SnapshotRepository
from app.services.openapi_exporter import OpenAPIExporter
from app.services.postman_exporter import PostmanExporter
from app.services.markdown_exporter import MarkdownExporter

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Response / Request schemas ────────────────────────────────────────────────

class EndpointReviewItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    endpoint_key: str
    method: str
    path: str
    status_code: int
    schema_data: dict | None = Field(default=None, alias="schema_json", serialization_alias="schema_json")
    confidence: float
    example_count: int
    is_excluded: bool
    reviewed_schema: dict | None = None
    has_review: bool


class ReviewPatchBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_data: Optional[dict] = Field(default=None, alias="schema")
    is_excluded: Optional[bool] = None


class ApproveBody(BaseModel):
    confidence_threshold: Optional[float] = None


class ApproveResponse(BaseModel):
    session_id: str
    captured_count: int
    excluded_count: int
    has_excluded: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_endpoint_key(key: str) -> tuple[str, str, int]:
    """Split ``METHOD:path:status_code`` → (method, path, status_code)."""
    parts = key.split(":", 2)
    if len(parts) == 3:
        method, path, status = parts
        return method, path, int(status) if status.isdigit() else 200
    return parts[0], "/", 200


def _snapshot_to_review_item(
    snapshot,
    reviewed_overrides: dict[str, Any],
) -> EndpointReviewItem:
    """Build a review list item from a CrawlSnapshot row + any existing override."""
    key = snapshot.endpoint_key
    override = reviewed_overrides.get(key, {})
    method, path, status_code = _parse_endpoint_key(key)

    schema = snapshot.schema_json or {}
    confidence: float = schema.get("x-confidence", schema.get("confidence", 0.5))
    example_count: int = schema.get("x-example-count", schema.get("example_count", 1))

    # The snapshot schema_json stores the full endpoint dict from AnalyzerNode
    # (which includes confidence, example_count as top-level keys alongside schema)
    inner_schema = schema.get("schema") or schema

    return EndpointReviewItem(
        endpoint_key=key,
        method=method,
        path=path,
        status_code=status_code,
        schema_json=inner_schema,
        confidence=confidence,
        example_count=example_count,
        is_excluded=override.get("is_excluded", False),
        reviewed_schema=override.get("reviewed_schema"),
        has_review=bool(override),
    )


def _build_export_endpoint_list(
    snapshots: list,
    reviewed_overrides: dict[str, Any],
    confidence_threshold: float | None,
) -> tuple[list[dict], int]:
    """Merge reviewed overrides over raw snapshots, apply exclusions.

    For each snapshot:
    - If override has ``is_excluded=True``: skip.
    - If override has ``reviewed_schema``: use it in place of raw schema.
    - Otherwise: use raw snapshot schema as-is.

    Returns (export_list, excluded_count).
    """
    export_list: list[dict] = []
    excluded = 0

    for snap in snapshots:
        key = snap.endpoint_key
        override = reviewed_overrides.get(key, {})
        schema = snap.schema_json or {}

        # Auto-exclude low-confidence items below threshold (if threshold set and no manual override)
        if confidence_threshold is not None and not override:
            raw_conf = schema.get("x-confidence", schema.get("confidence", 0.5))
            if raw_conf < confidence_threshold:
                excluded += 1
                continue

        if override.get("is_excluded", False):
            excluded += 1
            continue

        # Build the endpoint dict the exporters expect
        ep = dict(schema)  # copy raw
        if "reviewed_schema" in override and override["reviewed_schema"]:
            # Splice reviewed schema into the endpoint record
            ep["schema"] = override["reviewed_schema"]

        # Ensure endpoint_key fields are accessible
        method, path, status_code = _parse_endpoint_key(key)
        ep.setdefault("method", method)
        ep.setdefault("template_route", path)
        ep.setdefault("status", status_code)

        export_list.append(ep)

    return export_list, excluded


async def _get_owned_session(crawl_id: str, user_id: str, db: AsyncSession):
    """Load a CrawlSession and verify ownership. Raises 404/403 on failure."""
    repo = CrawlRepository(db)
    session = await repo.get_by_id(crawl_id)
    if not session:
        raise HTTPException(status_code=404, detail="Crawl session not found.")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this crawl.")
    return session, repo


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/{crawl_id}/endpoints", response_model=list[EndpointReviewItem])
async def list_endpoints_for_review(
    crawl_id: str,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """List all captured endpoints for review, sorted by confidence ascending.

    Reads raw schemas from ``crawl_snapshots`` and overlays any
    ``reviewed_endpoints`` overrides already stored on the crawl session.
    Endpoints are returned lowest-confidence-first so reviewers see the most
    uncertain schemas at the top.
    """
    session, _ = await _get_owned_session(crawl_id, x_user_id, db)

    snap_repo = SnapshotRepository(db)
    snapshots = await snap_repo.get_snapshots_for_crawl(crawl_id)

    if not snapshots:
        raise HTTPException(
            status_code=404,
            detail=(
                "No endpoint snapshots found for this crawl. "
                "Ensure the crawl completed successfully before reviewing."
            ),
        )

    reviewed_overrides: dict[str, Any] = session.reviewed_endpoints or {}

    items = [_snapshot_to_review_item(snap, reviewed_overrides) for snap in snapshots]
    # Sort by confidence ascending — lowest confidence first
    items.sort(key=lambda x: x.confidence)
    return items


@router.patch("/{crawl_id}/endpoints/{endpoint_key:path}", response_model=EndpointReviewItem)
async def patch_endpoint_review(
    crawl_id: str,
    endpoint_key: str,
    body: ReviewPatchBody,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Merge-patch a single endpoint's reviewed schema and/or exclusion flag.

    Only the fields present in the request body are updated.  Calling this
    endpoint multiple times is idempotent — each call overwrites only the
    supplied keys for this endpoint_key within the ``reviewed_endpoints`` blob.
    """
    session, repo = await _get_owned_session(crawl_id, x_user_id, db)

    if session.status not in ("pending_review", "completed"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot edit endpoints while crawl is in '{session.status}' state.",
        )

    # Validate JSON schema if provided
    if body.schema_data is not None:
        if not isinstance(body.schema_data, dict):
            raise HTTPException(status_code=400, detail="'schema' must be a JSON object.")

    # Load and update the reviewed_endpoints blob
    reviewed: dict[str, Any] = dict(session.reviewed_endpoints or {})
    existing = reviewed.get(endpoint_key, {})

    if body.schema_data is not None:
        existing["reviewed_schema"] = body.schema_data
    if body.is_excluded is not None:
        existing["is_excluded"] = body.is_excluded

    reviewed[endpoint_key] = existing
    await repo.save_reviewed_endpoints(crawl_id, reviewed)

    # Return the updated item
    snap_repo = SnapshotRepository(db)
    snapshots = await snap_repo.get_snapshots_for_crawl(crawl_id)
    target = next((s for s in snapshots if s.endpoint_key == endpoint_key), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Endpoint '{endpoint_key}' not found in snapshots.")

    return _snapshot_to_review_item(target, reviewed)


@router.post("/{crawl_id}/approve", response_model=ApproveResponse)
async def approve_crawl(
    crawl_id: str,
    body: ApproveBody,
    x_user_id: str = Header(..., alias="x-user-id"),
    db: AsyncSession = Depends(get_db),
):
    """Approve and export the reviewed crawl.

    This endpoint:
    1. Loads all raw endpoint snapshots.
    2. Merges ``reviewed_endpoints`` overrides (schema corrections, exclusions).
    3. Optionally auto-excludes endpoints below ``confidence_threshold``.
    4. Runs all three exporters (OpenAPI / Postman / Markdown) on the final list.
    5. Persists the exports and transitions status to ``completed``.
    """
    session, repo = await _get_owned_session(crawl_id, x_user_id, db)

    if session.status not in ("pending_review",):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Crawl is in '{session.status}' state. "
                "Only crawls in 'pending_review' can be approved. "
                "If the crawl is already 'completed', re-download the existing export."
            ),
        )

    snap_repo = SnapshotRepository(db)
    snapshots = await snap_repo.get_snapshots_for_crawl(crawl_id)

    if not snapshots:
        raise HTTPException(
            status_code=404,
            detail="No endpoint snapshots found for this crawl. Cannot approve without endpoint data.",
        )

    reviewed_overrides: dict[str, Any] = session.reviewed_endpoints or {}
    export_list, excluded_count = _build_export_endpoint_list(
        snapshots,
        reviewed_overrides,
        body.confidence_threshold,
    )

    if not export_list:
        raise HTTPException(
            status_code=400,
            detail=(
                "All endpoints were excluded from export. "
                "Un-exclude at least one endpoint before approving."
            ),
        )

    # Run exporters on the reviewed list
    try:
        title = f"Reviewed crawl — {session.target_url}"
        openapi_spec = json.loads(
            OpenAPIExporter.export_to_json(title, session.target_url, export_list)
        )
        postman_col = json.loads(
            PostmanExporter.export_to_json(title, session.target_url, export_list)
        )
        markdown_docs = MarkdownExporter.generate_markdown(title, session.target_url, export_list)
    except Exception as exc:
        logger.error(f"Exporter failed during approval for crawl {crawl_id}: {exc}")
        raise HTTPException(status_code=500, detail=f"Export generation failed: {exc}")

    # Persist and transition to completed
    await repo.approve_crawl(
        session_id=crawl_id,
        openapi_spec=openapi_spec,
        postman_collection=postman_col,
        markdown_docs=markdown_docs,
        captured_count=len(export_list),
    )

    logger.info(
        f"Crawl {crawl_id} approved by {x_user_id}: "
        f"{len(export_list)} endpoints exported, {excluded_count} excluded."
    )

    return ApproveResponse(
        session_id=crawl_id,
        captured_count=len(export_list),
        excluded_count=excluded_count,
        has_excluded=excluded_count > 0,
    )
