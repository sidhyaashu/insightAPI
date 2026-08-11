"""
stabilizer.py — Network & Page Loading Stability Tracker for InsightAPI AI

Design
------
Replaces hardcoded asyncio.sleep() delays with a dynamic stability tracking engine:
1. Listens to Playwright request, response, and requestfailed events to maintain in-flight count.
2. Enforces a 400ms "quiet window" with 0 pending XHR/fetch requests before declaring network idle.
3. Detects common CSS loading indicators (.spinner, .loading, [aria-busy="true"], .skeleton, loader animations)
   and waits until they detach or become invisible.
4. Provides configurable timeout guard so execution never hangs indefinitely.
"""
from __future__ import annotations

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

logger = logging.getLogger("engine.stabilizer")

COMMON_LOADING_SELECTORS: List[str] = [
    ".spinner",
    ".loading",
    ".loader",
    ".skeleton",
    "[aria-busy='true']",
    "[data-loading='true']",
    ".MuiCircularProgress-root",
    ".ant-spin",
    ".loading-spinner",
    "#loading",
    "#spinner",
]


class PageNetworkStabilizer:
    """
    Monitors in-flight network traffic and UI loading spinners to ensure the browser
    state and network quiet period have settled before extracting DOM or proceeding.
    """

    @classmethod
    async def wait_until_stable(
        cls,
        page: Page,
        timeout_ms: int = 10000,
        quiet_window_ms: int = 400,
    ) -> bool:
        """
        Waits until:
        1. All in-flight XHR/fetch requests settle for a continuous quiet_window_ms duration.
        2. All visible loading spinners/indicators disappear.

        Returns True if stability reached within timeout_ms, False on timeout.
        """
        if not page:
            return True

        in_flight = 0
        last_activity_time = time.time()

        def on_req(req):
            nonlocal in_flight, last_activity_time
            # Ignore static asset requests for network quiet window
            resource_type = getattr(req, "resource_type", "")
            if resource_type in ["image", "stylesheet", "font", "media"]:
                return
            in_flight += 1
            last_activity_time = time.time()

        def on_res_or_fail(res_or_req):
            nonlocal in_flight, last_activity_time
            in_flight = max(0, in_flight - 1)
            last_activity_time = time.time()

        # Attach Playwright network event listeners
        try:
            page.on("request", on_req)
            page.on("response", on_res_or_fail)
            page.on("requestfailed", on_res_or_fail)
        except Exception as e:
            logger.debug(f"Stabilizer listener attach warning: {e}")

        start_time = time.time()
        timeout_sec = timeout_ms / 1000.0
        quiet_window_sec = quiet_window_ms / 1000.0

        try:
            # 1. Wait for network quiet window (0 in-flight requests for quiet_window_sec)
            while (time.time() - start_time) < timeout_sec:
                now = time.time()
                quiet_duration = now - last_activity_time

                if in_flight == 0 and quiet_duration >= quiet_window_sec:
                    logger.debug(f"⚡ Network quiet period achieved (0 in-flight for {quiet_duration:.2f}s).")
                    break

                await asyncio.sleep(0.1)

            # 2. Check and wait for UI loading indicators to vanish
            await cls._wait_for_spinners_to_disappear(page, timeout_sec=max(1.0, timeout_sec - (time.time() - start_time)))

            elapsed = time.time() - start_time
            is_stable = elapsed < timeout_sec
            logger.debug(f"PageNetworkStabilizer finished in {elapsed:.2f}s | Stable: {is_stable}")
            return is_stable

        except Exception as e:
            logger.warning(f"PageNetworkStabilizer error: {e}")
            return True
        finally:
            # Remove listeners gracefully
            try:
                page.remove_listener("request", on_req)
                page.remove_listener("response", on_res_or_fail)
                page.remove_listener("requestfailed", on_res_or_fail)
            except Exception:
                pass

    @classmethod
    async def _wait_for_spinners_to_disappear(cls, page: Page, timeout_sec: float = 3.0) -> None:
        """
        Polls DOM to ensure visible loading spinners are detached or hidden.
        """
        start = time.time()
        selectors_str = ", ".join(COMMON_LOADING_SELECTORS)

        while (time.time() - start) < timeout_sec:
            try:
                has_visible_spinner = await page.evaluate(
                    f"""
                    () => {{
                        const els = Array.from(document.querySelectorAll('{selectors_str}'));
                        return els.some(el => {{
                            const style = window.getComputedStyle(el);
                            return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
                        }});
                    }}
                    """
                )
                if not has_visible_spinner:
                    break
                await asyncio.sleep(0.2)
            except Exception:
                break
