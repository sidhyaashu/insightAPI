"""
tools/js_ast_parser.py — Tree-sitter AST Static JavaScript & TypeScript Analyzer.

Architecture (AGENTS.md §8, §15):
  Replaces naive regex scanning with concrete Abstract Syntax Tree (AST) inspection
  over client-side bundles to discover:
    - fetch(), axios.<method>(), $.ajax() call expressions
    - Template literal routes (`/api/orders/${id}`) normalized to `/api/orders/{id}`
    - String concatenation routes ('/api/users/' + id)
    - WebSocket initializers (new WebSocket('wss://...'))
    - Inline GraphQL queries and mutations
"""
from __future__ import annotations

import re
import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Tree-sitter parser initialization with fallback
_PARSER = None
_LANGUAGE = None

try:
    import tree_sitter_javascript as tsjs
    from tree_sitter import Language, Parser
    _LANGUAGE = Language(tsjs.language())
    _PARSER = Parser(_LANGUAGE)
except Exception as e:
    logger.warning(f"Tree-sitter JavaScript parser initialization deferred: {e}")


def _normalize_ast_template_string(raw_str: str) -> Tuple[str, List[str]]:
    """
    Convert a JS template literal (e.g. `/api/orders/${orderId}/items`)
    into an OpenAPI route template (e.g. `/api/orders/{orderId}/items`)
    and extract parameter names.
    """
    clean = raw_str.strip("`'\" \t\r\n")
    params = re.findall(r"\$\{([^}]+)\}", clean)
    normalized = re.sub(r"\$\{([^}]+)\}", r"{\1}", clean)

    # Clean complex expressions inside {param} (e.g. {user.id} -> {user_id}, {id || 1} -> {id})
    def _sanitize_param(m: re.Match) -> str:
        inner = m.group(1).strip()
        inner_clean = re.sub(r"[^a-zA-Z0-9_]", "_", inner)
        return f"{{{inner_clean}}}"

    normalized = re.sub(r"\{([^}]+)\}", _sanitize_param, normalized)
    return normalized, params


def _extract_string_from_node(node, source_bytes: bytes) -> str:
    """Extract string content from string / template_string node."""
    if not node:
        return ""
    text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
    return text.strip("`'\" \t\r\n")


class JsAstParser:
    """
    High-performance Abstract Syntax Tree parser for JavaScript/TypeScript client bundles.
    """

    @classmethod
    def parse_bundle(cls, js_source: str, base_url: str = "") -> Dict[str, Any]:
        """
        Statically inspect JavaScript source code to extract API routes, GraphQL queries, and WebSockets.
        """
        results: Dict[str, Any] = {
            "endpoints": [],
            "graphql_operations": [],
            "websocket_endpoints": [],
            "total_ast_nodes_scanned": 0,
        }

        if not js_source or len(js_source) < 5:
            return results

        source_bytes = js_source.encode("utf-8", errors="ignore")

        # Fallback to regex parser if Tree-sitter is unavailable
        if _PARSER is None:
            from app.tools.traffic_parser import extract_endpoints_from_javascript
            results["endpoints"] = extract_endpoints_from_javascript(js_source, base_url)
            return results

        try:
            tree = _PARSER.parse(source_bytes)
        except Exception as parse_err:
            logger.debug(f"Tree-sitter parse error: {parse_err}")
            return results

        parsed_base = urllib.parse.urlparse(base_url) if base_url else None
        base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}" if parsed_base and parsed_base.scheme else ""

        discovered_endpoints: Dict[str, Dict[str, Any]] = {}
        discovered_graphql: List[Dict[str, Any]] = []
        discovered_ws: Dict[str, Dict[str, Any]] = {}
        node_count = 0

        # Stack-based AST traversal
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            node_count += 1
            ntype = node.type

            # 1. Call Expressions: fetch(), axios.get(), axios.post(), $.ajax()
            if ntype == "call_expression":
                cls._handle_call_expression(node, source_bytes, base_origin, discovered_endpoints)

            # 2. New Expressions: new WebSocket("wss://...")
            elif ntype == "new_expression":
                cls._handle_new_expression(node, source_bytes, base_origin, discovered_ws)

            # 3. Template Strings containing inline GraphQL or API paths
            elif ntype == "template_string":
                cls._handle_template_string(node, source_bytes, base_origin, discovered_endpoints, discovered_graphql)

            # Add children to stack
            stack.extend(node.children)

        results["total_ast_nodes_scanned"] = node_count
        results["endpoints"] = list(discovered_endpoints.values())
        results["graphql_operations"] = discovered_graphql
        results["websocket_endpoints"] = list(discovered_ws.values())
        return results

    @classmethod
    def _handle_call_expression(cls, node, source_bytes: bytes, base_origin: str, discovered: Dict[str, Dict[str, Any]]):
        fn_node = node.child_by_field_name("function")
        args_node = node.child_by_field_name("arguments")
        if not fn_node or not args_node:
            return

        fn_text = source_bytes[fn_node.start_byte:fn_node.end_byte].decode("utf-8", errors="ignore").strip()
        args = [c for c in args_node.children if c.type not in ("(", ")", ",")]
        if not args:
            return

        first_arg = args[0]
        first_arg_text = source_bytes[first_arg.start_byte:first_arg.end_byte].decode("utf-8", errors="ignore")

        # Determine HTTP Method
        method = "GET"
        fn_lower = fn_text.lower()
        if "post" in fn_lower:
            method = "POST"
        elif "put" in fn_lower:
            method = "PUT"
        elif "delete" in fn_lower:
            method = "DELETE"
        elif "patch" in fn_lower:
            method = "PATCH"

        # Check options object in 2nd argument (e.g. fetch(url, { method: 'POST' }))
        if len(args) > 1 and args[1].type == "object":
            opt_text = source_bytes[args[1].start_byte:args[1].end_byte].decode("utf-8", errors="ignore")
            method_match = re.search(r"""method\s*:\s*['"`]([A-Z]+)['"`]""", opt_text, re.IGNORECASE)
            if method_match:
                method = method_match.group(1).upper()

        # Is this an API call?
        is_api_client = any(client in fn_lower for client in ("fetch", "axios", "http", "api", "request", "ajax"))
        if not is_api_client and not any(p in first_arg_text for p in ("/api", "/v1", "/v2", "/graphql", "/auth")):
            return

        # Extract URL template
        url_template = ""
        inferred_params = []

        if first_arg.type == "string":
            raw_val = first_arg_text.strip("'\"")
            if raw_val.startswith("/") or raw_val.startswith("http"):
                url_template = raw_val
        elif first_arg.type == "template_string":
            url_template, inferred_params = _normalize_ast_template_string(first_arg_text)
        elif first_arg.type == "binary_expression":
            # e.g. "/api/users/" + id
            left_text = source_bytes[first_arg.start_byte:first_arg.end_byte].decode("utf-8", errors="ignore")
            str_match = re.search(r"""['"`](/(?:api|v[0-9]|graphql|auth|rest|admin)[^'"`]*)['"`]""", left_text)
            if str_match:
                base_path = str_match.group(1)
                url_template = f"{base_path.rstrip('/')}/{{param}}"
                inferred_params = ["param"]

        if not url_template or len(url_template) < 2:
            return

        # Normalize and filter static assets
        if any(url_template.lower().endswith(ext) for ext in (".png", ".jpg", ".css", ".svg", ".woff", ".ico")):
            return

        if url_template.startswith("http://") or url_template.startswith("https://"):
            full_url = url_template
            parsed_u = urllib.parse.urlparse(url_template)
            template_path = parsed_u.path or "/"
        else:
            template_path = url_template if url_template.startswith("/") else f"/{url_template}"
            full_url = f"{base_origin}{template_path}" if base_origin else template_path

        key = f"{method} {template_path}"
        if key not in discovered and template_path != "/":
            discovered[key] = {
                "method": method,
                "template_path": template_path,
                "example_url": full_url,
                "source": "javascript_ast",
                "ast_call": fn_text,
                "inferred_params": inferred_params,
                "confidence": "inferred",
            }

    @classmethod
    def _handle_new_expression(cls, node, source_bytes: bytes, base_origin: str, discovered_ws: Dict[str, Dict[str, Any]]):
        cons_node = node.child_by_field_name("constructor")
        args_node = node.child_by_field_name("arguments")
        if not cons_node or not args_node:
            return

        cons_text = source_bytes[cons_node.start_byte:cons_node.end_byte].decode("utf-8", errors="ignore")
        if "WebSocket" not in cons_text:
            return

        args = [c for c in args_node.children if c.type not in ("(", ")", ",")]
        if not args:
            return

        ws_url_raw = source_bytes[args[0].start_byte:args[0].end_byte].decode("utf-8", errors="ignore").strip("`'\"")
        if ws_url_raw.startswith("ws://") or ws_url_raw.startswith("wss://") or ws_url_raw.startswith("/"):
            discovered_ws[ws_url_raw] = {
                "url": ws_url_raw,
                "source": "javascript_ast",
                "protocol": "websocket",
            }

    @classmethod
    def _handle_template_string(cls, node, source_bytes: bytes, base_origin: str, discovered_endpoints: Dict[str, Dict[str, Any]], discovered_graphql: List[Dict[str, Any]]):
        text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore").strip("`")

        # 1. Inline GraphQL Query / Mutation
        if re.search(r"\b(?:query|mutation|subscription)\b\s+([a-zA-Z0-9_]+)?", text):
            op_match = re.search(r"\b(query|mutation|subscription)\b\s*([a-zA-Z0-9_]+)?", text)
            op_type = op_match.group(1) if op_match else "query"
            op_name = op_match.group(2) if op_match and op_match.group(2) else "AnonymousOperation"

            # Parse with graphql-core if available
            parsed_doc = None
            try:
                import graphql
                parsed_doc = graphql.parse(text)
            except Exception:
                pass

            discovered_graphql.append({
                "operation_name": op_name,
                "operation_type": op_type,
                "raw_query": text[:1000],
                "has_valid_ast": parsed_doc is not None,
                "source": "javascript_ast",
            })

            # Also ensure POST /graphql exists in discovered endpoints
            gql_key = "POST /graphql"
            if gql_key not in discovered_endpoints:
                discovered_endpoints[gql_key] = {
                    "method": "POST",
                    "template_path": "/graphql",
                    "example_url": f"{base_origin}/graphql" if base_origin else "/graphql",
                    "source": "javascript_ast",
                    "is_graphql": True,
                    "graphql_operation": op_name,
                    "confidence": "inferred",
                }

        # 2. Template string API route (e.g. `/api/v2/products/${id}`)
        elif any(p in text for p in ("/api/", "/v1/", "/v2/", "/auth/")):
            template_path, params = _normalize_ast_template_string(text)
            if template_path.startswith("/"):
                key = f"GET {template_path}"
                if key not in discovered_endpoints:
                    discovered_endpoints[key] = {
                        "method": "GET",
                        "template_path": template_path,
                        "example_url": f"{base_origin}{template_path}" if base_origin else template_path,
                        "source": "javascript_ast",
                        "inferred_params": params,
                        "confidence": "inferred",
                    }
