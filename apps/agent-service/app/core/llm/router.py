"""
router.py — ModelRouter for InsightAPI AI Intelligence Layer.
"""
from __future__ import annotations

import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.llm.interface import ModelTier
from app.core.llm.registry import registry

logger = logging.getLogger("agent.llm.router")


class ModelRouter:
    """
    Selects and builds the correct LangChain ChatModel instance for any task tier or model override.
    """

    @classmethod
    def get_provider(cls, requested_provider: Optional[str] = None, model: Optional[str] = None) -> str:
        """Determines active provider ID ('azure', 'gemini', 'openai', 'anthropic', 'local')."""
        provider = registry.resolve_provider(requested_provider=requested_provider, model=model)
        return provider.provider_id

    @classmethod
    def get_model_name(
        cls,
        tier: ModelTier = ModelTier.FAST,
        requested_provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Returns the resolved model or deployment name."""
        if model and model.strip():
            # Clean off prefix if passed like "azure/gpt-4.1-mini"
            if "/" in model:
                return model.split("/", 1)[1]
            return model.strip()
        provider = registry.resolve_provider(requested_provider=requested_provider)
        return provider.get_default_model(tier)

    @classmethod
    def get_llm(
        cls,
        tier: ModelTier = ModelTier.FAST,
        model: Optional[str] = None,
        temperature: float = 0.0,
        streaming: bool = False,
        provider: Optional[str] = None,
    ) -> BaseChatModel:
        """
        Returns a configured LangChain ChatModel instance for the given tier or explicit model.

        Parameters
        ----------
        tier        : Task complexity tier (FAST / SMART / VISION).
        model       : Optional explicit model or deployment override.
        temperature : Sampling temperature (0.0 = deterministic).
        streaming   : Enable streaming token generation.
        provider    : Explicit provider override ID.
        """
        active_provider = registry.resolve_provider(requested_provider=provider, model=model)
        resolved_model = model
        if model and "/" in model:
            resolved_model = model.split("/", 1)[1]

        logger.debug(
            f"ModelRouter: Instantiating client (provider={active_provider.provider_id}, "
            f"tier={tier.value}, model={resolved_model or active_provider.get_default_model(tier)}, "
            f"streaming={streaming})"
        )
        return active_provider.build_client(
            model=resolved_model,
            temperature=temperature,
            streaming=streaming,
            tier=tier,
        )


def get_llm(
    tier: ModelTier = ModelTier.FAST,
    model: Optional[str] = None,
    temperature: float = 0.0,
    streaming: bool = False,
    provider: Optional[str] = None,
) -> BaseChatModel:
    """
    Top-level convenience factory used by all agent nodes.

    Example
    -------
    >>> from app.core.llm import get_llm, ModelTier
    >>> llm = get_llm(ModelTier.FAST)
    >>> llm_streaming = get_llm(ModelTier.SMART, streaming=True)
    """
    return ModelRouter.get_llm(
        tier=tier,
        model=model,
        temperature=temperature,
        streaming=streaming,
        provider=provider,
    )
