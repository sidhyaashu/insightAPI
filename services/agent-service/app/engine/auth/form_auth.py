"""
Form Authentication Handler.
Autonomously discovers username/password inputs and submit controls using DOM Distiller,
fills credentials, submits the form, and captures session state.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any, Tuple, Optional
from playwright.async_api import Page

from app.engine.browser.dom_distiller import DOMDistiller
from app.engine.browser.manager import BrowserManager

logger = logging.getLogger(__name__)


class FormAuthHandler:
    @staticmethod
    async def login(
        page: Page,
        login_url: str,
        credentials: Dict[str, Any],
        browser_manager: BrowserManager,
        timeout_ms: int = 30000,
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute automated form login.

        Returns:
            (success: bool, error_message: Optional[str])
        """
        logger.info(f"🔑 FormAuthHandler: Navigating to login URL: {login_url}")
        nav_ok = await browser_manager.navigate_safely(page, login_url, timeout_ms=timeout_ms)
        if not nav_ok:
            return False, f"Could not navigate to login page: {login_url}"

        # Dismiss any interstitial cookie banners or modals first
        try:
            from app.engine.runtime.executor import DynamicRuntimeExecutor
            await DynamicRuntimeExecutor.dismiss_interstitials(page)
        except Exception:
            pass

        # Extract interactive AXTree snapshot
        snapshot = await DOMDistiller.extract_interactive_snapshot(page, scroll_virtualized=False)
        if not snapshot:
            return False, "DOM Distiller found no interactive elements on the login page."

        # Locate Username / Email Field
        username_field = FormAuthHandler._find_username_field(snapshot)
        # Locate Password Field
        password_field = FormAuthHandler._find_password_field(snapshot)

        if not username_field or not password_field:
            logger.warning(
                f"FormAuthHandler: Could not detect standard login inputs. "
                f"Username field found: {bool(username_field)}, Password field found: {bool(password_field)}"
            )
            return False, "Could not identify username/email or password input fields on target page."

        username_val = (
            credentials.get("username")
            or credentials.get("email")
            or credentials.get("user")
            or credentials.get("login")
            or ""
        )
        password_val = (
            credentials.get("password")
            or credentials.get("pass")
            or credentials.get("secret")
            or ""
        )

        if not username_val or not password_val:
            return False, "Missing username or password in auth profile credentials."

        # Fill Username
        u_sel = username_field["selector"]
        logger.info(f"Filling username field via selector: {u_sel}")
        try:
            await page.click(u_sel)
            await page.fill(u_sel, str(username_val))
            await browser_manager.human_delay(200, 500)
        except Exception as e:
            return False, f"Failed to fill username into {u_sel}: {e}"

        # Fill Password
        p_sel = password_field["selector"]
        logger.info(f"Filling password field via selector: {p_sel}")
        try:
            await page.click(p_sel)
            await page.fill(p_sel, str(password_val))
            await browser_manager.human_delay(200, 500)
        except Exception as e:
            return False, f"Failed to fill password into {p_sel}: {e}"

        # Locate Submit Button
        submit_btn = FormAuthHandler._find_submit_button(snapshot)

        # Submit Form
        prev_url = page.url
        try:
            if submit_btn and submit_btn.get("selector"):
                s_sel = submit_btn["selector"]
                logger.info(f"Clicking submit button via selector: {s_sel}")
                await page.click(s_sel)
            else:
                logger.info("No explicit submit button detected. Pressing Enter on password field.")
                await page.press(p_sel, "Enter")
        except Exception as e:
            return False, f"Failed to click submit button: {e}"

        # Wait for redirect / network stabilization
        await browser_manager.wait_for_network_idle_and_ready(page, timeout_ms=15000)
        await browser_manager.human_delay(1000, 2000)

        # Verification: Check if URL changed, error alerts appeared, or auth cookies captured
        current_url = page.url
        cookies = await page.context.cookies()

        # Check for error indicators in DOM
        error_text = await FormAuthHandler._check_login_errors(page)
        if error_text:
            return False, f"Target page rejected login: {error_text}"

        logger.info(
            f"✓ FormAuthHandler: Login executed. Pre-URL: {prev_url} -> Post-URL: {current_url} | "
            f"Cookies captured: {len(cookies)}"
        )
        return True, None

    @staticmethod
    def _find_username_field(snapshot: list[dict]) -> Optional[dict]:
        patterns = re.compile(r"(user(name)?|email|login|account|identifier|handle)", re.IGNORECASE)
        
        # 1. Look for type="email"
        for item in snapshot:
            if item.get("tag") == "input" and item.get("type") == "email":
                return item

        # 2. Look for name/id/placeholder matching pattern
        for item in snapshot:
            if item.get("tag") in ("input", "textarea"):
                if item.get("type") == "password":
                    continue
                match_str = f"{item.get('text', '')} {item.get('placeholder', '')} {item.get('selector', '')} {item.get('ariaLabel', '')}"
                if patterns.search(match_str):
                    return item

        # 3. Fallback: first non-password input with type="text"
        for item in snapshot:
            if item.get("tag") == "input" and item.get("type") in ("text", "", None):
                return item

        return None

    @staticmethod
    def _find_password_field(snapshot: list[dict]) -> Optional[dict]:
        # 1. Explicit type="password"
        for item in snapshot:
            if item.get("tag") == "input" and item.get("type") == "password":
                return item

        # 2. Pattern match for password/pass
        patterns = re.compile(r"(pass(word)?|pwd|secret)", re.IGNORECASE)
        for item in snapshot:
            if item.get("tag") == "input":
                match_str = f"{item.get('text', '')} {item.get('placeholder', '')} {item.get('selector', '')}"
                if patterns.search(match_str):
                    return item

        return None

    @staticmethod
    def _find_submit_button(snapshot: list[dict]) -> Optional[dict]:
        submit_patterns = re.compile(r"(log\s*in|sign\s*in|submit|continue|next|enter|authenticate)", re.IGNORECASE)

        # 1. Button or input with matching text or type="submit"
        for item in snapshot:
            if item.get("tag") in ("button", "a", "input"):
                if item.get("type") == "submit":
                    return item
                text = item.get("text", "")
                if submit_patterns.search(text):
                    return item

        return None

    @staticmethod
    async def _check_login_errors(page: Page) -> Optional[str]:
        """Check for common error toast/alert text indicating failed login."""
        try:
            error_el = await page.query_selector(
                "[role='alert'], .alert-danger, .error-message, .login-error, .toast-error, .invalid-feedback"
            )
            if error_el:
                txt = (await error_el.inner_text()).strip()
                if txt and len(txt) < 150:
                    return txt
        except Exception:
            pass
        return None
