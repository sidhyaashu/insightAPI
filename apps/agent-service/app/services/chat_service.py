"""Agentic LLM chat service with real-time tool execution and live telemetry streaming."""
from __future__ import annotations

import re
import uuid
import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.config import settings
from app.tools import (
    probe_http_endpoint,
    execute_curl,
    infer_openapi_schema,
    security_audit_endpoint,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are InsightBot, a world-class Agentic AI API Intelligence Engineer embedded in InsightAPI AI.

You act as an autonomous API pair-programmer and API architect. You inspect real endpoints, analyze live network traffic, debug cURL requests, design OpenAPI 3.1 & Postman specifications, validate schemas, architect microservice integrations, and perform security reasoning.

When real network execution results are provided in the context under `[Live Network Telemetry from Agent Execution]`:
- Use the REAL observed status code, latency, headers, and JSON fields in your response.
- Do NOT hallucinate mock endpoints when real execution data is present.

Reasoning & Response Guidelines:
1. **Internal Reasoning First**: Before composing your response, reason through the problem internally — analyze the request, the real network telemetry (if any), schema models, edge cases, and the best output structure. Do NOT expose this reasoning in your output.

2. **Rich Markdown & Visual Delivery**:
   - **HTTP & API Endpoints**: Use ````http```` blocks with the method and endpoint on line 1.
   - **Architecture & Sequence Diagrams**: Use ````mermaid```` blocks for sequence diagrams and system flows.
   - **Callout Alerts**: Use GitHub alerts (`> [!NOTE]`, `> [!TIP]`, `> [!WARNING]`, `> [!IMPORTANT]`, `> [!CAUTION]`).
   - **Structured Tables**: Use clean Markdown tables for parameter dictionaries, status codes, and type schemas.
   - **Syntax Highlighting**: Tag all code fences accurately (`json`, `yaml`, `python`, `typescript`, `bash`, `sql`).

Be concise, developer-centric, technically precise, and authoritative. Provide production-grade solutions."""


from app.core.utils import extract_urls as _extract_urls  # shared URL extractor; do not redefine here


def _extract_curl(text: str) -> Optional[str]:
    """Extract raw cURL commands from user message."""
    curl_match = re.search(r"(curl\s+(?:-[A-Za-z0-9\-_]+\s+[^\n]+|[^\n]+)+)", text, re.IGNORECASE)
    if curl_match:
        return curl_match.group(1).strip()
    return None


async def stream_agentic_chat(
    history: list[dict],
    user_message: str,
    crawl_context: str | None = None,
    model: str | None = None,
    auth_headers: Optional[Dict[str, str]] = None,
    approved_actions: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    db: Optional[Any] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Unified agentic execution stream powered by InvestigationRuntime (with ReActEngine fallback).
    Yields structured wire events:
      - {"type": "tool_start", "tool_id": "...", "tool": "...", "input": {...}}
      - {"type": "tool_result", "tool_id": "...", "tool": "...", "status": "completed"|"failed", "latency_ms": int, "output": {...}}
      - {"type": "approval_required", "approval_id": "...", "action": {...}}
      - {"type": "token", "content": "..."}
    """
    from app.runtime.service import InvestigationRequest, runtime_service
    from app.runtime.persistence import state_store

    effective_session_id = session_id or f"sess-{uuid.uuid4().hex[:12]}"
    detected_urls = _extract_urls(user_message)

    target_url = detected_urls[0] if detected_urls else None

    # Context Resolution: Fall back to existing active session or crawl context
    if not target_url and session_id:
        cached_state = await state_store.load_state(session_id, db=db)
        if cached_state and cached_state.current_url:
            target_url = cached_state.current_url

    if not target_url and crawl_context:
        ctx_urls = _extract_urls(crawl_context)
        if ctx_urls:
            target_url = ctx_urls[0]

    # Intent Detection: Check if user expresses autonomous discovery intent
    is_investigation_intent = bool(target_url) or any(
        kw in user_message.lower()
        for kw in ["discover", "crawl", "explore", "hidden", "undocumented", "map api", "investigate", "endpoints"]
    )

    if is_investigation_intent and target_url:
        req = InvestigationRequest(
            session_id=effective_session_id,
            target_url=target_url,
            goal_description=user_message,
            auth_headers=auth_headers or {},
            approved_actions=approved_actions or [],
            model=model,
            crawl_context=crawl_context,
        )
        async for event in runtime_service.stream_investigation(req, history=history, db=db):
            yield event
    else:
        from app.services.react_engine import ReActEngine
        async for event in ReActEngine.run(
            history=history,
            user_message=user_message,
            auth_headers=auth_headers,
            crawl_context=crawl_context,
            model=model,
            approved_actions=approved_actions,
            session_id=effective_session_id,
        ):
            yield event


# Legacy compatibility alias
async def stream_chat_response(
    history: list[dict],
    user_message: str,
    crawl_context: str | None = None,
    model: str | None = None,
) -> AsyncIterator[str]:
    """Compatibility wrapper that yields plain tokens."""
    async for event in stream_agentic_chat(history, user_message, crawl_context, model):
        if event.get("type") == "token":
            yield event.get("content", "")
