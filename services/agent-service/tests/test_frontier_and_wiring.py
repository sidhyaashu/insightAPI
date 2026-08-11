import pytest
from app.agents.nodes.planner import PlannerNode
from app.engine.network.deduplicator import DOMStateHasher, RouteClusterTracker
from app.core.compliance import RobotsChecker, DomainRateLimiter


def setup_function():
    RouteClusterTracker.reset()
    RobotsChecker.reset()
    DomainRateLimiter.reset()


def test_planner_scoring_prioritizes_inputs_and_search():
    el_link = {"tag": "a", "role": "link", "text": "About Us", "selector": "a#about"}
    el_search = {"tag": "input", "role": "searchbox", "text": "Search Products", "selector": "input#q"}

    score_link = PlannerNode.score_element(el_link)
    score_search = PlannerNode.score_element(el_search)

    # Search inputs must score significantly higher than simple links
    assert score_search > score_link
    assert score_search >= 20.0


def test_dom_state_hasher_sanitizes_volatile_text():
    url = "https://example.com/inbox"
    el_1 = [{"tag": "button", "role": "button", "text": "3 New Messages"}]
    el_2 = [{"tag": "button", "role": "button", "text": "5 New Messages"}]

    hash_1 = DOMStateHasher.compute_state_hash(url, el_1)
    hash_2 = DOMStateHasher.compute_state_hash(url, el_2)

    # Volatile count digits ("3" vs "5") should be sanitized so state hashes match!
    assert hash_1 == hash_2


def test_route_cluster_tracker_prunes_only_on_identical_dom_hashes():
    url_1 = "https://example.com/items/1"
    url_2 = "https://example.com/items/2"
    url_3 = "https://example.com/items/3"
    url_4 = "https://example.com/items/4"

    # Same DOM hash 3 times -> saturated and pruned
    same_hash = "hash_abc_123"
    RouteClusterTracker.register_route_visit(url_1, dom_hash=same_hash, max_cluster_size=3)
    RouteClusterTracker.register_route_visit(url_2, dom_hash=same_hash, max_cluster_size=3)
    RouteClusterTracker.register_route_visit(url_3, dom_hash=same_hash, max_cluster_size=3)

    assert RouteClusterTracker.should_prune_route(url_4, max_cluster_size=3)


def test_route_cluster_tracker_keeps_exploring_if_dom_hashes_diverge():
    url_1 = "https://example.com/items/1"
    url_2 = "https://example.com/items/2"
    url_3 = "https://example.com/items/3"
    url_4 = "https://example.com/items/4"

    # Different DOM hashes -> do NOT prune item 4
    RouteClusterTracker.register_route_visit(url_1, dom_hash="hash_1", max_cluster_size=3)
    RouteClusterTracker.register_route_visit(url_2, dom_hash="hash_2", max_cluster_size=3)
    RouteClusterTracker.register_route_visit(url_3, dom_hash="hash_3", max_cluster_size=3)

    assert not RouteClusterTracker.should_prune_route(url_4, max_cluster_size=3)
