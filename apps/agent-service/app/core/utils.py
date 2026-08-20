"""
utils.py — Shared deterministic utilities for InsightAPI agent layer.

Rules (AGENTS.md §34):
- Deterministic code (URL parsing, string extraction, deduplication, hashing) lives here.
- Do NOT add LLM calls, database access, or async I/O to this module.
- Import freely from any tool, service, or agent module.
"""
from __future__ import annotations

import re
import hashlib
from typing import List


# ── URL Extraction ────────────────────────────────────────────────────────────

_URL_PATTERN = re.compile(r"https?://[^\s<>\"'{}|\\^`]+")
_BARE_DOMAIN_PATTERN = re.compile(
    r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|io|ai|co|dev|app|edu|gov|xyz|tech|online|me)(?:/[^\s<>\"'()]*[a-zA-Z0-9/])?",
    re.IGNORECASE
)


def extract_urls(text: str) -> List[str]:
    """
    Extract all HTTP/HTTPS URLs from *text*.

    Falls back to bare domain detection (e.g. ``api.example.com/users``)
    when no explicit scheme is present.

    Returns
    -------
    List of fully-qualified URL strings (always starting with ``https://``).
    """
    urls = _URL_PATTERN.findall(text)
    if urls:
        # Strip trailing punctuation often attached from sentences
        return [re.sub(r"[.,;:!?'\")]*$", "", u) for u in urls if len(u) > 8]
    matches = _BARE_DOMAIN_PATTERN.findall(text)
    clean_matches = []
    for m in matches:
        clean_m = re.sub(r"[.,;:!?'\")]*$", "", m).strip()
        if "." in clean_m and len(clean_m) > 4:
            clean_matches.append(f"https://{clean_m}")
    return clean_matches


# ── Text / Payload Hashing ────────────────────────────────────────────────────

def stable_hash(value: str) -> str:
    """Return a stable, short SHA-256 hex digest of *value* (first 16 chars)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


# ── Route / URL Utilities ─────────────────────────────────────────────────────

_INT_SEG = re.compile(r"^\d+$")
_UUID_SEG = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_HEX_TOKEN_SEG = re.compile(r"^[0-9a-fA-F]{24,64}$")


def normalize_route_template(path: str) -> str:
    """
    Normalize a concrete URL path into a parameterized template.

    Examples::

        /users/123          → /users/{id}
        /orders/550e8400-…  → /orders/{uuid}
        /tokens/deadbeef…   → /tokens/{token}

    This is the canonical implementation; ``traffic_parser._normalize_route_template``
    delegates to this function (migration tracked in Phase 2).
    """
    segments = path.strip("/").split("/")
    normalized: List[str] = []
    for seg in segments:
        if not seg:
            continue
        if _INT_SEG.match(seg):
            normalized.append("{id}")
        elif _UUID_SEG.match(seg):
            normalized.append("{uuid}")
        elif _HEX_TOKEN_SEG.match(seg):
            normalized.append("{token}")
        else:
            normalized.append(seg)
    return "/" + "/".join(normalized)
