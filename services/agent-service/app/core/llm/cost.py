"""
cost.py — Token pricing table, cost estimation, and LLMCostManager budget tracking.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("agent.llm_cost")

# ---------------------------------------------------------------------------
# Approximate token pricing (USD per 1k tokens)
# ---------------------------------------------------------------------------

PRICE_PER_1K_TOKENS: Dict[str, float] = {
    # Google Gemini
    "gemini-3.7-flash": 0.000150,
    "gemini-3.6-flash": 0.000100,
    "gemini-2.5-flash": 0.000100,
    "gemini-2.5-pro": 0.001250,
    "gemini-1.5-pro": 0.001250,
    "gemini-1.5-flash": 0.000075,
    # Azure AI Foundry / OpenAI
    "gpt-4.1-mini": 0.000150,
    "gpt-4.1": 0.003000,
    "gpt-4o-mini": 0.000150,
    "gpt-4o": 0.005000,
    "o3-mini": 0.001100,
    "o1-mini": 0.003000,
    "o1": 0.015000,
    # Anthropic Claude
    "claude-3-7-sonnet": 0.003000,
    "claude-3-5-sonnet": 0.003000,
    "claude-3-5-haiku": 0.000800,
    "claude-3-opus": 0.015000,
    # DeepSeek & Local/Ollama
    "deepseek-r1": 0.000550,
    "deepseek-v3": 0.000140,
    "llama": 0.000000,
    "ollama": 0.000000,
    "local": 0.000000,
    "default": 0.000200,
}


def get_model_price_per_1k(model_name: str) -> float:
    """Returns USD cost per 1,000 tokens for the given model name."""
    if not model_name:
        return PRICE_PER_1K_TOKENS["default"]
    name_lower = model_name.lower()
    for k, v in PRICE_PER_1K_TOKENS.items():
        if k in name_lower:
            return v
    return PRICE_PER_1K_TOKENS["default"]


class LLMCostManager:
    """
    Per-session token budget tracker with response caching and UI-facing metrics.

    Usage
    -----
    Each crawl session creates one ``LLMCostManager`` instance and passes it
    through ``CrawlState``. All agent nodes call ``record_usage()`` after
    each LLM invocation. ``is_budget_exhausted()`` is checked before
    making a new LLM call — if True the caller falls back to heuristics.
    """

    _REDIS_CACHE_TTL = 86400  # 24 hours
    _REDIS_CACHE_PREFIX = "insightapi:llm_cache:"

    def __init__(
        self,
        token_budget: int = 0,       # 0 = unlimited
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

    def is_budget_exhausted(self) -> bool:
        """True if token budget is set and already consumed."""
        if self._token_budget > 0 and self._tokens_used >= self._token_budget:
            logger.warning(
                f"LLMCostManager: Token budget exhausted "
                f"({self._tokens_used}/{self._token_budget}). Falling back to heuristics."
            )
            return True
        return False

    def is_planner_budget_exhausted(self) -> bool:
        """True if planner call limit is set and reached."""
        if self._planner_max_calls > 0 and self._planner_calls_made >= self._planner_max_calls:
            logger.info(
                f"LLMCostManager: Planner call limit reached "
                f"({self._planner_calls_made}/{self._planner_max_calls}). Switching to heuristic scoring."
            )
            return True
        return False

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
        """
        try:
            from app.core.redis import get_redis_client
            redis = await get_redis_client()
            key = self._REDIS_CACHE_PREFIX + self._make_cache_key(prompt)
            cached = await redis.get(key)
            if cached:
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

    def record_usage(
        self,
        tokens_used: int,
        model_name: str,
        is_planner_call: bool = False,
        tier: str = "fast",
        node_name: Optional[str] = None,
        cached: bool = False,
    ) -> None:
        """Records token consumption after each LLM call."""
        self._tokens_used += tokens_used
        self._llm_calls_made += 1
        if is_planner_call:
            self._planner_calls_made += 1
        cost = (tokens_used / 1000.0) * get_model_price_per_1k(model_name)
        self._estimated_cost_usd += cost
        logger.debug(
            f"LLMCostManager: +{tokens_used} tokens | "
            f"total={self._tokens_used} | "
            f"calls={self._llm_calls_made} | "
            f"est. cost=${self._estimated_cost_usd:.4f}"
        )
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
                pass

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

    def get_metrics(self) -> Dict[str, Any]:
        """Returns a serialisable metrics dict for embedding in CrawlResult."""
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


def make_cost_manager(crawl_id: Optional[str] = None, user_id: Optional[str] = None) -> LLMCostManager:
    """Convenience factory creating an LLMCostManager using settings token budget and planner limits."""
    from app.core.config import settings
    token_budget = getattr(settings, "LLM_TOKEN_BUDGET_PER_CRAWL", 0) or 0
    planner_max = getattr(settings, "LLM_PLANNER_MAX_CALLS", 0) or 0
    return LLMCostManager(
        token_budget=token_budget,
        planner_max_calls=planner_max,
        crawl_id=crawl_id,
        user_id=user_id,
    )
