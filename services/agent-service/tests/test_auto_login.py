"""
Unit tests for Auth Profiles, Credential Encryption, FormAuthHandler, and AutoLoginExecutor.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from app.core.encryption import encrypt_credentials, decrypt_credentials, mask_credentials
from app.models.auth_profile import AuthProfile
from app.engine.auth.form_auth import FormAuthHandler
from app.engine.auth.executor import AutoLoginExecutor
from app.api.v1.endpoints.crawls import start_crawl, CrawlRequest


def test_fernet_encryption_decryption_and_masking():
    """Verify credentials encrypt to cipher tokens, decrypt faithfully, and mask secrets."""
    original_creds = {
        "username": "superadmin@example.com",
        "password": "MySuperSecretPassword#123",
        "client_secret": "sec_99999",
        "tenant_id": "tenant_abc",
    }

    # 1. Encrypt
    token = encrypt_credentials(original_creds)
    assert token != ""
    assert "MySuperSecretPassword#123" not in token
    assert "superadmin@example.com" not in token

    # 2. Decrypt
    decrypted = decrypt_credentials(token)
    assert decrypted == original_creds

    # 3. Mask
    masked = mask_credentials(decrypted)
    assert masked["username"] == "superadmin@example.com"
    assert masked["tenant_id"] == "tenant_abc"
    assert masked["password"] == "••••••••"
    assert masked["client_secret"] == "••••••••"


def test_form_auth_input_detection():
    """Verify FormAuthHandler detects username, password, and submit controls from AXTree."""
    snapshot = [
        {"id": 0, "tag": "div", "text": "Welcome to App"},
        {"id": 1, "tag": "input", "type": "text", "placeholder": "Enter your work email", "selector": "#user-email", "ariaLabel": ""},
        {"id": 2, "tag": "input", "type": "password", "placeholder": "Password", "selector": "#user-password", "ariaLabel": ""},
        {"id": 3, "tag": "button", "type": "submit", "text": "Sign In to Dashboard", "selector": "button.submit-btn"},
    ]

    username_field = FormAuthHandler._find_username_field(snapshot)
    assert username_field is not None
    assert username_field["selector"] == "#user-email"

    password_field = FormAuthHandler._find_password_field(snapshot)
    assert password_field is not None
    assert password_field["selector"] == "#user-password"

    submit_btn = FormAuthHandler._find_submit_button(snapshot)
    assert submit_btn is not None
    assert submit_btn["selector"] == "button.submit-btn"


@pytest.mark.asyncio
async def test_form_auth_login_execution_flow():
    """Verify FormAuthHandler navigates, fills credentials, clicks submit, and captures success."""
    mock_page = AsyncMock()
    mock_page.url = "https://app.example.com/dashboard"
    mock_page.context.cookies = AsyncMock(return_value=[{"name": "session_id", "value": "sid_123"}])
    mock_page.query_selector = AsyncMock(return_value=None)  # No error alert

    mock_bm = AsyncMock()
    mock_bm.navigate_safely = AsyncMock(return_value=True)
    mock_bm.wait_for_network_idle_and_ready = AsyncMock(return_value=True)
    mock_bm.human_delay = AsyncMock()

    snapshot = [
        {"id": 1, "tag": "input", "type": "email", "placeholder": "Email", "selector": "#email", "ariaLabel": ""},
        {"id": 2, "tag": "input", "type": "password", "placeholder": "Password", "selector": "#pass", "ariaLabel": ""},
        {"id": 3, "tag": "button", "type": "submit", "text": "Log In", "selector": "#login-btn"},
    ]

    with patch("app.engine.auth.form_auth.DOMDistiller.extract_interactive_snapshot", new=AsyncMock(return_value=snapshot)):
        success, error = await FormAuthHandler.login(
            page=mock_page,
            login_url="https://app.example.com/login",
            credentials={"username": "alice@example.com", "password": "secret_password"},
            browser_manager=mock_bm,
        )

        assert success is True
        assert error is None
        mock_page.fill.assert_any_call("#email", "alice@example.com")
        mock_page.fill.assert_any_call("#pass", "secret_password")
        mock_page.click.assert_any_call("#login-btn")


@pytest.mark.asyncio
async def test_autologin_executor_execute_login_success():
    """Verify AutoLoginExecutor executes FormAuthHandler and returns storage_state dict."""
    encrypted_token = encrypt_credentials({"username": "admin", "password": "password123"})
    profile = AuthProfile(
        id="prof_test_1",
        user_id="user_1",
        name="Admin Test",
        target_domain="example.com",
        login_url="https://example.com/login",
        auth_type="form",
        encrypted_credentials=encrypted_token,
    )

    mock_storage_state = {
        "cookies": [{"name": "auth_token", "value": "tok_xyz", "domain": "example.com"}],
        "origins": [],
    }

    mock_page = AsyncMock()
    mock_page.context.storage_state = AsyncMock(return_value=mock_storage_state)

    mock_bm = AsyncMock()
    mock_bm.new_page = AsyncMock(return_value=mock_page)
    mock_bm.start = AsyncMock()
    mock_bm.stop = AsyncMock()

    with patch("app.engine.auth.executor.BrowserManager", return_value=mock_bm), \
         patch("app.engine.auth.executor.FormAuthHandler.login", new=AsyncMock(return_value=(True, None))):

        storage_state = await AutoLoginExecutor.execute_login(profile, headless=True)
        assert storage_state == mock_storage_state
        assert len(storage_state["cookies"]) == 1
        mock_bm.stop.assert_called_once()


@pytest.mark.asyncio
async def test_start_crawl_validates_auth_profile_id_and_queues():
    """Verify start_crawl validates auth_profile_id ownership and passes it to run_background_crawl."""
    mock_db = AsyncMock()
    mock_bg = MagicMock()

    request = CrawlRequest(
        url="https://verified-app.com",
        tos_accepted=True,
        auth_profile_id="prof_valid_123",
    )

    mock_profile = AuthProfile(
        id="prof_valid_123",
        user_id="user_123",
        name="Staging Profile",
        target_domain="verified-app.com",
        login_url="https://verified-app.com/login",
        auth_type="form",
        encrypted_credentials=encrypt_credentials({"username": "test", "password": "123"}),
    )

    with patch("app.api.v1.endpoints.crawls.DomainRepository") as mock_domain_repo_cls, \
         patch("app.api.v1.endpoints.crawls.CrawlRepository") as mock_crawl_repo_cls, \
         patch("app.repositories.auth_profile_repo.AuthProfileRepository.get_profile", new=AsyncMock(return_value=mock_profile)):

        mock_domain_repo = MagicMock()
        mock_domain_repo.is_domain_verified = AsyncMock(return_value=True)
        mock_domain_repo_cls.return_value = mock_domain_repo

        mock_crawl_repo = MagicMock()
        mock_crawl_repo.check_daily_quota = AsyncMock(return_value=(0, False))
        mock_session_obj = MagicMock()
        mock_session_obj.id = "session_auth_crawl"
        mock_crawl_repo.create = AsyncMock(return_value=mock_session_obj)
        mock_crawl_repo.increment_daily_quota = AsyncMock()
        mock_crawl_repo_cls.return_value = mock_crawl_repo

        resp = await start_crawl(
            request=request,
            background_tasks=mock_bg,
            x_user_id="user_123",
            x_user_tier="FREE",
            db=mock_db,
        )

        assert resp.status == "running"
        assert resp.session_id == "session_auth_crawl"

        # Verify background task was queued with auth_profile_id="prof_valid_123"
        mock_bg.add_task.assert_called_once()
        _, kwargs = mock_bg.add_task.call_args
        assert kwargs["auth_profile_id"] == "prof_valid_123"


@pytest.mark.asyncio
async def test_start_crawl_with_nonexistent_auth_profile_raises_400():
    """Verify start_crawl returns 400 Bad Request when an invalid auth_profile_id is provided."""
    mock_db = AsyncMock()
    mock_bg = MagicMock()

    request = CrawlRequest(
        url="https://verified-app.com",
        tos_accepted=True,
        auth_profile_id="prof_nonexistent_404",
    )

    with patch("app.api.v1.endpoints.crawls.DomainRepository") as mock_domain_repo_cls, \
         patch("app.api.v1.endpoints.crawls.CrawlRepository") as mock_crawl_repo_cls, \
         patch("app.repositories.auth_profile_repo.AuthProfileRepository.get_profile", new=AsyncMock(return_value=None)):

        mock_domain_repo = MagicMock()
        mock_domain_repo.is_domain_verified = AsyncMock(return_value=True)
        mock_domain_repo_cls.return_value = mock_domain_repo

        mock_crawl_repo = MagicMock()
        mock_crawl_repo.check_daily_quota = AsyncMock(return_value=(0, False))
        mock_crawl_repo_cls.return_value = mock_crawl_repo

        with pytest.raises(HTTPException) as exc_info:
            await start_crawl(
                request=request,
                background_tasks=mock_bg,
                x_user_id="user_123",
                x_user_tier="FREE",
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "was not found for your account" in exc_info.value.detail
