"""GraphQL Operation Disaggregator & Schema Extractor."""
from __future__ import annotations

import re
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def parse_graphql_payload(payload: Any) -> List[Dict[str, Any]]:
    """
    Parse a GraphQL request payload (single dict or array of batch operations)
    and return individual disaggregated operation entries.
    """
    operations: List[Dict[str, Any]] = []

    try:
        data = payload
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except Exception:
                # Raw GraphQL query string (not wrapped in JSON)
                data = {"query": payload}

        items = data if isinstance(data, list) else [data]

        for item in items:
            if not isinstance(item, dict):
                continue

            query_str = item.get("query", "")
            op_name = item.get("operationName")
            variables = item.get("variables") or {}

            # Detect operation type (query, mutation, subscription)
            op_type = "query"
            if "mutation" in query_str.lower()[:50]:
                op_type = "mutation"
            elif "subscription" in query_str.lower()[:50]:
                op_type = "subscription"

            # If operationName was omitted, try to extract from query AST string
            if not op_name and query_str:
                match = re.search(r"(?:query|mutation|subscription)\s+([A-Za-z0-9_]+)", query_str)
                if match:
                    op_name = match.group(1)
                else:
                    # Look for first root field name
                    field_match = re.search(r"\{\s*([A-Za-z0-9_]+)", query_str)
                    if field_match:
                        op_name = field_match.group(1)

            final_op_name = op_name or "AnonymousOperation"

            operations.append({
                "operation_name": final_op_name,
                "operation_type": op_type,
                "virtual_endpoint": f"POST /graphql #{op_type}:{final_op_name}",
                "variables": variables,
                "query_snippet": query_str.strip()[:300],
            })

    except Exception as e:
        logger.debug(f"GraphQL parsing notice: {e}")

    return operations
