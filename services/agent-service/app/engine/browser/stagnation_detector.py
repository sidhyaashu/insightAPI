"""
stagnation_detector.py — Loop Breaker & Anti-Stuck Intelligence Module

Design
------
Prevents the autonomous agent from getting trapped in infinite loops, repeated tab toggles,
or zero-yield button cycles.

Key capabilities
----------------
1. Zero-Yield Action Tracker: Monitors consecutive actions yielding 0 new API endpoints.
2. State Oscillation Detection: Identifies back-and-forth state traps (State A -> State B -> State A -> State B).
3. Container Deprioritization: Automatically flags stagnation containers so Planner avoids them.
4. Anti-Loop Prompt Guidance: Injects past stagnation notes into LLM Planner prompt.
5. Force Un-stuck Recovery: Presses Escape, clears overlays, or force-closes stuck popups when streak threshold hit.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from app.agents.state import CrawlState

logger = logging.getLogger("engine.stagnation_detector")


class StagnationDetector:
    """
    Guarantees the agent never stays stuck in infinite action loops or unproductive UI traps.
    """
    ZERO_YIELD_STREAK_THRESHOLD = 3  # After 3 consecutive zero-yield actions, trigger un-stuck mode
    MAX_ZERO_YIELD_ABORT = 6         # After 6 consecutive zero-yield actions across all paths, end crawl cleanly

    @classmethod
    def record_action_yield(
        cls,
        state: CrawlState,
        endpoints_before: int,
        endpoints_after: int,
        current_hash: str,
    ) -> CrawlState:
        """
        Updates stagnation trackers in CrawlState after each executor action.
        """
        new_count = max(0, endpoints_after - endpoints_before)
        streak = state.get("zero_yield_streak", 0)

        if new_count == 0:
            streak += 1
            logger.info(f"⚠️ Zero-yield action recorded (Streak: {streak}/{cls.ZERO_YIELD_STREAK_THRESHOLD})")
        else:
            streak = 0
            logger.info(f"✨ API yield recorded! Captured {new_count} new endpoint(s). Reset zero-yield streak.")

        state["zero_yield_streak"] = streak

        # Detect oscillation (State A -> State B -> State A -> State B)
        hash_history = state.get("visited_state_hashes") or []
        if len(hash_history) >= 4:
            h1, h2, h3, h4 = hash_history[-4:]
            if h1 == h3 and h2 == h4 and h1 != h2:
                logger.warning(f"🔄 State Oscillation Detected ({h1[:6]} <-> {h2[:6]})! Deprioritizing current section.")
                cls.deprioritize_current_action(state)

        # If zero-yield streak hits threshold, deprioritize current selector container
        if streak >= cls.ZERO_YIELD_STREAK_THRESHOLD:
            cls.deprioritize_current_action(state)

        # If maximum zero-yield limit reached across entire graph, mark crawl complete gracefully
        if streak >= cls.MAX_ZERO_YIELD_ABORT:
            logger.warning(f"🛑 Maximum zero-yield streak ({streak}) reached across all candidate actions. Terminating crawl graph cleanly.")
            state["is_complete"] = True

        return state

    @classmethod
    def deprioritize_current_action(cls, state: CrawlState) -> None:
        """
        Extracts container/selector context from next_action and adds to deprioritized selectors.
        """
        next_action = state.get("next_action") or {}
        selector = next_action.get("selector", "")
        parent_text = next_action.get("parent_text", "")

        deprioritized = state.get("deprioritized_modal_selectors") or []
        if selector and selector not in deprioritized:
            deprioritized.append(selector)
        if parent_text and parent_text[:30] not in deprioritized:
            deprioritized.append(parent_text[:30])

        state["deprioritized_modal_selectors"] = deprioritized

    @classmethod
    def get_anti_loop_guidance(cls, state: CrawlState) -> str:
        """
        Generates prompt instructions for the LLM Planner when stagnation is detected.
        """
        streak = state.get("zero_yield_streak", 0)
        deprioritized = state.get("deprioritized_modal_selectors") or []

        if streak == 0 and not deprioritized:
            return ""

        notes = []
        if streak >= 2:
            notes.append(
                f"STAGNATION WARNING: The last {streak} actions produced 0 new API endpoints. "
                "DO NOT repeat similar buttons, filters, or tabs. Select a COMPLETELY DIFFERENT functional section."
            )
        if deprioritized:
            notes.append(f"DEPRIORITIZED SECTIONS TO AVOID: {deprioritized[:5]}")

        return "\n".join(notes)

    @classmethod
    async def force_unstick(cls, page: Any) -> None:
        """
        Executes escape procedures when stuck: presses Escape key, removes open modal overlays.
        """
        if not page:
            return
        logger.info("🛠️ Running Force Un-stuck Recovery: Pressing Escape and clearing active overlays.")
        try:
            if hasattr(page, "keyboard"):
                await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
            if hasattr(page, "evaluate"):
                await page.evaluate("""
                () => {
                    const overlays = document.querySelectorAll('.modal, dialog, [role="dialog"], .modal-backdrop, .overlay, .popup');
                    overlays.forEach(el => el.remove());
                }
                """)
        except Exception as e:
            logger.debug(f"Force unstick error: {e}")
