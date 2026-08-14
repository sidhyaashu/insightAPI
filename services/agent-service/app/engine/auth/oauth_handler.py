"""
OAuth & SAML Authentication Handlers for automated test account logins.
Supports Google OAuth, GitHub OAuth, and SAML SSO assertion redirects.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Tuple, Optional
from playwright.async_api import Page

from app.engine.browser.manager import BrowserManager

logger = logging.getLogger(__name__)


class OAuthHandler:
    @staticmethod
    async def login_google(
        page: Page,
        login_url: str,
        credentials: Dict[str, Any],
        browser_manager: BrowserManager,
        timeout_ms: int = 35000,
    ) -> Tuple[bool, Optional[str]]:
        """Automated Google OAuth login for pre-authorized testing accounts."""
        logger.info("🔑 OAuthHandler: Executing Google OAuth test flow")
        nav_ok = await browser_manager.navigate_safely(page, login_url, timeout_ms=timeout_ms)
        if not nav_ok:
            return False, f"Could not navigate to login URL: {login_url}"

        email = credentials.get("email") or credentials.get("username")
        password = credentials.get("password")
        if not email or not password:
            return False, "Missing Google test email or password in credentials."

        # If on application login page, look for "Continue with Google" or "Sign in with Google" button
        if "accounts.google.com" not in page.url:
            try:
                g_btn = await page.query_selector(
                    "button:has-text('Google'), a:has-text('Google'), [aria-label*='Google'], .google-btn"
                )
                if g_btn:
                    logger.info("Clicking 'Continue with Google' button")
                    await g_btn.click()
                    await browser_manager.wait_for_network_idle_and_ready(page, timeout_ms=10000)
            except Exception as e:
                logger.warning(f"Could not click Google button on initial page: {e}")

        # Fill Google Email
        try:
            email_input = await page.wait_for_selector("input[type='email'], #identifierId", timeout=10000)
            if email_input:
                await email_input.fill(str(email))
                await page.click("#identifierNext, button:has-text('Next')")
                await browser_manager.human_delay(1000, 1800)
        except Exception as e:
            return False, f"Google OAuth: Email field interaction failed: {e}"

        # Fill Google Password
        try:
            pass_input = await page.wait_for_selector("input[type='password'], input[name='Passwd']", timeout=10000)
            if pass_input:
                await pass_input.fill(str(password))
                await page.click("#passwordNext, button:has-text('Next')")
                await browser_manager.wait_for_network_idle_and_ready(page, timeout_ms=15000)
        except Exception as e:
            return False, f"Google OAuth: Password field interaction failed: {e}"

        # Consent prompt handling if present
        try:
            consent_btn = await page.query_selector("button:has-text('Allow'), button:has-text('Continue')")
            if consent_btn:
                await consent_btn.click()
                await browser_manager.wait_for_network_idle_and_ready(page, timeout_ms=10000)
        except Exception:
            pass

        return True, None

    @staticmethod
    async def login_github(
        page: Page,
        login_url: str,
        credentials: Dict[str, Any],
        browser_manager: BrowserManager,
        timeout_ms: int = 35000,
    ) -> Tuple[bool, Optional[str]]:
        """Automated GitHub OAuth login for pre-authorized testing accounts."""
        logger.info("🔑 OAuthHandler: Executing GitHub OAuth test flow")
        nav_ok = await browser_manager.navigate_safely(page, login_url, timeout_ms=timeout_ms)
        if not nav_ok:
            return False, f"Could not navigate to login URL: {login_url}"

        username = credentials.get("username") or credentials.get("email")
        password = credentials.get("password")
        if not username or not password:
            return False, "Missing GitHub test username or password in credentials."

        # If on application login page, look for "Continue with GitHub" button
        if "github.com/login" not in page.url:
            try:
                gh_btn = await page.query_selector(
                    "button:has-text('GitHub'), a:has-text('GitHub'), [aria-label*='GitHub'], .github-btn"
                )
                if gh_btn:
                    logger.info("Clicking 'Continue with GitHub' button")
                    await gh_btn.click()
                    await browser_manager.wait_for_network_idle_and_ready(page, timeout_ms=10000)
            except Exception as e:
                logger.warning(f"Could not click GitHub button on initial page: {e}")

        # Fill GitHub Credentials
        try:
            login_field = await page.wait_for_selector("#login_field, input[name='login']", timeout=10000)
            if login_field:
                await login_field.fill(str(username))
                pass_field = await page.wait_for_selector("#password, input[name='password']", timeout=5000)
                await pass_field.fill(str(password))
                await page.click("input[type='submit'][name='commit'], button:has-text('Sign in')")
                await browser_manager.wait_for_network_idle_and_ready(page, timeout_ms=15000)
        except Exception as e:
            return False, f"GitHub OAuth: Credentials interaction failed: {e}"

        # Handle Authorize application consent button if presented
        try:
            auth_btn = await page.query_selector("#js-oauth-authorize-btn, button:has-text('Authorize')")
            if auth_btn:
                logger.info("Clicking GitHub OAuth Authorize consent button")
                await auth_btn.click()
                await browser_manager.wait_for_network_idle_and_ready(page, timeout_ms=10000)
        except Exception:
            pass

        return True, None

    @staticmethod
    async def login_saml(
        page: Page,
        login_url: str,
        credentials: Dict[str, Any],
        browser_manager: BrowserManager,
        timeout_ms: int = 35000,
    ) -> Tuple[bool, Optional[str]]:
        """Automated SAML SSO IDP assertion flow."""
        logger.info("🔑 OAuthHandler: Executing SAML SSO assertion flow")
        from app.engine.auth.form_auth import FormAuthHandler
        return await FormAuthHandler.login(page, login_url, credentials, browser_manager, timeout_ms=timeout_ms)
