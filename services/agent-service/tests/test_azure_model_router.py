import pytest
from unittest.mock import patch, MagicMock
from app.agents.nodes.llm_client import ModelRouter, ModelTier, _model_price
from app.core.config import settings
from app.services.chat_service import _build_langchain_client


def test_azure_provider_resolution_with_keys(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "azure")
    monkeypatch.setattr(settings, "AZURE_OPENAI_ENDPOINT", "https://insightapi.openai.azure.com/")
    monkeypatch.setattr(settings, "AZURE_OPENAI_API_KEY", "test-key-12345")
    assert ModelRouter.get_provider() == "azure"


def test_azure_provider_fallback_when_keys_missing(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "azure")
    monkeypatch.setattr(settings, "AZURE_OPENAI_ENDPOINT", None)
    monkeypatch.setattr(settings, "AZURE_OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "gemini-key-123")
    # Falls back gracefully to Gemini instead of crashing with missing credentials
    assert ModelRouter.get_provider() == "gemini"


def test_azure_model_name_default_deployment(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "azure")
    monkeypatch.setattr(settings, "AZURE_OPENAI_ENDPOINT", "https://insightapi.openai.azure.com/")
    monkeypatch.setattr(settings, "AZURE_OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT_FAST", None)
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT_SMART", None)
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT_VISION", None)

    assert ModelRouter.get_model_name(ModelTier.FAST) == "gpt-4.1-mini"
    assert ModelRouter.get_model_name(ModelTier.SMART) == "gpt-4.1-mini"
    assert ModelRouter.get_model_name(ModelTier.VISION) == "gpt-4.1-mini"


def test_azure_model_name_tier_overrides(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "azure")
    monkeypatch.setattr(settings, "AZURE_OPENAI_ENDPOINT", "https://insightapi.openai.azure.com/")
    monkeypatch.setattr(settings, "AZURE_OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT_FAST", "gpt-4.1-mini")
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT_SMART", "gpt-4.1-smart-custom")
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT_VISION", "gpt-4.1-mini")

    assert ModelRouter.get_model_name(ModelTier.FAST) == "gpt-4.1-mini"
    assert ModelRouter.get_model_name(ModelTier.SMART) == "gpt-4.1-smart-custom"
    assert ModelRouter.get_model_name(ModelTier.VISION) == "gpt-4.1-mini"


def test_gpt_4_1_mini_pricing():
    price = _model_price("gpt-4.1-mini")
    assert price == 0.000150


def test_build_langchain_client_azure(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "azure")
    monkeypatch.setattr(settings, "AZURE_OPENAI_ENDPOINT", "https://insightapi.openai.azure.com/")
    monkeypatch.setattr(settings, "AZURE_OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    monkeypatch.setattr(settings, "AZURE_OPENAI_DEPLOYMENT_SMART", None)

    with patch("langchain_openai.AzureChatOpenAI") as mock_azure:
        _build_langchain_client()
        mock_azure.assert_called_once_with(
            azure_endpoint="https://insightapi.openai.azure.com/",
            azure_deployment="gpt-4.1-mini",
            api_version=settings.AZURE_OPENAI_API_VERSION,
            api_key="test-key-12345",
            streaming=True,
            temperature=0.7,
        )
