"""
Unit and integration tests for Production Readiness:
- Database Connection Pooling Configuration
- LLM Token and USD Cost Persistence
- Observability & Prometheus Metrics
- Correlation ID Distributed Tracing
- Redis Job Queue Worker Lifecycle
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from app.core.config import settings
from app.core.database import engine
from app.models.crawl_session import CrawlSession
from app.repositories.crawl_repo import CrawlRepository
from app.core.observability import MetricsRegistry, CorrelationIdMiddleware, correlation_id_ctx
from app.queue.client import CrawlQueueClient, QUEUE_NAME, JOB_PREFIX
from app.queue.worker import CrawlJobWorker


def test_db_connection_pooling_configuration():
    """Verify SQLAlchemy engine is configured with production connection pool limits."""
    pool = engine.pool
    assert hasattr(pool, "size") or hasattr(pool, "_pool")
    assert settings.DB_POOL_SIZE >= 10
    assert settings.DB_MAX_OVERFLOW >= 5
    assert settings.DB_POOL_TIMEOUT >= 10
    assert settings.DB_POOL_RECYCLE >= 300


@pytest.mark.asyncio
async def test_crawl_session_llm_metrics_persistence():
    """Verify CrawlSession model and repository persist exact LLM tokens and estimated USD costs."""
    session = CrawlSession(
        id="session-cost-1",
        user_id="usr-test",
        user_tier="PRO",
        target_url="https://api.store.com",
        prompt_tokens=1200,
        completion_tokens=450,
        total_tokens=1650,
        cost_usd=0.00345,
        llm_metrics_json={"llm_calls_made": 3, "tokens_used": 1650, "estimated_cost_usd": 0.00345},
    )

    data = session.to_dict()
    assert data["prompt_tokens"] == 1200
    assert data["completion_tokens"] == 450
    assert data["total_tokens"] == 1650
    assert data["cost_usd"] == 0.00345
    assert data["llm_metrics"]["llm_calls_made"] == 3


def test_observability_metrics_and_prometheus_renderer():
    """Verify MetricsRegistry accumulates crawl, endpoint, and token metrics and exports Prometheus text."""
    reg = MetricsRegistry()

    reg.record_crawl_start(tier="PRO")
    assert reg.active_crawls == 1

    reg.record_endpoint_discovered(method="POST")
    reg.record_endpoint_discovered(method="GET")
    reg.record_llm_tokens(tier_name="FAST", tokens=850)

    reg.record_crawl_complete(
        tier="PRO",
        status="completed",
        duration_seconds=12.5,
        captured_count=2,
        tokens_used=850,
        cost_usd=0.0012,
    )

    assert reg.active_crawls == 0
    prom_text = reg.render_prometheus_text()

    assert "insightapi_active_crawls 0" in prom_text
    assert 'insightapi_crawls_total{tier="PRO",status="completed"} 1' in prom_text
    assert 'insightapi_endpoints_discovered_total{method="POST"} 1' in prom_text
    assert 'insightapi_endpoints_discovered_total{method="GET"} 1' in prom_text
    assert 'insightapi_llm_tokens_total{tier="FAST"} 850' in prom_text
    assert "insightapi_llm_cost_usd_total 0.001200" in prom_text


def test_correlation_id_middleware():
    """Verify CorrelationIdMiddleware extracts and echoes X-Correlation-ID header."""
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/test-trace")
    async def test_trace():
        return {"correlation_id": correlation_id_ctx.get()}

    client = TestClient(app)

    # 1. Custom incoming Correlation ID
    resp1 = client.get("/test-trace", headers={"X-Correlation-ID": "corr-xyz-123"})
    assert resp1.status_code == 200
    assert resp1.headers["X-Correlation-ID"] == "corr-xyz-123"
    assert resp1.json()["correlation_id"] == "corr-xyz-123"

    # 2. Auto-generated Correlation ID
    resp2 = client.get("/test-trace")
    assert resp2.status_code == 200
    assert "X-Correlation-ID" in resp2.headers
    assert len(resp2.headers["X-Correlation-ID"]) > 10


@pytest.mark.asyncio
async def test_crawl_job_queue_enqueue_and_worker_execution():
    """Verify CrawlQueueClient enqueues task and CrawlJobWorker executes it."""
    mock_redis = AsyncMock()
    mock_storage = {}

    async def mock_set(key, val, **kw):
        mock_storage[key] = val

    async def mock_get(key):
        return mock_storage.get(key)

    async def mock_lpush(key, val):
        mock_storage.setdefault(key, []).append(val)

    mock_redis.set = AsyncMock(side_effect=mock_set)
    mock_redis.get = AsyncMock(side_effect=mock_get)
    mock_redis.lpush = AsyncMock(side_effect=mock_lpush)

    with patch("app.queue.client.get_redis_client", new=AsyncMock(return_value=mock_redis)), \
         patch("app.queue.worker.get_redis_client", new=AsyncMock(return_value=mock_redis)), \
         patch("app.api.v1.endpoints.crawls.run_background_crawl", new=AsyncMock()) as mock_run:

        session_id = "crawl-job-999"
        payload = {"url": "https://example.com", "max_pages": 3}

        # 1. Enqueue job
        job_id = await CrawlQueueClient.enqueue_crawl_job(session_id, payload)
        assert job_id == session_id
        assert f"{JOB_PREFIX}{session_id}" in mock_storage

        # 2. Process job via worker
        worker = CrawlJobWorker(worker_id="test-worker")
        success = await worker.process_job(session_id)

        assert success is True
        assert mock_run.called
        completed_meta = json.loads(mock_storage[f"{JOB_PREFIX}{session_id}"])
        assert completed_meta["status"] == "completed"
        assert completed_meta["worker_id"] == "test-worker"
