from typing import List, Dict, Any, Optional, TypedDict


class CrawlState(TypedDict):
    """
    Global TypedDict state container passed between LangGraph agent nodes.

    Intelligence-layer fields (Phase 1–3 additions)
    -----------------------------------------------
    goal                    : Optional natural-language crawl objective supplied by the
                              user (e.g. "Find all payment and billing APIs").  Injected
                              into LLM Planner + Reflection prompts to bias exploration.
    planner_reasoning       : Last explanation produced by the LLM Planner so the caller
                              (SDK / CLI / REST) can surface *why* each action was chosen.
    reflection_notes        : JSON string produced by the ReflectionNode every
                              LLM_REFLECTION_INTERVAL explored pages.
    endpoint_categories     : Running list of semantic category labels discovered so far
                              (e.g. ["User Management", "Product Catalog"]).  Used by
                              the LLM Planner to reason about coverage gaps.
    cost_manager            : LLMCostManager instance tracking per-session token spend,
                              cache hits, and UI-facing cost metrics.
    llm_planner_call_count  : How many times the LLM Planner has been invoked this
                              session — checked against LLM_PLANNER_MAX_CALLS budget.
    """
    # ── Core crawl fields (unchanged) ────────────────────────────────────────
    target_url: str
    current_url: str
    visited_urls: List[str]
    visited_state_hashes: List[str]
    visited_selectors: List[str]
    interactive_elements: List[Dict[str, Any]]
    captured_endpoints: List[Dict[str, Any]]
    next_action: Optional[Dict[str, Any]]
    is_safe_action: bool
    risk_reason: Optional[str]
    frontier: Optional[List[Dict[str, Any]]]
    explored_count: int
    max_pages: int
    is_complete: bool
    error_message: Optional[str]
    auth_required_url: Optional[str]
    modal_action_count: Optional[int]
    deprioritized_modal_selectors: Optional[List[str]]
    last_endpoint_count: Optional[int]
    network_observer: Optional[Any]
    page_ref: Optional[Any]
    rate_limit_ms: Optional[int]

    # ── Intelligence-layer fields (Phase 1–3) ────────────────────────────────
    goal: Optional[str]
    planner_reasoning: Optional[str]
    reflection_notes: Optional[str]
    endpoint_categories: Optional[List[str]]
    cost_manager: Optional[Any]          # LLMCostManager instance
    llm_planner_call_count: Optional[int]
    zero_yield_streak: Optional[int]     # Consecutive actions with 0 new API endpoints
    action_traces: Optional[List[Dict[str, Any]]]  # Ordered sequence of executed actions & triggered network calls
    needs_vision_fallback: Optional[bool]          # True when page has <canvas> and sparse/zero DOM interactive controls
    vision_action_count: Optional[int]             # Number of actions executed via Vision LLM coordinate fallback
    humanize_interactions: Optional[bool]          # Whether to use humanized Bezier mouse paths and typing jitter


