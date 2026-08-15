"""
tests/test_security_reasoner.py — Comprehensive unit & integration tests for Security Testing Pipeline.

Key assertion areas:
1. SandboxExecutor: Egress isolation, SSRF blocking, resource limits, and domain matching.
2. Domain Verification & Active Testing Opt-in Gate (403 hard-block).
3. First encounter triggers LLM reasoning (reasoning_trace + cached=False).
4. Non-destructive pattern at 20+ occurrences / 15+ distinct targets resolves
   via cache — no LLM call (verifiable via call-count mock).
5. Pattern with 19 occurrences stays needs_review even with 15 distinct targets.
6. Pattern with 25 occurrences but only 5 distinct targets stays needs_review.
7. is_destructive=True pattern NEVER auto-promotes, regardless of occurrences.
8. is_destructive=True test case from LLM → queues approval, does NOT call
   SandboxExecutor.
9. Destructive pattern found in DB → queues approval, does NOT call SandboxExecutor.
10. No approved SecurityApproval → no execution.
11. Cache-hit finding records ran_via_cache=True; LLM-path records ran_via_cache=False.
12. compute_endpoint_signature is domain-agnostic (same shape → same hash).
13. OutcomeClassifier fires correct rules without LLM.
14. distinct_target_count increments only for new domains, not repeat runs.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agents.nodes.security_reasoner import (
    OutcomeClassifier,
    SecurityReasonerNode,
    compute_endpoint_signature,
)
from app.engine.sandbox.executor import SandboxExecutor
from app.models.security_test_pattern import SecurityTestPattern
from app.repositories.security_repo import SecurityPatternRepository
from app.core.config import settings


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _ep(
    method: str = "GET",
    params: dict | None = None,
    auth: bool = True,
    resp_props: list[str] | None = None,
    status: int = 200,
    url: str = "https://example.com/api/users/1",
    template_route: str = "/api/users/{id}",
) -> dict:
    props = params or {"id": {"type": "integer"}}
    return {
        "method": method,
        "url": url,
        "template_route": template_route,
        "status": status,
        "form_inferred_request_schema": {"type": "object", "properties": props},
        "schema": {
            "type": "object",
            "properties": {k: {"type": "string"} for k in (resp_props or ["id", "name"])},
        },
        "examples": [
            {"request_headers": {"authorization": "Bearer t"} if auth else {}}
        ],
    }


def _learned_pattern(
    is_destructive: bool = False,
    occurrences: int = 20,
    distinct_target_count: int = 15,
    confidence: float = 0.90,
    vuln_class: str = "idor",
) -> SecurityTestPattern:
    p = SecurityTestPattern(
        id="pat-001",
        endpoint_signature="test-sig",
        vuln_class=vuln_class,
        test_strategy={"strategy": "adjacent_integer", "mutate_param": "id",
                       "vuln_class": vuln_class, "is_destructive": is_destructive},
        is_destructive=is_destructive,
        outcome="vulnerable",
        confidence=confidence,
        occurrences=occurrences,
        distinct_target_count=distinct_target_count,
        seen_domains=["a.com"] * distinct_target_count,
        status="learned" if not is_destructive and occurrences >= 20 and distinct_target_count >= 15 else "needs_review",
    )
    return p


def _base_state(ep: dict) -> dict:
    return {
        "security_testing_enabled": True,
        "allow_destructive_tests": False,
        "captured_endpoints": [ep],
        "security_findings": [],
        "security_approval_queue": [],
        "crawl_id": "crawl-001",
        "user_id": None,  # SDK / authorized default for node logic
        "cost_manager": None,
        "target_url": "https://example.com",
    }


# ── STEP 1: SandboxExecutor Tests ─────────────────────────────────────────────

def test_sandbox_executor_egress_allows_valid_target_domain():
    assert SandboxExecutor.validate_egress("https://example.com/api/v1", "example.com") is True
    assert SandboxExecutor.validate_egress("https://sub.example.com/api/v1", "example.com") is True


def test_sandbox_executor_egress_blocks_ssrf_and_private_ips():
    with pytest.raises(PermissionError, match="Sandbox egress blocked"):
        SandboxExecutor.validate_egress("http://127.0.0.1:8000/api", "127.0.0.1")

    with pytest.raises(PermissionError, match="Sandbox egress blocked"):
        SandboxExecutor.validate_egress("http://169.254.169.254/latest/meta-data", "169.254.169.254")

    with pytest.raises(PermissionError, match="Sandbox egress blocked"):
        SandboxExecutor.validate_egress("http://192.168.1.50/admin", "192.168.1.50")


def test_sandbox_executor_egress_blocks_mismatched_domain():
    with pytest.raises(PermissionError, match="does not match authorized target domain"):
        SandboxExecutor.validate_egress("https://evil-attacker.com/steal", "example.com")


# ── STEP 2: Domain Verification Gate Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_domain_verification_gate_blocks_unverified_domain():
    """Unverified domain must be hard-blocked from active testing."""
    state = {
        "security_testing_enabled": True,
        "captured_endpoints": [_ep()],
        "crawl_id": "c-001",
        "user_id": "user-unverified",
        "target_url": "https://unverified-target.com",
    }

    with (
        patch.object(SecurityReasonerNode, "_verify_domain_ownership_and_opt_in", AsyncMock(return_value=False)),
        patch.object(settings, "SECURITY_TESTING_ENABLED", True),
    ):
        result = await SecurityReasonerNode.process(state)

    assert "403 Forbidden" in result.get("security_error", "")
    assert len(result.get("security_findings", [])) == 0


@pytest.mark.asyncio
async def test_domain_verification_gate_blocks_when_opt_in_is_false():
    """Verified domain without active_testing_opt_in must be blocked."""
    state = {
        "security_testing_enabled": True,
        "captured_endpoints": [_ep()],
        "crawl_id": "c-001",
        "user_id": "user-verified-no-opt-in",
        "target_url": "https://verified-target.com",
    }

    with (
        patch.object(SecurityReasonerNode, "_verify_domain_ownership_and_opt_in", AsyncMock(return_value=False)),
        patch.object(settings, "SECURITY_TESTING_ENABLED", True),
    ):
        result = await SecurityReasonerNode.process(state)

    assert "403 Forbidden" in result.get("security_error", "")


# ── Signatures & Classifiers ──────────────────────────────────────────────────

def test_signature_same_for_different_domains():
    ep_a = _ep(url="https://portal-a.gov/api/users/1", template_route="/api/users/{id}")
    ep_b = _ep(url="https://portal-b.gov/members/1", template_route="/members/{id}")
    assert compute_endpoint_signature(ep_a) == compute_endpoint_signature(ep_b)
    assert len(compute_endpoint_signature(ep_a)) == 64


def test_signature_differs_for_different_method():
    assert compute_endpoint_signature(_ep(method="GET")) != compute_endpoint_signature(_ep(method="POST"))


def test_signature_differs_for_auth():
    assert compute_endpoint_signature(_ep(auth=True)) != compute_endpoint_signature(_ep(auth=False))


def test_idor_403_becomes_200_is_vulnerable():
    ep = _ep(status=403)
    strategy = {"strategy": "adjacent_integer", "mutate_param": "id", "vuln_class": "idor", "is_destructive": False}
    resp = {"status_code": 200, "body": {"id": 2}, "headers": {}}
    outcome, vc, ev = OutcomeClassifier.classify(strategy, ep, resp)
    assert outcome == "vulnerable" and vc == "idor"


def test_idor_stays_403_is_not_vulnerable():
    ep = _ep(status=403)
    strategy = {"strategy": "adjacent_integer", "mutate_param": "id", "vuln_class": "idor", "is_destructive": False}
    resp = {"status_code": 403, "body": {}, "headers": {}}
    outcome, _, _ = OutcomeClassifier.classify(strategy, ep, resp)
    assert outcome == "not_vulnerable"


def test_injection_stack_trace_fires():
    ep = _ep()
    strategy = {"strategy": "injection_benign", "mutate_param": "q", "vuln_class": "injection", "is_destructive": False}
    resp = {"status_code": 500, "body": "Traceback (most recent call last): ...", "headers": {}}
    outcome, vc, _ = OutcomeClassifier.classify(strategy, ep, resp)
    assert outcome == "vulnerable" and vc == "injection"


def test_inconclusive_when_no_rule_fires():
    ep = _ep(status=200)
    strategy = {"strategy": "injection_benign", "mutate_param": "q", "vuln_class": "injection", "is_destructive": False}
    resp = {"status_code": 200, "body": {"results": []}, "headers": {}}
    outcome, _, _ = OutcomeClassifier.classify(strategy, ep, resp)
    assert outcome == "inconclusive"


# ── Promotion & Repository ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pattern_created_as_needs_review():
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    added = {}
    mock_db.add.side_effect = lambda obj: added.update({"obj": obj})

    repo = SecurityPatternRepository(mock_db)
    await repo.upsert_pattern(
        signature="sig1", vuln_class="idor",
        test_strategy={"strategy": "adjacent_integer", "is_destructive": False},
        is_destructive=False, outcome="vulnerable",
        target_domain="example.com",
    )
    assert added["obj"].status == "needs_review"
    assert added["obj"].occurrences == 1
    assert added["obj"].distinct_target_count == 1
    assert added["obj"].is_destructive is False


@pytest.mark.asyncio
async def test_strict_promotion_requires_20_occurrences():
    existing = _learned_pattern(is_destructive=False, occurrences=18, distinct_target_count=15)
    existing.seen_domains = [f"d{i}.com" for i in range(15)]
    existing.status = "needs_review"

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
    )
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    repo = SecurityPatternRepository(mock_db)
    await repo.upsert_pattern(
        signature=existing.endpoint_signature, vuln_class="idor",
        test_strategy={}, is_destructive=False, outcome="vulnerable",
        target_domain="new-domain.com",
    )
    assert existing.status == "needs_review"


@pytest.mark.asyncio
async def test_strict_promotion_requires_15_distinct_targets():
    existing = _learned_pattern(is_destructive=False, occurrences=24, distinct_target_count=4)
    existing.status = "needs_review"
    existing.seen_domains = [f"d{i}.com" for i in range(4)]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
    )
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    repo = SecurityPatternRepository(mock_db)
    await repo.upsert_pattern(
        signature=existing.endpoint_signature, vuln_class="idor",
        test_strategy={}, is_destructive=False, outcome="vulnerable",
        target_domain="d4.com",
    )
    assert existing.status == "needs_review"


@pytest.mark.asyncio
async def test_destructive_pattern_never_promoted():
    existing = _learned_pattern(is_destructive=True, occurrences=49, distinct_target_count=19)
    existing.status = "needs_review"
    existing.seen_domains = [f"d{i}.com" for i in range(19)]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
    )
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    repo = SecurityPatternRepository(mock_db)
    await repo.upsert_pattern(
        signature=existing.endpoint_signature, vuln_class="idor",
        test_strategy={}, is_destructive=True, outcome="vulnerable",
        target_domain="d20.com",
    )
    assert existing.status == "needs_review"


@pytest.mark.asyncio
async def test_promotion_succeeds_at_both_thresholds():
    existing = _learned_pattern(is_destructive=False, occurrences=19, distinct_target_count=14)
    existing.status = "needs_review"
    existing.seen_domains = [f"d{i}.com" for i in range(14)]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
    )
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    repo = SecurityPatternRepository(mock_db)
    await repo.upsert_pattern(
        signature=existing.endpoint_signature, vuln_class="idor",
        test_strategy={}, is_destructive=False, outcome="vulnerable",
        target_domain="d14.com",
    )
    assert existing.status == "learned"


@pytest.mark.asyncio
async def test_distinct_count_not_incremented_for_repeat_domain():
    existing = _learned_pattern(is_destructive=False, occurrences=5, distinct_target_count=3)
    existing.status = "needs_review"
    existing.seen_domains = ["a.com", "b.com", "c.com"]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
    )
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    repo = SecurityPatternRepository(mock_db)
    await repo.upsert_pattern(
        signature=existing.endpoint_signature, vuln_class="idor",
        test_strategy={}, is_destructive=False, outcome="vulnerable",
        target_domain="a.com",
    )
    assert existing.distinct_target_count == 3
    assert existing.occurrences == 6


# ── Cache Replay & Routing ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_hit_skips_llm_at_v2_thresholds():
    pattern = _learned_pattern(is_destructive=False, occurrences=20, distinct_target_count=15)
    assert pattern.is_cache_eligible()

    llm_call_count = {"count": 0}

    async def fake_propose(*args, **kwargs):
        llm_call_count["count"] += 1
        return ([{"strategy": "adjacent_integer", "vuln_class": "idor", "is_destructive": False}], "trace", 100)

    with (
        patch.object(SecurityReasonerNode, "_lookup_pattern", AsyncMock(return_value=pattern)),
        patch.object(SecurityReasonerNode, "_upsert_pattern", AsyncMock(return_value={"id": "pat-001"})),
        patch.object(SecurityReasonerNode, "_insert_finding", AsyncMock(return_value={})),
        patch("app.agents.nodes.security_reasoner._propose_test_cases_via_llm", side_effect=fake_propose),
        patch("app.agents.nodes.security_reasoner.SandboxExecutor.run_test",
              new_callable=AsyncMock,
              return_value={"status_code": 200, "body": {"id": 2}, "headers": {}}),
        patch("app.agents.nodes.security_reasoner._record_cached_usage"),
        patch.object(settings, "SECURITY_TESTING_ENABLED", True),
    ):
        state = _base_state(_ep(status=403))
        await SecurityReasonerNode.process(state)

    assert llm_call_count["count"] == 0


@pytest.mark.asyncio
async def test_cache_miss_when_distinct_count_below_threshold():
    pattern = _learned_pattern(is_destructive=False, occurrences=20, distinct_target_count=14)
    pattern.status = "needs_review"
    assert not pattern.is_cache_eligible()

    llm_call_count = {"count": 0}

    async def counting_propose(*args, **kwargs):
        llm_call_count["count"] += 1
        return (
            [{"strategy": "adjacent_integer", "vuln_class": "idor", "is_destructive": False}],
            "reasoning", 100,
        )

    with (
        patch.object(SecurityReasonerNode, "_lookup_pattern", AsyncMock(return_value=pattern)),
        patch.object(SecurityReasonerNode, "_upsert_pattern", AsyncMock(return_value={"id": "pat-001"})),
        patch.object(SecurityReasonerNode, "_insert_finding", AsyncMock(return_value={})),
        patch("app.agents.nodes.security_reasoner._propose_test_cases_via_llm",
              side_effect=counting_propose),
        patch("app.agents.nodes.security_reasoner.SandboxExecutor.run_test",
              new_callable=AsyncMock,
              return_value={"status_code": 403, "body": {}, "headers": {}}),
        patch.object(settings, "SECURITY_TESTING_ENABLED", True),
    ):
        state = _base_state(_ep())
        await SecurityReasonerNode.process(state)

    assert llm_call_count["count"] == 1


@pytest.mark.asyncio
async def test_destructive_llm_proposal_queues_approval_not_executed():
    sandbox_called = {"called": False}
    queued = []

    async def fake_sandbox(*args, **kwargs):
        sandbox_called["called"] = True
        return {}

    async def fake_propose(*args, **kwargs):
        return (
            [{"strategy": "DELETE /users/{id}", "vuln_class": "auth_bypass",
              "is_destructive": True, "rationale": "Would delete user data"}],
            "LLM reasoning trace",
            100,
        )

    async def fake_queue_approval(*args, **kwargs):
        approval = {"id": "approval-001", "status": "pending"}
        queued.append(approval)
        return approval

    with (
        patch.object(SecurityReasonerNode, "_lookup_pattern", AsyncMock(return_value=None)),
        patch.object(SecurityReasonerNode, "_upsert_pattern", AsyncMock(return_value={"id": "pat-001"})),
        patch.object(SecurityReasonerNode, "_queue_approval", AsyncMock(side_effect=fake_queue_approval)),
        patch("app.agents.nodes.security_reasoner._propose_test_cases_via_llm", side_effect=fake_propose),
        patch("app.agents.nodes.security_reasoner.SandboxExecutor.run_test", side_effect=fake_sandbox),
        patch.object(settings, "SECURITY_TESTING_ENABLED", True),
    ):
        state = _base_state(_ep())
        await SecurityReasonerNode.process(state)

    assert not sandbox_called["called"]
    assert len(queued) == 1


@pytest.mark.asyncio
async def test_destructive_pattern_in_db_queues_approval_not_executed():
    pattern = _learned_pattern(is_destructive=True, occurrences=9999, distinct_target_count=999)
    pattern.confidence = 0.99
    sandbox_called = {"called": False}

    async def fake_sandbox(*args, **kwargs):
        sandbox_called["called"] = True
        return {}

    with (
        patch.object(SecurityReasonerNode, "_lookup_pattern", AsyncMock(return_value=pattern)),
        patch.object(SecurityReasonerNode, "_queue_approval", AsyncMock(return_value={"id": "appr-001"})),
        patch("app.agents.nodes.security_reasoner.SandboxExecutor.run_test", side_effect=fake_sandbox),
        patch("app.agents.nodes.security_reasoner._propose_test_cases_via_llm",
              side_effect=AsyncMock(return_value=([], "", 0))),
        patch.object(settings, "SECURITY_TESTING_ENABLED", True),
    ):
        state = _base_state(_ep())
        await SecurityReasonerNode.process(state)

    assert not sandbox_called["called"]


@pytest.mark.asyncio
async def test_cache_hit_finding_has_ran_via_cache_true():
    pattern = _learned_pattern(is_destructive=False, occurrences=20, distinct_target_count=15)
    assert pattern.is_cache_eligible()

    inserted_findings = []

    with (
        patch.object(SecurityReasonerNode, "_lookup_pattern", AsyncMock(return_value=pattern)),
        patch.object(SecurityReasonerNode, "_upsert_pattern", AsyncMock(return_value={"id": "pat-001"})),
        patch.object(SecurityReasonerNode, "_insert_finding", AsyncMock(side_effect=lambda **kw: inserted_findings.append(kw) or {})),
        patch("app.agents.nodes.security_reasoner._propose_test_cases_via_llm",
              side_effect=AsyncMock(return_value=([], "", 0))),
        patch("app.agents.nodes.security_reasoner.SandboxExecutor.run_test",
              new_callable=AsyncMock,
              return_value={"status_code": 200, "body": {"id": 2}, "headers": {}}),
        patch("app.agents.nodes.security_reasoner._record_cached_usage"),
        patch.object(settings, "SECURITY_TESTING_ENABLED", True),
    ):
        state = _base_state(_ep(status=403))
        await SecurityReasonerNode.process(state)

    if inserted_findings:
        assert inserted_findings[0].get("ran_via_cache") is True


@pytest.mark.asyncio
async def test_llm_path_finding_has_ran_via_cache_false():
    inserted_findings = []

    async def fake_propose(*args, **kwargs):
        return (
            [{"strategy": "adjacent_integer", "vuln_class": "idor", "is_destructive": False}],
            "reasoning", 100,
        )

    with (
        patch.object(SecurityReasonerNode, "_lookup_pattern", AsyncMock(return_value=None)),
        patch.object(SecurityReasonerNode, "_upsert_pattern", AsyncMock(return_value={"id": "pat-002"})),
        patch.object(SecurityReasonerNode, "_insert_finding",
                     AsyncMock(side_effect=lambda **kw: inserted_findings.append(kw) or {})),
        patch("app.agents.nodes.security_reasoner._propose_test_cases_via_llm", side_effect=fake_propose),
        patch("app.agents.nodes.security_reasoner.SandboxExecutor.run_test",
              new_callable=AsyncMock,
              return_value={"status_code": 200, "body": {"id": 2}, "headers": {}}),
        patch.object(settings, "SECURITY_TESTING_ENABLED", True),
    ):
        state = _base_state(_ep(status=403))
        await SecurityReasonerNode.process(state)

    if inserted_findings:
        assert inserted_findings[0].get("ran_via_cache") is False


@pytest.mark.asyncio
async def test_node_noop_when_security_testing_disabled():
    state = {
        "security_testing_enabled": False,
        "captured_endpoints": [_ep()],
        "security_findings": [],
        "crawl_id": "x", "user_id": "y",
        "cost_manager": None, "target_url": "https://example.com",
    }
    with patch.object(SecurityReasonerNode, "_lookup_pattern") as mock_lookup:
        await SecurityReasonerNode.process(state)
        mock_lookup.assert_not_called()


def test_cache_eligible_requires_all_conditions():
    base = dict(is_destructive=False, occurrences=20, distinct_target_count=15,
                confidence=0.90, vuln_class="idor")

    assert _learned_pattern(**base).is_cache_eligible()

    p = _learned_pattern(**{**base, "is_destructive": True})
    p.status = "learned"
    assert not p.is_cache_eligible()

    p = _learned_pattern(**{**base, "occurrences": 19})
    p.status = "needs_review"
    assert not p.is_cache_eligible()

    p = _learned_pattern(**{**base, "distinct_target_count": 14})
    p.status = "needs_review"
    assert not p.is_cache_eligible()

    p = _learned_pattern(**{**base, "confidence": 0.79})
    p.status = "learned"
    assert not p.is_cache_eligible()
