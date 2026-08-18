"""
app.core.llm — Shared LLM Architecture & Multi-Provider Infrastructure for InsightAPI AI.
"""
from app.core.llm.interface import BaseLLMProvider, ModelTier
from app.core.llm.registry import LLMProviderRegistry, registry
from app.core.llm.router import ModelRouter, get_llm
from app.core.llm.cost import LLMCostManager, make_cost_manager, get_model_price_per_1k, PRICE_PER_1K_TOKENS
from app.core.llm.utils import extract_text_content, repair_json_string

__all__ = [
    "BaseLLMProvider",
    "ModelTier",
    "LLMProviderRegistry",
    "registry",
    "ModelRouter",
    "get_llm",
    "LLMCostManager",
    "make_cost_manager",
    "get_model_price_per_1k",
    "PRICE_PER_1K_TOKENS",
    "extract_text_content",
    "repair_json_string",
]
