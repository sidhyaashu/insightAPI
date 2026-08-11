"""
test_third_party_integrations.py — Unit tests for third-party integrations and fallbacks
"""
import pytest
from unittest.mock import MagicMock
from app.services.fuzzer import APIFuzzer
from app.services.vector_store import EndpointVectorStore
from app.core.config import settings


def test_api_fuzzer_fallback():
    """Verify APIFuzzer generates heuristic property findings when schemathesis is not installed."""
    sample_spec = {
        "openapi": "3.0.3",
        "paths": {
            "/api/v1/users": {
                "post": {
                    "summary": "Create User",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    results = APIFuzzer.fuzz_openapi_spec(sample_spec)
    assert results["status"] == "completed"
    assert "endpoints_fuzzed" in results
    assert results["endpoints_fuzzed"] == 1
    assert len(results["findings"]) == 1


def test_integration_config_settings():
    """Verify integration configuration flags exist in settings."""
    assert hasattr(settings, "STEALTH_MODE_ENABLED")
    assert hasattr(settings, "PROXY_URL")
    assert hasattr(settings, "CHROME_EXTENSION_PATHS")
    assert hasattr(settings, "FUZZING_ENABLED")


@pytest.mark.asyncio
async def test_vector_store_chroma_fallback():
    """Verify EndpointVectorStore functions cleanly with or without ChromaDB."""
    eps = [{"method": "GET", "template_route": "/test", "ai_summary": "Test route"}]
    await EndpointVectorStore.store_endpoints("test-session-ext", eps)
    res = await EndpointVectorStore.search_similar("test route", top_k=1)
    assert isinstance(res, list)
