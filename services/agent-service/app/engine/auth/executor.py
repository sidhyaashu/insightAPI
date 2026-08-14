"""
AutoLoginExecutor — Autonomous login coordinator and storage_state session capturer.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, Tuple

from app.engine.browser.manager import BrowserManager
from app.engine.auth.form_auth import FormAuthHandler
from app.engine.auth.oauth_handler import OAuthHandler
from app.models.auth_profile import AuthProfile

logger = logging.getLogger(__name__)


class AutoLoginExecutor:
    """
    Executes automated login flows for configured AuthProfiles and captures
    authenticated Playwright storage_state (cookies + localStorage).
    """

    @classmethod
    async def execute_login(
        cls,
        auth_profile: AuthProfile,
        headless: bool = True,
    ) -> Dict[str, Any]:
        """
        Runs the automated login sequence for the given AuthProfile and returns
        the captured storage_state dictionary.

        Raises:
            RuntimeError: If authentication sequence fails.
        """
        login_url = auth_profile.login_url
        auth_type = (auth_profile.auth_type or "form").lower()
        credentials = auth_profile.get_decrypted_credentials()

        logger.info(
            f"🔐 AutoLoginExecutor: Initiating automated login for profile '{auth_profile.name}' "
            f"[{auth_type}] -> {login_url}"
        )

        browser_manager = BrowserManager(headless=headless)
        await browser_manager.start()

        try:
            page = await browser_manager.new_page()

            if auth_type == "form":
                success, error = await FormAuthHandler.login(page, login_url, credentials, browser_manager)
            elif auth_type == "oauth_google":
                success, error = await OAuthHandler.login_google(page, login_url, credentials, browser_manager)
            elif auth_type == "oauth_github":
                success, error = await OAuthHandler.login_github(page, login_url, credentials, browser_manager)
            elif auth_type == "saml":
                success, error = await OAuthHandler.login_saml(page, login_url, credentials, browser_manager)
            else:
                success, error = await FormAuthHandler.login(page, login_url, credentials, browser_manager)

            if not success:
                raise RuntimeError(error or f"Automated login failed for {auth_type} flow.")

            # Capture authenticated storage_state (cookies and localStorage)
            storage_state = await page.context.storage_state()
            cookies = storage_state.get("cookies", [])
            logger.info(
                f"✓ AutoLoginExecutor: Successfully authenticated profile '{auth_profile.name}'. "
                f"Captured {len(cookies)} session cookies."
            )
            return storage_state

        finally:
            await browser_manager.stop()

    @classmethod
    async def test_profile_login(
        cls,
        auth_profile: AuthProfile,
        headless: bool = True,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Test execute an auth profile with diagnostic feedback.

        Returns:
            (success: bool, error: Optional[str], diagnostics: Optional[dict])
        """
        try:
            storage_state = await cls.execute_login(auth_profile, headless=headless)
            cookies = storage_state.get("cookies", [])
            cookie_names = [c.get("name") for c in cookies[:5]]
            diagnostics = {
                "cookies_count": len(cookies),
                "sample_cookie_names": cookie_names,
                "origins_count": len(storage_state.get("origins", [])),
            }
            return True, None, diagnostics
        except Exception as e:
            return False, str(e), None
