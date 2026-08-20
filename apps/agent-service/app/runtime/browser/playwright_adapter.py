"""
runtime/browser/playwright_adapter.py — Playwright Implementation of BrowserAdapter.

Provides the primary computer-use actuator implementation for InsightAPI, wrapping
Playwright with anti-bot stealth evasion, multi-protocol network interception (REST & GraphQL),
Shadow DOM piercing, form automation, and accessibility tree extraction.

Reference: AGENTS.md §6, §18, §19.
"""
from __future__ import annotations

import re
import json
import hashlib
import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Set

from app.runtime.browser.adapter import (
    BrowserAdapter,
    PageState,
    AXNode,
    NetworkEvent,
    ConsoleEvent,
)
from app.tools.base import truncate_payload
from app.tools.stealth import apply_stealth_evasion, humanized_click
from app.tools.traffic_parser import _normalize_route_template, STATIC_EXTENSIONS
from app.tools.graphql_parser import parse_graphql_payload

logger = logging.getLogger("agent.runtime.browser.playwright")

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

UNSAFE_CLICK_PATTERNS = [
    r"\b(logout|log out|signout|sign out)\b",
    r"\b(delete|remove|destroy|purge|drop)\b",
    r"\b(cancel subscription|close account|terminate)\b",
    r"\b(pay|purchase|checkout|buy now|charge)\b",
    r"\b(reset password|change password)\b",
]


def _is_safe_element_to_click(text: str, tag_name: str) -> bool:
    """Check if an interactive element is safe to click autonomously."""
    lower = text.lower().strip()
    for pattern in UNSAFE_CLICK_PATTERNS:
        if re.search(pattern, lower):
            return False
    return True


class PlaywrightBrowserAdapter(BrowserAdapter):
    """
    Playwright implementation of BrowserAdapter with stealth and shadow-DOM piercing.
    """

    def __init__(
        self,
        auth_headers: Optional[Dict[str, str]] = None,
        headless: bool = True,
        viewport_width: int = 1440,
        viewport_height: int = 900,
    ) -> None:
        self.auth_headers = auth_headers or {}
        self.headless = headless
        self.viewport = {"width": viewport_width, "height": viewport_height}

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

        self._intercepted_events: Dict[str, NetworkEvent] = {}
        self._console_events: List[ConsoleEvent] = []
        self._visited_states: Set[str] = set()

    @property
    def page(self) -> Any:
        """Direct access to underlying Playwright page if needed by legacy helpers."""
        return self._page

    async def start(self) -> None:
        """Initialize the Playwright browser instance and stealth context."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        default_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        if self.auth_headers:
            default_headers.update(self.auth_headers)

        self._context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport=self.viewport,
            extra_http_headers=default_headers,
            locale="en-US",
            timezone_id="Asia/Kolkata",
        )

        # Apply stealth evasions
        await apply_stealth_evasion(self._context)

        self._page = await self._context.new_page()

        # Attach console logger
        self._page.on("console", lambda msg: self._console_events.append(
            ConsoleEvent(
                level=msg.type,
                text=msg.text,
                location=f"{msg.location.get('url', '')}:{msg.location.get('lineNumber', '')}" if msg.location else None,
            )
        ))

        # Attach multi-protocol network interceptor
        self._page.on("response", self._handle_network_response)

    async def _handle_network_response(self, response: Any) -> None:
        """Intercept, filter, and disaggregate REST & GraphQL network events."""
        try:
            req = response.request
            resource_type = req.resource_type
            req_url = req.url

            # Filter static assets and telemetry
            parsed_req = urllib.parse.urlparse(req_url)
            req_host = parsed_req.hostname or ""
            req_path = parsed_req.path or "/"
            lower_path = req_path.lower()

            if any(t in req_host for t in TELEMETRY_DOMAINS):
                return
            if any(lower_path.endswith(ext) for ext in STATIC_EXTENSIONS):
                return

            # Capture XHR, Fetch, and API-like requests
            content_type = (response.headers.get("content-type") or "").lower()
            is_api = (
                resource_type in ("fetch", "xhr", "eventsource", "websocket")
                or "application/json" in content_type
                or "application/xml" in content_type
                or "text/json" in content_type
                or any(k in lower_path for k in ("/api/", "/v1/", "/v2/", "/v3/", "/graphql", "/rest/", "/data/", "/services/", "/json/", "/bseindiaapi/", "/posts", "/users", "/comments", "/todos", "/albums", "/photos", "/products", "/items", "/orders", "/articles", "/tags"))
            )
            if not is_api:
                return

            method = req.method.upper()
            template_path = _normalize_route_template(req_path)

            resp_json = None
            try:
                resp_json = await response.json()
            except Exception:
                pass

            # Multi-Protocol: GraphQL Disaggregation
            if "/graphql" in req_path and req.post_data:
                ops = parse_graphql_payload(req.post_data)
                for op in ops:
                    op_key = op["virtual_endpoint"]
                    if op_key not in self._intercepted_events:
                        self._intercepted_events[op_key] = NetworkEvent(
                            method="POST",
                            url=req_url,
                            template_path=f"/graphql?op={op['operation_name']}",
                            status_code=response.status,
                            content_type=response.headers.get("content-type", "application/json"),
                            is_graphql=True,
                            graphql_operation=op["operation_name"],
                            graphql_type=op["operation_type"],
                            sample_response=truncate_payload(resp_json, 1000) if resp_json else None,
                            occurrences=1,
                        )
                    else:
                        self._intercepted_events[op_key].occurrences += 1
                return

            # Standard REST Interception
            endpoint_key = f"{method} {template_path}"
            if endpoint_key not in self._intercepted_events:
                self._intercepted_events[endpoint_key] = NetworkEvent(
                    method=method,
                    url=req_url,
                    template_path=template_path,
                    status_code=response.status,
                    content_type=response.headers.get("content-type", ""),
                    is_graphql=False,
                    sample_response=truncate_payload(resp_json, 1000) if resp_json else None,
                    occurrences=1,
                )
            else:
                self._intercepted_events[endpoint_key].occurrences += 1

        except Exception as e:
            logger.debug(f"Error intercepting response: {e}")

    async def navigate(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout_sec: float = 25.0,
    ) -> PageState:
        """Navigate to target URL, dismiss overlays, and return PageState."""
        if not self._page:
            await self.start()

        try:
            await self._page.goto(url, wait_until=wait_until, timeout=timeout_sec * 1000)
            await self._page.wait_for_timeout(1000)  # SPA hydration pause
        except Exception as e:
            logger.warning(f"Playwright navigation warning for {url}: {e}")

        # Auto-dismiss cookie/modal overlays
        await self._auto_dismiss_overlays()

        return await self.get_page_state()

    async def _auto_dismiss_overlays(self) -> None:
        """Dismiss common cookie banners and modal overlays."""
        if not self._page:
            return
        try:
            dismiss_btn = self._page.locator(
                "button:has-text('Accept'), button:has-text('Allow'), button:has-text('Close'), button:has-text('Got it'), button:has-text('I Agree')"
            ).first
            if await dismiss_btn.is_visible(timeout=1000):
                await dismiss_btn.click(timeout=1000)
                await self._page.wait_for_timeout(500)
        except Exception:
            pass

    async def get_page_state(self) -> PageState:
        """Compute state hash and return current PageState."""
        if not self._page:
            return PageState(url="")

        current_url = self._page.url
        title = await self._page.title()

        # Compute DOM state hash from interactive elements
        elements = await self._page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button, a[href], [role="button"], select').forEach(el => {
                results.push((el.innerText || el.getAttribute('aria-label') || el.tagName).trim());
            });
            return results.slice(0, 30);
        }""")
        raw_hash = f"{current_url}:{':'.join(sorted(elements))}"
        state_hash = hashlib.md5(raw_hash.encode("utf-8")).hexdigest()[:12]
        self._visited_states.add(state_hash)

        # Detect WAF or Edge bot challenges
        is_waf = False
        waf_detail = None
        lower_title = title.lower().strip()
        if any(w in lower_title for w in ("access denied", "just a moment...", "security challenge", "attention required", "cloudflare", "blocked")):
            is_waf = True
            waf_detail = f"Edge protection challenge detected: '{title}'"

        return PageState(
            url=current_url,
            title=title,
            status_code=403 if is_waf else 200,
            state_hash=state_hash,
            is_spa=True,
            is_waf_blocked=is_waf,
            waf_details=waf_detail,
        )

    async def get_accessibility_tree(self) -> List[AXNode]:
        """
        Extract interactive semantic nodes across standard DOM and pierced Shadow DOM roots.
        """
        if not self._page:
            return []

        raw_elements = await self._page.evaluate("""() => {
            const results = [];
            let idCounter = 0;

            function collectElements(root) {
                const candidates = root.querySelectorAll('button, a[href], [role="button"], [role="tab"], select, input, textarea');
                candidates.forEach(el => {
                    const tag = el.tagName.toLowerCase();
                    const text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim();
                    const role = el.getAttribute('role') || (tag === 'button' ? 'button' : tag === 'a' ? 'link' : tag);
                    idCounter++;
                    results.push({
                        ref_id: `elem-${idCounter}`,
                        role: role,
                        name: text,
                        tag_name: tag,
                        is_clickable: true
                    });
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

        nodes: List[AXNode] = []
        for r in raw_elements:
            nodes.append(
                AXNode(
                    ref_id=r.get("ref_id"),
                    role=r.get("role", ""),
                    name=r.get("name", ""),
                    tag_name=r.get("tag_name", ""),
                    is_clickable=r.get("is_clickable", True),
                )
            )
        return nodes

    async def get_internal_links(self, base_url: str) -> List[str]:
        """
        Extract all same-origin, in-scope internal HTML navigation URLs on the current page.
        Filters out static assets, fragment-only links, and external third-party domains.
        """
        if not self._page:
            return []

        try:
            parsed_base = urllib.parse.urlparse(base_url)
            base_domain = parsed_base.hostname or ""

            raw_hrefs = await self._page.evaluate("""() => {
                const links = [];
                document.querySelectorAll('a[href], nav a, header a, aside a, .navbar a, .pagination a, [role="link"]').forEach(a => {
                    const href = a.getAttribute('href');
                    if (href && !href.startsWith('#') && !href.startsWith('javascript:') && !href.startsWith('mailto:') && !href.startsWith('tel:')) {
                        links.push(href);
                    }
                });
                return Array.from(new Set(links));
            }""")

            internal_urls: Set[str] = set()
            for href in raw_hrefs:
                href_clean = href.strip()
                if not href_clean:
                    continue

                full_url = urllib.parse.urljoin(base_url, href_clean)
                parsed = urllib.parse.urlparse(full_url)

                # Must match base scheme and domain (or subdomain)
                if parsed.scheme not in ("http", "https"):
                    continue
                if parsed.hostname != base_domain and not (parsed.hostname or "").endswith(f".{base_domain}"):
                    continue

                # Filter static assets
                path_lower = parsed.path.lower()
                if any(path_lower.endswith(ext) for ext in STATIC_EXTENSIONS):
                    continue

                # Strip trailing fragments
                clean_target = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))
                if clean_target != base_url.rstrip("/"):
                    internal_urls.add(clean_target)

            return list(internal_urls)
        except Exception as e:
            logger.debug(f"Error extracting internal links: {e}")
            return []

    async def click(self, selector_or_ref: str, humanized: bool = True) -> bool:
        """Click element by selector or text with safety guardrails."""
        if not self._page:
            return False

        try:
            el = await self._page.query_selector(selector_or_ref)
            if not el or not await el.is_visible():
                return False

            text = (await el.inner_text()).strip()
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            aria = (await el.get_attribute("aria-label")) or ""
            desc = text or aria or tag

            if not _is_safe_element_to_click(desc, tag):
                logger.info(f"Skipped unsafe element click: {desc}")
                return False

            if humanized:
                await humanized_click(el)
            else:
                await el.click()

            await self._page.wait_for_timeout(600)  # allow AJAX responses
            return True
        except Exception as e:
            logger.debug(f"Click failed for {selector_or_ref}: {e}")
            return False

    async def type_text(self, selector_or_ref: str, text: str) -> bool:
        """Input text into target element."""
        if not self._page:
            return False
        try:
            el = await self._page.query_selector(selector_or_ref)
            if el and await el.is_visible():
                await el.fill(text)
                return True
            return False
        except Exception as e:
            logger.debug(f"type_text failed: {e}")
            return False

    async def scroll(self, direction: str = "down", amount: int = 400) -> None:
        """Perform virtual scrolling pass for lazy-loaded elements."""
        if not self._page:
            return
        delta = amount if direction == "down" else -amount
        try:
            await self._page.evaluate(f"""async () => {{
                window.scrollBy(0, {delta});
            }}""")
            await self._page.wait_for_timeout(400)
        except Exception:
            pass

    async def wait(self, ms: int) -> None:
        """Wait for specified milliseconds."""
        if self._page:
            await self._page.wait_for_timeout(ms)

    async def screenshot(self) -> Optional[bytes]:
        """Capture page screenshot."""
        if not self._page:
            return None
        try:
            return await self._page.screenshot(full_page=False)
        except Exception:
            return None

    def get_network_events(self) -> List[NetworkEvent]:
        """Return all unique intercepted network events."""
        return list(self._intercepted_events.values())

    def get_console_events(self) -> List[ConsoleEvent]:
        """Return all console events."""
        return list(self._console_events)

    async def close(self) -> None:
        """Close browser resources cleanly."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.debug(f"Browser close cleanup: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
