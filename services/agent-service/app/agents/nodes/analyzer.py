"""
AnalyzerNode — multi-example schema merging, confidence scoring, and example capture.

Design
------
After the crawl loop finishes, ``captured_endpoints`` may contain multiple raw
observations for the same ``(template_route, method, status)`` key (up to
``MAX_OBSERVATIONS_PER_ROUTE`` from ``NetworkObserver``).  This node:

1. Groups observations by ``(template_route, method, status)``.
2. Merges their schemas incrementally using ``merge_schemas()``.
3. Computes a ``confidence`` score per group using the formula below.
4. Collapses each group into a single enriched endpoint record that includes:
   - ``schema``      — merged OpenAPI 3.0 schema with nullable / optional fields
   - ``required``    — list of keys present in *every* observed response body
   - ``confidence``  — float in (0, 1)
   - ``examples``    — up to ``MAX_EXAMPLES_IN_OUTPUT`` redacted payload pairs
   - ``example_count`` — total observations used
5. Runs a single batched LLM call to add semantic enrichment (if enabled):
   - ``ai_summary``          — 2-3 sentence human description of the endpoint
   - ``ai_tags``             — list of semantic tags (e.g. ["pagination", "authenticated"])
   - ``ai_endpoint_category``— high-level domain (e.g. "User Management", "Product Catalog")
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

# Maximum redacted examples to embed in the exported spec per route.
MAX_EXAMPLES_IN_OUTPUT: int = 3

# Sentinel used to represent "field was absent in this observation"
_MISSING = object()


# ---------------------------------------------------------------------------
# Schema inference
# ---------------------------------------------------------------------------

def _python_type_to_openapi(data: Any) -> str:
    """Return the OpenAPI primitive type name for a Python scalar value."""
    if data is None:
        return "null"
    if isinstance(data, bool):
        return "boolean"
    if isinstance(data, int):
        return "integer"
    if isinstance(data, float):
        return "number"
    if isinstance(data, str):
        return "string"
    return "string"


def infer_json_schema(data: Any) -> Dict[str, Any]:
    """
    Recursively inspect a payload value and return an OpenAPI 3.0 schema dict.

    This is the **single-example** variant used as the starting point before
    merging.  Identical to the previous implementation but factored out so it
    can be tested and called independently.
    """
    if data is None:
        return {"type": "null"}
    if isinstance(data, bool):
        return {"type": "boolean"}
    if isinstance(data, int):
        return {"type": "integer"}
    if isinstance(data, float):
        return {"type": "number"}
    if isinstance(data, str):
        return {"type": "string"}
    if isinstance(data, list):
        if not data:
            return {"type": "array", "items": {}}
        item_schema = infer_json_schema(data[0])
        for element in data[1:]:
            item_schema = merge_schemas(item_schema, infer_json_schema(element))
        return {"type": "array", "items": item_schema}
    if isinstance(data, dict):
        properties: Dict[str, Any] = {}
        for k, v in data.items():
            properties[k] = infer_json_schema(v)
        required = sorted(properties.keys())
        schema: Dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema
    return {"type": "string"}


# ---------------------------------------------------------------------------
# Schema merging
# ---------------------------------------------------------------------------

def _schema_fingerprint(schema: Dict[str, Any]) -> str:
    """Stable hash of a schema dict — used to detect structural changes during merging."""
    return hashlib.md5(
        json.dumps(schema, sort_keys=True, default=str).encode()
    ).hexdigest()


def _dedup_one_of(schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate a list of schemas by fingerprint."""
    seen: Set[str] = set()
    result: List[Dict[str, Any]] = []
    for s in schemas:
        fp = _schema_fingerprint(s)
        if fp not in seen:
            seen.add(fp)
            result.append(s)
    return result


def merge_schemas(schema_a: Dict[str, Any], schema_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two OpenAPI 3.0 schemas derived from different observed payloads.

    Rules
    -----
    * **Identical schemas** — return a deep copy unchanged.
    * **null vs. non-null** — add ``nullable: true`` to the non-null branch (OpenAPI 3.0 style).
    * **Primitive type mismatch** — wrap in ``oneOf`` (deduplicated).
    * **object + object** — recurse on properties; fields absent in one side are marked
      optional (removed from ``required``).
    * **array + array** — recurse on ``items``.
    * **anything else** — ``oneOf`` fallback.
    """
    if schema_a == schema_b:
        return copy.deepcopy(schema_a)

    type_a = schema_a.get("type")
    type_b = schema_b.get("type")

    # --- null + X → nullable X ---
    if type_a == "null" and type_b not in (None, "null"):
        result = copy.deepcopy(schema_b)
        result["nullable"] = True
        return result
    if type_b == "null" and type_a not in (None, "null"):
        result = copy.deepcopy(schema_a)
        result["nullable"] = True
        return result

    # --- both objects → recursive property merge ---
    if type_a == "object" and type_b == "object":
        props_a: Dict[str, Any] = schema_a.get("properties", {})
        props_b: Dict[str, Any] = schema_b.get("properties", {})
        req_a: Set[str] = set(schema_a.get("required", list(props_a.keys())))
        req_b: Set[str] = set(schema_b.get("required", list(props_b.keys())))

        all_keys = set(props_a) | set(props_b)
        merged_props: Dict[str, Any] = {}
        for key in all_keys:
            if key in props_a and key in props_b:
                merged_props[key] = merge_schemas(props_a[key], props_b[key])
            elif key in props_a:
                # Field absent in B → still include it, but mark as optional
                merged_props[key] = props_a[key]
            else:
                # Field absent in A → still include it, but mark as optional
                merged_props[key] = props_b[key]

        # A field is required only if both sides required it
        new_required = sorted(req_a & req_b)
        merged: Dict[str, Any] = {"type": "object", "properties": merged_props}
        if new_required:
            merged["required"] = new_required
        return merged

    # --- both arrays → merge items ---
    if type_a == "array" and type_b == "array":
        items_a = schema_a.get("items", {})
        items_b = schema_b.get("items", {})
        merged_items = merge_schemas(items_a, items_b) if (items_a and items_b) else (items_a or items_b)
        return {"type": "array", "items": merged_items}

    # --- type mismatch (primitive or mixed) → oneOf ---
    # Flatten existing oneOf lists to avoid deep nesting
    candidates_a = schema_a.get("oneOf", [schema_a])
    candidates_b = schema_b.get("oneOf", [schema_b])
    return {"oneOf": _dedup_one_of(candidates_a + candidates_b)}


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def compute_confidence(
    example_count: int,
    schema_change_count: int,
    has_auth_header: bool,
    is_vision_derived: bool = False,
) -> float:
    """
    Compute a confidence score in the range (0, 0.99] for a merged endpoint schema.

    Formula
    -------
    ``base`` saturates around 1.0 as the number of examples grows:

        base = min(1.0, 0.5 + 0.1 * example_count)

    ``stability`` captures how often the merged schema *changed structure* when
    a new example was added.  A route whose schema never changes across all
    observed payloads gets stability = 1.0:

        stability = 1 - (schema_change_count / max(1, example_count - 1))

    ``auth_bonus`` rewards routes that were observed with explicit authentication
    (the request included an Authorization or Cookie header):

        auth_bonus = 0.05 if any example had an auth header, else 0

    ``vision_discount``: Endpoints derived from Vision LLM coordinate actions
    are weighted with a 15% uncertainty factor due to lack of DOM selector contracts:

        raw = (base * stability + auth_bonus) * (0.85 if is_vision_derived else 1.0)

    Final score (capped at 0.99 to signal it is still inferred, not ground truth):

        confidence = round(min(0.99, raw), 3)

    Args:
        example_count:      Number of raw observations available for this route.
        schema_change_count: Number of times the schema changed structurally when
                             a new example was merged in.
        has_auth_header:    True if any observation carried an Authorization or
                            Cookie request header.
        is_vision_derived:  True if the endpoint was captured during Vision LLM navigation.

    Returns:
        Float confidence score in (0, 0.99].
    """
    base = min(1.0, 0.5 + 0.1 * example_count)
    stability = 1.0 - (schema_change_count / max(1, example_count - 1)) if example_count > 1 else 1.0
    auth_bonus = 0.05 if has_auth_header else 0.0
    raw_confidence = min(0.99, base * stability + auth_bonus)
    if is_vision_derived:
        raw_confidence *= 0.85
    return round(raw_confidence, 3)


# ---------------------------------------------------------------------------
# AnalyzerNode
# ---------------------------------------------------------------------------

class AnalyzerNode:
    """
    Groups captured raw network observations by ``(template_route, method, status)``,
    merges their JSON schemas across all examples, and enriches each endpoint record
    with a merged schema, confidence score, and example request/response pairs.
    """

    # Keep the module-level helpers accessible as class methods for backward compat
    @classmethod
    def infer_json_schema(cls, data: Any) -> Dict[str, Any]:
        """Public alias — see module-level ``infer_json_schema``."""
        return infer_json_schema(data)

    @classmethod
    def merge_schemas(cls, schema_a: Dict[str, Any], schema_b: Dict[str, Any]) -> Dict[str, Any]:
        """Public alias — see module-level ``merge_schemas``."""
        return merge_schemas(schema_a, schema_b)

    @classmethod
    def compute_confidence(
        cls,
        example_count: int,
        schema_change_count: int,
        has_auth_header: bool,
        is_vision_derived: bool = False,
    ) -> float:
        """Public alias — see module-level ``compute_confidence``."""
        return compute_confidence(example_count, schema_change_count, has_auth_header, is_vision_derived=is_vision_derived)

    @classmethod
    async def process(cls, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node execution function.

        Reads ``captured_endpoints`` from *state*, groups them by
        ``(template_route, method, status)``, and writes back one merged record per group.
        """
        captured: List[Dict[str, Any]] = state.get("captured_endpoints", [])

        # ── Step 1: group observations by (template_route, method, status) ─────
        groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
        for item in captured:
            key = (
                item.get("template_route", "/"),
                item.get("method", "GET").upper(),
                str(item.get("status", 200)),
            )
            groups[key].append(item)

        # ── Step 2: merge each group into one enriched record ──────────────────
        analyzed_results: List[Dict[str, Any]] = []

        for (template_route, method, status), observations in groups.items():
            # Use the first observation as the base record (preserves all metadata)
            base = dict(observations[0])

            merged_schema: Optional[Dict[str, Any]] = None
            schema_change_count = 0
            has_auth = False
            is_vision = any(obs.get("is_vision_derived") for obs in observations)
            example_pairs: List[Dict[str, Any]] = []

            for obs in observations:
                response_body = obs.get("response_body")
                request_payload = obs.get("request_payload")
                req_headers: Dict[str, str] = obs.get("request_headers") or {}

                # Check for auth header presence (case-insensitive key scan)
                if not has_auth:
                    lower_keys = {k.lower() for k in req_headers}
                    if lower_keys & {"authorization", "cookie"}:
                        has_auth = True

                # Infer schema for this observation
                new_schema = infer_json_schema(response_body) if response_body is not None else {"type": "object"}

                # Merge incrementally; track structural changes for stability metric
                if merged_schema is None:
                    merged_schema = new_schema
                else:
                    prev_fp = _schema_fingerprint(merged_schema)
                    merged_schema = merge_schemas(merged_schema, new_schema)
                    if _schema_fingerprint(merged_schema) != prev_fp:
                        schema_change_count += 1

                # Collect example pairs (capped at MAX_EXAMPLES_IN_OUTPUT)
                if len(example_pairs) < MAX_EXAMPLES_IN_OUTPUT:
                    example_pairs.append({
                        "request_payload": request_payload,
                        "response_body": response_body,
                    })

            # ── Step 3: assemble the enriched record ───────────────────────────
            example_count = len(observations)
            confidence = compute_confidence(example_count, schema_change_count, has_auth, is_vision_derived=is_vision)

            # Preserve triggered_by and related_calls metadata if captured from form submission
            triggered_by = next((obs["triggered_by"] for obs in observations if obs.get("triggered_by")), None)
            related_calls = next((obs["related_calls"] for obs in observations if obs.get("related_calls")), [])

            base["schema"] = merged_schema or {"type": "object"}
            base["confidence"] = confidence
            base["example_count"] = example_count
            base["examples"] = example_pairs
            base["is_vision_derived"] = is_vision

            if triggered_by:
                base["triggered_by"] = triggered_by
                if related_calls:
                    base["related_calls"] = related_calls

                # Enrich request body schema using discovered form field names and submitted values
                fields = triggered_by.get("field_names") or []
                submitted = triggered_by.get("submitted_fields") or {}
                if fields:
                    req_props = {}
                    for f in fields:
                        val = submitted.get(f)
                        if isinstance(val, bool):
                            req_props[f] = {"type": "boolean"}
                        elif isinstance(val, int):
                            req_props[f] = {"type": "integer"}
                        elif isinstance(val, float):
                            req_props[f] = {"type": "number"}
                        else:
                            req_props[f] = {"type": "string"}
                    base["form_inferred_request_schema"] = {
                        "type": "object",
                        "properties": req_props,
                    }

            analyzed_results.append(base)

        state["captured_endpoints"] = analyzed_results
        state["vision_fallback_actions"] = state.get("vision_action_count", 0)

        # ── Step 4: LLM Semantic Enrichment (batched, optional) ───────────────
        cost_manager = state.get("cost_manager")
        enriched = await _enrich_endpoints_with_llm(analyzed_results, cost_manager=cost_manager)

        # Extract discovered endpoint categories for LLM Planner coverage gap reasoning
        categories = list({
            ep.get("ai_endpoint_category", "")
            for ep in enriched
            if ep.get("ai_endpoint_category")
        })
        if categories:
            state["endpoint_categories"] = categories

        state["captured_endpoints"] = enriched

        # ── Step 5: Vector Store Memory Persistence ───────────────────────────
        try:
            from app.services.vector_store import EndpointVectorStore
            import uuid
            session_id = str(uuid.uuid4())
            await EndpointVectorStore.store_endpoints(session_id, enriched)
        except Exception as e:
            import logging
            logging.getLogger("agent.analyzer").warning(f"Failed to persist endpoints to VectorStore: {e}")

        return state


async def _enrich_endpoints_with_llm(
    endpoints: list,
    cost_manager=None,
) -> list:
    """
    Adds ``ai_summary``, ``ai_tags``, and ``ai_endpoint_category`` to each endpoint
    using a **single batched LLM call** (one call for all endpoints, not one per endpoint).

    This is significantly cheaper than per-endpoint calls and still produces
    high-quality semantic descriptions.

    Falls back gracefully (leaves fields empty) when:
    - ``settings.LLM_SEMANTIC_SUMMARY_ENABLED`` is False
    - Token budget is exhausted
    - LLM call fails
    """
    from app.core.config import settings
    import json

    if not settings.LLM_SEMANTIC_SUMMARY_ENABLED or not endpoints:
        return endpoints

    if cost_manager and cost_manager.is_budget_exhausted():
        return endpoints

    # Build a compact batch prompt — one JSON array describing all endpoints
    endpoint_summaries = []
    for i, ep in enumerate(endpoints):
        route = ep.get("template_route", "/")
        method = ep.get("method", "GET")
        status = ep.get("status", 200)
        schema_keys = list(ep.get("schema", {}).get("properties", {}).keys())[:8]
        graphql_op = ep.get("graphql_operation_name")
        endpoint_summaries.append(
            f'  [{i}] {method} {route}'  
            + (f' (GraphQL: {graphql_op})' if graphql_op else '')
            + f' → HTTP {status} | schema keys: {schema_keys}'
        )

    prompt = (
        "You are analyzing API endpoints discovered from a web application.\n"
        "For each endpoint below, provide a JSON object with:\n"
        "  - \"summary\": 1-2 sentence description of purpose and returned data\n"
        "  - \"tags\": list of 1-3 semantic tags (e.g. pagination, authenticated, read-only, paginated, mutation)\n"
        "  - \"category\": high-level domain label (e.g. User Management, Product Catalog, Authentication, Orders, Payments)\n\n"
        "Endpoints:\n"
        + "\n".join(endpoint_summaries)
        + "\n\n"
        "Respond ONLY with a JSON array of objects in the same order as the endpoints.\n"
        "Example: [{\"summary\": \"...\", \"tags\": [...], \"category\": \"...\"}, ...]\n"
    )

    # Cache check
    import hashlib
    prompt_key = hashlib.md5(prompt.encode()).hexdigest()
    if cost_manager:
        cached = cost_manager.get_cached(prompt_key)
        if cached:
            try:
                enrichments = json.loads(cached)
                for i, ep in enumerate(endpoints):
                    if i < len(enrichments):
                        ep["ai_summary"] = enrichments[i].get("summary", "")
                        ep["ai_tags"] = enrichments[i].get("tags", [])
                        ep["ai_endpoint_category"] = enrichments[i].get("category", "")
                return endpoints
            except Exception:
                pass

    try:
        from app.agents.nodes.llm_client import get_llm, ModelTier, ModelRouter, extract_text_content, repair_json_string
        llm = get_llm(ModelTier.FAST)  # Summarization is a FAST-tier task
        response = await llm.ainvoke(prompt)
        response_text = extract_text_content(response)

        tokens_est = (len(prompt) + len(response_text)) // 4
        if cost_manager:
            model_name = ModelRouter.get_model_name(ModelTier.FAST)
            cost_manager.record_usage(tokens_est, model_name)
            cost_manager.put_cache(prompt_key, response_text, tokens_est)

        # Parse batch response
        clean = repair_json_string(response_text)
        enrichments = json.loads(clean)

        # Extract categories discovered for state (used by LLM Planner)
        for i, ep in enumerate(endpoints):
            if i < len(enrichments):
                ep["ai_summary"] = enrichments[i].get("summary", "")
                ep["ai_tags"] = enrichments[i].get("tags", [])
                ep["ai_endpoint_category"] = enrichments[i].get("category", "")

    except Exception as e:
        import logging
        logging.getLogger("agent.analyzer").warning(
            f"LLM semantic enrichment failed ({type(e).__name__}: {e}). Endpoints exported without AI summaries."
        )

    return endpoints
