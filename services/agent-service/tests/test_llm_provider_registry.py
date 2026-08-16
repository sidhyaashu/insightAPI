"""
test_llm_provider_registry.py — Comprehensive Unit Tests for app.core.llm Architecture.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.core.llm import (
    BaseLLMProvider,
    ModelTier,
    LLMProviderRegistry,
    registry,
    ModelRouter,
    get_llm,
    LLMCostManager,
    get_model_price_per_1k,
    extract_text_content,
    repair_json_string,
)
from app.core.llm.providers import (
    AzureOpenAIProvider,
    GoogleGeminiProvider,
    OpenAIProvider,
    AnthropicClaudeProvider,
    OllamaLocalProvider,
)


# ---------------------------------------------------------------------------
# 1. Provider Adapter Tests
# ---------------------------------------------------------------------------

def test_provider_adapter_metadata():
    azure = AzureOpenAIProvider()
    assert azure.provider_id == "azure"
    assert "Azure" in azure.display_name

    gemini = GoogleGeminiProvider()
    assert gemini.provider_id == "gemini"
    assert "Gemini" in gemini.display_name

    openai = OpenAIProvider()
    assert openai.provider_id == "openai"
    assert "OpenAI" in openai.display_name

    anthropic = AnthropicClaudeProvider()
    assert anthropic.provider_id == "anthropic"
    assert "Anthropic" in anthropic.display_name

    local = OllamaLocalProvider()
    assert local.provider_id == "local"
    assert "Ollama" in local.display_name or "Local" in local.display_name


def test_provider_is_configured():
    with patch.object(settings, "AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/"), \
         patch.object(settings, "AZURE_OPENAI_API_KEY", "test-key"):
        assert AzureOpenAIProvider().is_configured() is True

    with patch.object(settings, "AZURE_OPENAI_ENDPOINT", None), \
         patch.object(settings, "AZURE_OPENAI_API_KEY", None):
        assert AzureOpenAIProvider().is_configured() is False

    with patch.object(settings, "GEMINI_API_KEY", "test-gemini-key"):
        assert GoogleGeminiProvider().is_configured() is True

    with patch.object(settings, "GEMINI_API_KEY", None):
        assert GoogleGeminiProvider().is_configured() is False

    with patch.object(settings, "OPENAI_API_KEY", "test-openai-key"):
        assert OpenAIProvider().is_configured() is True

    with patch.object(settings, "ANTHROPIC_API_KEY", "test-anthropic-key"):
        assert AnthropicClaudeProvider().is_configured() is True

    with patch.object(settings, "LOCAL_OPENAI_BASE_URL", "http://localhost:11434/v1"):
        assert OllamaLocalProvider().is_configured() is True


# ---------------------------------------------------------------------------
# 2. Registry Resolution & Fallback Hierarchy Tests
# ---------------------------------------------------------------------------

def test_registry_fallback_to_gemini_when_azure_missing():
    custom_reg = LLMProviderRegistry()
    with patch.object(settings, "LLM_PROVIDER", "auto"), \
         patch.object(settings, "AZURE_OPENAI_ENDPOINT", None), \
         patch.object(settings, "AZURE_OPENAI_API_KEY", None), \
         patch.object(settings, "GEMINI_API_KEY", "valid-gemini-key"):
        resolved = custom_reg.resolve_provider()
        assert resolved.provider_id == "gemini"


def test_registry_resolves_azure_when_configured():
    custom_reg = LLMProviderRegistry()
    with patch.object(settings, "LLM_PROVIDER", "azure"), \
         patch.object(settings, "AZURE_OPENAI_ENDPOINT", "https://foundry.openai.azure.com/"), \
         patch.object(settings, "AZURE_OPENAI_API_KEY", "secret-key"):
        resolved = custom_reg.resolve_provider()
        assert resolved.provider_id == "azure"


def test_registry_resolves_by_model_name():
    custom_reg = LLMProviderRegistry()
    with patch.object(settings, "GEMINI_API_KEY", "valid-key"), \
         patch.object(settings, "AZURE_OPENAI_ENDPOINT", "https://test.azure.com"), \
         patch.object(settings, "AZURE_OPENAI_API_KEY", "azure-key"), \
         patch.object(settings, "ANTHROPIC_API_KEY", "anthropic-key"), \
         patch.object(settings, "LOCAL_OPENAI_BASE_URL", "http://localhost:11434/v1"):

        # Gemini model routing
        p1 = custom_reg.resolve_provider(model="gemini-3.7-flash")
        assert p1.provider_id == "gemini"

        # Anthropic model routing
        p2 = custom_reg.resolve_provider(model="claude-3-7-sonnet")
        assert p2.provider_id == "anthropic"

        # Local model routing
        p3 = custom_reg.resolve_provider(model="deepseek-r1:8b")
        assert p3.provider_id == "local"

        # Explicit prefix model routing
        p4 = custom_reg.resolve_provider(model="azure/gpt-4.1-mini")
        assert p4.provider_id == "azure"


# ---------------------------------------------------------------------------
# 3. ModelRouter Client Building Tests
# ---------------------------------------------------------------------------

def test_model_router_build_azure_client():
    with patch.object(settings, "LLM_PROVIDER", "azure"), \
         patch.object(settings, "AZURE_OPENAI_ENDPOINT", "https://insightapi.openai.azure.com/"), \
         patch.object(settings, "AZURE_OPENAI_API_KEY", "azure-secret-key"), \
         patch.object(settings, "AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"):
        llm = ModelRouter.get_llm(tier=ModelTier.SMART)
        assert llm is not None
        assert llm.deployment_name == "gpt-4.1-mini"


def test_model_router_build_gemini_client():
    with patch.object(settings, "LLM_PROVIDER", "gemini"), \
         patch.object(settings, "GEMINI_API_KEY", "gemini-secret-key"), \
         patch.object(settings, "GEMINI_MODEL_FAST", "gemini-3.7-flash"):
        llm = ModelRouter.get_llm(tier=ModelTier.FAST)
        assert llm is not None
        assert llm.model == "gemini-3.7-flash"


def test_model_router_build_local_client():
    with patch.object(settings, "LOCAL_OPENAI_BASE_URL", "http://localhost:11434/v1"):
        llm = ModelRouter.get_llm(model="ollama/deepseek-r1")
        assert llm is not None
        assert llm.model_name == "deepseek-r1"


# ---------------------------------------------------------------------------
# 4. Token Cost Calculation Tests
# ---------------------------------------------------------------------------

def test_token_cost_pricing():
    assert get_model_price_per_1k("gpt-4.1-mini") == 0.000150
    assert get_model_price_per_1k("gemini-3.7-flash") == 0.000150
    assert get_model_price_per_1k("gpt-4o") == 0.005000
    assert get_model_price_per_1k("claude-3-7-sonnet") == 0.003000
    assert get_model_price_per_1k("ollama/llama3") == 0.000000


def test_llm_cost_manager_budget():
    mgr = LLMCostManager(token_budget=1000, planner_max_calls=2)
    assert mgr.is_budget_exhausted() is False
    assert mgr.is_planner_budget_exhausted() is False

    mgr.record_usage(tokens_used=600, model_name="gpt-4.1-mini", is_planner_call=True)
    assert mgr.is_budget_exhausted() is False
    assert mgr.is_planner_budget_exhausted() is False

    mgr.record_usage(tokens_used=500, model_name="gpt-4.1-mini", is_planner_call=True)
    assert mgr.is_budget_exhausted() is True
    assert mgr.is_planner_budget_exhausted() is True

    metrics = mgr.get_metrics()
    assert metrics["tokens_used"] == 1100
    assert metrics["llm_calls_made"] == 2
    assert metrics["planner_calls_made"] == 2
    assert metrics["estimated_cost_usd"] > 0.0


# ---------------------------------------------------------------------------
# 5. Utilities Tests (extract_text_content & repair_json_string)
# ---------------------------------------------------------------------------

def test_extract_text_content_variants():
    # Plain string
    assert extract_text_content("hello world") == "hello world"

    # None
    assert extract_text_content(None) == ""

    # Mock Message with content attribute
    msg = MagicMock()
    msg.content = "message text"
    assert extract_text_content(msg) == "message text"

    # List of Gemini-style content blocks
    blocks = [{"type": "text", "text": "part1 "}, {"type": "text", "text": "part2"}]
    assert extract_text_content(blocks) == "part1 part2"


def test_repair_json_string():
    # Markdown fence stripping
    fenced = "```json\n{\"status\": \"ok\",}\n```"
    repaired = repair_json_string(fenced)
    assert repaired == '{"status": "ok"}'

    # Trailing comma removal in list
    list_json = "[1, 2, 3,]"
    assert repair_json_string(list_json) == "[1, 2, 3]"
