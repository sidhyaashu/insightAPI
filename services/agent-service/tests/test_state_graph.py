import pytest
from app.engine.network.deduplicator import DOMStateHasher, RouteClusterTracker


def setup_function():
    RouteClusterTracker.reset()


def test_dom_state_hasher_identical_elements():
    url = "https://example.com/dashboard"
    elements_1 = [{"tag": "button", "role": "button", "text": "Filter"}]
    elements_2 = [{"tag": "button", "role": "button", "text": "Filter"}]

    hash_1 = DOMStateHasher.compute_state_hash(url, elements_1)
    hash_2 = DOMStateHasher.compute_state_hash(url, elements_2)

    assert hash_1 == hash_2


def test_dom_state_hasher_modal_state_change():
    url = "https://example.com/dashboard"
    elements_base = [{"tag": "button", "role": "button", "text": "Open Modal"}]
    elements_modal_open = [
        {"tag": "button", "role": "button", "text": "Open Modal"},
        {"tag": "button", "role": "button", "text": "Confirm Modal"}
    ]

    hash_base = DOMStateHasher.compute_state_hash(url, elements_base)
    hash_modal = DOMStateHasher.compute_state_hash(url, elements_modal_open)

    # Modal open should produce a distinct state hash at the same URL!
    assert hash_base != hash_modal


def test_route_cluster_tracker_pruning():
    url_1 = "https://example.com/products/101"
    url_2 = "https://example.com/products/102"
    url_3 = "https://example.com/products/103"
    url_4 = "https://example.com/products/104"

    assert not RouteClusterTracker.should_prune_route(url_1, max_cluster_size=3)

    RouteClusterTracker.register_route_visit(url_1, dom_hash="hash_same", max_cluster_size=3)
    RouteClusterTracker.register_route_visit(url_2, dom_hash="hash_same", max_cluster_size=3)
    RouteClusterTracker.register_route_visit(url_3, dom_hash="hash_same", max_cluster_size=3)

    # After 3 instances of /products/{id} with identical DOM hashes, url_4 should be pruned!
    assert RouteClusterTracker.should_prune_route(url_4, max_cluster_size=3)
