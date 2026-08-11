import re
from urllib.parse import urlparse
from typing import List, Set, Dict, Any

STATIC_EXTENSIONS: Set[str] = {
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot", ".otf", ".mp4", ".webm", ".mp3",
    ".pdf", ".map", ".wasm", ".webp", ".avif", ".zip", ".gz", ".tar"
}

BLOCKED_DOMAINS: List[str] = [
    "google-analytics.com",
    "googletagmanager.com",
    "adtrafficquality.google",
    "adservice.google.com",
    "googleadservices.com",
    "sentry.io",
    "mixpanel.com",
    "segment.io",
    "hotjar.com",
    "amplitude.com",
    "facebook.net",
    "doubleclick.net",
    "datadoghq.com",
    "fullstory.com",
    "clarity.ms",
    "posthog.com",
    "bugsnag.com",
    "intercom.io",
    "crisp.chat"
]

API_CONTENT_TYPES: List[str] = [
    "application/json",
    "application/graphql+json",
    "application/x-www-form-urlencoded",
    "text/event-stream",
    "application/hal+json"
]


class NetworkFilter:
    """
    Evaluates HTTP requests and responses to filter out static assets,
    3rd party analytics telemetry, and non-API traffic.
    """
    @staticmethod
    def is_api_request(url: str, resource_type: str, content_type: str = "") -> bool:
        """Determines if a request URL & resource type correspond to a candidate API call."""
        parsed = urlparse(url)
        path = parsed.path.lower()

        for ext in STATIC_EXTENSIONS:
            if path.endswith(ext):
                return False

        domain = parsed.netloc.lower()
        for blocked in BLOCKED_DOMAINS:
            if blocked in domain:
                return False

        if resource_type in {"xhr", "fetch", "websocket", "eventsource"}:
            return True

        if resource_type == "document":
            if content_type and NetworkFilter.is_api_content_type(content_type):
                return True
            if "/api/" in path or path.endswith(".json"):
                return True

        return False

    @staticmethod
    def is_api_content_type(content_type: str) -> bool:
        """Checks if response Content-Type matches API response types."""
        if not content_type:
            return False
        ct_lower = content_type.lower()
        return any(api_ct in ct_lower for api_ct in API_CONTENT_TYPES)

    @staticmethod
    def is_rate_limited(status: int) -> bool:
        """Detects if response status indicates rate limiting or bot blocking."""
        return status in {429, 403}

    @staticmethod
    def redact_sensitive_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Redacts sensitive authorization tokens, session cookies, and API keys from headers."""
        if not headers:
            return {}
        
        redacted = {}
        sensitive_keys = {
            # Standard auth / session headers
            "authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "x-auth-token",
            "proxy-authorization",
            # CSRF / XSRF protection tokens
            "x-csrf-token",
            "x-xsrf-token",
            "x-request-token",
            # Session and bearer identifiers
            "x-session-token",
            "x-session-id",
            "bearer",
            "session-id",
        }
        for k, v in headers.items():
            if k.lower() in sensitive_keys:
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = v
        return redacted

    @staticmethod
    def redact_sensitive_body(body: Any) -> Any:
        """Recursively redacts passwords, secrets, and auth tokens from JSON body payloads."""
        if isinstance(body, dict):
            redacted_dict = {}
            sensitive_fields = {
                # Credential fields
                "password",
                "secret",
                "token",
                # OAuth / JWT tokens
                "access_token",
                "refresh_token",
                "id_token",
                "auth_token",
                "bearer_token",
                # API keys
                "api_key",
                "client_secret",
                # CSRF / XSRF
                "csrf_token",
                "xsrf_token",
                # Session identifiers
                "session_id",
                "session_token",
            }
            for k, v in body.items():
                if k.lower() in sensitive_fields:
                    redacted_dict[k] = "[REDACTED]"
                else:
                    redacted_dict[k] = NetworkFilter.redact_sensitive_body(v)
            return redacted_dict
        elif isinstance(body, list):
            return [NetworkFilter.redact_sensitive_body(item) for item in body]
        return body
