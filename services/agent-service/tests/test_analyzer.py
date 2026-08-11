"""
test_analyzer.py — Unit tests for AnalyzerNode schema merging, confidence scoring,
and process() grouping behaviour.

Coverage matrix
---------------
merge_schemas:
  - same field, different primitive types → oneOf
  - missing field in one example → field kept but removed from required
  - array of mixed object shapes → union items schema
  - null vs. non-null field → nullable: true added

compute_confidence:
  - confidence grows with example count
  - auth header presence adds 0.05 bonus

process():
  - multiple hits on same route → single merged record
  - examples list capped at MAX_EXAMPLES_IN_OUTPUT (3)
"""
import asyncio
import pytest

from app.agents.nodes.analyzer import (
    merge_schemas,
    infer_json_schema,
    compute_confidence,
    AnalyzerNode,
    MAX_EXAMPLES_IN_OUTPUT,
)


# ===========================================================================
# merge_schemas — type-level tests
# ===========================================================================

class TestMergeSchemas:

    def test_same_schema_returns_copy(self):
        s = {"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]}
        result = merge_schemas(s, s)
        assert result == s
        assert result is not s  # must be a deep copy

    def test_same_field_different_primitive_types(self):
        """{'id': 1} merged with {'id': 'abc'} → id field becomes oneOf[integer, string]."""
        schema_a = infer_json_schema({"id": 1})
        schema_b = infer_json_schema({"id": "abc"})
        merged = merge_schemas(schema_a, schema_b)

        assert merged["type"] == "object"
        id_schema = merged["properties"]["id"]
        assert "oneOf" in id_schema, f"Expected oneOf in id field, got: {id_schema}"
        types_in_one_of = [s.get("type") for s in id_schema["oneOf"]]
        assert "integer" in types_in_one_of
        assert "string" in types_in_one_of

    def test_missing_field_in_one_example(self):
        """{'a': 1, 'b': 2} + {'a': 1} → b present but NOT in required."""
        schema_a = infer_json_schema({"a": 1, "b": 2})
        schema_b = infer_json_schema({"a": 1})
        merged = merge_schemas(schema_a, schema_b)

        assert merged["type"] == "object"
        assert "b" in merged["properties"], "Field 'b' should still appear in properties"
        required = merged.get("required", [])
        assert "b" not in required, f"Field 'b' must NOT be required (missing in one example); required={required}"
        assert "a" in required, "Field 'a' must stay required (present in both examples)"

    def test_array_mixed_object_shapes(self):
        """[{x:1}] + [{x:1, y:'z'}] → items schema has both fields, y optional."""
        schema_a = infer_json_schema([{"x": 1}])
        schema_b = infer_json_schema([{"x": 1, "y": "hello"}])
        merged = merge_schemas(schema_a, schema_b)

        assert merged["type"] == "array"
        items = merged["items"]
        assert items["type"] == "object"
        assert "x" in items["properties"]
        assert "y" in items["properties"]
        # y is absent in the first example → must not be required
        required = items.get("required", [])
        assert "y" not in required, f"'y' must be optional; required={required}"

    def test_nullable_field_when_null_observed(self):
        """{'token': 'abc'} + {'token': None} → token becomes nullable."""
        schema_a = infer_json_schema({"token": "abc"})
        schema_b = infer_json_schema({"token": None})
        merged = merge_schemas(schema_a, schema_b)

        token_schema = merged["properties"]["token"]
        assert token_schema.get("nullable") is True, (
            f"Token field should be nullable=true when null observed; got {token_schema}"
        )
        assert token_schema.get("type") == "string"

    def test_null_is_first_operand(self):
        """Merge order shouldn't matter: null + string → same as string + null."""
        s_null = infer_json_schema({"x": None})
        s_str = infer_json_schema({"x": "hello"})
        merged_ab = merge_schemas(s_null, s_str)
        merged_ba = merge_schemas(s_str, s_null)
        assert merged_ab["properties"]["x"].get("nullable") is True
        assert merged_ba["properties"]["x"].get("nullable") is True

    def test_both_arrays_items_merged(self):
        """Arrays with different item types produce oneOf items."""
        schema_a = infer_json_schema([1, 2, 3])
        schema_b = infer_json_schema(["a", "b"])
        merged = merge_schemas(schema_a, schema_b)
        assert merged["type"] == "array"
        assert "oneOf" in merged["items"]

    def test_nested_object_merging(self):
        """Deeply nested objects are merged recursively."""
        schema_a = infer_json_schema({"user": {"id": 1, "name": "Alice"}})
        schema_b = infer_json_schema({"user": {"id": 2, "email": "a@b.com"}})
        merged = merge_schemas(schema_a, schema_b)

        user_props = merged["properties"]["user"]["properties"]
        assert "id" in user_props
        assert "name" in user_props
        assert "email" in user_props
        # name and email absent in one example each → not required
        user_req = merged["properties"]["user"].get("required", [])
        assert "name" not in user_req
        assert "email" not in user_req
        assert "id" in user_req

    def test_one_of_deduplicated(self):
        """Merging the same type three times doesn't produce duplicates in oneOf."""
        s_int = {"type": "integer"}
        s_str = {"type": "string"}
        partial = merge_schemas(s_int, s_str)       # → oneOf[integer, string]
        again = merge_schemas(partial, s_int)        # → should not add integer twice
        assert "oneOf" in again
        types = [s.get("type") for s in again["oneOf"]]
        assert types.count("integer") == 1, f"Duplicate integer in oneOf: {again['oneOf']}"


# ===========================================================================
# infer_json_schema
# ===========================================================================

class TestInferJsonSchema:

    def test_primitive_types(self):
        assert infer_json_schema(None) == {"type": "null"}
        assert infer_json_schema(True) == {"type": "boolean"}
        assert infer_json_schema(42) == {"type": "integer"}
        assert infer_json_schema(3.14) == {"type": "number"}
        assert infer_json_schema("hello") == {"type": "string"}

    def test_empty_list(self):
        assert infer_json_schema([]) == {"type": "array", "items": {}}

    def test_object_required_all_keys(self):
        result = infer_json_schema({"a": 1, "b": "x"})
        assert set(result.get("required", [])) == {"a", "b"}

    def test_array_items_merged_across_elements(self):
        """infer_json_schema on a mixed-type list produces a merged items schema."""
        result = infer_json_schema([{"x": 1}, {"x": 2, "y": "z"}])
        assert result["type"] == "array"
        props = result["items"]["properties"]
        assert "x" in props
        assert "y" in props


# ===========================================================================
# compute_confidence
# ===========================================================================

class TestComputeConfidence:

    def test_single_example_no_auth(self):
        c = compute_confidence(example_count=1, schema_change_count=0, has_auth_header=False)
        assert 0.5 <= c <= 0.65, f"Single example confidence out of range: {c}"

    def test_confidence_grows_with_examples(self):
        """Confidence should be strictly higher with more examples (before saturation cap)."""
        c1 = compute_confidence(1, 0, False)   # base = 0.6
        c3 = compute_confidence(3, 0, False)   # base = 0.8
        c5 = compute_confidence(5, 0, False)   # base = 1.0 → capped at 0.99
        assert c1 < c3, f"3 examples should beat 1 example: {c1} vs {c3}"
        assert c3 <= c5, f"5 examples should be >= 3 examples: {c3} vs {c5}"

    def test_confidence_capped_at_0_99(self):
        c = compute_confidence(100, 0, True)
        assert c <= 0.99

    def test_auth_bonus_adds_five_percent(self):
        without = compute_confidence(3, 0, False)
        with_auth = compute_confidence(3, 0, True)
        assert abs((with_auth - without) - 0.05) < 0.001, (
            f"Auth bonus should be exactly 0.05; got diff={with_auth - without}"
        )

    def test_schema_instability_reduces_confidence(self):
        stable = compute_confidence(5, 0, False)    # schema never changed
        unstable = compute_confidence(5, 4, False)  # schema changed every step
        assert stable > unstable, f"Stable ({stable}) should beat unstable ({unstable})"

    def test_confidence_rounded_to_3_decimals(self):
        c = compute_confidence(4, 1, True)
        assert c == round(c, 3)


# ===========================================================================
# AnalyzerNode.process()
# ===========================================================================

def _make_ep(template_route, method, status, response_body, request_payload=None, headers=None):
    """Helper: build a minimal captured endpoint dict."""
    return {
        "template_route": template_route,
        "method": method,
        "status": status,
        "url": f"https://example.com{template_route}",
        "response_body": response_body,
        "request_payload": request_payload,
        "request_headers": headers or {},
        "response_headers": {},
        "resource_type": "fetch",
        "graphql_operation_name": None,
    }


class TestAnalyzerNodeProcess:

    def _run(self, endpoints):
        state = {"captured_endpoints": endpoints}
        return asyncio.run(AnalyzerNode.process(state))

    def test_single_observation_produces_one_record(self):
        ep = _make_ep("/api/users", "GET", 200, {"id": 1, "name": "Alice"})
        result = self._run([ep])
        assert len(result["captured_endpoints"]) == 1
        record = result["captured_endpoints"][0]
        assert record["schema"]["type"] == "object"
        assert "id" in record["schema"]["properties"]

    def test_groups_by_route_method_status(self):
        """Two hits on the same route → one merged output record."""
        ep1 = _make_ep("/api/items", "GET", 200, {"id": 1, "name": "foo"})
        ep2 = _make_ep("/api/items", "GET", 200, {"id": 2, "tag": "bar"})
        result = self._run([ep1, ep2])
        records = result["captured_endpoints"]
        assert len(records) == 1, f"Expected 1 merged record, got {len(records)}"
        props = records[0]["schema"]["properties"]
        assert "id" in props and "name" in props and "tag" in props

    def test_different_routes_produce_separate_records(self):
        ep1 = _make_ep("/api/users", "GET", 200, {"id": 1})
        ep2 = _make_ep("/api/posts", "GET", 200, {"title": "hi"})
        result = self._run([ep1, ep2])
        assert len(result["captured_endpoints"]) == 2

    def test_missing_field_marks_not_required(self):
        ep1 = _make_ep("/api/things", "GET", 200, {"a": 1, "b": 2})
        ep2 = _make_ep("/api/things", "GET", 200, {"a": 1})
        result = self._run([ep1, ep2])
        record = result["captured_endpoints"][0]
        required = record["schema"].get("required", [])
        assert "b" not in required
        assert "a" in required

    def test_examples_list_capped_at_max(self):
        """5 observations → examples list has at most MAX_EXAMPLES_IN_OUTPUT entries."""
        eps = [
            _make_ep("/api/things", "GET", 200, {"id": i, "val": f"v{i}"})
            for i in range(5)
        ]
        result = self._run(eps)
        record = result["captured_endpoints"][0]
        assert len(record["examples"]) <= MAX_EXAMPLES_IN_OUTPUT

    def test_example_count_reflects_all_observations(self):
        eps = [_make_ep("/api/things", "GET", 200, {"n": i}) for i in range(4)]
        result = self._run(eps)
        assert result["captured_endpoints"][0]["example_count"] == 4

    def test_auth_header_detected_for_confidence_bonus(self):
        ep_no_auth = _make_ep("/api/a", "GET", 200, {"x": 1})
        ep_with_auth = _make_ep("/api/b", "GET", 200, {"x": 1},
                                headers={"Authorization": "Bearer tok"})
        result = self._run([ep_no_auth, ep_with_auth])

        records = {r["template_route"]: r for r in result["captured_endpoints"]}
        c_no_auth = records["/api/a"]["confidence"]
        c_with_auth = records["/api/b"]["confidence"]
        assert c_with_auth > c_no_auth, (
            f"Auth route should have higher confidence; no_auth={c_no_auth}, with_auth={c_with_auth}"
        )

    def test_nullable_field_propagated_in_merged_schema(self):
        ep1 = _make_ep("/api/tokens", "GET", 200, {"token": "abc123"})
        ep2 = _make_ep("/api/tokens", "GET", 200, {"token": None})
        result = self._run([ep1, ep2])
        token_schema = result["captured_endpoints"][0]["schema"]["properties"]["token"]
        assert token_schema.get("nullable") is True
