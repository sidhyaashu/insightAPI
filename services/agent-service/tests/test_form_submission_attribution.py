"""
Unit and integration tests for Form Submission Attribution & JS Fetch/XHR Correlation.
Tests native HTML forms, JS-driven React/Vue controlled forms, multi-request submissions,
AnalyzerNode requestBody schema inference, and OpenAPI/Markdown export extensions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.engine.network.listener import CapturedEndpoint, NetworkObserver
from app.agents.nodes.executor import ExecutorNode
from app.agents.nodes.analyzer import AnalyzerNode
from app.services.openapi_exporter import OpenAPIExporter
from app.services.markdown_exporter import MarkdownExporter


@pytest.mark.asyncio
async def test_native_form_submit_attribution():
    """Verify native HTML <form action="/api/v1/login" method="POST"> submit attaches triggered_by metadata."""
    mock_page = AsyncMock()
    mock_page.url = "https://example.com/login"

    mock_observer = MagicMock()
    mock_observer.captured_endpoints = []
    
    ep = CapturedEndpoint(
        method="POST",
        url="https://example.com/api/v1/login",
        template_route="/api/v1/login",
        status=200,
        resource_type="fetch",
        request_headers={},
        request_payload={"username": "testuser", "password": "securepassword"},
        response_headers={},
        response_body={"token": "jwt-123"},
    )

    async def _on_click(*args, **kwargs):
        mock_observer.captured_endpoints.append(ep)

    mock_page.click = AsyncMock(side_effect=_on_click)
    mock_page.mouse = AsyncMock()
    mock_page.mouse.down = AsyncMock(side_effect=_on_click)
    mock_page.mouse.up = AsyncMock()
    mock_page.mouse.move = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_locator = AsyncMock()
    mock_locator.is_visible = AsyncMock(return_value=False)
    mock_locator.bounding_box = AsyncMock(return_value={"x": 100, "y": 100, "width": 80, "height": 30})
    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    next_action = {
        "tag": "button",
        "type": "submit",
        "selector": "form#login-form button[type='submit']",
        "action": "click",
        "is_form_submit": True,
        "form_context": "Sign in to your account",
        "form_action": "/api/v1/login",
        "form_method": "POST",
        "form_fields": [
            {"name": "username", "type": "text"},
            {"name": "password", "type": "password"},
        ],
    }

    state = {
        "page_ref": mock_page,
        "current_url": "https://example.com/login",
        "next_action": next_action,
        "network_observer": mock_observer,
        "captured_endpoints": [],
        "action_traces": [],
    }

    with patch("app.engine.browser.dom_distiller.DOMDistiller.detect_login_wall", new=AsyncMock(return_value=False)), \
         patch("app.engine.browser.stabilizer.PageNetworkStabilizer.wait_until_stable", new=AsyncMock()), \
         patch("app.engine.browser.dom_distiller.DOMDistiller.extract_interactive_snapshot", new=AsyncMock(return_value=[])):

        res_state = await ExecutorNode.process(state)

        captured = res_state.get("captured_endpoints", [])
        assert len(captured) == 1
        ep_dict = captured[0]

        assert "triggered_by" in ep_dict
        trig = ep_dict["triggered_by"]
        assert trig["action_type"] == "form_submit"
        assert trig["selector"] == "form#login-form button[type='submit']"
        assert trig["form_context"] == "Sign in to your account"
        assert trig["form_action"] == "/api/v1/login"
        assert trig["field_names"] == ["username", "password"]


@pytest.mark.asyncio
async def test_js_driven_form_submit_attribution():
    """Verify JS-driven React/Vue form (no native action attribute) correlates to resulting fetch/XHR API call."""
    mock_page = AsyncMock()
    mock_page.url = "https://app.saas.io/signup"

    mock_observer = MagicMock()
    mock_observer.captured_endpoints = []

    # REST call captured via window.fetch inside React onClick handler
    ep = CapturedEndpoint(
        method="POST",
        url="https://app.saas.io/api/v2/users/register",
        template_route="/api/v2/users/register",
        status=201,
        resource_type="fetch",
        request_headers={},
        request_payload={"email": "dev@test.io", "tier": "PRO"},
        response_headers={},
        response_body={"userId": "usr_99"},
    )

    async def _on_click(*args, **kwargs):
        mock_observer.captured_endpoints.append(ep)

    mock_page.click = AsyncMock(side_effect=_on_click)
    mock_page.mouse = AsyncMock()
    mock_page.mouse.down = AsyncMock(side_effect=_on_click)
    mock_page.mouse.up = AsyncMock()
    mock_page.mouse.move = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_locator = AsyncMock()
    mock_locator.is_visible = AsyncMock(return_value=False)
    mock_locator.bounding_box = AsyncMock(return_value={"x": 100, "y": 100, "width": 80, "height": 30})
    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    next_action = {
        "tag": "button",
        "selector": "div.react-modal form div.btn-container button#submit-btn",
        "action": "click",
        "is_form_submit": True,
        "form_context": "Create your organization account",
        "form_action": "",  # Empty action attr in React SPA
        "form_method": "POST",
        "form_fields": [
            {"name": "email", "type": "email"},
            {"name": "tier", "type": "text"},
        ],
    }

    state = {
        "page_ref": mock_page,
        "current_url": "https://app.saas.io/signup",
        "next_action": next_action,
        "network_observer": mock_observer,
        "captured_endpoints": [],
        "action_traces": [],
    }

    with patch("app.engine.browser.dom_distiller.DOMDistiller.detect_login_wall", new=AsyncMock(return_value=False)), \
         patch("app.engine.browser.stabilizer.PageNetworkStabilizer.wait_until_stable", new=AsyncMock()), \
         patch("app.engine.browser.dom_distiller.DOMDistiller.extract_interactive_snapshot", new=AsyncMock(return_value=[])):

        res_state = await ExecutorNode.process(state)

        captured = res_state.get("captured_endpoints", [])
        assert len(captured) == 1
        ep_dict = captured[0]

        assert "triggered_by" in ep_dict
        trig = ep_dict["triggered_by"]
        assert trig["action_type"] == "form_submit"
        assert trig["selector"] == "div.react-modal form div.btn-container button#submit-btn"
        assert trig["form_context"] == "Create your organization account"
        assert trig["field_names"] == ["email", "tier"]


@pytest.mark.asyncio
async def test_multi_request_submit_primary_and_related_calls():
    """Verify multi-request submission separates primary mutation endpoint from preflight/validation calls."""
    mock_page = AsyncMock()
    mock_page.url = "https://app.saas.io/checkout"

    mock_observer = MagicMock()
    mock_observer.captured_endpoints = []

    # 1. Validation GET call
    ep_val = CapturedEndpoint(
        method="GET",
        url="https://app.saas.io/api/validate-coupon?code=DISCOUNT",
        template_route="/api/validate-coupon",
        status=200,
        resource_type="fetch",
        request_headers={},
        request_payload=None,
        response_headers={},
        response_body={"valid": True},
    )
    # 2. Primary POST submit call
    ep_submit = CapturedEndpoint(
        method="POST",
        url="https://app.saas.io/api/checkout/orders",
        template_route="/api/checkout/orders",
        status=200,
        resource_type="fetch",
        request_headers={},
        request_payload={"plan": "ENTERPRISE"},
        response_headers={},
        response_body={"order_id": "ord_555"},
    )

    async def _on_click(*args, **kwargs):
        mock_observer.captured_endpoints.extend([ep_val, ep_submit])

    mock_page.click = AsyncMock(side_effect=_on_click)
    mock_page.mouse = AsyncMock()
    mock_page.mouse.down = AsyncMock(side_effect=_on_click)
    mock_page.mouse.up = AsyncMock()
    mock_page.mouse.move = AsyncMock()
    mock_locator = AsyncMock()
    mock_locator.is_visible = AsyncMock(return_value=False)
    mock_locator.bounding_box = AsyncMock(return_value={"x": 100, "y": 100, "width": 80, "height": 30})
    mock_page.locator = MagicMock(return_value=MagicMock(first=mock_locator))

    next_action = {
        "tag": "button",
        "selector": "button#complete-order",
        "action": "click",
        "is_form_submit": True,
        "form_context": "Order Checkout Form",
        "form_fields": [{"name": "plan", "type": "text"}],
    }

    state = {
        "page_ref": mock_page,
        "current_url": "https://app.saas.io/checkout",
        "next_action": next_action,
        "network_observer": mock_observer,
        "captured_endpoints": [],
        "action_traces": [],
    }

    with patch("app.engine.browser.dom_distiller.DOMDistiller.detect_login_wall", new=AsyncMock(return_value=False)), \
         patch("app.engine.browser.stabilizer.PageNetworkStabilizer.wait_until_stable", new=AsyncMock()), \
         patch("app.engine.browser.dom_distiller.DOMDistiller.extract_interactive_snapshot", new=AsyncMock(return_value=[])):

        res_state = await ExecutorNode.process(state)

        captured = res_state.get("captured_endpoints", [])
        assert len(captured) == 2

        # Primary submit call (POST) has triggered_by and related_calls
        primary_dict = next(e for e in captured if e["method"] == "POST")
        assert "triggered_by" in primary_dict
        assert "related_calls" in primary_dict
        assert len(primary_dict["related_calls"]) == 1
        assert primary_dict["related_calls"][0]["template_route"] == "/api/validate-coupon"


@pytest.mark.asyncio
async def test_analyzer_node_form_inferred_request_schema():
    """Verify AnalyzerNode constructs inferred requestBody schema from form field metadata."""
    state = {
        "captured_endpoints": [
            {
                "template_route": "/api/v1/customers",
                "method": "POST",
                "status": 201,
                "response_body": {"id": 101},
                "request_payload": None,
                "triggered_by": {
                    "action_type": "form_submit",
                    "selector": "form#new-cust-form button",
                    "form_context": "Add New Customer",
                    "field_names": ["first_name", "last_name", "email", "age", "is_vip"],
                    "submitted_fields": {
                        "first_name": "Alice",
                        "last_name": "Smith",
                        "email": "alice@example.com",
                        "age": 30,
                        "is_vip": True,
                    },
                },
            }
        ]
    }

    with patch("app.agents.nodes.analyzer._enrich_endpoints_with_llm", new=AsyncMock(side_effect=lambda eps, **kw: eps)), \
         patch("app.services.vector_store.EndpointVectorStore.store_endpoints", new=AsyncMock()):
        analyzed_state = await AnalyzerNode.process(state)

    endpoints = analyzed_state.get("captured_endpoints", [])
    assert len(endpoints) == 1

    ep = endpoints[0]
    assert "form_inferred_request_schema" in ep
    props = ep["form_inferred_request_schema"]["properties"]
    assert props["first_name"]["type"] == "string"
    assert props["age"]["type"] == "integer"
    assert props["is_vip"]["type"] == "boolean"


def test_openapi_and_markdown_export_triggered_by():
    """Verify OpenAPIExporter and MarkdownExporter output x-triggered-by and form attribution."""
    sample_endpoints = [
        {
            "template_route": "/api/v1/projects",
            "method": "POST",
            "status": 201,
            "schema": {"type": "object", "properties": {"project_id": {"type": "string"}}},
            "confidence": 0.9,
            "example_count": 2,
            "triggered_by": {
                "action_type": "form_submit",
                "selector": "form#project-modal button.submit",
                "form_context": "Create New API Project",
                "field_names": ["project_name", "environment"],
            },
            "related_calls": [
                {"method": "GET", "template_route": "/api/v1/orgs/current", "status": 200}
            ],
            "form_inferred_request_schema": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "environment": {"type": "string"},
                },
            },
        }
    ]

    # 1. OpenAPI Exporter
    spec = OpenAPIExporter.generate_spec("Project API", "https://app.test.io", sample_endpoints)
    operation = spec["paths"]["/api/v1/projects"]["post"]

    assert "x-triggered-by" in operation
    assert operation["x-triggered-by"]["form_context"] == "Create New API Project"
    assert "x-related-calls" in operation
    assert len(operation["x-related-calls"]) == 1

    assert "requestBody" in operation
    assert "project_name" in operation["requestBody"]["content"]["application/json"]["schema"]["properties"]

    # 2. Markdown Exporter
    md = MarkdownExporter.generate_markdown("Project API", "https://app.test.io", sample_endpoints)
    assert "Triggered By" in md
    assert "Create New API Project" in md
    assert "Related Calls" in md
    assert "/api/v1/orgs/current" in md
