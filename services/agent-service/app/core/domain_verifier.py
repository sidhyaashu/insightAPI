"""
Domain Verification Engine — DNS TXT & Well-Known File Verification for InsightAPI.
"""
from __future__ import annotations

import logging
import re
import uuid
import urllib.parse
import httpx
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def generate_verification_token() -> str:
    """Generate a collision-resistant domain verification token."""
    return f"insightapi-verify-{uuid.uuid4().hex[:16]}"


def normalize_domain(url_or_domain: str) -> str:
    """Extract and normalize clean lowercase hostname without ports or protocol schemes."""
    raw = (url_or_domain or "").strip().lower()
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = f"https://{raw}"

    try:
        parsed = urllib.parse.urlparse(raw)
        hostname = (parsed.hostname or parsed.netloc or "").strip()
        # Strip port if present
        if ":" in hostname:
            hostname = hostname.split(":")[0]
        return hostname
    except Exception:
        # Fallback regex extraction
        cleaned = re.sub(r"^https?://", "", (url_or_domain or "").strip().lower())
        return cleaned.split("/")[0].split(":")[0]


class DomainVerifier:
    """
    Validates domain ownership via:
    1. DNS TXT records (_insightapi-challenge.{domain} or {domain})
    2. Well-Known HTTP file (/.well-known/insightapi-verification.txt)
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def verify_dns_txt(self, domain: str, token: str) -> bool:
        """
        Verify domain ownership via DNS TXT record check.
        Queries Cloudflare & Google DNS-over-HTTPS (DoH) APIs for maximum portability.
        """
        clean_domain = normalize_domain(domain)
        if not clean_domain:
            return False

        lookup_hosts = [
            f"_insightapi-challenge.{clean_domain}",
            clean_domain,
        ]

        # DoH providers: Cloudflare (1.1.1.1) and Google (8.8.8.8)
        doh_endpoints = [
            ("https://cloudflare-dns.com/dns-query", {"Accept": "application/dns-json"}),
            ("https://dns.google/resolve", {"Accept": "application/json"}),
        ]

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for host in lookup_hosts:
                for base_url, headers in doh_endpoints:
                    try:
                        resp = await client.get(
                            base_url,
                            params={"name": host, "type": "TXT"},
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            answers = data.get("Answer", [])
                            for ans in answers:
                                txt_data = (ans.get("data") or "").strip().strip('"')
                                # Check if token is matched in raw txt or standard key=value
                                if token in txt_data or f"insightapi-site-verification={token}" in txt_data:
                                    logger.info(f"DNS TXT verification succeeded for {clean_domain} on {host}")
                                    return True
                    except Exception as doh_err:
                        logger.debug(f"DoH query failed for {host} via {base_url}: {doh_err}")

        return False

    async def verify_well_known_file(self, domain: str, token: str) -> bool:
        """
        Verify domain ownership via well-known verification file:
        GET https://{domain}/.well-known/insightapi-verification.txt
        """
        clean_domain = normalize_domain(domain)
        if not clean_domain:
            return False

        urls = [
            f"https://{clean_domain}/.well-known/insightapi-verification.txt",
            f"http://{clean_domain}/.well-known/insightapi-verification.txt",
        ]

        async with httpx.AsyncClient(timeout=self.timeout, verify=False, follow_redirects=True) as client:
            for target_url in urls:
                try:
                    resp = await client.get(target_url)
                    if resp.status_code == 200:
                        body_text = resp.text.strip()
                        if token in body_text:
                            logger.info(f"Well-Known file verification succeeded for {clean_domain} at {target_url}")
                            return True
                except Exception as http_err:
                    logger.debug(f"Well-known verification request failed for {target_url}: {http_err}")

        return False

    async def verify(self, domain: str, token: str, method: str = "auto") -> Tuple[bool, Optional[str]]:
        """
        Orchestrate domain verification.
        Returns (is_verified, verification_method).
        """
        normalized_method = (method or "auto").lower()

        # 1. DNS TXT Check
        if normalized_method in ("auto", "dns", "dns_txt"):
            if await self.verify_dns_txt(domain, token):
                return True, "dns_txt"

        # 2. Well-Known File Check
        if normalized_method in ("auto", "well_known", "http"):
            if await self.verify_well_known_file(domain, token):
                return True, "well_known"

        return False, None
