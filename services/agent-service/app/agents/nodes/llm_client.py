"""
llm_client.py — Shared LLM Infrastructure for InsightAPI AI Intelligence Layer

Components
----------
ModelTier        : Enum of FAST / SMART / VISION task categories.
ModelRouter      : Selects the right LLM model for each task type based on
                   config settings, automatically using Azure or standard OpenAI.
LLMCostManager   : Per-session token budget tracker with caching and cost estimation.
                   Exposes UI-facing metrics (tokens_used, llm_calls_made,
                   estimated_cost_usd) so future dashboard can display spend.
get_llm()        : Convenience factory used by all agent nodes.
"""
from __future__ import annotations

import hashlib
import json
import logging
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

logger = logging.getLogger("agent.llm_client")


def repair_json_string(raw_text: str) -> str:
    """
    Cleans and repairs common JSON formatting issues in raw LLM outputs:
    - Strips markdown code fences (```json ... ```)
    - Removes trailing commas before closing brackets/braces
    - Strips leading/trailing non-JSON commentary
    """
    import re
    if not raw_text:
        return "{}"

    text = raw_text.strip()
    # 1. Strip markdown fences
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 2. Extract first JSON array or object
    obj_match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if obj_match:
        text = obj_match.group(1).strip()

    # 3. Remove trailing commas before } or ]
    text = re.sub(r",\s*([\}\]])", r"\1", text)
    return text


# ---------------------------------------------------------------------------
# Model Tier
# ---------------------------------------------------------------------------

class ModelTier(str, Enum):
    """
    Task-complexity tiers that drive model selection.

    FAST   – High-frequency, low-complexity tasks (planner routing, form
             injection, endpoint summaries).  Uses the cheapest capable model.
    SMART  – Complex reasoning tasks (reflection, goal-directed planning).
             Uses the most capable reasoning model.
    VISION – Screenshot-based UI understanding when AXTree extraction fails.
             Uses a vision-capable model (gpt-4o-mini supports vision and is
             significantly cheaper than gpt-4o).
    """
    FAST = "fast"
    SMART = "smart"
    VISION = "vision"


# ---------------------------------------------------------------------------
# Approximate token pricing (USD per 1k tokens) — used for cost estimation
# Update these if model pricing changes.
# ---------------------------------------------------------------------------

_PRICE_PER_1K_TOKENS: Dict[str, float] = {
    "gpt-4o-mini": 0.000150,   # input $0.15/M tokens
    "gpt-4o": 0.005,           # input $5.00/M tokens
    "gpt-5.4": 0.005,          # treat like gpt-4o for estimation
    "default": 0.002,
}


def _model_price(model_name: str) -> float:
    for k, v in _PRICE_PER_1K_TOKENS.items():
        if k in model_name.lower():
            return v
    return _PRICE_PER_1K_TOKENS["default"]


# ---------------------------------------------------------------------------
# ModelRouter
# ---------------------------------------------------------------------------

class ModelRouter:
    """
    Selects the correct LangChain LLM instance for a given task tier.

    Decision logic
    --------------
    1. If Azure credentials are configured → use AzureChatOpenAI with the
       deployment name mapped to the tier.
    2. Otherwise → use ChatOpenAI with the standard OpenAI model name.
    3. Falls back to FAST tier model on any configuration error.

    Model assignment per tier (configurable via config.py / .env):
        FAST   → OPENAI_MODEL_FAST   / AZURE_OPENAI_DEPLOYMENT_FAST
        SMART  → OPENAI_MODEL_SMART  / AZURE_OPENAI_DEPLOYMENT_SMART
        VISION → OPENAI_MODEL_VISION / AZURE_OPENAI_DEPLOYMENT_VISION
    """

    @staticmethod
    def _is_azure() -> bool:
        return bool(settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY)

    @classmethod
    def get_model_name(cls, tier: ModelTier) -> str:
        """Returns the resolved model/deployment name for a tier."""
        if cls._is_azure():
            mapping = {
                ModelTier.FAST: settings.AZURE_OPENAI_DEPLOYMENT_FAST,
                ModelTier.SMART: settings.AZURE_OPENAI_DEPLOYMENT_SMART,
                ModelTier.VISION: settings.AZURE_OPENAI_DEPLOYMENT_VISION,
            }
        else:
            mapping = {
                ModelTier.FAST: settings.OPENAI_MODEL_FAST,
                ModelTier.SMART: settings.OPENAI_MODEL_SMART,
                ModelTier.VISION: settings.OPENAI_MODEL_VISION,
            }
        return mapping.get(tier, settings.OPENAI_MODEL_FAST)

    @classmethod
    def get_llm(cls, tier: ModelTier = ModelTier.FAST, temperature: float = 0.0):
        """
        Returns a configured LangChain ChatModel instance for the given tier.

        Parameters
        ----------
        tier        : Task complexity tier (FAST / SMART / VISION).
        temperature : Sampling temperature; default 0.0 for deterministic outputs.
        """
        model_name = cls.get_model_name(tier)

        try:
            if cls._is_azure():
                from langchain_openai import AzureChatOpenAI
                return AzureChatOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_key=settings.AZURE_OPENAI_API_KEY,
                    api_version=settings.AZURE_OPENAI_API_VERSION,
                    azure_deployment=model_name,
                    temperature=temperature,
                )
            else:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    model=model_name,
                    temperature=temperature,
                )
        except Exception as e:
            logger.error(f"ModelRouter: Failed to build LLM client for tier={tier}, model={model_name}: {e}")
            raise


# ---------------------------------------------------------------------------
# LLMCostManager
# ---------------------------------------------------------------------------

class LLMCostManager:
    """
    Per-session token budget tracker with response caching and UI-facing metrics.

    Usage
    -----
    Each crawl session creates one ``LLMCostManager`` instance and passes it
    through ``CrawlState``.  All agent nodes call ``record_usage()`` after
    each LLM invocation.  ``is_budget_exhausted()`` is checked before
    making a new LLM call — if True the caller falls back to heuristics.

    UI-facing metrics
    -----------------
    ``get_metrics()`` returns a dict that is embedded in ``CrawlResult`` so
    the future dashboard can display per-crawl cost and LLM call counts.
    """

    def __init__(
        self,
        token_budget: int = 0,   # 0 = unlimited
        planner_max_calls: int = 0,  # 0 = unlimited
    ):
        self._token_budget = token_budget
        self._planner_max_calls = planner_max_calls

        self._tokens_used: int = 0
        self._llm_calls_made: int = 0
        self._planner_calls_made: int = 0
        self._estimated_cost_usd: float = 0.0

        # Cache: (cache_key) → (response_text, tokens_used)
        self._cache: Dict[str, Tuple[str, int]] = {}

    # ── Budget checks ──────────────────────────────────────────────────────

    def is_budget_exhausted(self) -> bool:
        """True if token budget is set and already consumed."""
        if self._token_budget > 0 and self._tokens_used >= self._token_budget:
            logger.warning(
                f"LLMCostManager: Token budget exhausted "
                f"({self._tokens_used}/{self._token_budget}). "
                "Falling back to heuristics."
            )
            return True
        return False

    def is_planner_budget_exhausted(self) -> bool:
        """True if planner call limit is set and reached."""
        if self._planner_max_calls > 0 and self._planner_calls_made >= self._planner_max_calls:
            logger.info(
                f"LLMCostManager: Planner call limit reached "
                f"({self._planner_calls_made}/{self._planner_max_calls}). "
                "Switching to heuristic scoring."
            )
            return True
        return False

    # ── Cache helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _make_cache_key(prompt: str) -> str:
        return hashlib.md5(prompt.encode("utf-8")).hexdigest()

    def get_cached(self, prompt: str) -> Optional[str]:
        """Return cached LLM response if available."""
        key = self._make_cache_key(prompt)
        if key in self._cache:
            cached_response, tokens = self._cache[key]
            logger.debug(f"LLMCostManager: Cache hit (saved ~{tokens} tokens).")
            return cached_response
        return None

    def put_cache(self, prompt: str, response: str, tokens_used: int) -> None:
        """Store LLM response in cache."""
        key = self._make_cache_key(prompt)
        self._cache[key] = (response, tokens_used)

    # ── Usage recording ────────────────────────────────────────────────────

    def record_usage(
        self,
        tokens_used: int,
        model_name: str,
        is_planner_call: bool = False,
    ) -> None:
        """
        Records token consumption after each LLM call.

        Parameters
        ----------
        tokens_used     : Actual tokens consumed (prompt + completion).
        model_name      : Model name for pricing lookup.
        is_planner_call : True when called from PlannerNode (tracked separately).
        """
        self._tokens_used += tokens_used
        self._llm_calls_made += 1
        if is_planner_call:
            self._planner_calls_made += 1
        self._estimated_cost_usd += (tokens_used / 1000.0) * _model_price(model_name)
        logger.debug(
            f"LLMCostManager: +{tokens_used} tokens | "
            f"total={self._tokens_used} | "
            f"calls={self._llm_calls_made} | "
            f"est. cost=${self._estimated_cost_usd:.4f}"
        )

    # ── UI-facing metrics export ───────────────────────────────────────────

    def get_metrics(self) -> Dict[str, Any]:
        """
        Returns a serialisable metrics dict for embedding in CrawlResult.
        The future UI dashboard consumes these fields to display per-crawl spend.
        """
        return {
            "tokens_used": self._tokens_used,
            "token_budget": self._token_budget,
            "budget_pct_used": round(
                (self._tokens_used / self._token_budget * 100) if self._token_budget else 0,
                1,
            ),
            "llm_calls_made": self._llm_calls_made,
            "planner_calls_made": self._planner_calls_made,
            "estimated_cost_usd": round(self._estimated_cost_usd, 4),
            "cache_size": len(self._cache),
        }


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def get_llm(tier: ModelTier = ModelTier.FAST, temperature: float = 0.0):
    """
    Module-level shortcut for ``ModelRouter.get_llm()``.

    Usage::

        from app.agents.nodes.llm_client import get_llm, ModelTier
        llm = get_llm(ModelTier.FAST)
        response = await llm.ainvoke(prompt)
    """
    return ModelRouter.get_llm(tier=tier, temperature=temperature)


def make_cost_manager() -> LLMCostManager:
    """Creates a new ``LLMCostManager`` pre-configured from global settings."""
    return LLMCostManager(
        token_budget=settings.LLM_TOKEN_BUDGET_PER_CRAWL,
        planner_max_calls=settings.LLM_PLANNER_MAX_CALLS,
    )
