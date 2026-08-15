"""
SecurityReasonerNode — V2 Adaptive, memory-driven security testing.

V2 Routing Logic (replaces V1)
------------------------------

For each captured endpoint:

  1. Compute domain-agnostic endpoint_signature (SHA-256, no URL/domain).

  2. DB lookup → pattern found?

     ┌──────────────────────────────────────────────────────────────────────┐
     │ pattern.is_cache_eligible():                                         │
     │   status=learned AND NOT is_destructive                              │
     │   AND occurrences>=20 AND distinct_target_count>=15                  │
     │   AND confidence>=0.80                                               │
     │ → Cache replay. No LLM call. LLM usage: cached=True.                │
     ├──────────────────────────────────────────────────────────────────────┤
     │ pattern found AND is_destructive=True                                │
     │ → Queue SecurityApproval (pending). NEVER execute. Ever.             │
     │   Even if this exact pattern succeeded 1000 times before.            │
     ├──────────────────────────────────────────────────────────────────────┤
     │ no pattern, OR status≠learned, OR thresholds not met                 │
     │ → LLM (SMART tier). Propose 1-3 test cases. LLM usage: cached=False. │
     │   Each test case tagged is_destructive=True|False by LLM.            │
     │   Destructive proposals → queue approval, skip execution.            │
     │   Non-destructive → execute via SandboxExecutor.                     │
     └──────────────────────────────────────────────────────────────────────┘

  3. Classify outcome (rule-based first, LLM fallback for inconclusive only).

  4. Upsert security_test_patterns with new V2 promotion rules.
     - distinct_target_count incremented only for new domains.
     - is_destructive=True patterns never promoted, ever.

  5. Insert security_findings only when outcome=vulnerable.
     - ran_via_cache=True for cache-replay path, False for LLM path.

Cost tracking: every call/skip recorded in llm_usage with node_name=SecurityReasonerNode.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.agents.state import CrawlState
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("agent.security_reasoner")

_SEVERITY_MAP: Dict[str, str] = {
    "idor": "high",
    "injection": "critical",
    "auth_bypass": "critical",
    "mass_assignment": "high",
    "rate_limit_bypass": "medium",
    "ssrf_via_param": "high",
    "other": "low",
}


# ---------------------------------------------------------------------------
# Endpoint Signature (unchanged from V1)
# ---------------------------------------------------------------------------

def compute_endpoint_signature(ep: Dict[str, Any]) -> str:
    """
    Compute a domain-agnostic SHA-256 signature for an endpoint.
    Excludes literal URL and domain — only structural shape is hashed.
    """
    method = (ep.get("method") or "GET").upper()

    req_schema = ep.get("form_inferred_request_schema") or {}
    req_props = req_schema.get("properties") or {}
    param_types = sorted(v.get("type", "string") for v in req_props.values())

    def _name_shape(name: str) -> str:
        n = name.lower()
        for suffix in ("_id", "_type", "_name", "_date", "_url", "_token",
                       "_code", "_key", "_hash", "_email", "_no"):
            if n.endswith(suffix):
                return suffix.lstrip("_")
        return "field"

    param_name_shapes = sorted(_name_shape(k) for k in req_props.keys())

    has_auth = False
    for ex in (ep.get("examples") or []):
        hdrs = ex.get("request_headers") or {}
        if any(k.lower() in {"authorization", "cookie", "x-access-token"} for k in hdrs):
            has_auth = True
            break

    resp_schema = ep.get("schema") or {}
    resp_props = resp_schema.get("properties") or {}
    resp_shape = sorted(resp_props.keys())

    fingerprint = json.dumps({
        "method": method,
        "param_types": param_types,
        "param_names": param_name_shapes,
        "auth_required": has_auth,
        "resp_shape": resp_shape,
    }, sort_keys=True)

    return hashlib.sha256(fingerprint.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Rule-based outcome classifier (unchanged from V1)
# ---------------------------------------------------------------------------

class OutcomeClassifier:
    STACK_TRACE_PATTERNS = (
        "traceback", "exception", "stack trace", "at line",
        "syntaxerror", "undefined method", "sql syntax",
        "pg::", "uncaught", "internal server error",
    )
    PROTO_POLLUTION_PATTERNS = ("__proto__", "__class__", "constructor",)

    @classmethod
    def classify(
        cls,
        test_strategy: Dict[str, Any],
        original_ep: Dict[str, Any],
        test_response: Dict[str, Any],
    ) -> Tuple[str, str, Dict[str, Any]]:
        strategy_name = test_strategy.get("strategy", "")
        vuln_class = test_strategy.get("vuln_class", "other")
        resp_status = test_response.get("status_code", 0)
        resp_body = test_response.get("body", "")
        resp_body_str = (
            json.dumps(resp_body) if isinstance(resp_body, dict) else str(resp_body)
        ).lower()
        original_status = original_ep.get("status", 200)

        evidence: Dict[str, Any] = {
            "strategy": strategy_name,
            "original_status": original_status,
            "test_status": resp_status,
        }

        # IDOR
        if vuln_class == "idor" and original_status in (403, 404, 401):
            if resp_status == 200:
                evidence["signal"] = "accessed_denied_resource"
                return "vulnerable", "idor", evidence
            return "not_vulnerable", "idor", evidence

        if vuln_class == "idor" and resp_status == 200:
            evidence["signal"] = "adjacent_id_returned_200"
            return "vulnerable", "idor", evidence

        # Injection — stack trace in body
        for pattern in cls.STACK_TRACE_PATTERNS:
            if pattern in resp_body_str:
                evidence["signal"] = f"stack_trace_pattern:{pattern}"
                evidence["vuln_class"] = "injection"
                return "vulnerable", "injection", evidence

        # Mass assignment — extra/proto fields
        if isinstance(resp_body, dict):
            original_props = set(
                (original_ep.get("schema") or {}).get("properties", {}).keys()
            )
            extra_fields = set(resp_body.keys()) - original_props
            proto_fields = {
                k for k in extra_fields
                if any(p in k.lower() for p in cls.PROTO_POLLUTION_PATTERNS)
            }
            if proto_fields:
                evidence["signal"] = "prototype_pollution_fields"
                evidence["extra_fields"] = list(proto_fields)
                return "vulnerable", "mass_assignment", evidence

        return "inconclusive", vuln_class, evidence


from app.engine.sandbox.executor import SandboxExecutor


# ---------------------------------------------------------------------------
# LLM test-case proposer
# ---------------------------------------------------------------------------

async def _propose_test_cases_via_llm(
    ep: Dict[str, Any],
    signature: str,
    cost_manager: Any,
    crawl_id: str,
    user_id: str,
) -> Tuple[List[Dict[str, Any]], str, int]:
    """
    Invoke LLM (SMART tier) to propose 1-3 security test cases.
    Each returned test case MUST include "is_destructive": true|false.
    If the LLM omits the field, we default to is_destructive=true (safe default).
    """
    from app.agents.nodes.llm_client import (
        get_llm, ModelTier, ModelRouter, extract_text_content, repair_json_string
    )

    req_schema = ep.get("form_inferred_request_schema") or {}
    req_props = req_schema.get("properties") or {}
    resp_schema = ep.get("schema") or {}
    resp_props = list((resp_schema.get("properties") or {}).keys())
    has_auth = any(
        any(k.lower() in {"authorization", "cookie", "x-access-token"}
            for k in (ex.get("request_headers") or {}))
        for ex in (ep.get("examples") or [])
    )
    has_id_param = any("id" in k.lower() for k in req_props)
    has_file_param = any("file" in k.lower() or "url" in k.lower() for k in req_props)

    prompt = (
        "You are a security analyst reviewing a discovered API endpoint.\n"
        "Propose 1-3 security test cases for this endpoint shape.\n"
        "CRITICAL: For each test case, explicitly tag is_destructive=true if the test "
        "would write/modify/delete data, trigger emails, payments, or any side effects. "
        "Tag is_destructive=false ONLY for pure read-only probes.\n\n"
        f"Endpoint shape:\n"
        f"  method: {ep.get('method', 'GET').upper()}\n"
        f"  request params: {list(req_props.keys())}\n"
        f"  response fields: {resp_props}\n"
        f"  auth_required: {has_auth}\n"
        f"  has_id_param: {has_id_param}\n"
        f"  has_file_or_url_param: {has_file_param}\n"
        f"  status: {ep.get('status', 200)}\n\n"
        "Vuln classes: idor, injection, auth_bypass, mass_assignment, "
        "rate_limit_bypass, ssrf_via_param, other.\n\n"
        "Respond ONLY with a JSON array of 1-3 objects:\n"
        '[{"vuln_class":"...","strategy":"adjacent_integer|injection_benign|missing_auth|mass_assign_extra_field",'
        '"mutate_param":"field_or_null","payload":null,"is_destructive":false,"rationale":"1 sentence"}]'
    )

    llm = get_llm(ModelTier.SMART)
    response = await llm.ainvoke(prompt)
    response_text = extract_text_content(response)
    tokens_used = (len(prompt) + len(response_text)) // 4

    _record_llm_usage(
        crawl_id=crawl_id, user_id=user_id, tokens_used=tokens_used,
        model_name=ModelRouter.get_model_name(ModelTier.SMART),
        cached=False, cost_manager=cost_manager,
    )

    try:
        clean = repair_json_string(response_text)
        test_cases = json.loads(clean)
        if not isinstance(test_cases, list):
            test_cases = [test_cases]
        # Enforce safe default: if is_destructive missing, assume True
        for tc in test_cases:
            if "is_destructive" not in tc:
                tc["is_destructive"] = True
    except Exception:
        test_cases = []

    reasoning_trace = response_text[:4000]
    return test_cases, reasoning_trace, tokens_used


def _record_llm_usage(
    crawl_id: str, user_id: str, tokens_used: int,
    model_name: str, cached: bool, cost_manager: Any,
) -> None:
    async def _write() -> None:
        try:
            from app.core.database import get_db
            async with contextlib.asynccontextmanager(get_db)() as db:
                from app.repositories.llm_usage_repo import LlmUsageRepository
                repo = LlmUsageRepository(db)
                cost_per_token = 0.000003 if "gpt-4o" in model_name else 0.0000015
                await repo.record(
                    crawl_id=crawl_id, user_id=user_id, model_name=model_name,
                    tier="smart",
                    prompt_tokens=tokens_used // 2,
                    completion_tokens=tokens_used // 2,
                    cost_usd=round(tokens_used * cost_per_token, 8),
                    cached=cached, node_name="SecurityReasonerNode",
                )
        except Exception as exc:
            logger.warning(f"Failed to record SecurityReasonerNode LLM usage: {exc}")
    asyncio.create_task(_write())


def _record_cached_usage(crawl_id: str, user_id: str, model_name: str, cost_manager: Any) -> None:
    _record_llm_usage(
        crawl_id=crawl_id, user_id=user_id, tokens_used=0,
        model_name=model_name, cached=True, cost_manager=cost_manager,
    )


# ---------------------------------------------------------------------------
# SecurityReasonerNode
# ---------------------------------------------------------------------------

class SecurityReasonerNode:
    """
    V2 post-crawl LangGraph node. Hard rules enforced:
    - is_destructive=True patterns never auto-execute, always queue approval.
    - Cache replay requires all V2 thresholds met simultaneously.
    - SandboxExecutor has a defence-in-depth destructive block as backup.
    """

    @classmethod
    async def process(cls, state: CrawlState) -> CrawlState:
        if not state.get("security_testing_enabled"):
            return state

        if not getattr(settings, "SECURITY_TESTING_ENABLED", False):
            logger.debug("SecurityReasonerNode skipped — SECURITY_TESTING_ENABLED=False")
            return state

        endpoints = state.get("captured_endpoints") or []
        if not endpoints:
            return state

        crawl_id = state.get("crawl_id") or "unknown"
        user_id = state.get("user_id") or "unknown"
        cost_manager = state.get("cost_manager")
        target_url = state.get("target_url", "")
        target_domain = _extract_domain(target_url)

        # ── Domain Verification & Active Testing Opt-in Gate ──────────────────
        if user_id and user_id != "unknown" and target_url:
            is_authorized = await cls._verify_domain_ownership_and_opt_in(target_url, user_id)
            if not is_authorized:
                logger.warning(
                    f"⛔ Security testing blocked: Domain '{target_domain}' is not verified "
                    f"or active_testing_opt_in is not enabled for user {user_id}."
                )
                state["security_error"] = (
                    f"403 Forbidden: Domain '{target_domain}' requires ownership verification "
                    "and active_testing_opt_in=True to run security tests."
                )
                return state

        findings: List[Dict[str, Any]] = []
        queued_approvals: List[Dict[str, Any]] = []

        from app.agents.nodes.llm_client import ModelRouter, ModelTier

        for ep in endpoints:
            try:
                signature = compute_endpoint_signature(ep)
                pattern = await cls._lookup_pattern(signature)

                if pattern is not None and pattern.is_destructive:
                    # ── Hard block: destructive pattern found → queue, never execute ──
                    logger.info(
                        f"🔐 Destructive pattern found | sig={signature[:12]}… "
                        f"→ queuing approval request (will NOT auto-execute)"
                    )
                    approval = await cls._queue_approval(
                        pattern_id=pattern.id,
                        crawl_id=crawl_id,
                        user_id=user_id,
                        ep=ep,
                        target_domain=target_domain,
                        test_strategy=pattern.test_strategy,
                    )
                    if approval:
                        queued_approvals.append(approval)
                        if crawl_id:
                            with contextlib.suppress(Exception):
                                from app.api.v1.endpoints.crawls import publish_ws_event
                                await publish_ws_event(crawl_id, {
                                    "type": "approval_required",
                                    "approval_id": approval.get("id"),
                                    "endpoint": ep.get("template_route") or ep.get("url"),
                                    "method": ep.get("method", "GET"),
                                    "vuln_class": pattern.vuln_class if pattern else "destructive_action",
                                    "test_strategy": pattern.test_strategy if pattern else {},
                                    "reasoning_trace": pattern.reasoning_trace if pattern else "Destructive security test requires single-use human authorization.",
                                })
                    continue

                if pattern is not None and pattern.is_cache_eligible():
                    # ── Cache replay path — no LLM ────────────────────────────
                    logger.info(
                        f"⚡ Cache HIT | sig={signature[:12]}… "
                        f"| class={pattern.vuln_class} | confidence={pattern.confidence} "
                        f"| occurrences={pattern.occurrences} "
                        f"| distinct_targets={pattern.distinct_target_count}"
                    )
                    _record_cached_usage(
                        crawl_id=crawl_id, user_id=user_id,
                        model_name=ModelRouter.get_model_name(ModelTier.SMART),
                        cost_manager=cost_manager,
                    )
                    test_cases = [pattern.test_strategy]
                    reasoning_trace = None
                    ran_via_cache = True
                    if crawl_id:
                        with contextlib.suppress(Exception):
                            from app.api.v1.endpoints.crawls import publish_ws_event
                            await publish_ws_event(crawl_id, {
                                "type": "pattern_cache_hit",
                                "endpoint": ep.get("template_route") or ep.get("url"),
                                "vuln_class": pattern.vuln_class,
                                "occurrences": pattern.occurrences,
                                "distinct_targets": pattern.distinct_target_count,
                                "confidence": pattern.confidence,
                                "tokens_saved": 450,
                            })
                else:
                    # ── Cache miss or thresholds not met → LLM ────────────────
                    reason = "cache miss" if pattern is None else (
                        f"thresholds not met "
                        f"(occ={getattr(pattern,'occurrences',0)}, "
                        f"dist={getattr(pattern,'distinct_target_count',0)})"
                    )
                    logger.info(
                        f"🔍 LLM reasoning | sig={signature[:12]}… | reason={reason}"
                    )
                    if crawl_id:
                        with contextlib.suppress(Exception):
                            from app.api.v1.endpoints.crawls import publish_ws_event
                            await publish_ws_event(crawl_id, {
                                "type": "pattern_llm_reasoning",
                                "endpoint": ep.get("template_route") or ep.get("url"),
                                "node_name": "SecurityReasonerNode",
                                "model": ModelRouter.get_model_name(ModelTier.SMART),
                                "reason": reason,
                            })
                    test_cases, reasoning_trace, _ = await _propose_test_cases_via_llm(
                        ep=ep, signature=signature, cost_manager=cost_manager,
                        crawl_id=crawl_id, user_id=user_id,
                    )
                    ran_via_cache = False

                # ── Route each test case by is_destructive ────────────────────
                for test_case in test_cases[:3]:
                    is_destructive = test_case.get("is_destructive", True)
                    vuln_class = test_case.get("vuln_class", "other")

                    if is_destructive:
                        # Queue for human approval — never execute here
                        logger.info(
                            f"🔐 Destructive test proposed | sig={signature[:12]}… "
                            f"| class={vuln_class} → queuing approval"
                        )
                        approval = await cls._queue_approval(
                            pattern_id=pattern.id if pattern else "unknown",
                            crawl_id=crawl_id, user_id=user_id,
                            ep=ep, target_domain=target_domain,
                            test_strategy=test_case,
                        )
                        if approval:
                            queued_approvals.append(approval)
                            if crawl_id:
                                with contextlib.suppress(Exception):
                                    from app.api.v1.endpoints.crawls import publish_ws_event
                                    await publish_ws_event(crawl_id, {
                                        "type": "approval_required",
                                        "approval_id": approval.get("id"),
                                        "endpoint": ep.get("template_route") or ep.get("url"),
                                        "method": ep.get("method", "GET"),
                                        "vuln_class": vuln_class,
                                        "test_strategy": test_case,
                                        "reasoning_trace": reasoning_trace or "Destructive vulnerability test proposed by Security Reasoner.",
                                    })

                        # Still upsert the pattern so we track the signature
                        await cls._upsert_pattern(
                            signature=signature, vuln_class=vuln_class,
                            test_strategy=test_case, is_destructive=True,
                            outcome="inconclusive",  # Not executed yet
                            target_domain=target_domain,
                            reasoning_trace=reasoning_trace,
                        )
                        continue

                    # ── Non-destructive → execute via SandboxExecutor ────────
                    if crawl_id:
                        with contextlib.suppress(Exception):
                            from app.api.v1.endpoints.crawls import publish_ws_event
                            await publish_ws_event(crawl_id, {
                                "type": "security_test_running",
                                "endpoint": ep.get("template_route") or ep.get("url"),
                                "method": ep.get("method", "GET"),
                                "vuln_class": vuln_class,
                                "is_cache_hit": ran_via_cache,
                                "is_destructive": False,
                            })

                    test_response = await SandboxExecutor.run_test(
                        ep=ep,
                        test_strategy=test_case,
                        target_domain=target_domain,
                        allow_destructive=False,
                        crawl_id=crawl_id,   # enables sandbox_action WS events in UI
                    )
                    if test_response.get("blocked"):
                        continue

                    outcome, classified_vuln, evidence = OutcomeClassifier.classify(
                        test_strategy=test_case,
                        original_ep=ep,
                        test_response=test_response,
                    )

                    if outcome == "inconclusive":
                        outcome, classified_vuln, evidence = await cls._classify_via_llm(
                            ep=ep, test_case=test_case, test_response=test_response,
                            evidence=evidence, crawl_id=crawl_id,
                            user_id=user_id, cost_manager=cost_manager,
                        )

                    # Upsert pattern with V2 strict promotion
                    updated = await cls._upsert_pattern(
                        signature=signature, vuln_class=classified_vuln,
                        test_strategy=test_case, is_destructive=False,
                        outcome=outcome, target_domain=target_domain,
                        reasoning_trace=reasoning_trace,
                    )

                    if crawl_id:
                        with contextlib.suppress(Exception):
                            from app.api.v1.endpoints.crawls import publish_ws_event
                            await publish_ws_event(crawl_id, {
                                "type": "security_test_outcome",
                                "endpoint": ep.get("template_route") or ep.get("url"),
                                "method": ep.get("method", "GET"),
                                "vuln_class": classified_vuln,
                                "outcome": outcome,
                                "ran_via_cache": ran_via_cache,
                            })

                    if outcome == "vulnerable":
                        finding = await cls._insert_finding(
                            crawl_id=crawl_id, user_id=user_id,
                            pattern_id=updated["id"] if updated else "unknown",
                            signature=signature, vuln_class=classified_vuln,
                            ep=ep, evidence=evidence, ran_via_cache=ran_via_cache,
                        )
                        findings.append(finding)


            except Exception as exc:
                logger.warning(
                    f"SecurityReasonerNode error for {ep.get('template_route')}: {exc}"
                )
                continue

        state["security_findings"] = findings
        state["security_approval_queue"] = queued_approvals
        logger.info(
            f"🔒 SecurityReasonerNode done | endpoints={len(endpoints)} "
            f"| findings={len(findings)} | approvals_queued={len(queued_approvals)}"
        )
        return state

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    async def _lookup_pattern(signature: str):
        try:
            from app.core.database import get_db
            from app.repositories.security_repo import SecurityPatternRepository
            async with contextlib.asynccontextmanager(get_db)() as db:
                return await SecurityPatternRepository(db).get_by_signature(signature)
        except Exception as exc:
            logger.warning(f"Pattern lookup failed: {exc}")
            return None

    @staticmethod
    async def _upsert_pattern(
        signature: str, vuln_class: str, test_strategy: dict,
        is_destructive: bool, outcome: str,
        target_domain: Optional[str], reasoning_trace: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        try:
            from app.core.database import get_db
            from app.repositories.security_repo import SecurityPatternRepository
            async with contextlib.asynccontextmanager(get_db)() as db:
                repo = SecurityPatternRepository(db)
                pattern = await repo.upsert_pattern(
                    signature=signature, vuln_class=vuln_class,
                    test_strategy=test_strategy, is_destructive=is_destructive,
                    outcome=outcome, target_domain=target_domain,
                    reasoning_trace=reasoning_trace,
                )
                return pattern.to_dict()
        except Exception as exc:
            logger.warning(f"Pattern upsert failed: {exc}")
            return None

    @staticmethod
    async def _insert_finding(
        crawl_id: str, user_id: str, pattern_id: str, signature: str,
        vuln_class: str, ep: Dict[str, Any], evidence: Dict[str, Any],
        ran_via_cache: bool,
    ) -> Dict[str, Any]:
        severity = _SEVERITY_MAP.get(vuln_class, "medium")
        try:
            from app.core.database import get_db
            from app.repositories.security_repo import SecurityPatternRepository
            async with contextlib.asynccontextmanager(get_db)() as db:
                repo = SecurityPatternRepository(db)
                finding = await repo.insert_finding(
                    crawl_id=crawl_id, user_id=user_id, pattern_id=pattern_id,
                    endpoint_signature=signature, vuln_class=vuln_class,
                    endpoint_route=ep.get("template_route"), method=ep.get("method"),
                    evidence=evidence, severity=severity, ran_via_cache=ran_via_cache,
                )
                return finding.to_dict()
        except Exception as exc:
            logger.warning(f"Finding insert failed: {exc}")
            return {}

    @staticmethod
    async def _queue_approval(
        pattern_id: str, crawl_id: str, user_id: str,
        ep: Dict[str, Any], target_domain: Optional[str],
        test_strategy: dict,
    ) -> Optional[Dict[str, Any]]:
        try:
            from app.core.database import get_db
            from app.repositories.security_repo import SecurityPatternRepository
            async with contextlib.asynccontextmanager(get_db)() as db:
                repo = SecurityPatternRepository(db)
                approval = await repo.create_approval_request(
                    pattern_id=pattern_id, crawl_id=crawl_id, user_id=user_id,
                    endpoint_route=ep.get("template_route"),
                    method=ep.get("method"),
                    target_domain=target_domain,
                    test_strategy_snapshot=test_strategy,
                )
                return approval.to_dict()
        except Exception as exc:
            logger.warning(f"Approval queue failed: {exc}")
            return None

    @staticmethod
    async def _classify_via_llm(
        ep: Dict[str, Any], test_case: Dict[str, Any],
        test_response: Dict[str, Any], evidence: Dict[str, Any],
        crawl_id: str, user_id: str, cost_manager: Any,
    ) -> Tuple[str, str, Dict[str, Any]]:
        try:
            from app.agents.nodes.llm_client import (
                get_llm, ModelTier, ModelRouter, extract_text_content, repair_json_string
            )
            prompt = (
                "Classify this API security test result.\n"
                f"Strategy: {json.dumps(test_case)}\n"
                f"Original status: {ep.get('status')}\n"
                f"Test status: {test_response.get('status_code')}\n"
                f"Body (first 500): {str(test_response.get('body', ''))[:500]}\n\n"
                'Respond ONLY with JSON: {"outcome":"vulnerable|not_vulnerable",'
                '"vuln_class":"idor|injection|auth_bypass|mass_assignment|rate_limit_bypass|ssrf_via_param|other",'
                '"reason":"1 sentence"}'
            )
            llm = get_llm(ModelTier.FAST)
            response = await llm.ainvoke(prompt)
            response_text = extract_text_content(response)
            tokens = (len(prompt) + len(response_text)) // 4
            _record_llm_usage(
                crawl_id=crawl_id, user_id=user_id, tokens_used=tokens,
                model_name=ModelRouter.get_model_name(ModelTier.FAST),
                cached=False, cost_manager=cost_manager,
            )
            result = json.loads(repair_json_string(response_text))
            evidence["llm_reason"] = result.get("reason", "")
            return result.get("outcome", "not_vulnerable"), result.get("vuln_class", "other"), evidence
        except Exception as exc:
            logger.warning(f"LLM classifier failed: {exc}")
            return "not_vulnerable", test_case.get("vuln_class", "other"), evidence

    @staticmethod
    async def _verify_domain_ownership_and_opt_in(target_url: str, user_id: str) -> bool:
        try:
            domain = _extract_domain(target_url)
            if not domain:
                return False
            from app.core.database import get_db
            from app.repositories.domain_repo import DomainRepository
            async with contextlib.asynccontextmanager(get_db)() as db:
                repo = DomainRepository(db)
                return await repo.is_domain_opted_in_for_active_testing(user_id=user_id, domain=domain)
        except Exception as exc:
            logger.warning(f"Domain verification & opt-in check failed: {exc}")
            return False


def _extract_domain(url: str) -> Optional[str]:
    try:
        return urlparse(url).netloc or None
    except Exception:
        return None
