"""
llm_client.py — Agent Node Gateway & Backward-Compatible Bridge to app.core.llm.

Provides 100% backward compatibility for all existing LangGraph nodes, test suites,
and utilities while delegating to the unified app.core.llm multi-provider engine.
"""
from __future__ import annotations

from app.core.llm import (
    BaseLLMProvider,
    ModelTier,
    LLMProviderRegistry,
    registry,
    ModelRouter,
    get_llm,
    LLMCostManager,
    make_cost_manager,
    get_model_price_per_1k,
    PRICE_PER_1K_TOKENS,
    extract_text_content,
    repair_json_string,
)

# Backward-compatible internal pricing aliases
_PRICE_PER_1K_TOKENS = PRICE_PER_1K_TOKENS
_model_price = get_model_price_per_1k

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
    "_PRICE_PER_1K_TOKENS",
    "_model_price",
    "extract_text_content",
    "repair_json_string",
]
