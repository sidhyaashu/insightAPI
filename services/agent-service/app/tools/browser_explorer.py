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
    # Try Headless Playwright Browser with Stealth Evasions
    # ──────────────────────────────────────────────────────────────────────────
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 InsightAPI-Agent/2.0",
                viewport={"width": 1440, "height": 900},
                extra_http_headers=auth_headers or {},
            )

            # Apply Anti-Bot Stealth Evasions
            await apply_stealth_evasion(context)

            page = await context.new_page()

            # Attach Multi-Protocol Network Interceptor (REST & GraphQL)
            async def handle_response(response):
                try:
                    req = response.request
                    resource_type = req.resource_type
                    req_url = req.url

                    # Filter out static web assets and 3rd party telemetry
                    parsed_req = urllib.parse.urlparse(req_url)
                    req_host = parsed_req.hostname or ""
                    req_path = parsed_req.path or "/"
                    lower_path = req_path.lower()

                    if any(t in req_host for t in TELEMETRY_DOMAINS):
                        return
                    if any(lower_path.endswith(ext) for ext in STATIC_EXTENSIONS):
                        return

                    # Only capture XHR, Fetch, or API-like requests
                    is_api_type = resource_type in ("fetch", "xhr") or "/api/" in req_path or "/v1/" in req_path or "/v2/" in req_path or "/graphql" in req_path
                    if not is_api_type:
                        return

                    method = req.method.upper()
                    template_path = _normalize_route_template(req_path)

                    # Try to capture response body (capped)
                    resp_json = None
                    try:
                        resp_json = await response.json()
                    except Exception:
                        pass

                    # ── Multi-Protocol: GraphQL Disaggregation ────────────────
                    if "/graphql" in req_path and req.post_data:
                        ops = parse_graphql_payload(req.post_data)
                        for op in ops:
                            op_key = op["virtual_endpoint"]
                            if op_key not in intercepted_requests:
                                intercepted_requests[op_key] = {
                                    "method": "POST",
                                    "template_path": f"/graphql?op={op['operation_name']}",
                                    "example_url": req_url,
                                    "status_code": response.status,
                                    "content_type": response.headers.get("content-type", "application/json"),
                                    "is_graphql": True,
                                    "graphql_operation": op["operation_name"],
                                    "graphql_type": op["operation_type"],
                                    "sample_response": truncate_payload(resp_json, 1000) if resp_json else None,
                                    "occurrences": 1,
                                }
                            else:
                                intercepted_requests[op_key]["occurrences"] += 1
                        return

                    # ── Standard REST Interception ────────────────────────────
                    endpoint_key = f"{method} {template_path}"
                    if endpoint_key not in intercepted_requests:
                        intercepted_requests[endpoint_key] = {
                            "method": method,
                            "template_path": template_path,
                            "example_url": req_url,
                            "status_code": response.status,
                            "content_type": response.headers.get("content-type", ""),
                            "is_graphql": False,
                            "sample_response": truncate_payload(resp_json, 1000) if resp_json else None,
                            "occurrences": 1,
                        }
                    else:
                        intercepted_requests[endpoint_key]["occurrences"] += 1

                except Exception as e:
                    logger.debug(f"Error intercepting response: {e}")

            page.on("response", handle_response)

            # ── 1. Navigate to URL ────────────────────────────────────────────
            actions_taken.append({"action": "stealth_navigate", "target": url})
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_sec * 1000)
                await page.wait_for_timeout(1000)  # SPA hydration pause
            except Exception as e:
                logger.warning(f"Page goto timeout/warning for {url}: {e}")

            # ── 2. Auto-dismiss Cookie/Modal Overlays ─────────────────────────
            try:
                dismiss_btn = page.locator("button:has-text('Accept'), button:has-text('Allow'), button:has-text('Close'), button:has-text('Got it'), button:has-text('I Agree')").first
                if await dismiss_btn.is_visible(timeout=1000):
                    await dismiss_btn.click(timeout=1000)
                    await page.wait_for_timeout(500)
            except Exception:
                pass

            # ── 3. Semantic Contextual Form Injection ────────────────────────
            try:
                forms_filled = await fill_page_forms(page, max_forms=3)
                for ff in forms_filled:
                    actions_taken.append({
                        "action": "form_fill_and_submit",
                        "details": ff["fields_populated"],
                    })
            except Exception as e:
                logger.debug(f"Form filler step warning: {e}")

            # ── 4. Virtual Scrolling Pass for Lazy-Loaded Items ──────────────
            try:
                await page.evaluate("""async () => {
                    const scrollStep = 400;
                    for (let i = 0; i < 4; i++) {
                        window.scrollBy(0, scrollStep);
                        await new Promise(r => setTimeout(r, 200));
                    }
                    window.scrollTo(0, 0);
                }""")
                await page.wait_for_timeout(600)
                actions_taken.append({"action": "virtual_scroll_pass", "status": "completed"})
            except Exception:
                pass

            # ── 5. Recursive Shadow DOM Piercing & Safe Click Navigation ─────
            try:
                # Pierce open shadow DOM roots to find encapsulated interactive controls
                pierced_selectors = await page.evaluate("""() => {
                    const results = [];
                    function collectElements(root) {
                        const candidates = root.querySelectorAll('button, a[href], [role="button"], [role="tab"], select');
                        candidates.forEach(el => {
                            const text = el.innerText || el.getAttribute('aria-label') || el.tagName;
                            results.push(text.trim());
                        });
                        // Recurse into shadow roots
                        const all = root.querySelectorAll('*');
                        all.forEach(el => {
                            if (el.shadowRoot) {
                                collectElements(el.shadowRoot);
                            }
                        });
                    }
                    collectElements(document);
                    return results;
                }""")

                # State Hash Loop Detection
                state_hash = _compute_dom_state_hash(url, pierced_selectors)
                visited_states.add(state_hash)

                clickables = await page.query_selector_all("button, a[href], [role='button'], [role='tab'], select")
                clicks_done = 0

                for el in clickables[:30]:
                    if clicks_done >= max_clicks:
                        break

                    try:
                        is_visible = await el.is_visible()
                        if not is_visible:
                            continue

                        text = (await el.inner_text()).strip()
                        tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                        aria_label = (await el.get_attribute("aria-label")) or ""
                        el_desc = text or aria_label or tag_name

                        if not _is_safe_element_to_click(el_desc, tag_name):
                            continue

                        # Perform humanized click
                        await humanized_click(el)
                        clicks_done += 1
                        actions_taken.append({
                            "action": "click",
                            "element": tag_name,
                            "label": el_desc[:40],
                        })
                        await page.wait_for_timeout(600)  # allow AJAX responses

                    except Exception:
                        continue

            except Exception as e:
                logger.debug(f"Click iteration notice: {e}")

            await browser.close()

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
