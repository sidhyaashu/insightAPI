import asyncio
import random
import logging
from typing import Optional
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
window.chrome = { runtime: {} };

// WebGL Vendor & Renderer Fingerprint Evasion
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.apply(this, arguments);
};

// Permissions API Evasion Patch
if (navigator.permissions) {
    const originalQuery = navigator.permissions.query;
    navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: 'prompt', onchange: null }) :
            originalQuery(parameters)
    );
}
"""


class BrowserManager:
    """
    Manages Playwright browser lifecycle with modern Chromium '--headless=new'
    stealth anti-bot evasion, network idle page load guards, and humanized action pacing.
    """
    def __init__(self, headless: bool = True, storage_state: Optional[dict] = None):
        self.headless = headless
        self._storage_state = storage_state
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self, storage_state: Optional[dict] = None):
        """
        Initialize Playwright and launch Chromium with modern stealth evasion flags.

        Accepts an optional ``storage_state`` dict (Playwright format: cookies + origins/localStorage).
        When supplied, the dict is passed directly to ``browser.new_context(storage_state=…)`` so the
        crawl agent begins the session already authenticated.  The value is only used here to configure
        the browser context — it is never logged, persisted, or included in any output document.
        """
        if not self._playwright:
            self._playwright = await async_playwright().start()
            
            # Launch arguments using Chrome's modern headless engine (--headless=new)
            args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--window-size=1280,800"
            ]
            if self.headless:
                args.append("--headless=new")

            # ── 5. Chrome Extensions Loading Support ────────────────────────
            from app.core.config import settings
            ext_paths = settings.CHROME_EXTENSION_PATHS or []
            if ext_paths:
                ext_str = ",".join(ext_paths)
                args.append(f"--disable-extensions-except={ext_str}")
                args.append(f"--load-extension={ext_str}")
                logger.info(f"🧩 BrowserManager: Loaded {len(ext_paths)} Chrome extension(s).")

            # ── 4. Protocol Proxy Support (mitmproxy) ───────────────────────
            launch_kwargs: dict = {"headless": self.headless, "args": args}
            if settings.PROXY_URL:
                launch_kwargs["proxy"] = {"server": settings.PROXY_URL}
                logger.info(f"🌐 BrowserManager: Routing traffic through proxy: {settings.PROXY_URL}")

            self._browser = await self._playwright.chromium.launch(**launch_kwargs)


            # Resolve storage_state: prefer argument, then constructor value
            active_storage_state = storage_state or self._storage_state

            context_kwargs: dict = {
                "viewport": {"width": 1280, "height": 800},
                "ignore_https_errors": True,
                "extra_http_headers": {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Upgrade-Insecure-Requests": "1"
                }
            }

            if active_storage_state:
                # Inject saved session (cookies + localStorage) into the new context.
                # We deliberately omit setting a custom User-Agent when restoring a session because
                # the saved cookies were issued to whatever UA the original login used.
                context_kwargs["storage_state"] = active_storage_state
                logger.info("BrowserManager: Launching context with injected storage_state (authenticated session).")
            else:
                # ── 1. Advanced Anti-Bot Stealth (fake-useragent) ────────────
                ua_string = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                )
                try:
                    from fake_useragent import UserAgent
                    ua = UserAgent(browsers=['chrome', 'edge'])
                    ua_string = ua.random
                    logger.debug("BrowserManager: Generated dynamic User-Agent via fake-useragent.")
                except ImportError:
                    pass

                context_kwargs["user_agent"] = ua_string

            self._context = await self._browser.new_context(**context_kwargs)
            await self._context.add_init_script(STEALTH_JS)

            # ── 1. Advanced Anti-Bot Stealth (playwright-stealth) ───────────
            if settings.STEALTH_MODE_ENABLED:
                try:
                    from playwright_stealth import stealth_async
                    await stealth_async(self._context)
                    logger.info("🥷 BrowserManager: Applied playwright-stealth anti-bot evasion scripts.")
                except ImportError:
                    pass


    async def save_storage_state(self, path: str) -> None:
        """
        Serialises the current browser context's cookies and localStorage to a local JSON file.

        Used by the ``insightapi login`` CLI command after the user has logged in manually.
        The resulting file contains live session cookies and should be treated with the same
        sensitivity as a password — keep it local and do not commit it to version control.
        """
        if not self._context:
            raise RuntimeError("BrowserManager.save_storage_state(): context is not initialised.")
        await self._context.storage_state(path=path)
        logger.info(f"Storage state saved to: {path}")

    async def new_page(self) -> Page:
        """Create and return a stealth-configured page instance."""
        if not self._context:
            await self.start()
        return await self._context.new_page()

    async def wait_for_network_idle_and_ready(self, page: Page, timeout_ms: int = 15000) -> bool:
        """
        Security & Stability Guard: Ensures the page is fully loaded and active network
        requests have settled before performing subsequent DOM actions. Uses PageNetworkStabilizer.
        """
        from app.engine.browser.stabilizer import PageNetworkStabilizer
        return await PageNetworkStabilizer.wait_until_stable(page, timeout_ms=timeout_ms)

    async def human_delay(self, min_ms: int = 500, max_ms: int = 1500):
        """Adds a randomized human-like jitter delay between UI interactions."""
        delay_sec = random.uniform(min_ms / 1000.0, max_ms / 1000.0)
        await asyncio.sleep(delay_sec)

    async def navigate_safely(self, page: Page, url: str, timeout_ms: int = 30000) -> bool:
        """
        Navigates safely with multi-stage fallback and network ready guard.
        """
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        strategies = ["commit", "domcontentloaded", "load"]
        for strategy in strategies:
            try:
                await page.goto(url, wait_until=strategy, timeout=timeout_ms)
                await self.wait_for_network_idle_and_ready(page, timeout_ms=10000)
                await self.human_delay(800, 1500)
                return True
            except Exception as e:
                logger.warning(f"Navigation with strategy '{strategy}' failed: {e}")
        return False

    async def stop(self):
        """Close browser context and stop Playwright driver gracefully."""
        if self._context:
            try:
                await self._context.close()
            except Exception as e:
                logger.debug(f"Context close error: {e}")
            self._context = None
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.debug(f"Browser close error: {e}")
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.debug(f"Playwright stop error: {e}")
            self._playwright = None
