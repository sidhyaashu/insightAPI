import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.nodes.security_reasoner import SecurityReasonerNode, compute_endpoint_signature
from app.models.security_test_pattern import SecurityTestPattern


@pytest.mark.asyncio
async def test_destructive_test_no_prior_cache_creates_pattern_before_approval():
    """
    Verify F-20: When no cached pattern exists and LLM proposes a destructive test,
    SecurityReasonerNode creates the SecurityTestPattern row FIRST, ensuring a valid UUID pattern_id
    is passed to _queue_approval (never the literal string 'unknown').
    """
    ep = {
        "method": "DELETE",
        "url": "https://api.example.com/users/1",
        "template_route": "/users/{id}",
        "status": 200,
        "form_inferred_request_schema": {"type": "object", "properties": {"id": {"type": "integer"}}},
        "schema": {"type": "object", "properties": {"success": {"type": "boolean"}}},
        "examples": [],
    }

    state = {
        "security_testing_enabled": True,
        "captured_endpoints": [ep],
        "crawl_id": "crawl-destructive-123",
        "user_id": "user-test-1",
        "target_url": "https://api.example.com",
    }

    destructive_test_case = {
        "strategy": "adjacent_integer",
        "mutate_param": "id",
        "vuln_class": "idor",
        "is_destructive": True,
        "rationale": "Deleting resource is destructive",
    }

    queued_approval_payload = {}

    async def mock_queue_approval(pattern_id, crawl_id, user_id, ep, target_domain, test_strategy):
        queued_approval_payload["pattern_id"] = pattern_id
        queued_approval_payload["crawl_id"] = crawl_id
        return {
            "id": "appr-001",
            "pattern_id": pattern_id,
            "crawl_id": crawl_id,
            "user_id": user_id,
            "status": "pending",
        }

    mock_pattern_dict = {
        "id": "pat-generated-uuid-999",
        "endpoint_signature": compute_endpoint_signature(ep),
        "vuln_class": "idor",
        "is_destructive": True,
        "status": "needs_review",
    }

    with patch("app.agents.nodes.security_reasoner.settings.SECURITY_TESTING_ENABLED", True), \
         patch.object(SecurityReasonerNode, "_verify_domain_ownership_and_opt_in", new=AsyncMock(return_value=True)), \
         patch.object(SecurityReasonerNode, "_lookup_pattern", new=AsyncMock(return_value=None)), \
         patch.object(SecurityReasonerNode, "_upsert_pattern", new=AsyncMock(return_value=mock_pattern_dict)) as mock_upsert, \
         patch.object(SecurityReasonerNode, "_queue_approval", new=AsyncMock(side_effect=mock_queue_approval)) as mock_queue, \
         patch("app.agents.nodes.security_reasoner._propose_test_cases_via_llm", new=AsyncMock(return_value=([destructive_test_case], "LLM trace", 50))):

        updated_state = await SecurityReasonerNode.process(state)

        # 1. Verify pattern upsert was called before queue approval
        mock_upsert.assert_called_once()
        assert mock_upsert.call_args[1]["is_destructive"] is True

        # 2. Verify _queue_approval was called with the real pattern_id from upsert (NOT 'unknown')
        mock_queue.assert_called_once()
        assert queued_approval_payload["pattern_id"] == "pat-generated-uuid-999"
        assert queued_approval_payload["pattern_id"] != "unknown"

        # 3. Verify approval queue in state has the real approval record
        assert len(updated_state["security_approval_queue"]) == 1
        assert updated_state["security_approval_queue"][0]["pattern_id"] == "pat-generated-uuid-999"
