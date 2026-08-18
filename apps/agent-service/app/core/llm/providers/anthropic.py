"""
anthropic.py — Anthropic Claude LLM Provider Adapter.
"""
from __future__ import annotations

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings
from app.core.llm.interface import BaseLLMProvider, ModelTier

logger = logging.getLogger("agent.llm.anthropic")


class AnthropicClaudeProvider(BaseLLMProvider):
    """Adapter for Anthropic Claude models (claude-3-7-sonnet, claude-3-5-haiku, etc.)."""

    @property
    def provider_id(self) -> str:
        return "anthropic"

    @property
    def display_name(self) -> str:
        return "Anthropic Claude"

    def is_configured(self) -> bool:
        key = getattr(settings, "ANTHROPIC_API_KEY", None)
        return bool(key and key.strip())

    def get_default_model(self, tier: ModelTier = ModelTier.FAST) -> str:
        if tier == ModelTier.FAST:
            return getattr(settings, "ANTHROPIC_MODEL_FAST", "claude-3-5-haiku-20241022")
        elif tier == ModelTier.SMART:
            return getattr(settings, "ANTHROPIC_MODEL_SMART", "claude-3-7-sonnet-20250219")
        elif tier == ModelTier.VISION:
            return getattr(settings, "ANTHROPIC_MODEL_VISION", "claude-3-7-sonnet-20250219")
        return getattr(settings, "ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")

    def supports_model(self, model_name: str) -> bool:
        if not model_name:
            return False
        lower = model_name.lower()
        return "claude" in lower or "anthropic" in lower

    def build_client(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        streaming: bool = False,
        tier: ModelTier = ModelTier.FAST,
    ) -> BaseChatModel:
        model_name = model or self.get_default_model(tier)
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                model_name=model_name,
                temperature=temperature,
                streaming=streaming,
            )
        except ImportError:
            # Fallback via OpenAI-compatible endpoint proxy or error guidance
            from langchain_openai import ChatOpenAI
            logger.warning(
                "langchain-anthropic package is not installed. Attempting ChatOpenAI proxy fallback."
            )
            return ChatOpenAI(
                api_key=settings.ANTHROPIC_API_KEY or "none",
                model=model_name,
                temperature=temperature,
                streaming=streaming,
            )
