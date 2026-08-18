"""Autonomous Playwright Deep Browser Exploration & Multi-Protocol Intelligence Engine."""
from __future__ import annotations

import re
import json
import time
import hashlib
import logging
import asyncio
import urllib.parse
from typing import Any, Dict, List, Optional, Set

from app.tools.base import ToolResult, truncate_payload
from app.tools.guardrails import validate_target_url
from app.tools.traffic_parser import _normalize_route_template, STATIC_EXTENSIONS
from app.tools.stealth import apply_stealth_evasion, humanized_click
from app.tools.form_filler import fill_page_forms
from app.tools.graphql_parser import parse_graphql_payload
from app.tools.dependency_chainer import chain_api_dependencies

logger = logging.getLogger(__name__)

# Sensitive action labels that should NEVER be clicked during autonomous exploration
UNSAFE_CLICK_PATTERNS = [
    r"\b(logout|log out|signout|sign out)\b",
    r"\b(delete|remove|destroy|purge|drop)\b",
    r"\b(cancel subscription|close account|terminate)\b",
    r"\b(pay|purchase|checkout|buy now|charge)\b",
    r"\b(reset password|change password)\b",
]

TELEMETRY_DOMAINS = {
    "google-analytics.com",
    "googletagmanager.com",
    "sentry.io",
    "hotjar.com",
    "segment.io",
    "mixpanel.com",
    "facebook.com",
    "doubleclick.net",
    "intercom.io",
}


def _is_safe_element_to_click(text: str, element_type: str) -> bool:
    """Check if an interactive element is safe to click autonomously."""
    lower_text = text.lower().strip()
    for pattern in UNSAFE_CLICK_PATTERNS:
        if re.search(pattern, lower_text):
            return False
    return True


def _compute_dom_state_hash(url: str, elements: List[str]) -> str:
    """Compute a hash of the current DOM state to avoid infinite exploration loops."""
    raw = f"{url}:{':'.join(sorted(elements[:30]))}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


async def explore_web_app_browser(
    url: str,
    max_clicks: int = 15,
    timeout_sec: float = 25.0,
    auth_headers: Optional[Dict[str, str]] = None,
) -> ToolResult:
    """
    Launch an autonomous stealth headless browser session, navigate the web app,
    pierce Shadow DOMs, execute virtual scrolling, contextually populate and submit forms,
    and intercept all hidden REST, GraphQL, and AJAX endpoints.
    """
    start_time = time.perf_counter()
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    # SSRF guardrail check
    is_safe, err_msg = validate_target_url(url)
    if not is_safe:
        return ToolResult(
            tool_name="browser_explore_app",
            status="error",
            latency_ms=0,
            error=f"Guardrail Blocked: {err_msg}",
            data={"url": url},
        )

    parsed_target = urllib.parse.urlparse(url)
    target_hostname = parsed_target.hostname or ""

    intercepted_requests: Dict[str, Dict[str, Any]] = {}
    actions_taken: List[Dict[str, Any]] = []
    visited_states: Set[str] = set()

    # ──────────────────────────────────────────────────────────────────────────
    # Headless Playwright Browser with Stealth Evasions via BrowserAdapter
    # ──────────────────────────────────────────────────────────────────────────
    try:
        from app.runtime.browser.playwright_adapter import PlaywrightBrowserAdapter

        async with PlaywrightBrowserAdapter(auth_headers=auth_headers) as adapter:
            actions_taken.append({"action": "stealth_navigate", "target": url})
            page_state = await adapter.navigate(url, timeout_sec=timeout_sec)
            if page_state.state_hash:
                visited_states.add(page_state.state_hash)

            # ── 2. Contextual Form Injection ──────────────────────────────────
            try:
                if adapter.page:
                    forms_filled = await fill_page_forms(adapter.page, max_forms=3)
                    for ff in forms_filled:
                        actions_taken.append({
                            "action": "form_fill_and_submit",
                            "details": ff["fields_populated"],
                        })
            except Exception as e:
                logger.debug(f"Form filler step warning: {e}")

            # ── 3. Virtual Scrolling Pass ─────────────────────────────────────
            await adapter.scroll("down", 400)
            actions_taken.append({"action": "virtual_scroll_pass", "status": "completed"})

            # ── 4. Shadow DOM Piercing & Interactive Element Exploration ──────
            try:
                ax_nodes = await adapter.get_accessibility_tree()
                clicks_done = 0
                if adapter.page:
                    clickables = await adapter.page.query_selector_all("button, a[href], [role='button'], [role='tab'], select")
                    for el in clickables[:30]:
                        if clicks_done >= max_clicks:
                            break
                        try:
                            if not await el.is_visible():
                                continue
                            text = (await el.inner_text()).strip()
                            tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                            aria_label = (await el.get_attribute("aria-label")) or ""
                            el_desc = text or aria_label or tag_name

                            if not _is_safe_element_to_click(el_desc, tag_name):
                                continue

                            await humanized_click(el)
                            clicks_done += 1
                            actions_taken.append({
                                "action": "click",
                                "element": tag_name,
                                "label": el_desc[:40],
                            })
                            await adapter.wait(600)
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"Click iteration notice: {e}")

            # Collect intercepted network events from adapter
            for evt in adapter.get_network_events():
                key = f"{evt.method} {evt.template_path}"
                intercepted_requests[key] = {
                    "method": evt.method,
                    "template_path": evt.template_path,
                    "example_url": evt.url,
                    "status_code": evt.status_code,
                    "content_type": evt.content_type,
                    "is_graphql": evt.is_graphql,
                    "graphql_operation": evt.graphql_operation,
                    "graphql_type": evt.graphql_type,
                    "sample_response": evt.sample_response,
                    "occurrences": evt.occurrences,
                }

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        raw_discovered = list(intercepted_requests.values())

        # ── 6. Dependency Chaining & Correlation ──────────────────────────────
        chained_catalog = chain_api_dependencies(raw_discovered)

        return ToolResult(
            tool_name="browser_explore_app",
            status="success",
            latency_ms=latency_ms,
            data={
                "target_url": url,
                "engine": "Playwright Stealth Chromium with Shadow DOM & Form Filler",
                "actions_executed": len(actions_taken),
                "actions_log": actions_taken,
                "hidden_endpoints_discovered": len(raw_discovered),
                "endpoints": raw_discovered,
                "dependency_chain": chained_catalog,
            },
        )

    except ImportError:
        logger.info("Playwright not installed, falling back to static AST DOM analysis.")
        return await _fallback_static_exploration(url, target_hostname, start_time, auth_headers)
    except Exception as e:
        logger.warning(f"Playwright browser exploration failed ({e}), falling back to static exploration.")
        return await _fallback_static_exploration(url, target_hostname, start_time, auth_headers)


async def _fallback_static_exploration(
    url: str,
    target_hostname: str,
    start_time: float,
    auth_headers: Optional[Dict[str, str]] = None,
) -> ToolResult:
    """Fallback exploration extracting embedded script APIs and SPA routes when browser is not available."""
    import httpx
    actions_taken = [{"action": "fallback_http_analysis", "target": url}]
    discovered_endpoints: List[Dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=auth_headers or {})
            html = resp.text

            # Extract embedded API routes and endpoints via regex from JS/HTML
            api_patterns = re.findall(r'["\'](/api/v[0-9]+/[a-zA-Z0-9_\-\/{}]*|/api/[a-zA-Z0-9_\-\/{}]*|/v[0-9]+/[a-zA-Z0-9_\-\/{}]*|/graphql)[\'"]', html)
            unique_paths = list(set(api_patterns))

            for path in unique_paths[:15]:
                template = _normalize_route_template(path)
                discovered_endpoints.append({
                    "method": "GET" if "/graphql" not in path else "POST",
                    "template_path": template,
                    "example_url": f"{url.rstrip('/')}{path}",
                    "status_code": 200,
                    "is_graphql": "/graphql" in path.lower(),
                    "sample_response": None,
                    "occurrences": 1,
                })

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        chained_catalog = chain_api_dependencies(discovered_endpoints)

        return ToolResult(
            tool_name="browser_explore_app",
            status="success",
            latency_ms=latency_ms,
            data={
                "target_url": url,
                "engine": "Static DOM & Script AST Fallback",
                "actions_executed": 1,
                "actions_log": actions_taken,
                "hidden_endpoints_discovered": len(discovered_endpoints),
                "endpoints": discovered_endpoints,
                "dependency_chain": chained_catalog,
            },
        )
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return ToolResult(
            tool_name="browser_explore_app",
            status="error",
            latency_ms=latency_ms,
            error=f"Exploration failed: {str(e)}",
            data={"target_url": url},
        )
