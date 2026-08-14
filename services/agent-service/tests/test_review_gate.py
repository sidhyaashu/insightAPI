"""Unit tests for the Crawl Review & Approval Gate (app.api.v1.endpoints.review)."""

import json
from unittest.mock import MagicMock
from app.api.v1.endpoints.review import _build_export_endpoint_list, _parse_endpoint_key
from app.services.openapi_exporter import OpenAPIExporter


class MockSnapshot:
    def __init__(self, endpoint_key: str, schema_json: dict):
        self.endpoint_key = endpoint_key
        self.schema_json = schema_json


def test_parse_endpoint_key():
    method, path, status = _parse_endpoint_key("GET:/api/v1/users:200")
    assert method == "GET"
    assert path == "/api/v1/users"
    assert status == 200

    method, path, status = _parse_endpoint_key("POST:/api/v1/orders/create:201")
    assert method == "POST"
    assert path == "/api/v1/orders/create"
    assert status == 201


def test_review_gate_schema_correction_and_exclusion():
    # 1. Setup raw snapshots with inferred schemas and confidence scores
    raw_user_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},  # Inferred as string by analyzer
            "name": {"type": "string"},
        },
        "required": ["id", "name"],
    }

    raw_health_schema = {
        "type": "object",
        "properties": {"status": {"type": "string"}},
    }

    raw_debug_schema = {
        "type": "object",
        "properties": {"temp_debug_dump": {"type": "string"}},
    }

    snapshots = [
        MockSnapshot(
            endpoint_key="GET:/api/v1/users:200",
            schema_json={
                "method": "GET",
                "template_route": "/api/v1/users",
                "status": 200,
                "confidence": 0.45,  # Low confidence
                "schema": raw_user_schema,
            },
        ),
        MockSnapshot(
            endpoint_key="GET:/health:200",
            schema_json={
                "method": "GET",
                "template_route": "/health",
                "status": 200,
                "confidence": 0.95,
                "schema": raw_health_schema,
            },
        ),
        MockSnapshot(
            endpoint_key="GET:/internal/debug:200",
            schema_json={
                "method": "GET",
                "template_route": "/internal/debug",
                "status": 200,
                "confidence": 0.30,
                "schema": raw_debug_schema,
            },
        ),
    ]

    # 2. User reviews and applies overrides:
    # - Corrects /api/v1/users "id" field type from "string" to "integer"
    # - Marks /internal/debug as excluded
    reviewed_user_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},  # Corrected to integer!
            "name": {"type": "string"},
            "is_active": {"type": "boolean"},  # Added optional field!
        },
        "required": ["id", "name"],
    }

    reviewed_overrides = {
        "GET:/api/v1/users:200": {
            "reviewed_schema": reviewed_user_schema,
            "is_excluded": False,
        },
        "GET:/internal/debug:200": {
            "is_excluded": True,  # Excluded!
        },
    }

    # 3. Build export endpoint list
    export_list, excluded_count = _build_export_endpoint_list(
        snapshots=snapshots,
        reviewed_overrides=reviewed_overrides,
        confidence_threshold=None,
    )

    assert excluded_count == 1
    assert len(export_list) == 2

    # 4. Verify the exporter output reflects the reviewed schema corrections
    spec_json = OpenAPIExporter.export_to_json("Reviewed API", "https://api.example.com", export_list)
    spec = json.loads(spec_json)

    paths = spec["paths"]

    # Excluded endpoint must NOT be present
    assert "/internal/debug" not in paths

    # Included endpoints must be present
    assert "/health" in paths
    assert "/api/v1/users" in paths

    # The corrected schema (type: integer) must appear in the final OpenAPI output
    user_response_schema = paths["api/v1/users" if "api/v1/users" in paths else "/api/v1/users"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert user_response_schema["properties"]["id"]["type"] == "integer"
    assert user_response_schema["properties"]["is_active"]["type"] == "boolean"


def test_review_gate_confidence_threshold_auto_exclude():
    snapshots = [
        MockSnapshot(
            endpoint_key="GET:/api/v1/high:200",
            schema_json={
                "method": "GET",
                "template_route": "/api/v1/high",
                "status": 200,
                "confidence": 0.85,
                "schema": {"type": "object"},
            },
        ),
        MockSnapshot(
            endpoint_key="GET:/api/v1/low:200",
            schema_json={
                "method": "GET",
                "template_route": "/api/v1/low",
                "status": 200,
                "confidence": 0.40,
                "schema": {"type": "object"},
            },
        ),
    ]

    # No manual overrides, but threshold set to 0.70
    export_list, excluded_count = _build_export_endpoint_list(
        snapshots=snapshots,
        reviewed_overrides={},
        confidence_threshold=0.70,
    )

    assert excluded_count == 1
    assert len(export_list) == 1
    assert export_list[0]["template_route"] == "/api/v1/high"
