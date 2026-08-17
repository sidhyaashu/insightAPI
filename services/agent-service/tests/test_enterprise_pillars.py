"""Unit tests for the 6 enterprise pillars: SSRF, HAR Parsing, Test Gen, and ReAct Engine."""
import pytest
from app.tools.guardrails import validate_target_url
from app.tools.traffic_parser import parse_har_traffic
from app.tools.test_generator import generate_pytest_suite, generate_postman_collection


def test_ssrf_guardrail():
    # Private / Localhost / AWS metadata should be blocked
    is_safe, err = validate_target_url("http://127.0.0.1:8000/secret")
    assert not is_safe
    assert "blocked" in err.lower()

    is_safe, err = validate_target_url("http://169.254.169.254/latest/meta-data")
    assert not is_safe

    is_safe, err = validate_target_url("http://localhost:5432")
    assert not is_safe

    is_safe, err = validate_target_url("http://insightapi_db:5432")
    assert not is_safe

    # Public HTTPS domains should pass
    is_safe, err = validate_target_url("https://httpbin.org/json")
    assert is_safe
    assert err is None


def test_har_traffic_parser():
    sample_har = {
        "log": {
            "entries": [
                {
                    "request": {"method": "GET", "url": "https://api.example.com/v1/users/101"},
                    "response": {"status": 200, "content": {"mimeType": "application/json", "text": '{"id": 101, "name": "Alice"}'}},
                },
                {
                    "request": {"method": "GET", "url": "https://api.example.com/v1/users/102"},
                    "response": {"status": 200, "content": {"mimeType": "application/json", "text": '{"id": 102, "name": "Bob"}'}},
                },
                {
                    "request": {"method": "GET", "url": "https://api.example.com/assets/logo.png"},
                    "response": {"status": 200, "content": {"mimeType": "image/png", "text": ""}},
                },
            ]
        }
    }

    result = parse_har_traffic(sample_har)
    assert result.status == "success"
    data = result.data
    assert data["total_entries_scanned"] == 3
    assert data["static_assets_filtered"] == 1
    # Both /users/101 and /users/102 should be deduplicated into /users/{id}
    assert data["unique_endpoints_found"] == 1
    endpoint = data["endpoints"][0]
    assert endpoint["template_path"] == "/v1/users/{id}"
    assert endpoint["occurrences"] == 2


def test_test_generation():
    endpoints = [
        {"method": "GET", "template_path": "/api/v1/users/{id}", "status_code": 200},
        {"method": "POST", "template_path": "/api/v1/auth/login", "status_code": 200},
    ]

    pytest_code = generate_pytest_suite(endpoints, base_url="https://api.example.com")
    assert "import pytest" in pytest_code
    assert "def test_get_api_v1_users_id" in pytest_code
    assert "def test_post_api_v1_auth_login" in pytest_code
    assert "assert response.status_code == 200" in pytest_code

    postman = generate_postman_collection(endpoints, collection_name="Test Suite")
    assert postman["info"]["name"] == "Test Suite"
    assert len(postman["item"]) == 2
    assert "pm.test('Status code is 200'" in postman["item"][0]["event"][0]["script"]["exec"][0]
