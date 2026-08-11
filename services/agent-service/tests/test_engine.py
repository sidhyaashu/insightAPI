import pytest
from app.engine.network.filter import NetworkFilter
from app.engine.network.deduplicator import URLDeduplicator


def test_network_filter_static_assets():
    assert NetworkFilter.is_api_request("https://example.com/api/products", "fetch") is True
    assert NetworkFilter.is_api_request("https://example.com/static/main.js", "script") is False
    assert NetworkFilter.is_api_request("https://www.google-analytics.com/collect", "xhr") is False
    assert NetworkFilter.is_api_request("https://example.com/styles.css", "stylesheet") is False
    # Expanded static extensions & telemetry domains
    assert NetworkFilter.is_api_request("https://example.com/hero.webp", "fetch") is False
    assert NetworkFilter.is_api_request("https://example.com/archive.zip", "fetch") is False
    assert NetworkFilter.is_api_request("https://app.posthog.com/e/", "xhr") is False
    assert NetworkFilter.is_api_request("https://api.bugsnag.com/notify", "fetch") is False


def test_network_filter_content_type():
    assert NetworkFilter.is_api_content_type("application/json; charset=utf-8") is True
    assert NetworkFilter.is_api_content_type("application/graphql+json") is True
    assert NetworkFilter.is_api_content_type("text/html") is False
    assert NetworkFilter.is_api_content_type("image/png") is False


def test_url_deduplicator():
    # Test numeric ID replacement
    url1 = "https://example.com/api/v1/users/101/orders/55"
    assert URLDeduplicator.parameterize_path(url1) == "https://example.com/api/v1/users/{id}/orders/{id}"

    # Test UUID replacement
    url2 = "https://example.com/api/products/f47ac10b-58cc-4372-a567-0e02b2c3d479"
    assert URLDeduplicator.parameterize_path(url2) == "https://example.com/api/products/{uuid}"

    # Test Mongo ObjectID replacement
    url_mongo = "https://example.com/api/documents/507f1f77bcf86cd799439011"
    assert URLDeduplicator.parameterize_path(url_mongo) == "https://example.com/api/documents/{id}"

    # Test MD5 Hash replacement
    url_hash = "https://example.com/api/cache/5d41402abc4b2a76b9719d911017c592"
    assert URLDeduplicator.parameterize_path(url_hash) == "https://example.com/api/cache/{hash}"

    # Test Date replacement
    url3 = "https://example.com/api/logs/2026-08-02"
    assert URLDeduplicator.parameterize_path(url3) == "https://example.com/api/logs/{date}"

    # Test Query Parameter replacement and deterministic key sorting
    url4_a = "https://example.com/api/search?sort=asc&page=2"
    url4_b = "https://example.com/api/search?page=2&sort=asc"
    assert URLDeduplicator.parameterize_path(url4_a) == URLDeduplicator.parameterize_path(url4_b)

