import pytest
from app.agents.nodes.risk_evaluator import RiskEvaluatorNode


def setup_function():
    RiskEvaluatorNode.clear_cache()


def test_tier_1_unsafe_guardrail():
    action = {"text": "Delete Account", "selector": "#delete-btn", "tag": "button"}
    is_safe, reason = RiskEvaluatorNode.evaluate_action_risk(action)
    assert not is_safe
    assert "[Tier-1 Guardrail]" in reason
    assert "delete" in reason.lower()


def test_tier_1_safe_guardrail():
    action = {"text": "Next Page", "selector": ".pagination-next", "tag": "a"}
    is_safe, reason = RiskEvaluatorNode.evaluate_action_risk(action)
    assert is_safe
    assert "[Tier-1 Guardrail]" in reason


def test_tier_2_contextual_ambiguous_unsafe_form():
    # Ambiguous text 'Submit' inside password reset form context
    action = {
        "text": "Submit",
        "selector": "form > button",
        "tag": "button",
        "form_context": "enter your current password and new password"
    }
    is_safe, reason = RiskEvaluatorNode.evaluate_action_risk(action)
    assert not is_safe
    assert "[Tier-2 Context]" in reason


def test_tier_2_contextual_ambiguous_safe_form():
    # Ambiguous text 'Submit' inside search query form context
    action = {
        "text": "Submit",
        "selector": "form > button",
        "tag": "button",
        "form_context": "search products by filter keyword"
    }
    is_safe, reason = RiskEvaluatorNode.evaluate_action_risk(action)
    assert is_safe
    assert "[Tier-2 Context]" in reason


def test_decision_caching():
    action = {"text": "View Details", "selector": "#view-item-1", "tag": "button"}
    is_safe_1, reason_1 = RiskEvaluatorNode.evaluate_action_risk(action)
    assert is_safe_1

    # Second call should return cache hit
    is_safe_2, reason_2 = RiskEvaluatorNode.evaluate_action_risk(action)
    assert is_safe_2
    assert "[Cache Hit]" in reason_2
