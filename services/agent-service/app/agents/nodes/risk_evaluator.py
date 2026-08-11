import re
from typing import Dict, Any, Tuple, Optional
from app.agents.state import CrawlState
from app.core.logging_config import get_logger, log_risk_event

logger = get_logger("agent.risk_evaluator")

# High-confidence regex patterns for Tier-1 Fast Guardrail
UNSAFE_PATTERNS = [
    r"\b(delete|remove|destroy|drop|wipe|purge|clear\s+db)\b",
    r"\b(pay|checkout|purchase|buy|subscribe|billing|invoice|credit\s*card)\b",
    r"\b(cancel\s+sub|reset\s+pass|update\s+pass|password|passcode|change\s+email)\b",
    r"\b(revoke|grant\s+admin|modify\s+perm|sudo|root)\b"
]

SAFE_PATTERNS = [
    r"\b(next|prev|previous|page|pagination|tab|filter|sort)\b",
    r"\b(view|details|show|expand|collapse|open|close|modal)\b",
    r"\b(search|find|query|explore|home|menu|nav|link)\b"
]


class RiskEvaluatorNode:
    """
    Two-Tier Action Risk Classifier:
    - Tier 1: Fast deterministic regex guardrails (<1ms, zero cost).
    - Tier 2: Context-enriched form & ancestor DOM evaluation fallback for ambiguous targets (e.g. 'Submit').
    """
    _decision_cache: Dict[str, Tuple[bool, str]] = {}

    @classmethod
    def clear_cache(cls):
        """Resets the decision cache."""
        cls._decision_cache.clear()

    @classmethod
    def evaluate_tier_1(cls, combined_text: str) -> Optional[Tuple[bool, str]]:
        """
        Tier 1 fast guardrail evaluation.
        Returns (is_safe, reason) if deterministically matched, else None.
        """
        # Check high-risk destructive patterns
        for pattern in UNSAFE_PATTERNS:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                return False, f"[Tier-1 Guardrail] Unsafe action matches high-risk pattern: '{match.group(0)}'"

        # Check high-confidence safe patterns
        for pattern in SAFE_PATTERNS:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                return True, f"[Tier-1 Guardrail] Safe navigation action matches pattern: '{match.group(0)}'"

        return None

    @classmethod
    def evaluate_tier_2_context(
        cls,
        action: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Tier 2 contextual evaluation for ambiguous targets (e.g., generic 'Submit', 'Save' buttons).
        Inspects parent form fields, ancestor titles, and surrounding DOM context.
        """
        form_context = ((action.get("form_context") or "") + " " + (action.get("parent_text") or "")).lower()
        page_title = ((context.get("page_title") if context else "") or "").lower()
        combined_context = f"{form_context} {page_title}"

        # Contextual threat check
        for pattern in UNSAFE_PATTERNS:
            match = re.search(pattern, combined_context, re.IGNORECASE)
            if match:
                return False, f"[Tier-2 Context] Ambiguous action '{action.get('text')}' is inside a high-risk form/context: '{match.group(0)}'"

        return True, f"[Tier-2 Context] Action '{action.get('text')}' evaluated as safe read-only/navigation target."

    @classmethod
    def evaluate_action_risk(
        cls,
        action: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates element risk safety using the two-tier evaluation architecture with caching.
        Returns (is_safe: bool, reason: str).
        """
        if not action:
            return True, "No action target specified."

        text = (action.get("text") or "").strip()
        aria_label = (action.get("ariaLabel") or "").strip()
        selector = (action.get("selector") or "").strip()
        tag = (action.get("tag") or "").strip()
        combined_str = f"{text} {aria_label} {selector} {tag}".lower()

        # Cache Lookup
        cache_key = f"{selector}:{combined_str}"
        if cache_key in cls._decision_cache:
            is_safe, reason = cls._decision_cache[cache_key]
            log_risk_event(logger, "CACHE", "SAFE" if is_safe else "UNSAFE", selector, f"[Cache Hit] {reason}")
            return is_safe, f"[Cache Hit] {reason}"

        # Tier 1 Evaluation
        tier1_result = cls.evaluate_tier_1(combined_str)
        if tier1_result is not None:
            cls._decision_cache[cache_key] = tier1_result
            is_safe, reason = tier1_result
            log_risk_event(logger, "Tier-1 Regex", "SAFE" if is_safe else "UNSAFE", selector, reason)
            return tier1_result

        # Tier 2 Evaluation (Ambiguous Cases)
        tier2_result = cls.evaluate_tier_2_context(action, context)
        cls._decision_cache[cache_key] = tier2_result
        is_safe, reason = tier2_result
        log_risk_event(logger, "Tier-2 Context", "SAFE" if is_safe else "UNSAFE", selector, reason)
        return tier2_result

    @classmethod
    async def process(cls, state: CrawlState) -> CrawlState:
        """LangGraph node execution function."""
        next_action = state.get("next_action")
        context = {
            "current_url": state.get("current_url", ""),
            "page_title": state.get("page_title", "") if "page_title" in state else ""
        }
        is_safe, reason = cls.evaluate_action_risk(next_action, context)

        state["is_safe_action"] = is_safe
        state["risk_reason"] = reason

        if not is_safe:
            logger.warning(f"🚫 Unsafe action detected and bypassed: selector=`{next_action.get('selector')}` | Reason: {reason}")
        return state
