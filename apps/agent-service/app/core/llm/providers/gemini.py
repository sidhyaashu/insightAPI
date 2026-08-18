"""
gemini.py — Google Gemini LLM Provider Adapter.
"""
from __future__ import annotations

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.core.llm.interface import BaseLLMProvider, ModelTier

logger = logging.getLogger("agent.llm.gemini")


class GoogleGeminiProvider(BaseLLMProvider):
    """Adapter for Google Gemini models (gemini-3.7-flash, gemini-2.5-pro, etc.)."""

    @property
    def provider_id(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Google Gemini"

    def is_configured(self) -> bool:
        key = getattr(settings, "GEMINI_API_KEY", None)
        return bool(key and key.strip())

    def get_default_model(self, tier: ModelTier = ModelTier.FAST) -> str:
        if tier == ModelTier.FAST:
            return getattr(settings, "GEMINI_MODEL_FAST", "gemini-3.7-flash")
        elif tier == ModelTier.SMART:
            return getattr(settings, "GEMINI_MODEL_SMART", "gemini-3.7-flash")
        elif tier == ModelTier.VISION:
            return getattr(settings, "GEMINI_MODEL_VISION", "gemini-3.7-flash")
        return getattr(settings, "GEMINI_MODEL", "gemini-3.7-flash")

    def supports_model(self, model_name: str) -> bool:
        if not model_name:
            return False
        lower = model_name.lower()
        return "gemini" in lower or "google" in lower

    def build_client(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        streaming: bool = False,
        tier: ModelTier = ModelTier.FAST,
    ) -> BaseChatModel:
        model_name = model or self.get_default_model(tier)
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
            streaming=streaming,
        )
