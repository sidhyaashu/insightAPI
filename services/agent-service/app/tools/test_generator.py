"""Automated Pytest & Newman CI/CD test suite generator."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from app.tools.base import ToolResult


def generate_pytest_suite(
    endpoints: List[Dict[str, Any]],
    base_url: str = "https://api.example.com",
    auth_header: Optional[str] = None,
) -> str:
    """
    Generate a production-grade pytest test suite using httpx.
    """
    lines = [
        '"""',
        'Auto-generated API Regression Test Suite by InsightAPI AI.',
        f'Target Base URL: {base_url}',
        '"""',
        "import pytest",
        "import httpx",
        "",
        f'BASE_URL = "{base_url.rstrip("/")}"',
        "",
        "@pytest.fixture",
        "def client():",
        '    headers = {"Accept": "application/json"}',
    ]

    if auth_header:
        lines.append(f'    headers["Authorization"] = "{auth_header}"')

    lines.extend([
        "    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=10.0) as c:",
        "        yield c",
        "",
    ])

    for i, ep in enumerate(endpoints):
        method = ep.get("method", "GET").upper()
        path = ep.get("path") or ep.get("template_path") or "/"
        # Replace template brackets {id} with test id 1
        clean_path = path.replace("{id}", "1").replace("{uuid}", "101").replace("{token}", "test_token")
        expected_status = ep.get("status_code", 200)
        func_name = f"test_{method.lower()}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '') or 'root'}"

        lines.extend([
            f"def {func_name}(client: httpx.Client):",
            f'    """Test {method} {path} returns expected status code."""',
            f'    response = client.request("{method}", "{clean_path}")',
            f"    assert response.status_code == {expected_status}, f\"Expected {expected_status} but got {{response.status_code}}: {{response.text}}\"",
            "    assert response.elapsed.total_seconds() < 3.0, \"Response latency exceeded 3.0s threshold\"",
            "",
        ])

    return "\n".join(lines)


def generate_postman_collection(
    endpoints: List[Dict[str, Any]],
    collection_name: str = "InsightAPI Generated Collection",
    base_url: str = "https://api.example.com",
) -> Dict[str, Any]:
    """
    Generate a Postman Collection v2.1 with Newman assertion scripts.
    """
    items = []
    for ep in endpoints:
        method = ep.get("method", "GET").upper()
        path = (ep.get("path") or ep.get("template_path") or "/").lstrip("/")
        expected_status = ep.get("status_code", 200)

        items.append({
            "name": f"{method} /{path}",
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            f"pm.test('Status code is {expected_status}', function () {{",
                            f"    pm.response.to.have.status({expected_status});",
                            "});",
                            "pm.test('Response time is under 2000ms', function () {",
                            "    pm.expect(pm.response.responseTime).to.be.below(2000);",
                            "});",
                        ],
                    },
                }
            ],
            "request": {
                "method": method,
                "header": [{"key": "Accept", "value": "application/json"}],
                "url": {
                    "raw": f"{{{{baseUrl}}}}/{path}",
                    "host": ["{{baseUrl}}"],
                    "path": path.split("/"),
                },
            },
        })

    return {
        "info": {
            "name": collection_name,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [{"key": "baseUrl", "value": base_url}],
        "item": items,
    }
