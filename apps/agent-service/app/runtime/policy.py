"""
runtime/policy.py — Formal Policy, Safety & Scope Enforcement Engine for InsightAPI.

Architecture (AGENTS.md §22, §23):
  - "Never allow the LLM to be the final authority on dangerous actions."
  - All actions pass through PolicyEngine before execution.
  - Policy decides: ALLOW, DENY, REQUIRE_APPROVAL, or DEFER.
  - Strict Scope Control: Enforces authorized domains, max budgets, and SSRF guardrails.
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple

from app.runtime.models import (
    Action,
    ActionType,
    AgentState,
    Goal,
    PolicyDecision,
    PolicyResult,
    RiskLevel,
)
from app.tools.guardrails import validate_target_url

DESTRUCTIVE_HTTP_METHODS = {"DELETE", "PUT", "PATCH"}
DESTRUCTIVE_PATH_KEYWORDS = {"delete", "remove", "destroy", "purge", "drop", "cancel", "terminate", "revoke"}
SENSITIVE_AUTH_KEYWORDS = {"login", "auth", "token", "password", "credential", "secret", "oauth"}


class PolicyEngine:
    """
    Authoritative policy evaluation and scope enforcement engine.
    """

    @staticmethod
    def classify_risk(action: Action) -> RiskLevel:
        """
        Classify the risk level of a requested Action.
        """
        # 1. Security testing actions
        if action.action_type == ActionType.SECURITY_AUDIT:
            return RiskLevel.SECURITY_TEST

        # 2. HTTP Probing / cURL / Replay
        if action.action_type in (ActionType.PROBE_HTTP, ActionType.EXECUTE_CURL, ActionType.REPLAY_REQUEST):
            method = (action.parameters.get("method") or "GET").upper().strip()
            target_url = (action.target or action.parameters.get("url") or "").lower()

            if method in DESTRUCTIVE_HTTP_METHODS:
                return RiskLevel.DESTRUCTIVE

            if method == "POST":
                if any(kw in target_url for kw in DESTRUCTIVE_PATH_KEYWORDS):
                    return RiskLevel.DESTRUCTIVE
                if any(kw in target_url for kw in SENSITIVE_AUTH_KEYWORDS):
                    return RiskLevel.AUTH_SENSITIVE
                return RiskLevel.MODIFYING

            if method in ("HEAD", "OPTIONS"):
                return RiskLevel.LOW_RISK

            return RiskLevel.READ_ONLY

        # 3. Browser actions
        if action.action_type in (ActionType.CLICK, ActionType.SUBMIT, ActionType.FILL):
            target = (action.target or "").lower()
            if any(kw in target for kw in DESTRUCTIVE_PATH_KEYWORDS):
                return RiskLevel.DESTRUCTIVE
            if any(kw in target for kw in SENSITIVE_AUTH_KEYWORDS):
                return RiskLevel.AUTH_SENSITIVE
            if action.action_type in (ActionType.SUBMIT, ActionType.FILL):
                return RiskLevel.MODIFYING
            return RiskLevel.LOW_RISK

        # 4. Safe read-only actions
        if action.action_type in (
            ActionType.RECONNAISSANCE,
            ActionType.NAVIGATE,
            ActionType.SCROLL,
            ActionType.WAIT,
            ActionType.SCREENSHOT,
            ActionType.INSPECT_SCHEMA,
            ActionType.INSPECT_ACCESSIBILITY_TREE,
            ActionType.CREATE_HYPOTHESIS,
            ActionType.VERIFY_ENDPOINT,
            ActionType.REFLECT,
            ActionType.FINISH,
        ):
            return RiskLevel.READ_ONLY

        return RiskLevel.LOW_RISK

    @classmethod
    def check_scope(cls, target_url: str, goal: Goal) -> Tuple[bool, Optional[str]]:
        """
        Verify target URL against SSRF guardrails and Goal scope constraints (AGENTS.md §23).
        """
        if not target_url:
            return True, None

        # 1. Base SSRF guardrails (private IPs, loopback, metadata services)
        is_safe, err_msg = validate_target_url(target_url)
        if not is_safe:
            return False, f"SSRF Violation: {err_msg}"

        # 2. Domain scope check if allowed_domains is specified
        if goal.allowed_domains:
            parsed = urllib.parse.urlparse(target_url)
            hostname = (parsed.hostname or "").lower()

            # Check exact match or subdomain match
            in_scope = False
            for allowed in goal.allowed_domains:
                allowed_lower = allowed.lower().strip()
                if hostname == allowed_lower or hostname.endswith(f".{allowed_lower}"):
                    in_scope = True
                    break

            if not in_scope:
                return False, f"Domain Out-of-Scope: '{hostname}' is not in authorized domains {goal.allowed_domains}"

        return True, None

    @classmethod
    def evaluate(
        cls,
        action: Action,
        state: AgentState,
        approved_action_keys: Optional[Set[str]] = None,
    ) -> PolicyResult:
        """
        Evaluate whether an action is allowed, denied, or requires human approval.
        """
        approved_set = approved_action_keys or set()
        risk = cls.classify_risk(action)
        action.risk_level = risk

        target_url = action.target or action.parameters.get("url") or ""

        # 1. Scope and SSRF Check
        if target_url:
            in_scope, scope_err = cls.check_scope(target_url, state.goal)
            if not in_scope:
                return PolicyResult(
                    action_id=action.id,
                    decision=PolicyDecision.DENY,
                    risk_level=risk,
                    reason=scope_err or "Scope or SSRF violation",
                )

        # 2. Budget Check (AGENTS.md §29)
        if state.budget.is_exhausted:
            return PolicyResult(
                action_id=action.id,
                decision=PolicyDecision.DENY,
                risk_level=risk,
                reason="Investigation budget exhausted",
            )

        if state.budget.is_timed_out:
            return PolicyResult(
                action_id=action.id,
                decision=PolicyDecision.DENY,
                risk_level=risk,
                reason="Investigation session runtime timed out",
            )

        # 3. Human Approval Gate for Destructive Actions
        if risk in (RiskLevel.DESTRUCTIVE, RiskLevel.SECURITY_TEST):
            action_key = f"{action.parameters.get('method', 'ACTION')}:{target_url}"
            if action_key not in approved_set and action.id not in approved_set:
                return PolicyResult(
                    action_id=action.id,
                    decision=PolicyDecision.REQUIRE_APPROVAL,
                    risk_level=risk,
                    reason=f"Potentially destructive action ({risk.value}) requires explicit human approval.",
                    requires_approval_id=f"appr-{action.id}",
                )

        # 4. Standard Allow
        return PolicyResult(
            action_id=action.id,
            decision=PolicyDecision.ALLOW,
            risk_level=risk,
            reason="Action permitted under current policy and scope.",
        )
