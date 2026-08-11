import json
import pytest
from app import AgentEngine, CrawlResult, OpenAPIExporter, PostmanExporter, MarkdownExporter


def test_openapi_exporter():
    endpoints = [
        {"method": "GET", "template_route": "/api/products", "status": 200, "schema": {"id": "int"}}
    ]
    json_str = OpenAPIExporter.export_to_json("Test App", "https://example.com", endpoints)
    data = json.loads(json_str)

    assert data["openapi"] == "3.0.3"
    assert "/api/products" in data["paths"]
    assert "get" in data["paths"]["/api/products"]


def test_postman_exporter():
    endpoints = [
        {"method": "POST", "template_route": "/api/users", "status": 201, "url": "https://example.com/api/users"}
    ]
    json_str = PostmanExporter.export_to_json("Test App", "https://example.com", endpoints)
    data = json.loads(json_str)

    assert "schema" in data["info"]
    assert len(data["item"]) == 1
    assert data["item"][0]["request"]["method"] == "POST"


def test_markdown_exporter():
    endpoints = [
        {"method": "GET", "template_route": "/api/health", "status": 200, "url": "https://example.com/api/health"}
    ]
    md_str = MarkdownExporter.generate_markdown("Test App", "https://example.com", endpoints)

    assert "# API Documentation" in md_str
    assert "curl -X GET" in md_str


def test_sdk_result_export():
    endpoints = [
        {"method": "GET", "template_route": "/api/v1/status", "status": 200}
    ]
    res = CrawlResult("https://example.com", endpoints)
    assert "openapi" in res.to_openapi()
    assert "schema" in res.to_postman()
    assert "# API Documentation" in res.to_markdown()
