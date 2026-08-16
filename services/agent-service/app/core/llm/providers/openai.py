"""
openai.py — Standard OpenAI LLM Provider Adapter.
"""
from __future__ import annotations

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.llm.interface import BaseLLMProvider, ModelTier

logger = logging.getLogger("agent.llm.openai")


class OpenAIProvider(BaseLLMProvider):
    """Adapter for standard OpenAI models (gpt-4o, gpt-4o-mini, o3-mini, etc.)."""

    @property
    def provider_id(self) -> str:
        return "openai"

    @property
    def display_name(self) -> str:
        return "OpenAI"

    def is_configured(self) -> bool:
        key = getattr(settings, "OPENAI_API_KEY", None)
        return bool(key and key.strip())

    def get_default_model(self, tier: ModelTier = ModelTier.FAST) -> str:
        if tier == ModelTier.FAST:
            return getattr(settings, "OPENAI_MODEL_FAST", "gpt-4o-mini")
        elif tier == ModelTier.SMART:
            return getattr(settings, "OPENAI_MODEL_SMART", "gpt-4o")
        elif tier == ModelTier.VISION:
            return getattr(settings, "OPENAI_MODEL_VISION", "gpt-4o-mini")
        return getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    def supports_model(self, model_name: str) -> bool:
        if not model_name:
            return False
        lower = model_name.lower()
        return (
            lower.startswith("gpt-") or
            lower.startswith("o1") or
            lower.startswith("o3") or
            "openai" in lower
        )

    def build_client(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        streaming: bool = False,
        tier: ModelTier = ModelTier.FAST,
    ) -> BaseChatModel:
        model_name = model or self.get_default_model(tier)
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=model_name,
            temperature=temperature,
            streaming=streaming,
        )
