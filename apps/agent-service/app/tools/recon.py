"""
tools/recon.py — Autonomous Website Reconnaissance & Tech-Stack Fingerprinting Engine.

Capabilities:
1. Sitemap & robots.txt Discovery: Fetches and parses /sitemap.xml, /sitemap_index.xml, and /robots.txt
   to extract comprehensive URL hierarchies and hidden application routes.
2. Technology Stack Fingerprinting: Analyzes HTTP headers, DOM <meta> tags, script bundle patterns,
   and server signatures to detect frontend frameworks, API backends, and edge WAFs.
3. Structured Metadata Extraction: Extracts JSON-LD schemas (schema.org), OpenGraph, and Microdata.
"""
from __future__ import annotations

import re
import json
import time
import logging
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set

import httpx

from app.tools.base import ToolResult
from app.tools.guardrails import validate_target_url
from app.tools.traffic_parser import STATIC_EXTENSIONS, _normalize_route_template

logger = logging.getLogger("agent.tools.recon")

# Technology Fingerprint Signatures
FRAMEWORK_SIGNATURES: Dict[str, Dict[str, Any]] = {
    # Frontend Frameworks
    "Next.js": {
        "headers": ["x-nextjs-page", "x-nextjs-cache", "x-nextjs-matched-path"],
        "html": [r'id="__NEXT_DATA__"', r'/_next/static/', r'<script[^>]+src="[^"]*/_next/'],
        "category": "Frontend Framework",
    },
    "React": {
        "headers": [],
        "html": [r'data-reactroot', r'react-dom', r'__reactFiber', r'_reactListening'],
        "category": "Frontend Library",
    },
    "Angular": {
        "headers": [],
        "html": [r'ng-version=', r'data-critters-container', r'<app-root', r'ng-reflect-'],
        "category": "Frontend Framework",
    },
    "Vue.js": {
        "headers": [],
        "html": [r'data-v-[a-f0-9]+', r'__vue__', r'vue-router', r'<div id="app"'],
        "category": "Frontend Framework",
    },
    "Nuxt.js": {
        "headers": ["x-nuxt-cache"],
        "html": [r'id="__NUXT__"', r'/_nuxt/'],
        "category": "Frontend Framework",
    },
    "Svelte / SvelteKit": {
        "headers": [],
        "html": [r'class="svelte-[a-z0-9]+"', r'__sveltekit'],
        "category": "Frontend Framework",
    },
    "Tailwind CSS": {
        "headers": [],
        "html": [r'class="[^"]*(?:flex|grid|hidden|bg-|text-|p-|m-|rounded-)[^"]*"'],
        "category": "UI Framework",
    },

    # Backend / API Gateways
    "FastAPI": {
        "headers": [],
        "html": [r'/docs', r'/openapi.json', r'/redoc'],
        "category": "API Framework",
    },
    "Express.js": {
        "headers": [("x-powered-by", r"Express")],
        "html": [],
        "category": "Backend Framework",
    },
    "Django": {
        "headers": [("x-frame-options", r"DENY|SAMEORIGIN"), ("set-cookie", r"csrftoken=")],
        "html": [r'csrfmiddlewaretoken'],
        "category": "Backend Framework",
    },
    "Laravel": {
        "headers": [("set-cookie", r"laravel_session="), ("set-cookie", r"XSRF-TOKEN=")],
        "html": [],
        "category": "Backend Framework",
    },
    "ASP.NET": {
        "headers": ["x-aspnet-version", "x-aspnetmvc-version", ("x-powered-by", r"ASP\.NET")],
        "html": [r'__VIEWSTATE', r'__EVENTVALIDATION'],
        "category": "Backend Framework",
    },
    "Spring Boot": {
        "headers": [("x-application-context", r".*")],
        "html": [],
        "category": "Backend Framework",
    },

    # CDN & WAF
    "Akamai EdgeSuite": {
        "headers": ["x-akamai-transformed", "akamai-grn", "x-akamai-request-id", ("server", r"AkamaiNetStorage|AkamaiGHost")],
        "html": [r'errors\.edgesuite\.net', r'Reference\s*#18\.[a-f0-9]+'],
        "category": "CDN / WAF",
    },
    "Cloudflare": {
        "headers": ["cf-ray", "cf-cache-status", ("server", r"cloudflare")],
        "html": [r'challenges\.cloudflare\.com', r'__cf_chl_'],
        "category": "CDN / WAF",
    },
    "AWS CloudFront": {
        "headers": ["x-amz-cf-id", "x-amz-cf-pop", ("via", r"CloudFront")],
        "html": [],
        "category": "CDN",
    },
    "Fastly": {
        "headers": ["x-fastly-request-id", ("via", r"varnish")],
        "html": [],
        "category": "CDN",
    },
    "Vercel": {
        "headers": ["x-vercel-id", "x-vercel-cache", ("server", r"Vercel")],
        "html": [],
        "category": "Cloud Platform",
    },
}


def fingerprint_technologies(headers: Dict[str, str], html: str) -> List[Dict[str, str]]:
    """
    Inspect HTTP response headers and HTML body against known technology signatures.
    """
    detected: List[Dict[str, str]] = []
    headers_lower = {k.lower(): str(v) for k, v in headers.items()}
    html_sample = html[:50000] if html else ""

    for tech_name, sig in FRAMEWORK_SIGNATURES.items():
        matched = False
        evidence = ""

        # Check headers
        for h_rule in sig.get("headers", []):
            if isinstance(h_rule, tuple):
                h_name, h_pattern = h_rule
                h_val = headers_lower.get(h_name.lower(), "")
                if h_val and re.search(h_pattern, h_val, re.IGNORECASE):
                    matched = True
                    evidence = f"Header {h_name}: {h_val}"
                    break
            elif isinstance(h_rule, str):
                if h_rule.lower() in headers_lower:
                    matched = True
                    evidence = f"Header: {h_rule}"
                    break

        # Check HTML signatures
        if not matched and html_sample:
            for pattern in sig.get("html", []):
                if re.search(pattern, html_sample, re.IGNORECASE):
                    matched = True
                    evidence = f"DOM Pattern: {pattern}"
                    break

        if matched:
            detected.append({
                "name": tech_name,
                "category": sig.get("category", "General"),
                "evidence": evidence,
            })

    # Deduplicate React if Next.js is already detected
    names = {d["name"] for d in detected}
    if "Next.js" in names:
        detected = [d for d in detected if d["name"] != "React"]
    if "Nuxt.js" in names:
        detected = [d for d in detected if d["name"] != "Vue.js"]

    return detected


def extract_structured_metadata(html: str) -> Dict[str, Any]:
    """
    Extract JSON-LD (schema.org), OpenGraph meta tags, and title from HTML.
    """
    metadata: Dict[str, Any] = {
        "title": "",
        "description": "",
        "json_ld": [],
        "opengraph": {},
    }
    if not html:
        return metadata

    # 1. Title
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if title_match:
        metadata["title"] = title_match.group(1).strip()

    # 2. Meta description
    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not desc_match:
        desc_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']', html, re.IGNORECASE)
    if desc_match:
        metadata["description"] = desc_match.group(1).strip()

    # 3. OpenGraph tags
    og_matches = re.findall(r'<meta[^>]+property=["\']og:([a-zA-Z0-9_\-]+)["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    for og_k, og_v in og_matches:
        metadata["opengraph"][og_k] = og_v.strip()

    # 4. JSON-LD scripts
    json_ld_blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    for block in json_ld_blocks:
        try:
            parsed = json.loads(block.strip())
            if isinstance(parsed, list):
                metadata["json_ld"].extend(parsed)
            elif isinstance(parsed, dict):
                metadata["json_ld"].append(parsed)
        except Exception:
            pass

    return metadata


async def fetch_sitemap_urls(client: httpx.AsyncClient, base_url: str, max_urls: int = 50) -> List[str]:
    """
    Discover and parse XML sitemaps (/sitemap.xml, /sitemap_index.xml).
    """
    parsed_base = urllib.parse.urlparse(base_url)
    base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    discovered_urls: Set[str] = set()

    candidate_sitemaps = [
        f"{base_origin}/sitemap.xml",
        f"{base_origin}/sitemap_index.xml",
        f"{base_origin}/sitemap1.xml",
    ]

    for sitemap_url in candidate_sitemaps:
        if len(discovered_urls) >= max_urls:
            break
        try:
            res = await client.get(sitemap_url, timeout=5.0)
            if res.status_code != 200 or not res.text:
                continue

            content = res.text.strip()
            if not ("<urlset" in content or "<sitemapindex" in content or "<url" in content):
                continue

            # Parse XML
            try:
                root = ET.fromstring(content)
                # Strip XML namespaces for uniform querying
                for elem in root.iter():
                    if "}" in elem.tag:
                        elem.tag = elem.tag.split("}", 1)[1]

                # Check if sitemap index (contains child sitemaps)
                for sitemap_elem in root.findall(".//sitemap/loc"):
                    child_loc = (sitemap_elem.text or "").strip()
                    if child_loc and len(discovered_urls) < max_urls:
                        try:
                            child_res = await client.get(child_loc, timeout=5.0)
                            if child_res.status_code == 200:
                                child_root = ET.fromstring(child_res.text.strip())
                                for c_elem in child_root.iter():
                                    if "}" in c_elem.tag:
                                        c_elem.tag = c_elem.tag.split("}", 1)[1]
                                for url_loc in child_root.findall(".//url/loc"):
                                    u = (url_loc.text or "").strip()
                                    if u and not any(u.lower().endswith(ext) for ext in STATIC_EXTENSIONS):
                                        discovered_urls.add(u)
                        except Exception:
                            pass

                # Check urlset locs
                for url_elem in root.findall(".//url/loc"):
                    u = (url_elem.text or "").strip()
                    if u and not any(u.lower().endswith(ext) for ext in STATIC_EXTENSIONS):
                        discovered_urls.add(u)

            except ET.ParseError:
                # Fallback to regex loc extraction
                locs = re.findall(r"<loc>(https?://[^<]+)</loc>", content)
                for loc in locs:
                    if not any(loc.lower().endswith(ext) for ext in STATIC_EXTENSIONS):
                        discovered_urls.add(loc.strip())

        except Exception as e:
            logger.debug(f"Sitemap check error on {sitemap_url}: {e}")

    return list(discovered_urls)[:max_urls]


async def fetch_robots_txt(client: httpx.AsyncClient, base_url: str) -> Dict[str, Any]:
    """
    Fetch and parse /robots.txt for sitemap declarations and disallowed paths.
    """
    parsed_base = urllib.parse.urlparse(base_url)
    robots_url = f"{parsed_base.scheme}://{parsed_base.netloc}/robots.txt"
    result: Dict[str, Any] = {
        "sitemaps": [],
        "disallowed_paths": [],
        "allowed_paths": [],
    }

    try:
        res = await client.get(robots_url, timeout=5.0)
        if res.status_code == 200 and res.text:
            for line in res.text.splitlines():
                line_clean = line.strip()
                if not line_clean or line_clean.startswith("#"):
                    continue
                if line_clean.lower().startswith("sitemap:"):
                    s_url = line_clean.split(":", 1)[1].strip()
                    if s_url:
                        result["sitemaps"].append(s_url)
                elif line_clean.lower().startswith("disallow:"):
                    d_path = line_clean.split(":", 1)[1].strip()
                    if d_path and d_path != "/":
                        result["disallowed_paths"].append(d_path)
                elif line_clean.lower().startswith("allow:"):
                    a_path = line_clean.split(":", 1)[1].strip()
                    if a_path and a_path != "/":
                        result["allowed_paths"].append(a_path)
    except Exception as e:
        logger.debug(f"Robots.txt check warning: {e}")

    return result


API_SUBDOMAIN_PREFIXES = [
    "api", "api-v1", "api-v2", "app", "auth", "gateway", "graphql",
    "v1", "v2", "v3", "admin", "staging", "dev", "portal", "ws", "rest", "backend"
]


def resolve_subdomains_and_dns(domain: str, timeout_sec: float = 2.0) -> Dict[str, Any]:
    """
    Query DNS A and CNAME records for common API host prefixes using dnspython and tldextract.
    """
    discovered: List[Dict[str, Any]] = []
    parsed = urllib.parse.urlparse(domain if "://" in domain else f"https://{domain}")
    base_host = (parsed.hostname or domain).lower()

    # Extract registered domain using Public Suffix List (e.g. example.co.uk from sub.example.co.uk)
    try:
        import tldextract
        ext = tldextract.extract(base_host)
        root_domain = ext.registered_domain if ext.registered_domain else ".".join(base_host.split(".")[-2:])
    except Exception:
        parts = base_host.split(".")
        root_domain = ".".join(parts[-2:]) if len(parts) >= 2 else base_host

    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout_sec
        resolver.lifetime = timeout_sec

        for prefix in API_SUBDOMAIN_PREFIXES:
            sub_host = f"{prefix}.{root_domain}"
            if sub_host == base_host:
                continue
            try:
                answers = resolver.resolve(sub_host, "A")
                ips = [rdata.to_text() for rdata in answers]
                cnames = []
                try:
                    cname_answers = resolver.resolve(sub_host, "CNAME")
                    cnames = [r.to_text() for r in cname_answers]
                except Exception:
                    pass

                discovered.append({
                    "subdomain": sub_host,
                    "url": f"https://{sub_host}",
                    "ips": ips,
                    "cnames": cnames,
                    "prefix": prefix,
                })
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"DNS resolution warning on {domain}: {e}")

    return {
        "root_domain": root_domain,
        "base_host": base_host,
        "discovered_subdomains": discovered,
    }


async def recon_website(
    url: str,
    auth_headers: Optional[Dict[str, str]] = None,
    timeout_sec: float = 15.0,
) -> ToolResult:
    """
    Execute autonomous Phase 1 reconnaissance against the target application:
    - Analyzes root response headers & body for tech stack fingerprinting.
    - Discovers XML sitemaps and extracts public subpaths.
    - Parses /robots.txt for route hints.
    - Extracts JSON-LD, OpenGraph, and title metadata.
    """
    start_time = time.perf_counter()
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    is_safe, err = validate_target_url(url)
    if not is_safe:
        return ToolResult(
            tool_name="recon_website",
            status="error",
            latency_ms=0,
            error=f"Guardrail Blocked: {err}",
            data={"url": url},
        )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if auth_headers:
        headers.update(auth_headers)

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout_sec, verify=False) as client:
            # 1. Fetch Landing Page
            landing_res = await client.get(url)
            status_code = landing_res.status_code
            resp_headers = dict(landing_res.headers)
            html_content = landing_res.text or ""

            # 2. Fingerprint Technologies & WAF
            technologies = fingerprint_technologies(resp_headers, html_content)
            waf_detected = any(t["category"] == "CDN / WAF" for t in technologies) or (status_code == 403)

            # 3. Extract Metadata (Title, OpenGraph, JSON-LD)
            metadata = extract_structured_metadata(html_content)

            # 4. Fetch Robots.txt and Sitemaps
            robots_data = await fetch_robots_txt(client, url)
            sitemap_urls = await fetch_sitemap_urls(client, url, max_urls=30)

            # 5. DNS & Subdomain API Gateway Enumeration
            dns_data = resolve_subdomains_and_dns(url)
            discovered_subdomains = dns_data.get("discovered_subdomains", [])

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            tech_names = [t["name"] for t in technologies]
            summary_desc = (
                f"Reconnaissance complete on {url}: "
                f"Status {status_code}, detected {len(technologies)} technologies ({', '.join(tech_names) if tech_names else 'Generic Web'}), "
                f"discovered {len(sitemap_urls)} sitemap routes, {len(discovered_subdomains)} subdomains."
            )

            return ToolResult(
                tool_name="recon_website",
                status="success",
                latency_ms=latency_ms,
                data={
                    "target_url": url,
                    "status_code": status_code,
                    "title": metadata.get("title", ""),
                    "description": metadata.get("description", ""),
                    "technologies": technologies,
                    "tech_stack_summary": tech_names,
                    "is_waf_protected": waf_detected,
                    "sitemap_urls": sitemap_urls,
                    "robots_txt": robots_data,
                    "dns_data": dns_data,
                    "discovered_subdomains": discovered_subdomains,
                    "json_ld_schemas": metadata.get("json_ld", []),
                    "opengraph": metadata.get("opengraph", {}),
                },
            )

    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        logger.warning(f"Reconnaissance failure on {url}: {e}")
        return ToolResult(
            tool_name="recon_website",
            status="error",
            latency_ms=latency_ms,
            error=str(e),
            data={"target_url": url},
        )
