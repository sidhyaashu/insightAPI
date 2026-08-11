import pytest
from app.agents.nodes.risk_evaluator import RiskEvaluatorNode
from app.agents.nodes.planner import PlannerNode
from app.agents.nodes.analyzer import AnalyzerNode
from app.agents.graph import build_crawl_graph


def test_risk_evaluator_safe():
    safe_action = {"text": "View Details", "selector": "button#details"}
    is_safe, reason = RiskEvaluatorNode.evaluate_action_risk(safe_action)
    assert is_safe is True


def test_risk_evaluator_unsafe():
    unsafe_action = {"text": "Delete Workspace Account", "selector": "button.btn-danger"}
    is_safe, reason = RiskEvaluatorNode.evaluate_action_risk(unsafe_action)
    assert is_safe is False
    assert "delete" in reason.lower()

    unsafe_action_2 = {"text": "Confirm Purchase", "selector": "button[name='checkout']"}
    is_safe2, reason2 = RiskEvaluatorNode.evaluate_action_risk(unsafe_action_2)
    assert is_safe2 is False

    unsafe_action_3 = {"text": "Grant Admin Role", "selector": "button.grant-admin"}
    is_safe3, reason3 = RiskEvaluatorNode.evaluate_action_risk(unsafe_action_3)
    assert is_safe3 is False


def test_planner_dom_hashing():
    url = "https://example.com"
    elements = [{"text": "Home"}, {"text": "About"}]
    hash1 = PlannerNode.compute_dom_hash(url, elements)
    hash2 = PlannerNode.compute_dom_hash(url, elements)
    assert hash1 == hash2


def test_analyzer_recursive_schema_inference():
    data = {
        "id": 1,
        "name": "Laptop",
        "price": 999.99,
        "in_stock": True,
        "categories": ["electronics", "computers"],
        "details": {"brand": "Dell", "warranty_years": 2},
        "metadata": None
    }
    schema = AnalyzerNode.infer_json_schema(data)
    assert schema["type"] == "object"
    assert schema["properties"]["id"]["type"] == "integer"
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["price"]["type"] == "number"
    assert schema["properties"]["in_stock"]["type"] == "boolean"
    assert schema["properties"]["categories"]["type"] == "array"
    assert schema["properties"]["details"]["type"] == "object"
    assert schema["properties"]["details"]["properties"]["brand"]["type"] == "string"
    assert schema["properties"]["metadata"]["type"] == "null"


def test_crawl_graph_compilation():
    graph = build_crawl_graph()
    assert graph is not None
