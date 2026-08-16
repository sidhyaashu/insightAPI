"""
interface.py — Abstract LLM Provider Protocol and Model Tiers for InsightAPI AI.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel


class ModelTier(str, Enum):
    """
    Task-complexity tiers that drive model selection across autonomous agent nodes.

    FAST   – High-frequency, low-latency tasks (planner routing, form
             injection, endpoint summaries). Uses the most cost-effective model.
    SMART  – Complex reasoning tasks (reflection, goal-directed planning,
             security vulnerability analysis). Uses the most capable reasoning model.
    VISION – Screenshot-based UI understanding when AXTree extraction fails.
             Uses a vision-capable multimodal model.
    """
    FAST = "fast"
    SMART = "smart"
    VISION = "vision"


class BaseLLMProvider(ABC):
    """
    Abstract Base Class for all LLM providers (Azure, Gemini, OpenAI, Anthropic, Ollama/Local).
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique lowercase identifier for the provider (e.g. 'azure', 'gemini', 'openai', 'anthropic', 'local')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name (e.g. 'Azure AI Foundry', 'Google Gemini', 'Anthropic Claude')."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the required credentials/endpoints for this provider are set and non-empty."""
        ...

    @abstractmethod
    def get_default_model(self, tier: ModelTier = ModelTier.FAST) -> str:
        """Returns the default configured model/deployment name for the given tier."""
        ...

    @abstractmethod
    def build_client(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        streaming: bool = False,
        tier: ModelTier = ModelTier.FAST,
    ) -> BaseChatModel:
        """
        Instantiates and returns a configured LangChain ChatModel instance.

        Parameters
        ----------
        model       : Explicit model or deployment override. If None, uses tier default.
        temperature : Sampling temperature (0.0 = deterministic).
        streaming   : Whether to enable streaming token generation.
        tier        : Complexity tier used to look up default model if `model` is None.
        """
        ...

    def supports_model(self, model_name: str) -> bool:
        """Returns True if this provider can handle the requested model name."""
        return False

    def supports_vision(self, model_name: str) -> bool:
        """Returns True if the given model supports multimodal/vision input."""
        return True
