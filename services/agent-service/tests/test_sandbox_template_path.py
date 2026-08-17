import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.engine.sandbox.executor import SandboxExecutor


@pytest.mark.asyncio
async def test_run_test_template_path_without_target_domain_raises():
    """
    Verify F-23: Calling run_test with a template/relative path and no target_domain
    must explicitly raise ValueError, not silently allow egress bypass.
    """
    ep_relative = {
        "method": "GET",
        "url": "/api/v1/users/{id}",
        "template_route": "/api/v1/users/{id}",
        "status": 200,
    }
    test_strategy = {
        "strategy": "adjacent_integer",
        "mutate_param": "id",
        "vuln_class": "idor",
        "is_destructive": False,
    }

    # No target_domain provided and ep['url'] is a template path
    with pytest.raises(ValueError) as exc_info:
        await SandboxExecutor.run_test(
            ep=ep_relative,
            test_strategy=test_strategy,
            target_domain=None,
            allow_destructive=False,
        )

    assert "Invalid target URL" in str(exc_info.value)
    assert "target_domain required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_run_test_template_path_with_target_domain_resolves_correctly():
    """Verify that when target_domain is provided, a relative path is resolved to absolute URL."""
    ep_relative = {
        "method": "GET",
        "url": "/api/v1/users/1",
        "template_route": "/api/v1/users/{id}",
        "status": 200,
    }
    test_strategy = {
        "strategy": "adjacent_integer",
        "mutate_param": "id",
        "vuln_class": "idor",
        "is_destructive": False,
    }

    mock_resp = {
        "status_code": 200,
        "body": {"id": 2, "name": "Alice"},
        "headers": {},
        "error": None,
        "blocked": False,
    }

    with patch.object(SandboxExecutor, "run_request", new=AsyncMock(return_value=mock_resp)) as mock_run_req:
        res = await SandboxExecutor.run_test(
            ep=ep_relative,
            test_strategy=test_strategy,
            target_domain="api.example.com",
            allow_destructive=False,
        )

        assert res["status_code"] == 200
        mock_run_req.assert_called_once()
        call_url = mock_run_req.call_args[1]["url"]
        assert call_url.startswith("https://api.example.com/api/v1/users/")
