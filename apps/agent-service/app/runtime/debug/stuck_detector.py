"""
runtime/debug/stuck_detector.py — Autonomous Stuck & No-Progress Detection Engine.

Detects repetitive action loops, static DOM state cycles, zero-information-gain runs,
and recommends bounded self-healing recovery actions (AGENTS.md §24, Debug Prompt §18, §19).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.runtime.debug.models import StuckDetectionTrace


class StuckDetector:
    """
    Monitors agent execution cycles to detect stalls, infinite loops, and repetitive actions.
    """

    def __init__(self, repeat_threshold: int = 3, no_progress_threshold: int = 4) -> None:
        self.repeat_threshold = repeat_threshold
        self.no_progress_threshold = no_progress_threshold
        self._action_history: Dict[str, List[Dict[str, Any]]] = {}  # session_id -> list of actions
        self._state_hashes: Dict[str, List[str]] = {}               # session_id -> list of hashes
        self._progress_history: Dict[str, List[int]] = {}           # session_id -> list of observation counts

    def record_step(
        self,
        session_id: str,
        action_type: str,
        target: str,
        state_hash: Optional[str] = None,
        new_observations_count: int = 0,
    ) -> StuckDetectionTrace:
        """
        Record an action step and evaluate whether the investigation is stuck.
        """
        # Track action
        actions = self._action_history.setdefault(session_id, [])
        actions.append({"action_type": action_type, "target": target})

        # Track state hash
        if state_hash:
            hashes = self._state_hashes.setdefault(session_id, [])
            hashes.append(state_hash)

        # Track progress
        progress = self._progress_history.setdefault(session_id, [])
        progress.append(new_observations_count)

        # ── 1. Check Repeated Action Loop ─────────────────────────────────────
        if len(actions) >= self.repeat_threshold:
            last_n_actions = actions[-self.repeat_threshold:]
            first_action = last_n_actions[0]
            if all(a["action_type"] == first_action["action_type"] and a["target"] == first_action["target"] for a in last_n_actions):
                return StuckDetectionTrace(
                    session_id=session_id,
                    is_stuck=True,
                    stuck_reason=f"Repeated identical action '{first_action['action_type']}' on '{first_action['target']}' {self.repeat_threshold} times consecutively.",
                    repeated_action_types=[a["action_type"] for a in last_n_actions],
                    suggested_recoveries=[
                        "Refresh page and re-read accessibility tree (AXTree)",
                        "Select alternative candidate action from planner queue",
                        "Switch to static DOM script extraction fallback",
                    ],
                )

        # ── 2. Check Static DOM State Cycle ───────────────────────────────────
        hashes = self._state_hashes.get(session_id, [])
        if len(hashes) >= self.repeat_threshold:
            last_n_hashes = hashes[-self.repeat_threshold:]
            if len(set(last_n_hashes)) == 1 and sum(progress[-self.repeat_threshold:]) == 0:
                return StuckDetectionTrace(
                    session_id=session_id,
                    is_stuck=True,
                    stuck_reason=f"DOM state hash '{last_n_hashes[0]}' unchanged over {self.repeat_threshold} actions with 0 new observations.",
                    repeated_state_hashes=last_n_hashes,
                    suggested_recoveries=[
                        "Scroll container or dismiss overlay blocking interactive elements",
                        "Execute virtual navigation to parent breadcrumb URL",
                        "Trigger hypothesis verification for already observed endpoints",
                    ],
                )

        # ── 3. Check No-Progress Horizon ──────────────────────────────────────
        if len(progress) >= self.no_progress_threshold:
            last_n_progress = progress[-self.no_progress_threshold:]
            if sum(last_n_progress) == 0:
                return StuckDetectionTrace(
                    session_id=session_id,
                    is_stuck=True,
                    stuck_reason=f"No new endpoints or observations discovered over last {self.no_progress_threshold} steps.",
                    steps_without_progress=self.no_progress_threshold,
                    suggested_recoveries=[
                        "Broaden planner search scope to unvisited links",
                        "Verify pending behavioral hypotheses",
                        "Gracefully complete investigation session with current findings",
                    ],
                )

        return StuckDetectionTrace(
            session_id=session_id,
            is_stuck=False,
            stuck_reason="Investigation progressing normally.",
        )

    def clear(self, session_id: Optional[str] = None) -> None:
        """Reset stuck detector tracking."""
        if session_id:
            self._action_history.pop(session_id, None)
            self._state_hashes.pop(session_id, None)
            self._progress_history.pop(session_id, None)
        else:
            self._action_history.clear()
            self._state_hashes.clear()
            self._progress_history.clear()


# Global stuck detector singleton
stuck_detector = StuckDetector()
