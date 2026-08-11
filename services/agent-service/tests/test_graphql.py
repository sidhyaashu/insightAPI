import json
import pytest
from app.services.openapi_exporter import OpenAPIExporter
from app.services.postman_exporter import PostmanExporter
from app.services.markdown_exporter import MarkdownExporter


def test_graphql_openapi_export_disambiguation():
    endpoints = [
        {
            "method": "POST",
            "url": "https://example.com/graphql",
            "template_route": "https://example.com/graphql (GetUserProfile)",
            "status": 200,
            "resource_type": "fetch",
            "request_headers": {},
            "request_payload": {"operationName": "GetUserProfile", "query": "query GetUserProfile { user { id name } }"},
            "response_headers": {},
            "response_body": {"data": {"user": {"id": 1, "name": "Alice"}}},
            "graphql_operation_name": "GetUserProfile"
        },
        {
            "method": "POST",
            "url": "https://example.com/graphql",
            "template_route": "https://example.com/graphql (GetOrderHistory)",
            "status": 200,
            "resource_type": "fetch",
            "request_headers": {},
            "request_payload": {"operationName": "GetOrderHistory", "query": "query GetOrderHistory { orders { id } }"},
            "response_headers": {},
            "response_body": {"data": {"orders": [{"id": 99}]}},
            "graphql_operation_name": "GetOrderHistory"
        }
    ]

    spec = OpenAPIExporter.generate_spec(
        title="GraphQL Test Suite",
        target_url="https://example.com",
        captured_endpoints=endpoints
    )

    paths = spec["paths"]
    assert "/graphql/GetUserProfile" in paths
    assert "/graphql/GetOrderHistory" in paths

    assert paths["/graphql/GetUserProfile"]["post"]["operationId"] == "graphql_GetUserProfile"
    assert paths["/graphql/GetOrderHistory"]["post"]["operationId"] == "graphql_GetOrderHistory"
    assert "GetUserProfile" in paths["/graphql/GetUserProfile"]["post"]["summary"]


def test_graphql_postman_and_markdown_exporters():
    endpoints = [
        {
            "method": "POST",
            "url": "https://example.com/graphql",
            "template_route": "https://example.com/graphql (BatchOperations)",
            "status": 200,
            "resource_type": "fetch",
            "request_headers": {},
            "request_payload": [{"operationName": "GetUsers"}, {"operationName": "GetMetrics"}],
            "response_headers": {},
            "response_body": [{"data": {}}, {"data": {}}],
            "graphql_operation_name": "GetUsers+GetMetrics"
        }
    ]

    collection = PostmanExporter.generate_collection("GraphQL Test", "https://example.com", endpoints)
    item_name = collection["item"][0]["name"]
    assert "GetUsers+GetMetrics" in item_name

    md_docs = MarkdownExporter.generate_markdown("GraphQL Test", "https://example.com", endpoints)
    assert "GraphQL" in md_docs
