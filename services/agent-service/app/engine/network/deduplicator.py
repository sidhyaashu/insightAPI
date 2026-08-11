import re
import hashlib
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

UUID_REGEX = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
MONGO_ID_REGEX = re.compile(r"^[0-9a-fA-F]{24}$")
HASH_HEX_REGEX = re.compile(r"^[0-9a-fA-F]{32,64}$")
DATE_REGEX = re.compile(r"^\d{4}[-/]\d{2}[-/]\d{2}$")
NUMERIC_REGEX = re.compile(r"^\d+$")
STRIPE_PREFIX_REGEX = re.compile(r"^(cus|sub|pi|ch|evt|usr|org|inv)_[a-zA-Z0-9]{14,32}$")
NANOID_REGEX = re.compile(r"^[A-Za-z0-9_-]{16,32}$")


class URLDeduplicator:
    """
    Normalizes dynamic URL paths containing IDs, UUIDs, dates, or hashes into
    parameterized template routes (e.g. /api/users/123 -> /api/users/{id}).
    """
    @staticmethod
    def parameterize_path(url: str) -> str:
        """
        Parses a URL string and replaces dynamic path parameters and query values with generic placeholders.
        """
        parsed = urlparse(url)
        path = parsed.path
        segments = path.split("/")
        parameterized_segments = []

        for seg in segments:
            if not seg:
                parameterized_segments.append(seg)
                continue

            if UUID_REGEX.match(seg):
                parameterized_segments.append("{uuid}")
            elif MONGO_ID_REGEX.match(seg):
                parameterized_segments.append("{id}")
            elif STRIPE_PREFIX_REGEX.match(seg):
                parameterized_segments.append("{id}")
            elif HASH_HEX_REGEX.match(seg):
                parameterized_segments.append("{hash}")
            elif DATE_REGEX.match(seg):
                parameterized_segments.append("{date}")
            elif NUMERIC_REGEX.match(seg):
                parameterized_segments.append("{id}")
            elif NANOID_REGEX.match(seg) and not seg.startswith("api"):
                parameterized_segments.append("{id}")
            else:
                parameterized_segments.append(seg)

        parameterized_path = "/".join(parameterized_segments)
        
        # Parameterize dynamic query params (e.g. ?page=2&sort=asc -> ?page={val}&sort={val})
        query_params = parse_qs(parsed.query)
        if query_params:
            parameterized_query = urlencode([(k, "{val}") for k in sorted(query_params.keys())])
            return urlunparse((parsed.scheme, parsed.netloc, parameterized_path, "", parameterized_query, ""))

        return urlunparse((parsed.scheme, parsed.netloc, parameterized_path, "", "", ""))


class DOMStateHasher:
    """
    Computes a deterministic hash representation of a UI state given a URL
    and its interactive accessibility tree (AXTree) DOM elements, with volatile text normalization.
    """
    @staticmethod
    def compute_state_hash(url: str, interactive_elements: Optional[List[Dict[str, Any]]] = None) -> str:
        parsed = urlparse(url)
        normalized_url = f"{parsed.netloc}{parsed.path}"
        
        elements_signature = []
        if interactive_elements:
            for el in interactive_elements:
                tag = el.get("tag", "").lower()
                role = el.get("role", "").lower()
                raw_text = (el.get("text") or el.get("ariaLabel") or "").strip().lower()
                # Sanitize volatile standalone numbers/digits and dates to prevent state hash traps
                sanitized_text = re.sub(r"\b\d+\b", "", raw_text).strip()
                elements_signature.append(f"{tag}:{role}:{sanitized_text}")
            elements_signature.sort()
            
        raw_repr = f"{normalized_url}|{'|'.join(elements_signature)}"
        return hashlib.md5(raw_repr.encode("utf-8")).hexdigest()


class RouteClusterTracker:
    """
    Tracks template route clusters and prunes redundant crawl instances
    only when consecutive instances exhibit identical DOM state hashes.
    """
    _cluster_counts: Dict[str, set] = {}
    _cluster_dom_history: Dict[str, List[str]] = {}

    @classmethod
    def reset(cls):
        """Resets route cluster counts and DOM history."""
        cls._cluster_counts.clear()
        cls._cluster_dom_history.clear()

    @classmethod
    def register_route_visit(cls, url: str, dom_hash: Optional[str] = None, max_cluster_size: int = 3) -> bool:
        """
        Registers a visited URL in its template route cluster.
        """
        template_route = URLDeduplicator.parameterize_path(url)
        if template_route not in cls._cluster_counts:
            cls._cluster_counts[template_route] = set()
            cls._cluster_dom_history[template_route] = []

        entry_key = dom_hash if dom_hash else url
        cls._cluster_counts[template_route].add(entry_key)
        cls._cluster_dom_history[template_route].append(entry_key)

        return cls.should_prune_route(url, max_cluster_size=max_cluster_size)

    @classmethod
    def should_prune_route(cls, url: str, max_cluster_size: int = 3) -> bool:
        """
        Checks if a URL belongs to a saturated route cluster that should be pruned.
        Only prunes if the last max_cluster_size DOM state hashes were identical.
        """
        template_route = URLDeduplicator.parameterize_path(url)
        history = cls._cluster_dom_history.get(template_route, [])
        
        if len(history) < max_cluster_size:
            return False

        # Check if the last max_cluster_size instances have identical DOM hashes
        recent_hashes = history[-max_cluster_size:]
        return len(set(recent_hashes)) == 1
