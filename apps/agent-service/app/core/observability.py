"""
Observability, Prometheus Metrics & Distributed Request Tracing.
Provides:
- X-Correlation-ID header propagation across gateway, core, and agent service.
- Prometheus /metrics exporter (crawls, active jobs, discovered endpoints, LLM token/cost metrics).
- Structured logging context with correlation IDs.
"""
import time
import uuid
import logging
from contextvars import ContextVar
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("core.observability")

# ContextVar storing current request correlation ID for async logging
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="system")


class CorrelationIdLogFilter(logging.Filter):
    """Injects correlation_id into all logging records."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_ctx.get()
        return True


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Extracts or generates an X-Correlation-ID header, propagates it across
    the request lifecycle, and appends it to response headers.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        corr_id = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4())
        )
        token = correlation_id_ctx.set(corr_id)
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            correlation_id_ctx.reset(token)


class MetricsRegistry:
    """
    In-memory Prometheus-compatible metrics registry.
    Can export to standard Prometheus scrapers via /metrics.
    """
    def __init__(self):
        self.crawls_total: Dict[Tuple[str, str], int] = {}  # (tier, status) -> count
        self.active_crawls: int = 0
        self.endpoints_discovered_total: Dict[str, int] = {}  # method -> count
        self.llm_tokens_total: Dict[str, int] = {}  # (model_tier) -> count
        self.llm_cost_usd_total: float = 0.0
        self.crawl_duration_seconds: list[float] = []

    def record_crawl_start(self, tier: str = "FREE") -> None:
        self.active_crawls = max(0, self.active_crawls + 1)

    def record_crawl_complete(
        self,
        tier: str = "FREE",
        status: str = "completed",
        duration_seconds: float = 0.0,
        captured_count: int = 0,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        self.active_crawls = max(0, self.active_crawls - 1)
        key = (tier.upper(), status.lower())
        self.crawls_total[key] = self.crawls_total.get(key, 0) + 1
        if duration_seconds > 0:
            self.crawl_duration_seconds.append(duration_seconds)
            # Keep sample buffer manageable
            if len(self.crawl_duration_seconds) > 1000:
                self.crawl_duration_seconds = self.crawl_duration_seconds[-1000:]
        self.llm_cost_usd_total += cost_usd

    def record_endpoint_discovered(self, method: str = "GET") -> None:
        m = method.upper()
        self.endpoints_discovered_total[m] = self.endpoints_discovered_total.get(m, 0) + 1

    def record_llm_tokens(self, tier_name: str, tokens: int) -> None:
        self.llm_tokens_total[tier_name] = self.llm_tokens_total.get(tier_name, 0) + tokens

    def render_prometheus_text(self) -> str:
        """Renders metrics in standard Prometheus exposition format."""
        lines = [
            "# HELP insightapi_active_crawls Number of currently running crawl sessions",
            "# TYPE insightapi_active_crawls gauge",
            f"insightapi_active_crawls {self.active_crawls}",
            "",
            "# HELP insightapi_crawls_total Total number of completed/failed crawl sessions",
            "# TYPE insightapi_crawls_total counter",
        ]
        for (tier, status), count in self.crawls_total.items():
            lines.append(f'insightapi_crawls_total{{tier="{tier}",status="{status}"}} {count}')

        lines.extend([
            "",
            "# HELP insightapi_endpoints_discovered_total Total number of API endpoints discovered",
            "# TYPE insightapi_endpoints_discovered_total counter",
        ])
        for method, count in self.endpoints_discovered_total.items():
            lines.append(f'insightapi_endpoints_discovered_total{{method="{method}"}} {count}')

        lines.extend([
            "",
            "# HELP insightapi_llm_tokens_total Total LLM tokens consumed",
            "# TYPE insightapi_llm_tokens_total counter",
        ])
        for t_name, count in self.llm_tokens_total.items():
            lines.append(f'insightapi_llm_tokens_total{{tier="{t_name}"}} {count}')

        lines.extend([
            "",
            "# HELP insightapi_llm_cost_usd_total Total estimated LLM cost in USD",
            "# TYPE insightapi_llm_cost_usd_total counter",
            f"insightapi_llm_cost_usd_total {self.llm_cost_usd_total:.6f}",
        ])
        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
