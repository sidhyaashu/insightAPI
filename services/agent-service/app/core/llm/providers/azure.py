"""
azure.py — Azure OpenAI / Microsoft Foundry LLM Provider Adapter.
"""
from __future__ import annotations

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import AzureChatOpenAI

from app.core.config import settings
from app.core.llm.interface import BaseLLMProvider, ModelTier

logger = logging.getLogger("agent.llm.azure")


class AzureOpenAIProvider(BaseLLMProvider):
    """Adapter for Azure OpenAI / Microsoft AI Foundry deployments."""

    @property
    def provider_id(self) -> str:
        return "azure"

    @property
    def display_name(self) -> str:
        return "Azure AI Foundry / OpenAI"

    def is_configured(self) -> bool:
        endpoint = getattr(settings, "AZURE_OPENAI_ENDPOINT", None)
        api_key = getattr(settings, "AZURE_OPENAI_API_KEY", None)
        return bool(endpoint and endpoint.strip() and api_key and api_key.strip())

    def get_default_model(self, tier: ModelTier = ModelTier.FAST) -> str:
        default_deployment = getattr(settings, "AZURE_OPENAI_DEPLOYMENT", None) or "gpt-4.1-mini"
        if tier == ModelTier.FAST:
            return getattr(settings, "AZURE_OPENAI_DEPLOYMENT_FAST", None) or default_deployment
        elif tier == ModelTier.SMART:
            return getattr(settings, "AZURE_OPENAI_DEPLOYMENT_SMART", None) or default_deployment
        elif tier == ModelTier.VISION:
            return getattr(settings, "AZURE_OPENAI_DEPLOYMENT_VISION", None) or default_deployment
        return default_deployment

    def supports_model(self, model_name: str) -> bool:
        if not model_name:
            return False
        lower = model_name.lower()
        return "azure" in lower or lower in ("gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini-azure")

    def build_client(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        streaming: bool = False,
        tier: ModelTier = ModelTier.FAST,
    ) -> BaseChatModel:
        from urllib.parse import urlparse
        from langchain_openai import AzureChatOpenAI

        deployment = model or self.get_default_model(tier)
        raw_endpoint = settings.AZURE_OPENAI_ENDPOINT or ""
        parsed = urlparse(raw_endpoint)
        sanitized_endpoint = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else raw_endpoint

        return AzureChatOpenAI(
            azure_endpoint=sanitized_endpoint,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_deployment=deployment,
            temperature=temperature,
            streaming=streaming,
        )
