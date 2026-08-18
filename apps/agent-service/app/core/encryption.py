"""
Fernet-based symmetric encryption and secret masking utilities for Auth Profiles.
Guarantees stored credentials are encrypted at rest and never exposed in plaintext.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any, Dict

from cryptography.fernet import Fernet
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_fernet_instance() -> Fernet:
    """Derive a deterministic 32-byte URL-safe base64 Fernet key from AUTH_PROFILE_SECRET_KEY."""
    raw_secret = settings.AUTH_PROFILE_SECRET_KEY or "insightapi-default-secret-key-fallback"
    digest = hashlib.sha256(raw_secret.encode("utf-8")).digest()
    urlsafe_key = base64.urlsafe_b64encode(digest)
    return Fernet(urlsafe_key)


def encrypt_credentials(credentials: Dict[str, Any] | str) -> str:
    """Encrypt a credentials dictionary or JSON string into a Fernet ciphertext token."""
    if isinstance(credentials, dict):
        payload = json.dumps(credentials)
    else:
        payload = str(credentials)

    f = _get_fernet_instance()
    encrypted_bytes = f.encrypt(payload.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_credentials(encrypted_token: str) -> Dict[str, Any]:
    """Decrypt a Fernet ciphertext token back into a credentials dictionary."""
    if not encrypted_token:
        return {}

    f = _get_fernet_instance()
    try:
        decrypted_bytes = f.decrypt(encrypted_token.encode("utf-8"))
        raw_text = decrypted_bytes.decode("utf-8")
        return json.loads(raw_text)
    except Exception as err:
        logger.error(f"Failed to decrypt auth profile credentials: {err}")
        return {}


def mask_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mask sensitive credential fields (password, client_secret, private_key, tokens)
    while preserving non-sensitive identifiers (username, email, client_id) for UI inspection.
    """
    if not isinstance(credentials, dict):
        return {}

    sensitive_keys = {
        "password",
        "pass",
        "secret",
        "client_secret",
        "private_key",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "auth_token",
    }

    masked = {}
    for key, value in credentials.items():
        if any(s_key in key.lower() for s_key in sensitive_keys):
            masked[key] = "••••••••"
        else:
            masked[key] = value

    return masked
