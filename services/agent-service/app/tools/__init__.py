"""Agent Tool Library for real-time in-chat execution."""
from app.tools.base import ToolResult, ToolMetadata
from app.tools.http_probe import probe_http_endpoint
from app.tools.curl_executor import execute_curl, parse_curl_command
from app.tools.schema_inferencer import infer_openapi_schema
from app.tools.security_checker import security_audit_endpoint

from app.tools.browser_explorer import explore_web_app_browser
from app.tools.stealth import apply_stealth_evasion, humanized_click, humanized_type
from app.tools.form_filler import fill_page_forms, get_contextual_value_for_input
from app.tools.graphql_parser import parse_graphql_payload
from app.tools.dependency_chainer import chain_api_dependencies, extract_identifiers_from_payload

__all__ = [
    "ToolResult",
    "ToolMetadata",
    "probe_http_endpoint",
    "execute_curl",
    "parse_curl_command",
    "infer_openapi_schema",
    "security_audit_endpoint",
    "explore_web_app_browser",
    "apply_stealth_evasion",
    "humanized_click",
    "humanized_type",
    "fill_page_forms",
    "get_contextual_value_for_input",
    "parse_graphql_payload",
    "chain_api_dependencies",
    "extract_identifiers_from_payload",
]
