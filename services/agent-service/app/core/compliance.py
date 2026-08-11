import time
import asyncio
from typing import Dict, Optional, Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx
from app.core.logging_config import get_logger, log_compliance_event

logger = get_logger("core.compliance")


class RobotsChecker:
    """
    Parses and enforces target site robots.txt rules using urllib.robotparser and httpx.
    """
    _parsers: Dict[str, RobotFileParser] = {}

    @classmethod
    def reset(cls):
        """Resets cached robots.txt parsers."""
        cls._parsers.clear()

    @classmethod
    def parse_robots_content(cls, domain: str, robots_txt_content: str):
        """Parses raw robots.txt string content directly for testing/offline use."""
        parser = RobotFileParser()
        parser.parse(robots_txt_content.splitlines())
        cls._parsers[domain] = parser
        log_compliance_event(logger, domain, "Parsed Inline robots.txt Rules", f"Rules loaded for domain '{domain}'")

    @classmethod
    async def fetch_and_parse(cls, target_url: str, user_agent: str = "InsightAPI-Bot", timeout_sec: float = 5.0):
        """Fetches and parses robots.txt from target domain if not already cached."""
        parsed = urlparse(target_url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        if not domain or domain in cls._parsers:
            return

        robots_url = f"{parsed.scheme or 'https'}://{domain}/robots.txt"
        parser = RobotFileParser()
        
        try:
            async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
                res = await client.get(robots_url)
                if res.status_code == 200:
                    parser.parse(res.text.splitlines())
                    log_compliance_event(logger, domain, "Fetched & Parsed robots.txt", f"Status 200 from {robots_url}")
                else:
                    parser.allow_all = True
                    log_compliance_event(logger, domain, "robots.txt Not Found", f"Status {res.status_code}. Defaulting to allow_all.")
        except Exception as e:
            logger.debug(f"Failed to fetch robots.txt from {robots_url}: {e}")
            parser.allow_all = True

        cls._parsers[domain] = parser

    @classmethod
    def is_allowed(cls, url: str, user_agent: str = "InsightAPI-Bot") -> bool:
        """Checks if navigating to target URL is allowed under robots.txt."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if not domain or domain not in cls._parsers:
            return True

        parser = cls._parsers[domain]
        allowed = parser.can_fetch(user_agent, url)
        if not allowed:
            log_compliance_event(logger, domain, "DISALLOWED by robots.txt", f"Blocked path: {url}")
        return allowed

    @classmethod
    def check_disallowed_warning(cls, target_url: str, user_agent: str = "InsightAPI-Bot") -> Optional[Dict[str, Any]]:
        """
        Evaluates whether the target URL or root path is disallowed by robots.txt.
        Returns a dict with warning details if disallowed, or None if allowed.
        """
        parsed = urlparse(target_url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        if not domain or domain not in cls._parsers:
            return None

        parser = cls._parsers[domain]
        if getattr(parser, "allow_all", False):
            return None

        root_url = f"{parsed.scheme or 'https'}://{domain}/"
        url_allowed = parser.can_fetch(user_agent, target_url) or parser.can_fetch("*", target_url)
        root_allowed = parser.can_fetch(user_agent, root_url) or parser.can_fetch("*", root_url)

        if not url_allowed or not root_allowed:
            disallowed_path = target_url if not url_allowed else root_url
            return {
                "disallowed": True,
                "domain": domain,
                "disallowed_path": disallowed_path,
                "reason": f"Path '{disallowed_path}' is disallowed by robots.txt rules for User-Agent: {user_agent} / *"
            }
        return None


class DomainRateLimiter:
    """
    Enforces minimum request spacing per target domain to prevent aggressive bursts.
    """
    _last_request_time: Dict[str, float] = {}

    @classmethod
    def reset(cls):
        """Resets last request timestamps."""
        cls._last_request_time.clear()

    @classmethod
    async def enforce_rate_limit(cls, url: str, min_delay_ms: int = 500):
        """Pauses execution if requests to domain occur faster than min_delay_ms."""
        parsed = urlparse(url)
        domain = parsed.netloc or "default"
        
        now = time.time()
        last_time = cls._last_request_time.get(domain, 0.0)
        elapsed_ms = (now - last_time) * 1000.0

        if elapsed_ms < min_delay_ms:
            wait_sec = (min_delay_ms - elapsed_ms) / 1000.0
            log_compliance_event(logger, domain, "Rate Limit Pausing", f"Waiting {wait_sec:.2f}s to respect {min_delay_ms}ms domain delay.")
            await asyncio.sleep(wait_sec)

        cls._last_request_time[domain] = time.time()
