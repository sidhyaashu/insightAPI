"""
local.py — Ollama / Local OpenAI-Compatible LLM Provider Adapter.
"""
from __future__ import annotations

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.llm.interface import BaseLLMProvider, ModelTier

logger = logging.getLogger("agent.llm.local")


class OllamaLocalProvider(BaseLLMProvider):
    """Adapter for Local LLMs (Ollama, vLLM, LM Studio, LocalAI) via OpenAI-compatible API."""

    @property
    def provider_id(self) -> str:
        return "local"

    @property
    def display_name(self) -> str:
        return "Ollama / Local (OpenAI-Compatible)"

    def is_configured(self) -> bool:
        url = getattr(settings, "LOCAL_OPENAI_BASE_URL", None)
        return bool(url and url.strip())

    def get_default_model(self, tier: ModelTier = ModelTier.FAST) -> str:
        if tier == ModelTier.FAST:
            return getattr(settings, "LOCAL_OPENAI_MODEL_FAST", "llama3.2:3b")
        elif tier == ModelTier.SMART:
            return getattr(settings, "LOCAL_OPENAI_MODEL_SMART", "deepseek-r1:8b")
        elif tier == ModelTier.VISION:
            return getattr(settings, "LOCAL_OPENAI_MODEL_VISION", "llava:7b")
        return getattr(settings, "LOCAL_OPENAI_MODEL", "deepseek-r1:8b")

    def supports_model(self, model_name: str) -> bool:
        if not model_name:
            return False
        lower = model_name.lower()
        return (
            "ollama" in lower or
            "local" in lower or
            "deepseek" in lower or
            "llama" in lower or
            "mistral" in lower or
            "qwen" in lower or
            "vllm" in lower
        )

    def build_client(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        streaming: bool = False,
        tier: ModelTier = ModelTier.FAST,
    ) -> BaseChatModel:
        model_name = model or self.get_default_model(tier)
        base_url = getattr(settings, "LOCAL_OPENAI_BASE_URL", "http://localhost:11434/v1")
        api_key = getattr(settings, "LOCAL_OPENAI_API_KEY", "ollama")
        return ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model=model_name,
            temperature=temperature,
            streaming=streaming,
        )
