"""Comprehensive Unit Tests for Advanced Stealth, Form Filling, GraphQL, and Dependency Chaining."""
import pytest
from app.tools.stealth import STEALTH_JS_INJECTION
from app.tools.form_filler import get_contextual_value_for_input
from app.tools.graphql_parser import parse_graphql_payload
from app.tools.dependency_chainer import extract_identifiers_from_payload, chain_api_dependencies
from app.tools.browser_explorer import explore_web_app_browser, _compute_dom_state_hash


def test_stealth_script_evasions():
    """Verify stealth script contains evasions for webdriver, plugins, and WebGL."""
    assert "navigator, 'webdriver'" in STEALTH_JS_INJECTION
    assert "navigator, 'languages'" in STEALTH_JS_INJECTION
    assert "window.chrome.runtime" in STEALTH_JS_INJECTION
    assert "Google Inc. (NVIDIA)" in STEALTH_JS_INJECTION


def test_form_filler_heuristics():
    """Verify contextual input value synthesizer produces valid realistic data."""
    # Email
    email_val = get_contextual_value_for_input({"type": "email", "name": "user_email"})
    assert "@" in email_val

    # Date
    date_val = get_contextual_value_for_input({"type": "date", "name": "birthdate"})
    assert len(date_val.split("-")) == 3  # YYYY-MM-DD

    # Search
    search_val = get_contextual_value_for_input({"type": "search", "name": "q", "placeholder": "Search catalog..."})
    assert len(search_val) > 0

    # Password
    pass_val = get_contextual_value_for_input({"type": "password", "name": "pwd"})
    assert len(pass_val) >= 8

    # Number / Quantity
    num_val = get_contextual_value_for_input({"type": "number", "name": "quantity"})
    assert num_val.isdigit()


def test_graphql_operation_disaggregation():
    """Verify single and batch GraphQL requests are parsed into distinct operation endpoints."""
    # Single query
    payload = {
        "operationName": "GetUserProfile",
        "query": "query GetUserProfile($id: ID!) { user(id: $id) { name email } }",
        "variables": {"id": "123"}
    }
    ops = parse_graphql_payload(payload)
    assert len(ops) == 1
    assert ops[0]["operation_name"] == "GetUserProfile"
    assert ops[0]["operation_type"] == "query"
    assert ops[0]["virtual_endpoint"] == "POST /graphql #query:GetUserProfile"

    # Batch mutation
    batch_payload = [
        {"query": "mutation CreateOrder { createOrder { id } }"},
        {"query": "query ListInventory { items { id name } }"}
    ]
    ops_batch = parse_graphql_payload(batch_payload)
    assert len(ops_batch) == 2
    assert ops_batch[0]["operation_name"] == "CreateOrder"
    assert ops_batch[0]["operation_type"] == "mutation"
    assert ops_batch[1]["operation_name"] == "ListInventory"


def test_api_dependency_chaining():
    """Verify dynamic IDs and tokens are extracted and substituted into downstream routes."""
    upstream_response = {
        "token": "eyJhbGciOi...",
        "user": {
            "id": 42,
            "order_id": "ORD-9872"
        }
    }
    extracted = extract_identifiers_from_payload(upstream_response)
    assert extracted["id"] == 42
    assert extracted["order_id"] == "ORD-9872"
    assert extracted["token"] == "eyJhbGciOi..."

    endpoints = [
        {
            "method": "POST",
            "template_path": "/api/v1/auth/login",
            "sample_response": upstream_response,
            "status_code": 200
        },
        {
            "method": "GET",
            "template_path": "/api/v1/users/{id}/orders/{order_id}",
            "sample_response": None,
            "status_code": 200
        }
    ]

    chain = chain_api_dependencies(endpoints)
    assert len(chain) == 2
    assert chain[1]["resolved_path"] == "/api/v1/users/42/orders/ORD-9872"
    assert chain[1]["has_chained_parameters"] is True


def test_dom_state_hashing():
    """Verify DOM state hash computation prevents infinite loops."""
    hash1 = _compute_dom_state_hash("https://app.com", ["btn-1", "btn-2", "tab-settings"])
    hash2 = _compute_dom_state_hash("https://app.com", ["btn-2", "btn-1", "tab-settings"])
    hash3 = _compute_dom_state_hash("https://app.com/profile", ["btn-1", "btn-2"])

    assert hash1 == hash2  # Same elements should match regardless of ordering
    assert hash1 != hash3  # Different URL/elements should produce distinct hashes


@pytest.mark.asyncio
async def test_deep_browser_exploration():
    """Verify full browser exploration runs against live web endpoint."""
    res = await explore_web_app_browser("https://httpbin.org/forms/post", max_clicks=2)
    assert res.status == "success"
    assert res.data["actions_executed"] >= 1
    assert "dependency_chain" in res.data
