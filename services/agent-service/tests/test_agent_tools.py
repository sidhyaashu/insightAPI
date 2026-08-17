"""Tests for in-chat agent tools."""
import pytest
from app.tools.curl_executor import parse_curl_command
from app.tools.schema_inferencer import infer_openapi_schema


def test_parse_curl_command():
    raw_curl = 'curl -X POST https://api.example.com/v1/users -H "Content-Type: application/json" -H "Authorization: Bearer token123" -d \'{"name": "Alice", "role": "admin"}\''
    parsed = parse_curl_command(raw_curl)
    assert parsed["url"] == "https://api.example.com/v1/users"
    assert parsed["method"] == "POST"
    assert parsed["headers"]["Content-Type"] == "application/json"
    assert parsed["headers"]["Authorization"] == "Bearer token123"
    assert '"name": "Alice"' in parsed["body"]


def test_infer_openapi_schema_object():
    payload = {
        "user_id": 101,
        "username": "octocat",
        "is_active": True,
        "score": 98.6,
        "email": "user@example.com",
        "tags": ["developer", "admin"],
    }
    res = infer_openapi_schema(payload)
    assert res.status == "success"
    schema = res.data["schema"]
    assert schema["type"] == "object"
    assert schema["properties"]["user_id"]["type"] == "integer"
    assert schema["properties"]["username"]["type"] == "string"
    assert schema["properties"]["email"]["format"] == "email"
    assert schema["properties"]["tags"]["type"] == "array"
