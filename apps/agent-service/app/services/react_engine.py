"""Autonomous Multi-Step ReAct (Reason + Act) Execution Engine."""
from __future__ import annotations

import re
import json
import uuid
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.tools import (
    probe_http_endpoint,
    execute_curl,
    infer_openapi_schema,
    security_audit_endpoint,
    explore_web_app_browser,
)
from app.tools.traffic_parser import parse_har_traffic
from app.tools.test_generator import generate_pytest_suite, generate_postman_collection
from app.runtime.event_bridge import publish_raw

logger = logging.getLogger(__name__)

DESTRUCTIVE_METHODS = {"DELETE", "PUT", "PATCH"}
MAX_REACT_STEPS = 5


def _is_action_destructive(method: str, url: str) -> bool:
    """Identify if an HTTP action is potentially destructive and requires human approval."""
    method_upper = method.upper().strip()
    if method_upper in DESTRUCTIVE_METHODS:
        return True
    if method_upper == "POST" and any(word in url.lower() for word in ["delete", "remove", "drop", "cancel", "purge", "revoke"]):
        return True
    return False


from app.core.utils import extract_urls as _extract_all_urls  # shared URL extractor; do not redefine here


def _extract_curl(text: str) -> Optional[str]:
    curl_match = re.search(r"(curl\s+(?:-[A-Za-z0-9\-_]+\s+[^\n]+|[^\n]+)+)", text, re.IGNORECASE)
    if curl_match:
        return curl_match.group(1).strip()
    return None


def _is_har_or_json_dump(text: str) -> bool:
    trimmed = text.strip()
    return ('"log"' in trimmed and '"entries"' in trimmed) or ('"swagger"' in trimmed or '"openapi"' in trimmed)


class ReActEngine:
    """Multi-Step ReAct Execution Engine for InsightAPI."""

    @staticmethod
    async def run(
        history: list[dict],
        user_message: str,
        auth_headers: Optional[Dict[str, str]] = None,
        crawl_context: str | None = None,
        model: str | None = None,
        approved_actions: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute multi-step ReAct loop and stream tool events + synthesis tokens.

        Yields structured event dicts to the WebSocket client (unchanged).
        Also publishes typed AgentEvents to AgentEventBus (fire-and-forget)
        when session_id is provided.
        """
        async def _execution_stream() -> AsyncIterator[Dict[str, Any]]:
            from app.core.llm import ModelRouter, ModelTier, extract_text_content
            from app.services.chat_service import SYSTEM_PROMPT

            approved_set = set(approved_actions or [])
            telemetry_log: List[str] = []
            discovered_endpoints: List[Dict[str, Any]] = []

            # ──────────────────────────────────────────────────────────────────────
            # Step 1: Detect File / HAR Traffic Dumps
            # ──────────────────────────────────────────────────────────────────────
            if _is_har_or_json_dump(user_message):
                har_tool_id = f"tool-{uuid.uuid4().hex[:8]}"
                yield {
                    "type": "tool_start",
                    "tool_id": har_tool_id,
                    "tool": "parse_har_traffic",
                    "title": "Ingesting Network Traffic Log (HAR)",
                    "input": {"payload_length": len(user_message)},
                }
                har_res = parse_har_traffic(user_message)
                yield {
                    "type": "tool_result",
                    "tool_id": har_tool_id,
                    "tool": "parse_har_traffic",
                    "status": har_res.status,
                    "latency_ms": har_res.latency_ms,
                    "output": har_res.data,
                    "error": har_res.error,
                }
                if har_res.status == "success":
                    endpoints = har_res.data.get("endpoints", [])
                    discovered_endpoints.extend(endpoints)
                    telemetry_log.append(
                        f"[HAR Traffic Ingestion Telemetry]\n"
                        f"Scanned {har_res.data.get('total_entries_scanned')} entries, "
                        f"found {len(endpoints)} unique API endpoints.\n"
                        f"Endpoints Sample: {json.dumps(endpoints[:10])}\n"
                    )

            # ──────────────────────────────────────────────────────────────────────
            # Step 2: Detect cURL Commands
            # ──────────────────────────────────────────────────────────────────────
            curl_cmd = _extract_curl(user_message)
            if curl_cmd:
                curl_tool_id = f"tool-{uuid.uuid4().hex[:8]}"
                yield {
                    "type": "tool_start",
                    "tool_id": curl_tool_id,
                    "tool": "execute_curl",
                    "title": "Executing cURL Request",
                    "input": {"curl_command": curl_cmd[:200]},
                }
                res = await execute_curl(curl_cmd)
                yield {
                    "type": "tool_result",
                    "tool_id": curl_tool_id,
                    "tool": "execute_curl",
                    "status": "completed" if res.status == "success" else "failed",
                    "latency_ms": res.latency_ms,
                    "output": res.data,
                    "error": res.error,
                }
                if res.status == "success":
                    discovered_endpoints.append({
                        "method": res.data.get("method"),
                        "path": res.data.get("url"),
                        "status_code": res.data.get("status_code"),
                    })
                    telemetry_log.append(
                        f"[cURL Telemetry]\n"
                        f"URL: {res.data.get('url')} | Status: {res.data.get('status_code')}\n"
                        f"Body: {json.dumps(res.data.get('body', {}))[:5000]}\n"
                    )

            # ──────────────────────────────────────────────────────────────────────
            # Step 3: Single Direct HTTP Probe (Ad-Hoc Pair-Programming Testing)
            # ──────────────────────────────────────────────────────────────────────
            urls = _extract_all_urls(user_message)
            for target_url in urls[:MAX_REACT_STEPS]:  # enforce MAX_REACT_STEPS budget
                method = "GET"
                # Check for explicit method mention e.g. "POST https://..." or "DELETE https://..."
                method_match = re.search(r"\b(POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\s+" + re.escape(target_url), user_message, re.IGNORECASE)
                if method_match:
                    method = method_match.group(1).upper()

                # Human-in-the-Loop Approval Check for Destructive Actions
                is_destructive = _is_action_destructive(method, target_url)
                action_key = f"{method}:{target_url}"
                if is_destructive and action_key not in approved_set:
                    approval_id = f"appr-{uuid.uuid4().hex[:8]}"
                    yield {
                        "type": "approval_required",
                        "approval_id": approval_id,
                        "action": {
                            "method": method,
                            "url": target_url,
                            "description": f"Executing potentially destructive {method} request on live server.",
                        },
                    }
                    # Skip executing this destructive action until approved
                    continue

                probe_id = f"tool-{uuid.uuid4().hex[:8]}"
                yield {
                    "type": "tool_start",
                    "tool_id": probe_id,
                    "tool": "probe_http_endpoint",
                    "title": f"Probing {method} {target_url}",
                    "input": {"url": target_url, "method": method, "authenticated": bool(auth_headers)},
                }
                probe_res = await probe_http_endpoint(
                    url=target_url,
                    method=method,
                    headers=auth_headers,
                )
                yield {
                    "type": "tool_result",
                    "tool_id": probe_id,
                    "tool": "probe_http_endpoint",
                    "status": "completed" if probe_res.status == "success" else "failed",
                    "latency_ms": probe_res.latency_ms,
                    "output": probe_res.data,
                    "error": probe_res.error,
                }

                if probe_res.status == "success":
                    discovered_endpoints.append({
                        "method": method,
                        "path": probe_res.data.get("url"),
                        "status_code": probe_res.data.get("status_code"),
                    })
                    telemetry_log.append(
                        f"[Probe Telemetry: {method} {target_url}]\n"
                        f"Status: {probe_res.data.get('status_code')} | Latency: {probe_res.latency_ms}ms\n"
                        f"Headers: {json.dumps(probe_res.data.get('response_headers', {}))}\n"
                        f"Body: {json.dumps(probe_res.data.get('body', {}))[:8000]}\n"
                    )

                    # Chained Schema Inference if response is JSON
                    if probe_res.data.get("is_json") and isinstance(probe_res.data.get("body"), (dict, list)):
                        schema_tool_id = f"tool-{uuid.uuid4().hex[:8]}"
                        yield {
                            "type": "tool_start",
                            "tool_id": schema_tool_id,
                            "tool": "infer_openapi_schema",
                            "title": "Inferring OpenAPI 3.1 Schema",
                            "input": {"field_count": len(probe_res.data.get("body")) if isinstance(probe_res.data.get("body"), dict) else 0},
                        }
                        schema_res = infer_openapi_schema(probe_res.data.get("body"))
                        yield {
                            "type": "tool_result",
                            "tool_id": schema_tool_id,
                            "tool": "infer_openapi_schema",
                            "status": "completed",
                            "latency_ms": 1,
                            "output": schema_res.data,
                        }
                        if schema_res.status == "success":
                            telemetry_log.append(
                                f"[Inferred OpenAPI Schema]\n{json.dumps(schema_res.data.get('schema', {}))[:4000]}\n"
                            )

                    # Chained Security Audit if requested
                    if any(w in user_message.lower() for w in ["security", "audit", "vulnerability", "tls", "cors"]):
                        sec_id = f"tool-{uuid.uuid4().hex[:8]}"
                        yield {
                            "type": "tool_start",
                            "tool_id": sec_id,
                            "tool": "security_audit_endpoint",
                            "title": f"Security & TLS Header Audit ({target_url})",
                            "input": {"url": target_url},
                        }
                        sec_res = await security_audit_endpoint(url=target_url)
                        yield {
                            "type": "tool_result",
                            "tool_id": sec_id,
                            "tool": "security_audit_endpoint",
                            "status": "completed" if sec_res.status == "success" else "failed",
                            "latency_ms": sec_res.latency_ms,
                            "output": sec_res.data,
                            "error": sec_res.error,
                        }
                        if sec_res.status == "success":
                            telemetry_log.append(
                                f"[Security Audit Findings]\n"
                                f"Score: {sec_res.data.get('security_score')}/100\n"
                                f"Findings: {json.dumps(sec_res.data.get('findings', []))}\n"
                            )

            # ──────────────────────────────────────────────────────────────────────
            # Step 4: Stream Synthesized Response via LLM
            # ──────────────────────────────────────────────────────────────────────
            try:
                client = ModelRouter.get_llm(
                    tier=ModelTier.SMART,
                    model=model,
                    temperature=0.7,
                    streaming=True,
                )

                messages = [SystemMessage(content=SYSTEM_PROMPT)]
                if crawl_context:
                    messages.append(SystemMessage(content=f"[Context]\n{crawl_context}"))

                if telemetry_log:
                    telemetry_str = "\n\n".join(telemetry_log)
                    messages.append(
                        SystemMessage(
                            content=(
                                f"IMPORTANT: The agent has autonomously executed real network actions before responding.\n"
                                f"Verified ground-truth telemetry:\n\n{telemetry_str}"
                            )
                        )
                    )

                for msg in history[-20:]:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))

                messages.append(HumanMessage(content=user_message))

                async for chunk in client.astream(messages):
                    token = extract_text_content(chunk.content if hasattr(chunk, "content") else chunk)
                    if token:
                        yield {"type": "token", "content": token}

            except Exception as e:
                logger.error(f"ReAct LLM streaming error: {e}")
                yield {
                    "type": "token",
                    "content": f"\n\n> [!WARNING]\n> **Agent Streaming Error**: {str(e)}\n\nPlease ensure your LLM credentials are configured in `.env`.",
                }

        async for event in _execution_stream():
            if session_id:
                await publish_raw(session_id, event)
            yield event
