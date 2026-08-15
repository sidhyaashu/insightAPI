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

import asyncio
import hashlib
import json
import logging
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

logger = logging.getLogger("agent.llm_client")


def extract_text_content(content: Any) -> str:
    """
    Safely extracts plain text string from any LLM response or message content.
    Handles:
    - Plain string (ChatOpenAI, AzureChatOpenAI)
    - List of dicts/blocks (ChatGoogleGenerativeAI: [{'type': 'text', 'text': ...}])
    - Objects with .content attribute (AIMessage, BaseMessage)
    - Fallback str conversion
    """
    if content is None:
        return ""
    if hasattr(content, "content"):
        content = content.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    parts.append(str(item["text"]))
                elif "text" in item:
                    parts.append(str(item["text"]))
                else:
                    parts.append(str(item))
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


def repair_json_string(raw_text: str) -> str:
    """
    Cleans and repairs common JSON formatting issues in raw LLM outputs:
    - Extracts text if given an AIMessage/dict list
    - Strips markdown code fences (```json ... ```)
    - Removes trailing commas before closing brackets/braces
    - Strips leading/trailing non-JSON commentary
    """
    import re
    if raw_text is None:
        return "{}"
    if not isinstance(raw_text, str):
        raw_text = extract_text_content(raw_text)

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
             injection, endpoint summaries). Uses the cheapest capable model.
    SMART  – Complex reasoning tasks (reflection, goal-directed planning).
             Uses the most capable reasoning model.
    VISION – Screenshot-based UI understanding when AXTree extraction fails.
             Uses a vision-capable model (gemini-3.6-flash / gpt-4o-mini).
    """
    FAST = "fast"
    SMART = "smart"
    VISION = "vision"


# ---------------------------------------------------------------------------
# Approximate token pricing (USD per 1k tokens) — used for cost estimation
# Update these if model pricing changes.
# ---------------------------------------------------------------------------

_PRICE_PER_1K_TOKENS: Dict[str, float] = {
    "gemini-3.6-flash": 0.000100,
    "gemini-3.7-flash": 0.000150,
    "gemini-2.5-flash": 0.000100,
    "gemini-2.5-pro": 0.001250,
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
    1. If provider is explicitly specified in settings.LLM_PROVIDER, use that.
    2. Otherwise auto-detects in order: Gemini -> Azure OpenAI -> OpenAI.
    3. Falls back to FAST tier model on any configuration error.

    Model assignment per tier (configurable via config.py / .env):
        Gemini: GEMINI_MODEL_FAST / GEMINI_MODEL_SMART / GEMINI_MODEL_VISION
        Azure:  AZURE_OPENAI_DEPLOYMENT_FAST / SMART / VISION
        OpenAI: OPENAI_MODEL_FAST / SMART / VISION
    """

    @classmethod
    def get_provider(cls) -> str:
        """
        Determines active provider: "gemini", "azure", or "openai".
        """
        req_provider = (getattr(settings, "LLM_PROVIDER", "auto") or "auto").lower()
        if req_provider in ("gemini", "google"):
            return "gemini"
        if req_provider == "azure":
            return "azure"
        if req_provider == "openai":
            return "openai"

        # Auto-detection priority
        if settings.GEMINI_API_KEY:
            return "gemini"
        if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
            return "azure"
        if settings.OPENAI_API_KEY:
            return "openai"
        return "gemini" if settings.GEMINI_API_KEY else "openai"

    @classmethod
    def get_model_name(cls, tier: ModelTier) -> str:
        """Returns the resolved model/deployment name for a tier."""
        provider = cls.get_provider()
        if provider == "gemini":
            mapping = {
                ModelTier.FAST: settings.GEMINI_MODEL_FAST,
                ModelTier.SMART: settings.GEMINI_MODEL_SMART,
                ModelTier.VISION: settings.GEMINI_MODEL_VISION,
            }
            return mapping.get(tier, settings.GEMINI_MODEL_FAST)
        elif provider == "azure":
            mapping = {
                ModelTier.FAST: settings.AZURE_OPENAI_DEPLOYMENT_FAST,
                ModelTier.SMART: settings.AZURE_OPENAI_DEPLOYMENT_SMART,
                ModelTier.VISION: settings.AZURE_OPENAI_DEPLOYMENT_VISION,
            }
            return mapping.get(tier, settings.AZURE_OPENAI_DEPLOYMENT_FAST)
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
        provider = cls.get_provider()
        model_name = cls.get_model_name(tier)

        try:
            if provider == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=temperature,
                )
            elif provider == "azure":
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
            logger.error(
                f"ModelRouter: Failed to build LLM client (provider={provider}, tier={tier}, model={model_name}): {e}"
            )
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
        crawl_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self._token_budget = token_budget
        self._planner_max_calls = planner_max_calls
        self._crawl_id = crawl_id
        self._user_id = user_id

        self._tokens_used: int = 0
        self._llm_calls_made: int = 0
        self._planner_calls_made: int = 0
        self._estimated_cost_usd: float = 0.0

        # In-memory cache: (cache_key) → (response_text, tokens_used)
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

    _REDIS_CACHE_TTL = 86400  # 24 hours
    _REDIS_CACHE_PREFIX = "insightapi:llm_cache:"

    @staticmethod
    def _make_cache_key(prompt: str) -> str:
        return hashlib.md5(prompt.encode("utf-8")).hexdigest()

    def get_cached(self, prompt: str) -> Optional[str]:
        """Check in-memory cache first (fast path)."""
        key = self._make_cache_key(prompt)
        if key in self._cache:
            cached_response, tokens = self._cache[key]
            logger.debug(f"LLMCostManager: In-memory cache hit (saved ~{tokens} tokens).")
            return cached_response
        return None

    async def get_cached_redis(self, prompt: str) -> Optional[str]:
        """
        Cross-session Redis cache lookup.
        Checks Redis AFTER in-memory to avoid network latency for hot items.
        Returns cached response string or None.
        """
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            key = self._REDIS_CACHE_PREFIX + self._make_cache_key(prompt)
            cached = await redis.get(key)
            if cached:
                # Populate local in-memory cache for subsequent calls in same session
                data = json.loads(cached)
                self._cache[self._make_cache_key(prompt)] = (data["response"], data["tokens"])
                logger.debug(f"LLMCostManager: Redis cache hit (saved ~{data['tokens']} tokens).")
                return data["response"]
        except Exception as e:
            logger.debug(f"LLMCostManager: Redis cache lookup failed (non-fatal): {e}")
        return None

    def put_cache(self, prompt: str, response: str, tokens_used: int) -> None:
        """Store in in-memory cache."""
        key = self._make_cache_key(prompt)
        self._cache[key] = (response, tokens_used)

    async def put_cache_redis(self, prompt: str, response: str, tokens_used: int) -> None:
        """Store in Redis cross-session cache (fire-and-forget)."""
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            key = self._REDIS_CACHE_PREFIX + self._make_cache_key(prompt)
            await redis.set(
                key,
                json.dumps({"response": response, "tokens": tokens_used}),
                ex=self._REDIS_CACHE_TTL,
            )
        except Exception as e:
            logger.debug(f"LLMCostManager: Redis cache write failed (non-fatal): {e}")

    # ── Usage recording ────────────────────────────────────────────────────

    def record_usage(
        self,
        tokens_used: int,
        model_name: str,
        is_planner_call: bool = False,
        tier: str = "fast",
        node_name: Optional[str] = None,
        cached: bool = False,
    ) -> None:
        """
        Records token consumption after each LLM call.

        Parameters
        ----------
        tokens_used     : Actual tokens consumed (prompt + completion).
        model_name      : Model name for pricing lookup.
        is_planner_call : True when called from PlannerNode (tracked separately).
        tier            : ModelTier name for per-tier breakdowns.
        node_name       : Agent node identifier for cost attribution.
        cached          : True if this was a cache hit (no actual LLM call).
        """
        self._tokens_used += tokens_used
        self._llm_calls_made += 1
        if is_planner_call:
            self._planner_calls_made += 1
        cost = (tokens_used / 1000.0) * _model_price(model_name)
        self._estimated_cost_usd += cost
        logger.debug(
            f"LLMCostManager: +{tokens_used} tokens | "
            f"total={self._tokens_used} | "
            f"calls={self._llm_calls_made} | "
            f"est. cost=${self._estimated_cost_usd:.4f}"
        )
        # Async DB persistence — schedule as fire-and-forget if we have context
        if self._crawl_id and self._user_id and not cached:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(
                        self._persist_to_db(
                            model_name=model_name,
                            tier=tier,
                            prompt_tokens=tokens_used // 2,
                            completion_tokens=tokens_used - tokens_used // 2,
                            cost_usd=cost,
                            cached=cached,
                            node_name=node_name,
                        )
                    )
            except RuntimeError:
                pass  # No event loop available (e.g., called from sync Celery context)

    async def _persist_to_db(
        self,
        model_name: str,
        tier: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        cached: bool,
        node_name: Optional[str],
    ) -> None:
        """Fire-and-forget DB persistence of one LLM call to llm_usage table."""
        try:
            from app.core.database import AsyncSessionLocal
            from app.repositories.llm_usage_repo import LlmUsageRepository
            async with AsyncSessionLocal() as db:
                repo = LlmUsageRepository(db)
                await repo.record(
                    crawl_id=self._crawl_id,
                    user_id=self._user_id,
                    model_name=model_name,
                    tier=tier,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost_usd,
                    cached=cached,
                    node_name=node_name,
                )
        except Exception as e:
            logger.debug(f"LLMCostManager: DB persistence failed (non-fatal): {e}")

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


def make_cost_manager(
    crawl_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> LLMCostManager:
    """Creates a new ``LLMCostManager`` pre-configured from global settings.

    Parameters
    ----------
    crawl_id : str, optional
        CrawlSession UUID. When provided, each ``record_usage()`` call also
        persists a row to the ``llm_usage`` table for the ``/costs`` endpoint.
    user_id : str, optional
        User UUID for tenant scoping in ``llm_usage`` rows.
    """
    return LLMCostManager(
        token_budget=settings.LLM_TOKEN_BUDGET_PER_CRAWL,
        planner_max_calls=settings.LLM_PLANNER_MAX_CALLS,
        crawl_id=crawl_id,
        user_id=user_id,
    )
