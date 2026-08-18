"""Enterprise Guardrails & SSRF Defense for Agent Tools."""
from __future__ import annotations

import ipaddress
import socket
import logging
import urllib.parse
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Disallowed private and cloud metadata CIDR ranges
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # AWS / GCP / Azure Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),   # Docker default subnets & private networks
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("fc00::/7"),        # IPv6 Unique Local Address
    ipaddress.ip_network("::1/128"),         # IPv6 Loopback
    ipaddress.ip_network("fe80::/10"),       # IPv6 Link-Local
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "insightapi_db",
    "insightapi_redis",
    "insightapi_agent",
    "insightapi_core",
    "insightapi_gateway",
    "insightapi_nginx",
    "insightapi_client",
    "db",
    "redis",
    "gateway",
    "agent-service",
    "core-service",
}


def validate_target_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate target URL against SSRF, internal network probing, and illegal protocols.
    Returns (is_valid, error_message).
    """
    if not url:
        return False, "Target URL cannot be empty."

    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme.lower() not in {"http", "https"}:
            return False, f"Invalid scheme '{parsed.scheme}'. Only HTTP and HTTPS are allowed."

        hostname = parsed.hostname
        if not hostname:
            return False, "Could not resolve a valid hostname from the URL."

        hostname_lower = hostname.lower()

        # 1. Block internal container hostnames and localhost
        if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
            return False, f"Access to internal infrastructure hostname '{hostname}' is blocked for security."

        # 2. Check if hostname is directly an IP literal
        try:
            ip_obj = ipaddress.ip_address(hostname)
            for blocked_net in BLOCKED_IP_NETWORKS:
                if ip_obj in blocked_net:
                    return False, f"Access to private IP address range '{ip_obj}' is blocked."
            return True, None
        except ValueError:
            pass  # It's a standard domain name, proceed to DNS resolution

        # 3. Resolve DNS and check resolved IP addresses
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                try:
                    ip_obj = ipaddress.ip_address(ip_str)
                    for blocked_net in BLOCKED_IP_NETWORKS:
                        if ip_obj in blocked_net:
                            return False, f"Host '{hostname}' resolved to blocked private address '{ip_obj}'."
                except ValueError:
                    continue
        except socket.gaierror as e:
            logger.debug(f"DNS lookup failed for {hostname}: {e}")
            # Allow DNS failure to be handled gracefully by the HTTP client

        return True, None

    except Exception as e:
        return False, f"URL validation failed: {str(e)}"
