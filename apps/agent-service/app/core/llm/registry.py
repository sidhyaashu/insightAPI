"""
registry.py — Provider Registry and dynamic multi-provider discovery for InsightAPI AI.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.llm.interface import BaseLLMProvider, ModelTier
from app.core.llm.providers.azure import AzureOpenAIProvider
from app.core.llm.providers.gemini import GoogleGeminiProvider
from app.core.llm.providers.openai import OpenAIProvider
from app.core.llm.providers.anthropic import AnthropicClaudeProvider
from app.core.llm.providers.local import OllamaLocalProvider

logger = logging.getLogger("agent.llm.registry")


class LLMProviderRegistry:
    """
    Central registry managing all LLM provider instances.
    Provides automated fallback resolution and per-request model routing.
    """

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._register_default_providers()

    def _register_default_providers(self) -> None:
        """Register built-in providers."""
        self.register(AzureOpenAIProvider())
        self.register(GoogleGeminiProvider())
        self.register(OpenAIProvider())
        self.register(AnthropicClaudeProvider())
        self.register(OllamaLocalProvider())

    def register(self, provider: BaseLLMProvider) -> None:
        """Register or override a provider adapter."""
        self._providers[provider.provider_id] = provider
        logger.debug(f"LLMProviderRegistry: Registered provider '{provider.provider_id}' ({provider.display_name})")

    def get(self, provider_id: str) -> Optional[BaseLLMProvider]:
        """Get provider by identifier."""
        return self._providers.get(provider_id.lower().strip())

    def get_configured_providers(self) -> List[BaseLLMProvider]:
        """Returns list of all providers that currently have valid credentials configured."""
        return [p for p in self._providers.values() if p.is_configured()]

    def resolve_provider(self, requested_provider: Optional[str] = None, model: Optional[str] = None) -> BaseLLMProvider:
        """
        Resolves the appropriate BaseLLMProvider instance.

        Resolution hierarchy:
        1. If a specific model name is requested (e.g. 'claude-3-7-sonnet', 'gemini-3.7-flash', 'gpt-4.1-mini'):
           Checks if any configured provider supports that model name.
        2. If `requested_provider` is explicitly passed or set in `settings.LLM_PROVIDER`:
           If that provider is configured, returns it. Otherwise logs a warning and falls back.
        3. Automated Fallback Chain:
           Azure -> Gemini -> OpenAI -> Anthropic -> Local -> First available configured.
        4. If nothing is configured, returns Azure (or requested) to provide descriptive error on instantiation.
        """
        # 1. Check if model name maps directly to a configured provider
        if model:
            model_clean = model.strip()
            # Explicit provider prefix in model name (e.g. "azure/gpt-4.1-mini" or "ollama/llama3")
            if "/" in model_clean:
                prefix, raw_model = model_clean.split("/", 1)
                p = self.get(prefix)
                if p and p.is_configured():
                    return p

            for p in self.get_configured_providers():
                if p.supports_model(model_clean):
                    return p

        # 2. Check explicitly requested provider or settings.LLM_PROVIDER
        pref = (requested_provider or getattr(settings, "LLM_PROVIDER", "auto") or "auto").strip().lower()
        if pref not in ("auto", "default"):
            # Normalize synonyms
            if pref == "google":
                pref = "gemini"
            p = self.get(pref)
            if p:
                if p.is_configured():
                    return p
                logger.warning(
                    f"LLM_PROVIDER is configured as '{pref}' but its credentials are missing. "
                    "Falling back to available provider credentials."
                )

        # 3. Automated Fallback Priority: Azure -> Gemini -> OpenAI -> Anthropic -> Local
        priority = ["azure", "gemini", "openai", "anthropic", "local"]
        for pid in priority:
            p = self.get(pid)
            if p and p.is_configured():
                return p

        # 4. Fallback to default registered provider
        fallback = self.get(pref) or self.get("azure") or self.get("gemini") or list(self._providers.values())[0]
        return fallback


# Global singleton registry instance
registry = LLMProviderRegistry()
