"""Agent Service Constants — Tier quotas, maximum exploration bounds, and feature matrices."""

# ── Daily Crawl Quotas per Tier ──────────────────────────────────────────────
TIER_QUOTAS = {
    "FREE": 1,
    "PAYG": 999999,
    "STARTER": 20,
    "PRO": 100,
    "ENTERPRISE": 999999,
    "ADMIN": 999999,
}

# ── Maximum Pages per Crawl ──────────────────────────────────────────────────
TIER_MAX_PAGES = {
    "FREE": 10,
    "PAYG": 100,
    "STARTER": 50,
    "PRO": 200,
    "ENTERPRISE": 1000,
    "ADMIN": 1000,
}

# ── Parallel Agent Workers ───────────────────────────────────────────────────
TIER_MAX_AGENTS = {
    "FREE": 1,
    "PAYG": 3,
    "STARTER": 1,
    "PRO": 3,
    "ENTERPRISE": 10,
    "ADMIN": 10,
}

# ── Feature Availability Matrix ──────────────────────────────────────────────
TIER_FEATURES = {
    "FREE": {
        "export_markdown": True,
        "export_openapi": False,
        "export_postman": False,
        "ai_chatbot": False,
        "vision_fallback": False,
        "semantic_search": False,
        "api_keys": False,
        "priority_queue": False,
        "drift_detection": False,
    },
    "PAYG": {
        "export_markdown": True,
        "export_openapi": True,
        "export_postman": True,
        "ai_chatbot": True,
        "vision_fallback": True,
        "semantic_search": True,
        "api_keys": True,
        "priority_queue": True,
        "drift_detection": True,
    },
    "STARTER": {
        "export_markdown": True,
        "export_openapi": True,
        "export_postman": True,
        "ai_chatbot": True,         # 50 queries/day limit
        "vision_fallback": True,
        "semantic_search": True,
        "api_keys": True,
        "priority_queue": False,
        "drift_detection": False,
    },
    "PRO": {
        "export_markdown": True,
        "export_openapi": True,
        "export_postman": True,
        "ai_chatbot": True,         # Unlimited
        "vision_fallback": True,
        "semantic_search": True,
        "api_keys": True,
        "priority_queue": True,
        "drift_detection": True,
    },
    "ENTERPRISE": {
        "export_markdown": True,
        "export_openapi": True,
        "export_postman": True,
        "ai_chatbot": True,
        "vision_fallback": True,
        "semantic_search": True,
        "api_keys": True,
        "priority_queue": True,
        "drift_detection": True,
    },
    "ADMIN": {
        "export_markdown": True,
        "export_openapi": True,
        "export_postman": True,
        "ai_chatbot": True,
        "vision_fallback": True,
        "semantic_search": True,
        "api_keys": True,
        "priority_queue": True,
        "drift_detection": True,
    },
}

