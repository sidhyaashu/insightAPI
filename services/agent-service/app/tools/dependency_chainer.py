"""API Dependency Chaining & Dynamic Parameter Propagation Engine."""
from __future__ import annotations

import re
import json
import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

ID_KEY_CANDIDATES = {
    "id", "user_id", "userId", "order_id", "orderId",
    "account_id", "accountId", "item_id", "itemId",
    "session_id", "sessionId", "token", "access_token",
    "cursor", "next_cursor", "uuid"
}


def extract_identifiers_from_payload(payload: Any) -> Dict[str, Any]:
    """Recursively traverse a JSON payload and extract common entity IDs and auth tokens."""
    identifiers: Dict[str, Any] = {}

    def _traverse(obj: Any, prefix: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = k.lower()
                if k in ID_KEY_CANDIDATES or k_lower.endswith("_id") or k_lower.endswith("id"):
                    if isinstance(v, (str, int)) and str(v).strip():
                        identifiers[k] = v
                if isinstance(v, (dict, list)):
                    _traverse(v, f"{prefix}{k}.")
        elif isinstance(obj, list):
            for item in obj[:5]:  # limit array traversal
                if isinstance(item, (dict, list)):
                    _traverse(item, prefix)

    try:
        _traverse(payload)
    except Exception as e:
        logger.debug(f"Identifier extraction warning: {e}")

    return identifiers


def chain_api_dependencies(
    endpoints: List[Dict[str, Any]],
    known_identifiers: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Correlate endpoints into a dependency chain:
    Substitutes captured parameters into downstream template endpoints.
    """
    resolved_chain: List[Dict[str, Any]] = []
    pool = dict(known_identifiers or {})

    # Extract all IDs from existing sample responses in the catalog
    for ep in endpoints:
        sample_resp = ep.get("sample_response")
        if sample_resp and isinstance(sample_resp, (dict, list)):
            extracted = extract_identifiers_from_payload(sample_resp)
            pool.update(extracted)

    # Resolve template paths
    for ep in endpoints:
        template = ep.get("template_path") or ep.get("path") or "/"
        method = ep.get("method", "GET").upper()
        resolved_path = template
        dependencies_used: List[str] = []

        # Find placehoders {id}, {user_id}, {uuid}, etc.
        placeholders = re.findall(r"\{([A-Za-z0-9_]+)\}", template)
        for ph in placeholders:
            ph_lower = ph.lower()
            matching_val = None

            # Look up in pool
            for pool_key, pool_val in pool.items():
                if pool_key.lower() == ph_lower or ph_lower in pool_key.lower() or (ph_lower == "id" and pool_key.lower().endswith("id")):
                    matching_val = pool_val
                    dependencies_used.append(f"{ph} <- {pool_key}:{pool_val}")
                    break

            if matching_val is not None:
                resolved_path = resolved_path.replace(f"{{{ph}}}", str(matching_val))
            else:
                # Fallback realistic placeholder value
                resolved_path = resolved_path.replace(f"{{{ph}}}", "101")

        resolved_chain.append({
            "method": method,
            "template_path": template,
            "resolved_path": resolved_path,
            "status_code": ep.get("status_code", 200),
            "dependencies": dependencies_used,
            "has_chained_parameters": len(dependencies_used) > 0,
        })

    return resolved_chain
