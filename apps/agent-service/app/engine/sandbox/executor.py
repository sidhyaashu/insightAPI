"""
SandboxExecutor — Isolated, resource-constrained execution runtime for active security testing.

Design & Security Invariants:
-----------------------------
1. Isolated Context: Runs test requests and browser actions in an isolated runtime/HTTP client
   or ephemeral container, strictly separated from the passive crawler browser context.
2. Hard Resource Limits:
   - Wall-clock timeout: default 10.0 seconds (hard cap 30.0s)
   - Max response body payload: 512 KB
   - Memory & concurrency throttles
3. Strict Egress Control:
   - Validates that every target URL/hostname strictly matches the authorized target domain.
   - Rejects localhost, RFC1918 private subnets, cloud metadata IPs (169.254.169.254),
     and non-target third-party domains before initiating any socket connection.
4. Destructive Safeguards:
   - Refuses execution of test cases marked `is_destructive=True` unless `allow_destructive=True`
     is passed from an approved review token/state.
"""
from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import json
import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("engine.sandbox.executor")

BLOCKED_IP_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
)

MAX_RESPONSE_BYTES = 512 * 1024  # 512 KB payload limit


class SandboxExecutor:
    """
    Isolated execution harness for active security probes.
    All active testing (non-passive discovery) MUST route through this class.
    """

    DEFAULT_TIMEOUT_SECONDS: float = 10.0
    MAX_TIMEOUT_SECONDS: float = 30.0

    @classmethod
    def validate_egress(cls, url: str, target_domain: Optional[str] = None) -> bool:
        """
        Validate network egress destination.
        Returns True if the URL is safe and strictly matches the target domain.
        Raises ValueError / PermissionError if egress is forbidden.
        """
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"Invalid scheme '{parsed.scheme}'. Only http and https allowed in sandbox.")

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise ValueError("Target URL missing valid hostname.")

        # 1. Block private/local and metadata IPs
        if hostname in {"localhost", "127.0.0.1", "::1", "169.254.169.254"}:
            raise PermissionError(f"Sandbox egress blocked: target '{hostname}' is a restricted local/metadata address.")

        try:
            ip = ipaddress.ip_address(hostname)
            for net in BLOCKED_IP_NETWORKS:
                if ip in net:
                    raise PermissionError(f"Sandbox egress blocked: IP '{ip}' is in private network range.")
        except ValueError:
            pass  # Domain name, not a raw IP

        # 2. Strict target domain match (if target_domain specified)
        if target_domain:
            norm_target = target_domain.lower().strip()
            # Allow target_domain or any direct subdomain of target_domain
            if hostname != norm_target and not hostname.endswith(f".{norm_target}"):
                raise PermissionError(
                    f"Sandbox egress blocked: Request to '{hostname}' does not match authorized target domain '{norm_target}'."
                )

        return True

    @classmethod
    async def run_test(
        cls,
        ep: Dict[str, Any],
        test_strategy: Dict[str, Any],
        target_domain: Optional[str] = None,
        allow_destructive: bool = False,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        crawl_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a security test probe against an endpoint shape.
        Guards against destructive runs and egress policy violations.
        """
        is_destructive = test_strategy.get("is_destructive", True)
        if is_destructive and not allow_destructive:
            logger.warning(
                f"SandboxExecutor: Attempted to run destructive test '{test_strategy.get('strategy')}' "
                "without authorization — BLOCKED."
            )
            return {
                "status_code": 403,
                "body": {"error": "Destructive test blocked: Human approval required."},
                "headers": {},
                "blocked": True,
                "error": "Destructive test blocked by policy.",
            }

        raw_url = ep.get("url") or ep.get("template_route") or "/"
        method = (ep.get("method") or "GET").upper()
        strategy = test_strategy.get("strategy", "")
        mutate_param = test_strategy.get("mutate_param")
        params: Dict[str, Any] = {}
        body: Optional[Dict[str, Any]] = None

        # Resolve relative / template paths against target_domain if needed
        if not raw_url.startswith(("http://", "https://")):
            if target_domain:
                url = f"https://{target_domain.rstrip('/')}/{raw_url.lstrip('/')}"
            else:
                url = raw_url
        else:
            url = raw_url

        effective_domain = target_domain or urlparse(url).netloc
        if not effective_domain or not effective_domain.strip():
            raise ValueError(
                f"SandboxExecutor: Invalid target URL '{url}'. Absolute URL or target_domain required, got empty domain."
            )

        # Resolve URL mutations based on test strategy
        if strategy == "adjacent_integer" and mutate_param:
            original_id = test_strategy.get("original_value", 1)
            try:
                adjacent_id = int(original_id) + 1
            except (ValueError, TypeError):
                adjacent_id = 2
            mutated_url = re.sub(r"/(\d+)(/|$)", f"/{adjacent_id}\\2", url, count=1)
            url = mutated_url if mutated_url != url else f"{url.rstrip('/')}?{mutate_param}={adjacent_id}"
            method = "GET"

        elif strategy == "injection_benign":
            payload = test_strategy.get("payload", "' OR '1'='1")
            if mutate_param:
                params[mutate_param] = payload

        elif strategy == "missing_auth":
            pass  # Explicitly stripped below

        elif strategy == "mass_assign_extra_field":
            body = test_strategy.get("payload", {"__proto__": {"admin": True}})

        try:
            cls.validate_egress(url, effective_domain)
        except Exception as egress_err:
            logger.warning(f"SandboxExecutor egress validation failed for {url}: {egress_err}")
            return {
                "status_code": 0,
                "body": None,
                "headers": {},
                "error": f"Egress Policy Violation: {egress_err}",
                "blocked": True,
            }

        # ── sandbox_action WS event — makes the probe visible in the inline
        # CrawlReasoningMessage stream in the UI (left-side reasoning, Claude style)
        if crawl_id:
            with contextlib.suppress(Exception):
                from app.api.v1.endpoints.crawls import publish_ws_event
                asyncio.create_task(publish_ws_event(crawl_id, {
                    "type": "sandbox_action",
                    "action": "http_probe",
                    "method": method,
                    "url": url,
                    "strategy": strategy,
                    "vuln_class": test_strategy.get("vuln_class", "other"),
                }))

        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "InsightAPI-SandboxExecutor/1.0 (Security Intelligence Node)",
        }
        if strategy != "missing_auth":
            for ex in (ep.get("examples") or []):
                cookie = (ex.get("request_headers") or {}).get("cookie")
                if cookie:
                    headers["Cookie"] = cookie
                    break
                auth_hdr = (ex.get("request_headers") or {}).get("authorization")
                if auth_hdr:
                    headers["Authorization"] = auth_hdr
                    break

        return await cls.run_request(
            method=method,
            url=url,
            params=params or None,
            json_body=body,
            headers=headers,
            target_domain=effective_domain,
            timeout=min(timeout, cls.MAX_TIMEOUT_SECONDS),
        )

    @classmethod
    async def run_request(
        cls,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        target_domain: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> Dict[str, Any]:
        """
        Execute an isolated HTTP probe with strict resource limits and error containment.
        """
        try:
            cls.validate_egress(url, target_domain)
        except Exception as e:
            return {
                "status_code": 0,
                "body": None,
                "headers": {},
                "error": f"Egress policy error: {e}",
                "blocked": True,
            }

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(timeout, connect=5.0),
                follow_redirects=False,
                limits=httpx.Limits(max_keepalive_connections=2, max_connections=5),
            ) as client:
                resp = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_body,
                    headers=headers,
                )

                content_len = len(resp.content)
                if content_len > MAX_RESPONSE_BYTES:
                    text_preview = resp.text[:2000]
                    body: Any = {"truncated": True, "preview": text_preview, "size_bytes": content_len}
                else:
                    try:
                        body = resp.json()
                    except Exception:
                        body = resp.text[:2000]

                return {
                    "status_code": resp.status_code,
                    "body": body,
                    "headers": dict(resp.headers),
                    "error": None,
                    "blocked": False,
                }
        except httpx.TimeoutException:
            logger.warning(f"SandboxExecutor timeout ({timeout}s) exceeded for {url}")
            return {
                "status_code": 504,
                "body": None,
                "headers": {},
                "error": f"Sandbox timeout after {timeout}s",
                "blocked": False,
            }
        except Exception as exc:
            logger.warning(f"SandboxExecutor request failure: {exc}")
            return {
                "status_code": 0,
                "body": None,
                "headers": {},
                "error": str(exc),
                "blocked": False,
            }
