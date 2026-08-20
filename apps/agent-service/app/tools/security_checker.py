"""Security checker tool for API vulnerability and posture evaluation."""
from __future__ import annotations

import ssl
import socket
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.tools.base import ToolResult
from app.tools.http_probe import probe_http_endpoint

logger = logging.getLogger(__name__)


def audit_tls_transport_posture(hostname: str, port: int = 443, timeout_sec: float = 3.0) -> Dict[str, Any]:
    """
    Perform passive TLS protocol version, cipher suite, and X.509 certificate posture auditing.
    """
    result: Dict[str, Any] = {
        "hostname": hostname,
        "port": port,
        "tls_version": None,
        "cipher_suite": None,
        "cipher_bits": None,
        "cert_subject": None,
        "cert_issuer": None,
        "cert_sans": [],
        "expires_at": None,
        "days_remaining": None,
        "is_expired": False,
        "findings": [],
    }

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # Permissive to inspect broken/self-signed certs

        with socket.create_connection((hostname, port), timeout=timeout_sec) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert(binary_form=False)
                cipher = ssock.cipher()
                tls_ver = ssock.version()

                result["tls_version"] = tls_ver
                if cipher:
                    result["cipher_suite"] = cipher[0]
                    result["cipher_bits"] = cipher[2]

                if tls_ver in ("TLSv1", "TLSv1.1", "SSLv3", "SSLv2"):
                    result["findings"].append({
                        "category": "Transport Security",
                        "severity": "HIGH",
                        "title": f"Deprecated TLS Protocol Version ({tls_ver})",
                        "description": f"The host negotiated {tls_ver}. TLS 1.0 and 1.1 are formally deprecated (RFC 8996).",
                    })

                if cipher and any(w in cipher[0].lower() for w in ("rc4", "des", "3des", "md5", "null", "anon")):
                    result["findings"].append({
                        "category": "Transport Security",
                        "severity": "HIGH",
                        "title": f"Weak Cipher Suite ({cipher[0]})",
                        "description": "The negotiated cipher suite contains insecure cryptographic primitives.",
                    })

                # Certificate parsing using cryptography DER loader
                der_cert = ssock.getpeercert(binary_form=True)
                if der_cert:
                    try:
                        from cryptography import x509
                        from cryptography.x509.oid import NameOID, ExtensionOID

                        x509_cert = x509.load_der_x509_certificate(der_cert)

                        # Subject CommonName
                        cns = x509_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                        if cns:
                            result["cert_subject"] = cns[0].value

                        # Issuer Organization
                        orgs = x509_cert.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
                        if orgs:
                            result["cert_issuer"] = orgs[0].value

                        # Validity Expiry
                        exp_dt = x509_cert.not_valid_after_utc if hasattr(x509_cert, "not_valid_after_utc") else x509_cert.not_valid_after.replace(tzinfo=timezone.utc)
                        result["expires_at"] = exp_dt.isoformat()
                        days_rem = (exp_dt - datetime.now(timezone.utc)).days
                        result["days_remaining"] = days_rem

                        if days_rem < 0:
                            result["is_expired"] = True
                            result["findings"].append({
                                "category": "Transport Security",
                                "severity": "HIGH",
                                "title": "Expired SSL/TLS Certificate",
                                "description": f"The certificate expired {abs(days_rem)} days ago.",
                            })
                        elif days_rem < 30:
                            result["findings"].append({
                                "category": "Transport Security",
                                "severity": "MEDIUM",
                                "title": "Certificate Expiring Soon",
                                "description": f"The certificate expires in {days_rem} days.",
                            })

                        # Subject Alternative Names (SANs)
                        try:
                            san_ext = x509_cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                            result["cert_sans"] = san_ext.value.get_values_for_type(x509.DNSName)
                        except Exception:
                            pass

                    except Exception as cert_err:
                        logger.debug(f"x509 parse warning on {hostname}: {cert_err}")

    except Exception as e:
        logger.debug(f"TLS posture audit error on {hostname}:{port}: {e}")

    return result


async def security_audit_endpoint(url: str, method: str = "GET") -> ToolResult:
    """
    Perform passive and active security header and transport auditing on an API endpoint.
    """
    probe = await probe_http_endpoint(url=url, method=method)
    if probe.status != "success":
        return ToolResult(
            tool_name="security_audit_endpoint",
            status="error",
            latency_ms=probe.latency_ms,
            error=probe.error,
            data={"url": url},
        )

    headers = {k.lower(): v for k, v in probe.data.get("response_headers", {}).items()}
    findings: List[Dict[str, Any]] = []

    # 0. TLS Transport Posture Audit (if HTTPS)
    tls_posture = None
    if url.startswith("https://"):
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or url
        port = parsed.port or 443
        tls_posture = audit_tls_transport_posture(host, port)
        findings.extend(tls_posture.get("findings", []))

    # 1. HSTS Check
    if url.startswith("https://"):
        if "strict-transport-security" not in headers:
            findings.append({
                "category": "Transport Security",
                "severity": "MEDIUM",
                "title": "Missing HSTS Header",
                "description": "Strict-Transport-Security header is missing. Users could be vulnerable to SSL stripping attacks.",
            })
    else:
        findings.append({
            "category": "Transport Security",
            "severity": "HIGH",
            "title": "Insecure HTTP Protocol",
            "description": "The endpoint communicates over plaintext HTTP without TLS encryption.",
        })

    # 2. CORS Misconfiguration Check
    cors_origin = headers.get("access-control-allow-origin")
    if cors_origin == "*":
        findings.append({
            "category": "CORS Policy",
            "severity": "LOW",
            "title": "Wildcard Access-Control-Allow-Origin",
            "description": "Access-Control-Allow-Origin is set to '*'. Safe for public APIs, but dangerous if credentials/cookies are shared.",
        })

    # 3. Content-Type Sniffing Check
    if headers.get("x-content-type-options") != "nosniff":
        findings.append({
            "category": "MIME Sniffing",
            "severity": "LOW",
            "title": "Missing X-Content-Type-Options",
            "description": "X-Content-Type-Options: nosniff is missing, leaving browsers open to MIME type confusion.",
        })

    # 4. Clickjacking Frame Options
    if "x-frame-options" not in headers and "content-security-policy" not in headers:
        findings.append({
            "category": "Framing Protection",
            "severity": "LOW",
            "title": "Missing Frame Protections",
            "description": "Neither X-Frame-Options nor CSP frame-ancestors is present.",
        })

    # 5. Rate Limiting Headers Check
    rate_limit_headers = [k for k in headers.keys() if "ratelimit" in k or "x-rate-limit" in k]
    has_rate_limiting = len(rate_limit_headers) > 0

    score = 100 - (len([f for f in findings if f["severity"] == "HIGH"]) * 30) - (len([f for f in findings if f["severity"] == "MEDIUM"]) * 15) - (len([f for f in findings if f["severity"] == "LOW"]) * 5)
    score = max(0, min(100, score))

    return ToolResult(
        tool_name="security_audit_endpoint",
        status="success",
        latency_ms=probe.latency_ms,
        data={
            "url": url,
            "security_score": score,
            "findings_count": len(findings),
            "findings": findings,
            "tls_posture": tls_posture,
            "has_rate_limiting": has_rate_limiting,
            "status_code": probe.data.get("status_code"),
            "headers_inspected": list(headers.keys()),
        },
    )
