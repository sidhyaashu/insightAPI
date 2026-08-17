import json
import hashlib
from typing import Dict, Any, Optional, List
from app.agents.state import CrawlState
from app.engine.network.deduplicator import DOMStateHasher, RouteClusterTracker
from app.core.compliance import RobotsChecker
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("agent.planner")


# ---------------------------------------------------------------------------
# LLM Planner Strategy
# ---------------------------------------------------------------------------

class LLMPlannerStrategy:
    """
    Uses an LLM to intelligently select the next UI action based on:
    - Current page interactive elements (selector, tag, text, role)
    - Already-discovered endpoint categories (coverage gap awareness)
    - Remaining page budget
    - Optional crawl goal supplied by the user

    Falls back to heuristic scoring when:
    - ``settings.LLM_PLANNER_ENABLED`` is False
    - Token budget or planner call limit is exhausted
    - LLM call raises an exception
    """

    @staticmethod
    def _build_elements_summary(elements: List[Dict[str, Any]], max_elements: int = 25) -> str:
        """Compact element list for the LLM prompt (avoids huge prompts)."""
        rows = []
        for i, el in enumerate(elements[:max_elements]):
            tag = el.get("tag", "")
            role = el.get("role", "")
            text = (el.get("text") or el.get("ariaLabel") or el.get("placeholder") or "").strip()[:50]
            sel = (el.get("selector") or "")[:60]
            rows.append(f"  [{i}] {tag}/{role} | text='{text}' | selector='{sel}'")
        if len(elements) > max_elements:
            rows.append(f"  ... and {len(elements) - max_elements} more elements")
        return "\n".join(rows)

    @classmethod
    async def select_action(
        cls,
        state: CrawlState,
        frontier: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Asks the LLM to select the best frontier item for maximum API discovery.

        Returns
        -------
        The selected frontier item dict (with keys: element, selector_key, score, source_url),
        or ``None`` if the LLM cannot be used (triggers heuristic fallback in PlannerNode).
        """
        # Guard: feature flag
        if not settings.LLM_PLANNER_ENABLED:
            return None

        # Guard: cost manager budget
        cost_manager = state.get("cost_manager")
        if cost_manager is None:
            from app.agents.nodes.llm_client import make_cost_manager
            cost_manager = make_cost_manager(
                crawl_id=state.get("crawl_id") or "fallback",
                user_id=state.get("user_id"),
            )
            state["cost_manager"] = cost_manager

        if cost_manager.is_budget_exhausted() or cost_manager.is_planner_budget_exhausted():
            logger.info("Planner budget exhausted or overall budget exhausted. Falling back to heuristic planner.")
            return None

        if not frontier:
            return None

        # Build compact prompt — cap frontier at top 15 candidates to bound token usage
        top_candidates = frontier[:15]
        candidate_lines = []
        for i, item in enumerate(top_candidates):
            el = item["element"]
            tag = el.get("tag", "")
            role = el.get("role", "")
            text = (el.get("text") or el.get("ariaLabel") or "").strip()[:50]
            sel = (el.get("selector") or "")[:60]
            candidate_lines.append(f"  [{i}] {tag}/{role} | text='{text}' | selector='{sel}'")

        categories = state.get("endpoint_categories") or []
        goal = state.get("goal") or "Discover all API endpoints used by this web application"
        explored = state.get("explored_count", 0)
        max_pages = state.get("max_pages", 10)
        current_url = state.get("current_url", "")
        endpoint_count = len(state.get("captured_endpoints") or [])

        # Get anti-loop / stagnation warning instructions if zero-yield streak active
        from app.engine.browser.stagnation_detector import StagnationDetector
        anti_loop_text = StagnationDetector.get_anti_loop_guidance(state)

        prompt = (
            f"You are an API discovery agent exploring a web application.\n\n"
            f"PRIMARY GOAL: {goal}\n\n"
            + (f"{anti_loop_text}\n\n" if anti_loop_text else "") +
            f"Current state:\n"
            f"  - Current URL: {current_url}\n"
            f"  - Pages explored: {explored}/{max_pages}\n"
            f"  - API endpoints captured so far: {endpoint_count}\n"
            f"  - Endpoint categories already discovered: {categories or ['none yet']}\n\n"
            f"Candidate UI elements to interact with next:\n"
            + "\n".join(candidate_lines)
            + "\n\n"
            "Which candidate (by index) should I interact with to discover the MOST NEW and UNEXPLORED "
            "API endpoints? Prefer: search/filter inputs, navigation to unexplored sections, "
            "form submissions that likely trigger backend calls.\n"
            "Avoid: elements in already-explored API categories, repeating zero-yield clicks, pagination if we have enough data.\n\n"
            'Respond ONLY with valid JSON: {"index": <int>, "reason": "<short explanation>"}'
        )

        # Cache check — avoid re-calling for identical page + frontier states
        prompt_cache_key = hashlib.md5(prompt.encode()).hexdigest()
        if cost_manager:
            cached = cost_manager.get_cached(prompt_cache_key)
            if cached:
                try:
                    result = json.loads(cached)
                    idx = int(result.get("index", 0))
                    if 0 <= idx < len(top_candidates):
                        return top_candidates[idx]
                except Exception:
                    pass

        # LLM call
        try:
            from app.agents.nodes.llm_client import get_llm, ModelTier, ModelRouter, extract_text_content, repair_json_string
            # Use FAST model for routine planner decisions
            llm = get_llm(ModelTier.FAST)
            response = await llm.ainvoke(prompt)
            response_text = extract_text_content(response)

            # Estimate tokens (rough: 1 token ≈ 4 chars)
            tokens_est = (len(prompt) + len(response_text)) // 4
            if cost_manager:
                model_name = ModelRouter.get_model_name(ModelTier.FAST)
                cost_manager.record_usage(tokens_est, model_name, is_planner_call=True)
                cost_manager.put_cache(prompt_cache_key, response_text, tokens_est)

            # Parse response
            clean = repair_json_string(response_text)
            result = json.loads(clean)
            idx = int(result.get("index", 0))
            reason = result.get("reason", "")

            if 0 <= idx < len(top_candidates):
                selected = top_candidates[idx]
                planner_call_count = (state.get("llm_planner_call_count") or 0) + 1
                state["llm_planner_call_count"] = planner_call_count
                state["planner_reasoning"] = reason
                logger.info(
                    f"🤖 LLM Planner selected [{idx}] | "
                    f"reason='{reason[:80]}' | "
                    f"calls={planner_call_count}"
                )
                return selected

        except Exception as e:
            logger.warning(f"LLM Planner call failed ({type(e).__name__}: {e}). Using heuristic fallback.")

        return None


# ---------------------------------------------------------------------------
# PlannerNode
# ---------------------------------------------------------------------------

class PlannerNode:
    """
    Analyzes interactive DOM snapshots and crawl history using a Priority Queue Frontier.

    Selection strategy (in order of preference)
    --------------------------------------------
    1. LLMPlannerStrategy  — LLM reasons about coverage gaps and goal alignment.
    2. Heuristic scoring   — Original score_element() function used as fallback
                             when LLM is disabled, budget exhausted, or call fails.

    Both paths enforce robots.txt compliance and route cluster pruning.
    """
    @staticmethod
    def compute_dom_hash(url: str, elements: list) -> str:
        """Computes a deterministic hash of current URL + structural AXTree interactive elements."""
        return DOMStateHasher.compute_state_hash(url, elements)

    @staticmethod
    def score_element(el: Dict[str, Any], deprioritized_selectors: Optional[List[str]] = None) -> float:
        """
        Calculates a priority score for a candidate action element.
        - High API yield (forms, inputs, selects, search/submit buttons): +10 to +15
        - Role & Tag novelty: +5 to +10
        - Deprioritized modal targets: -50.0 (Fixes modal trap loops)
        """
        score = 1.0
        tag = (el.get("tag") or "").lower()
        role = (el.get("role") or "").lower()
        text = (el.get("text") or el.get("ariaLabel") or "").lower()
        selector = (el.get("selector") or "").lower()
        parent_text = (el.get("parent_text") or "").lower()
        form_context = (el.get("form_context") or "").lower()

        # Modal trap deprioritization penalty
        if deprioritized_selectors:
            for dep in deprioritized_selectors:
                dep_lower = dep.lower()
                if dep_lower and (dep_lower in selector or dep_lower in parent_text or dep_lower in form_context):
                    score -= 50.0
                    break

        # Form controls (High API yield)
        if tag in ["input", "textarea", "select"]:
            score += 10.0
        
        # Search & submit actions (Very High API yield)
        if any(kw in text for kw in ["search", "filter", "submit", "apply", "find", "query"]):
            score += 15.0
            
        # Role-based scoring
        if role in ["searchbox", "combobox"]:
            score += 15.0
        elif role in ["button", "tab"]:
            score += 8.0
        elif role == "link" or tag == "a":
            score += 3.0

        return score

    @classmethod
    async def process(cls, state: CrawlState) -> CrawlState:
        """LangGraph node execution function using LLM selection + Priority Queue Frontier fallback."""
        explored_count = state.get("explored_count", 0)
        max_pages = state.get("max_pages", 10)
        interactive_elements = state.get("interactive_elements", [])
        current_url = state.get("current_url", "")
        visited_selectors = state.get("visited_selectors", [])
        frontier: List[Dict[str, Any]] = state.get("frontier") or []
        deprioritized_selectors = state.get("deprioritized_modal_selectors") or []

        # Check termination limits
        if explored_count >= max_pages:
            logger.info(f"Crawl limit reached ({explored_count}/{max_pages} pages). Terminating crawl graph.")
            state["is_complete"] = True
            state["next_action"] = None
            return state

        # Compute current DOM state hash and register visit
        current_hash = cls.compute_dom_hash(current_url, interactive_elements)
        RouteClusterTracker.register_route_visit(current_url, current_hash)
        logger.debug(f"Computed DOM state hash for '{current_url}': {current_hash[:8]}")

        # Enqueue new unvisited candidate elements from current page into the Priority Frontier
        existing_selectors = {entry["selector_key"] for entry in frontier}
        added_to_frontier = 0

        for el in interactive_elements:
            selector = el.get("selector")
            if not selector:
                continue
            selector_key = f"{current_url}::{selector}"

            if selector_key in visited_selectors or selector_key in existing_selectors:
                continue

            target_href = el.get("href") or el.get("url")
            if target_href:
                if RouteClusterTracker.should_prune_route(target_href):
                    logger.debug(f"Pruning saturated route cluster candidate: {target_href}")
                    continue
                if settings.RESPECT_ROBOTS_TXT and not RobotsChecker.is_allowed(target_href):
                    logger.info(f"Robots.txt disallow rule matched for candidate URL: {target_href}")
                    continue

            score = cls.score_element(el, deprioritized_selectors)
            frontier.append({
                "source_url": current_url,
                "selector_key": selector_key,
                "element": el,
                "score": score
            })
            existing_selectors.add(selector_key)
            added_to_frontier += 1

        # Re-score existing elements in frontier if deprioritized_selectors active
        if deprioritized_selectors:
            for item in frontier:
                item["score"] = cls.score_element(item["element"], deprioritized_selectors)

        logger.info(f"Planner discovered {added_to_frontier} new candidate actions on page. Frontier queue size: {len(frontier)}")

        if not frontier:
            logger.info("Frontier queue empty. No remaining unexplored interactive elements found. Terminating crawl.")
            state["is_complete"] = True
            state["next_action"] = None
            return state

        # ── Selection: LLM first, heuristic fallback ──────────────────────────
        top_item = None

        llm_selected = await LLMPlannerStrategy.select_action(state, frontier)
        if llm_selected is not None:
            # Remove the LLM-selected item from the frontier list
            try:
                frontier.remove(llm_selected)
            except ValueError:
                pass
            top_item = llm_selected
        else:
            # Heuristic: sort frontier by score descending, pop highest
            frontier.sort(key=lambda item: item["score"], reverse=True)
            top_item = frontier.pop(0)
            state["planner_reasoning"] = f"[Heuristic] score={top_item['score']}"

        selected_action = top_item["element"]
        selector_key = top_item["selector_key"]
        score = top_item["score"]

        if selector_key not in state.get("visited_selectors", []):
            state["visited_selectors"].append(selector_key)

        state["next_action"] = selected_action
        state["visited_state_hashes"].append(current_hash)
        state["frontier"] = frontier

        tag_info = selected_action.get("tag") or selected_action.get("role")
        logger.info(
            f"🎯 Selected Next Action (Score {score}): "
            f"[{tag_info}] selector=`{selected_action.get('selector')}` "
            f"text='{selected_action.get('text', '')[:30]}'"
        )

        return state



class PlannerNode:
    """
    Analyzes interactive DOM snapshots and crawl history using a Priority Queue Frontier.
    Scores candidate elements by estimated API yield, enforces robots.txt compliance,
    and prunes redundant route clusters.
    """
    @staticmethod
    def compute_dom_hash(url: str, elements: list) -> str:
        """Computes a deterministic hash of current URL + structural AXTree interactive elements."""
        return DOMStateHasher.compute_state_hash(url, elements)

    @staticmethod
    def score_element(el: Dict[str, Any], deprioritized_selectors: Optional[List[str]] = None) -> float:
        """
        Calculates a priority score for a candidate action element.
        - High API yield (forms, inputs, selects, search/submit buttons): +10 to +15
        - Role & Tag novelty: +5 to +10
        - Deprioritized modal targets: -50.0 (Fixes modal trap loops)
        """
        score = 1.0
        tag = (el.get("tag") or "").lower()
        role = (el.get("role") or "").lower()
        text = (el.get("text") or el.get("ariaLabel") or "").lower()
        selector = (el.get("selector") or "").lower()
        parent_text = (el.get("parent_text") or "").lower()
        form_context = (el.get("form_context") or "").lower()

        # Modal trap deprioritization penalty
        if deprioritized_selectors:
            for dep in deprioritized_selectors:
                dep_lower = dep.lower()
                if dep_lower and (dep_lower in selector or dep_lower in parent_text or dep_lower in form_context):
                    score -= 50.0
                    break

        # Form controls (High API yield)
        if tag in ["input", "textarea", "select"]:
            score += 10.0
        
        # Search & submit actions (Very High API yield)
        if any(kw in text for kw in ["search", "filter", "submit", "apply", "find", "query"]):
            score += 15.0
            
        # Role-based scoring
        if role in ["searchbox", "combobox"]:
            score += 15.0
        elif role in ["button", "tab"]:
            score += 8.0
        elif role == "link" or tag == "a":
            score += 3.0

        return score

    @classmethod
    async def process(cls, state: CrawlState) -> CrawlState:
        """LangGraph node execution function using Priority Queue Frontier graph search."""
        explored_count = state.get("explored_count", 0)
        max_pages = state.get("max_pages", 10)
        interactive_elements = state.get("interactive_elements", [])
        current_url = state.get("current_url", "")
        visited_selectors = state.get("visited_selectors", [])
        frontier: List[Dict[str, Any]] = state.get("frontier") or []
        deprioritized_selectors = state.get("deprioritized_modal_selectors") or []

        # Check termination limits
        if explored_count >= max_pages:
            logger.info(f"Crawl limit reached ({explored_count}/{max_pages} pages). Terminating crawl graph.")
            state["is_complete"] = True
            state["next_action"] = None
            return state

        # Compute current DOM state hash and register visit
        current_hash = cls.compute_dom_hash(current_url, interactive_elements)
        RouteClusterTracker.register_route_visit(current_url, current_hash)
        logger.debug(f"Computed DOM state hash for '{current_url}': {current_hash[:8]}")

        # Enqueue new unvisited candidate elements from current page into the Priority Frontier
        existing_selectors = {entry["selector_key"] for entry in frontier}
        added_to_frontier = 0

        for el in interactive_elements:
            selector = el.get("selector")
            if not selector:
                continue
            selector_key = f"{current_url}::{selector}"

            if selector_key in visited_selectors or selector_key in existing_selectors:
                continue

            target_href = el.get("href") or el.get("url")
            if target_href:
                if RouteClusterTracker.should_prune_route(target_href):
                    logger.debug(f"Pruning saturated route cluster candidate: {target_href}")
                    continue
                if settings.RESPECT_ROBOTS_TXT and not RobotsChecker.is_allowed(target_href):
                    logger.info(f"Robots.txt disallow rule matched for candidate URL: {target_href}")
                    continue

            score = cls.score_element(el, deprioritized_selectors)
            frontier.append({
                "source_url": current_url,
                "selector_key": selector_key,
                "element": el,
                "score": score
            })
            existing_selectors.add(selector_key)
            added_to_frontier += 1

        # Re-score existing elements in frontier if deprioritized_selectors active
        if deprioritized_selectors:
            for item in frontier:
                item["score"] = cls.score_element(item["element"], deprioritized_selectors)

        logger.info(f"Planner discovered {added_to_frontier} new candidate actions on page. Frontier queue size: {len(frontier)}")

        # Sort frontier queue by priority score descending
        frontier.sort(key=lambda item: item["score"], reverse=True)

        if frontier:
            top_item = frontier.pop(0)
            selected_action = top_item["element"]
            selector_key = top_item["selector_key"]
            score = top_item["score"]

            if selector_key not in state.get("visited_selectors", []):
                state["visited_selectors"].append(selector_key)

            state["next_action"] = selected_action
            state["visited_state_hashes"].append(current_hash)
            state["frontier"] = frontier

            tag_info = selected_action.get("tag") or selected_action.get("role")
            logger.info(f"🎯 Selected Next Action (Score {score}): [{tag_info}] selector=`{selected_action.get('selector')}` text='{selected_action.get('text', '')[:30]}'")
        else:
            # Check if Vision LLM fallback can explore canvas / graphical UI before terminating
            page = state.get("page_ref")
            needs_vision = state.get("needs_vision_fallback", False)
            if not needs_vision and page:
                from app.engine.browser.dom_distiller import DOMDistiller
                if await DOMDistiller.has_canvas_element(page):
                    needs_vision = True
                    state["needs_vision_fallback"] = True

            if needs_vision and page and getattr(settings, "LLM_VISION_FALLBACK_ENABLED", True):
                logger.info("👁️ Frontier queue empty on Canvas page. Triggering VisionPlannerNode fallback...")
                from app.agents.nodes.vision_planner import VisionPlannerNode
                vision_action = await VisionPlannerNode.select_action(state)
                if vision_action:
                    state["next_action"] = vision_action
                    state["planner_reasoning"] = vision_action.get("reasoning", "Vision LLM Set-of-Mark selection")
                    state["visited_state_hashes"].append(current_hash)
                    return state

            logger.info("Frontier queue empty. No remaining unexplored interactive elements found. Terminating crawl.")
            state["is_complete"] = True
            state["next_action"] = None

        return state
