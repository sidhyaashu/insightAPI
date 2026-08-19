"""
runtime/debug/redaction.py — Centralized Immutable Secret Redaction Pipeline.

Guarantees that authorization headers, cookies, JWTs, API keys, private keys,
and credential parameters are stripped or masked before persistence, logging,
telemetry, and artifact generation (AGENTS.md §21, Debug Prompt §41).
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Union
from pydantic import BaseModel

# Redacted placeholder
REDACTED_STR = "[REDACTED]"

# Sensitive Header Keys (case-insensitive)
SENSITIVE_HEADER_KEYS = {
    "authorization",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
    "api-key",
    "apikey",
    "access-token",
    "token",
    "secret",
    "client-secret",
}

# Sensitive Dictionary / JSON / Form Fields (case-insensitive)
SENSITIVE_FIELD_PATTERNS = [
    r"^.*(pass|password|passwd|secret|token|jwt|auth|bearer|apikey|api_key|access_token|refresh_token|private_key|client_secret).*$",
]

# Sensitive String Patterns (Regex)
JWT_REGEX = re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]+")
BEARER_REGEX = re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9_\-\.=]+", re.IGNORECASE)
BASIC_AUTH_REGEX = re.compile(r"(?i)\bBasic\s+[a-zA-Z0-9+/=]+", re.IGNORECASE)
PRIVATE_KEY_REGEX = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")


def redact_string(val: str) -> str:
    """Sanitizes raw strings by masking embedded JWTs, Bearer tokens, and private keys."""
    if not val or not isinstance(val, str):
        return val

    # Mask private keys
    val = PRIVATE_KEY_REGEX.sub(REDACTED_STR, val)
    # Mask JWTs
    val = JWT_REGEX.sub(REDACTED_STR, val)
    # Mask Bearer tokens
    val = BEARER_REGEX.sub(f"Bearer {REDACTED_STR}", val)
    # Mask Basic auth tokens
    val = BASIC_AUTH_REGEX.sub(f"Basic {REDACTED_STR}", val)

    return val


def redact_url(url: str) -> str:
    """Masks credentials in userinfo and sensitive query parameters in a URL."""
    if not url or not isinstance(url, str) or "://" not in url:
        return redact_string(url)

    try:
        parsed = urllib.parse.urlsplit(url)
        # Redact password in userinfo (e.g., http://user:pass@host)
        netloc = parsed.netloc
        if "@" in netloc:
            userinfo, host = netloc.split("@", 1)
            if ":" in userinfo:
                user, _ = userinfo.split(":", 1)
                netloc = f"{user}:{REDACTED_STR}@{host}"
            else:
                netloc = f"{REDACTED_STR}@{host}"

        # Redact sensitive query parameters
        if parsed.query:
            query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            sanitized_params = []
            for k, v in query_params:
                k_lower = k.lower()
                if any(re.match(pat, k_lower) for pat in SENSITIVE_FIELD_PATTERNS):
                    sanitized_params.append((k, REDACTED_STR))
                else:
                    sanitized_params.append((k, redact_string(v)))
            sanitized_query = urllib.parse.urlencode(sanitized_params)
        else:
            sanitized_query = ""

        return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, sanitized_query, parsed.fragment))
    except Exception:
        return redact_string(url)


def redact_headers(headers: Dict[str, Any]) -> Dict[str, str]:
    """Sanitizes HTTP headers dictionary by masking sensitive values."""
    if not headers or not isinstance(headers, dict):
        return {}

    sanitized: Dict[str, str] = {}
    for k, v in headers.items():
        k_str = str(k)
        v_str = str(v) if v is not None else ""
        if k_str.lower() in SENSITIVE_HEADER_KEYS:
            sanitized[k_str] = REDACTED_STR
        else:
            sanitized[k_str] = redact_string(v_str)
    return sanitized


def sanitize_data(data: Any, max_depth: int = 10) -> Any:
    """
    Recursively redacts secrets and credentials from dicts, lists, primitives,
    and Pydantic models.
    """
    if max_depth <= 0 or data is None:
        return data

    if isinstance(data, BaseModel):
        return sanitize_data(data.model_dump(), max_depth - 1)

    if isinstance(data, dict):
        sanitized_dict: Dict[str, Any] = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(re.match(pat, k_lower) for pat in SENSITIVE_FIELD_PATTERNS):
                sanitized_dict[k] = REDACTED_STR
            else:
                sanitized_dict[k] = sanitize_data(v, max_depth - 1)
        return sanitized_dict

    if isinstance(data, list):
        return [sanitize_data(item, max_depth - 1) for item in data]

    if isinstance(data, tuple):
        return tuple(sanitize_data(item, max_depth - 1) for item in data)

    if isinstance(data, str):
        if "://" in data:
            return redact_url(data)
        return redact_string(data)

    return data
