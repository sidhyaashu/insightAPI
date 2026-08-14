"""API Drift Detection Service — ``app.core.drift``

``compare_snapshots(old_crawl_id, new_crawl_id, db)`` loads two sets of
``CrawlSnapshot`` rows and produces a structured ``DriftReport`` Pydantic model
classifying every change as breaking or non-breaking.

Breaking change taxonomy
------------------------
* ``endpoint_removed``       — endpoint present in base, absent in compare
* ``type_changed``           — a property's JSON Schema ``type`` changed
* ``required_field_removed`` — a field in ``required[]`` array was removed
* ``auth_added``             — ``security`` scheme added where none existed

Non-breaking change taxonomy
-----------------------------
* ``endpoint_added``         — new endpoint in compare not in base
* ``optional_field_added``   — new property not in ``required[]``
* ``description_changed``    — only ``description``/``summary`` text changed
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.snapshot_repo import SnapshotRepository

logger = logging.getLogger(__name__)


# ── Pydantic output models ────────────────────────────────────────────────────

class EndpointDiff(BaseModel):
    endpoint_key: str
    method: str
    path: str
    status_code: int


class BreakingChange(BaseModel):
    endpoint_key: str
    change_type: str
    field_path: str | None = None
    old_value: Any = None
    new_value: Any = None
    description: str


class NonBreakingChange(BaseModel):
    endpoint_key: str
    change_type: str
    field_path: str | None = None
    old_value: Any = None
    new_value: Any = None
    description: str


class DriftSummary(BaseModel):
    added_count: int
    removed_count: int
    breaking_count: int
    non_breaking_count: int
    total_endpoints_base: int
    total_endpoints_compare: int


class DriftReport(BaseModel):
    base_crawl_id: str
    compare_crawl_id: str
    generated_at: datetime
    summary: DriftSummary
    added_endpoints: list[EndpointDiff]
    removed_endpoints: list[EndpointDiff]
    breaking_changes: list[BreakingChange]
    non_breaking_changes: list[NonBreakingChange]
    has_breaking_changes: bool


# ── Schema diff helpers ───────────────────────────────────────────────────────

def _parse_key(endpoint_key: str) -> tuple[str, str, str]:
    """Split ``METHOD:path:status`` into its three components."""
    parts = endpoint_key.split(":", 2)
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return parts[0], "/", "200"


def _get_properties(schema: dict | None) -> dict[str, Any]:
    """Safely extract ``properties`` dict from an OpenAPI schema blob."""
    if not schema or not isinstance(schema, dict):
        return {}
    return schema.get("properties") or {}


def _get_required(schema: dict | None) -> set[str]:
    """Return the ``required`` field list as a set."""
    if not schema or not isinstance(schema, dict):
        return set()
    return set(schema.get("required") or [])


def _get_security(schema: dict | None) -> list:
    """Return the ``security`` list (may be on the operation or path level)."""
    if not schema or not isinstance(schema, dict):
        return []
    return schema.get("security") or []


def _diff_properties(
    endpoint_key: str,
    old_props: dict[str, Any],
    new_props: dict[str, Any],
    old_required: set[str],
    new_required: set[str],
) -> tuple[list[BreakingChange], list[NonBreakingChange]]:
    """Compare two OpenAPI ``properties`` dicts and classify changes."""
    breaking: list[BreakingChange] = []
    non_breaking: list[NonBreakingChange] = []

    old_keys = set(old_props.keys())
    new_keys = set(new_props.keys())

    # Fields removed entirely
    for field in old_keys - new_keys:
        if field in old_required:
            breaking.append(BreakingChange(
                endpoint_key=endpoint_key,
                change_type="required_field_removed",
                field_path=field,
                old_value=old_props[field],
                new_value=None,
                description=f"Required field '{field}' was removed from the response schema.",
            ))
        # optional field removed — non-breaking (consumers just stop receiving it)
        else:
            non_breaking.append(NonBreakingChange(
                endpoint_key=endpoint_key,
                change_type="optional_field_removed",
                field_path=field,
                old_value=old_props[field],
                new_value=None,
                description=f"Optional field '{field}' was removed from the response schema.",
            ))

    # Fields added
    for field in new_keys - old_keys:
        if field in new_required:
            breaking.append(BreakingChange(
                endpoint_key=endpoint_key,
                change_type="required_field_added",
                field_path=field,
                old_value=None,
                new_value=new_props[field],
                description=f"New required field '{field}' was added — clients that don't supply it will break.",
            ))
        else:
            non_breaking.append(NonBreakingChange(
                endpoint_key=endpoint_key,
                change_type="optional_field_added",
                field_path=field,
                old_value=None,
                new_value=new_props[field],
                description=f"New optional field '{field}' added — backwards compatible.",
            ))

    # Fields present in both — check type changes
    for field in old_keys & new_keys:
        old_type = (old_props[field] or {}).get("type")
        new_type = (new_props[field] or {}).get("type")
        if old_type and new_type and old_type != new_type:
            breaking.append(BreakingChange(
                endpoint_key=endpoint_key,
                change_type="type_changed",
                field_path=field,
                old_value=old_type,
                new_value=new_type,
                description=f"Field '{field}' type changed from '{old_type}' to '{new_type}' — breaking for typed consumers.",
            ))
        # Description-only change
        elif (old_props[field] or {}).get("description") != (new_props[field] or {}).get("description"):
            non_breaking.append(NonBreakingChange(
                endpoint_key=endpoint_key,
                change_type="description_changed",
                field_path=field,
                old_value=(old_props[field] or {}).get("description"),
                new_value=(new_props[field] or {}).get("description"),
                description=f"Field '{field}' description text changed — no runtime impact.",
            ))

    # Required field demoted (was required, now optional) — non-breaking
    for field in old_required - new_required:
        if field in old_keys and field in new_keys:
            non_breaking.append(NonBreakingChange(
                endpoint_key=endpoint_key,
                change_type="field_made_optional",
                field_path=field,
                description=f"Field '{field}' changed from required to optional — backwards compatible.",
            ))

    return breaking, non_breaking


def _diff_endpoint_schemas(
    endpoint_key: str,
    old_schema: dict | None,
    new_schema: dict | None,
) -> tuple[list[BreakingChange], list[NonBreakingChange]]:
    """Run all schema-level diff checks for a single endpoint."""
    breaking: list[BreakingChange] = []
    non_breaking: list[NonBreakingChange] = []

    old_props = _get_properties(old_schema)
    new_props = _get_properties(new_schema)
    old_required = _get_required(old_schema)
    new_required = _get_required(new_schema)

    prop_breaking, prop_non_breaking = _diff_properties(
        endpoint_key, old_props, new_props, old_required, new_required
    )
    breaking.extend(prop_breaking)
    non_breaking.extend(prop_non_breaking)

    # Security scheme added where none existed before — breaking
    old_security = _get_security(old_schema)
    new_security = _get_security(new_schema)
    if not old_security and new_security:
        breaking.append(BreakingChange(
            endpoint_key=endpoint_key,
            change_type="auth_added",
            old_value=None,
            new_value=new_security,
            description="Authentication requirement added to previously open endpoint — breaking for unauthenticated clients.",
        ))
    elif old_security and not new_security:
        non_breaking.append(NonBreakingChange(
            endpoint_key=endpoint_key,
            change_type="auth_removed",
            old_value=old_security,
            new_value=None,
            description="Authentication requirement removed — endpoint now publicly accessible.",
        ))

    return breaking, non_breaking


def _make_endpoint_diff(endpoint_key: str) -> EndpointDiff:
    method, path, status = _parse_key(endpoint_key)
    return EndpointDiff(
        endpoint_key=endpoint_key,
        method=method,
        path=path,
        status_code=int(status) if status.isdigit() else 200,
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def compare_snapshots(
    base_crawl_id: str,
    compare_crawl_id: str,
    db: AsyncSession,
) -> DriftReport:
    """Load two crawl snapshot sets and return a structured :class:`DriftReport`.

    Args:
        base_crawl_id:    The reference crawl (e.g. last main-branch crawl).
        compare_crawl_id: The candidate crawl (e.g. new PR staging crawl).
        db:               Async SQLAlchemy session.

    Returns:
        A fully populated :class:`DriftReport` Pydantic model.
    """
    repo = SnapshotRepository(db)

    base_rows = await repo.get_snapshots_for_crawl(base_crawl_id)
    compare_rows = await repo.get_snapshots_for_crawl(compare_crawl_id)

    # Index by endpoint_key for O(1) lookup
    base_map: dict[str, dict | None] = {r.endpoint_key: r.schema_json for r in base_rows}
    compare_map: dict[str, dict | None] = {r.endpoint_key: r.schema_json for r in compare_rows}

    base_keys = set(base_map.keys())
    compare_keys = set(compare_map.keys())

    # ── Added / removed endpoints ────────────────────────────────────────────
    added_keys = compare_keys - base_keys
    removed_keys = base_keys - compare_keys
    shared_keys = base_keys & compare_keys

    added_endpoints = [_make_endpoint_diff(k) for k in sorted(added_keys)]
    removed_endpoints = [_make_endpoint_diff(k) for k in sorted(removed_keys)]

    all_breaking: list[BreakingChange] = []
    all_non_breaking: list[NonBreakingChange] = []

    # Removed endpoints are always breaking
    for key in removed_keys:
        all_breaking.append(BreakingChange(
            endpoint_key=key,
            change_type="endpoint_removed",
            description=f"Endpoint '{key}' was present in the base crawl but is missing in the new crawl.",
        ))

    # Added endpoints are non-breaking
    for key in added_keys:
        all_non_breaking.append(NonBreakingChange(
            endpoint_key=key,
            change_type="endpoint_added",
            description=f"New endpoint '{key}' discovered in the compare crawl.",
        ))

    # Shared endpoints — diff schemas
    for key in sorted(shared_keys):
        b, nb = _diff_endpoint_schemas(key, base_map[key], compare_map[key])
        all_breaking.extend(b)
        all_non_breaking.extend(nb)

    has_breaking = len(all_breaking) > 0

    return DriftReport(
        base_crawl_id=base_crawl_id,
        compare_crawl_id=compare_crawl_id,
        generated_at=datetime.now(timezone.utc),
        summary=DriftSummary(
            added_count=len(added_endpoints),
            removed_count=len(removed_endpoints),
            breaking_count=len(all_breaking),
            non_breaking_count=len(all_non_breaking),
            total_endpoints_base=len(base_keys),
            total_endpoints_compare=len(compare_keys),
        ),
        added_endpoints=added_endpoints,
        removed_endpoints=removed_endpoints,
        breaking_changes=all_breaking,
        non_breaking_changes=all_non_breaking,
        has_breaking_changes=has_breaking,
    )
