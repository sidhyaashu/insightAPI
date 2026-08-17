"""
crawl_tasks.py — Celery task for autonomous crawl execution.

Architecture
------------
Celery workers are separate *synchronous* Python processes. Our crawl engine
is fully async (asyncio + Playwright). The bridge is a single ``asyncio.run()``
call inside the Celery task, which creates a fresh event loop per task execution.

This is safe because:
- Celery workers use the ``prefork`` pool by default (separate OS processes, not threads).
- Each task gets its own process-scoped event loop via ``asyncio.run()``.
- Playwright's async API works correctly inside ``asyncio.run()``.

Retry strategy
--------------
- Transient failures (network errors, LLM timeouts, browser crashes, DB blips)
  → retry up to 2 times with exponential back-off: 60s, 120s.
- Logic errors (already-handled by run_background_crawl: domain rejected, quota
  exceeded) → these exceptions are caught inside ``run_background_crawl`` and
  persist the failure to Postgres; we do NOT re-raise them here.
- After max retries: ``on_failure`` marks crawl status=failed in Postgres and
  publishes a WS failure event so the client knows.

Dead-letter path
----------------
Exhausted jobs are not silently dropped — ``on_failure`` is called by Celery
after the final retry fails, persisting the terminal failure to Postgres.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

try:
    from celery import Task
    from celery.utils.log import get_task_logger
    HAS_CELERY = True
except ImportError:
    Task = object
    def get_task_logger(name):
        import logging
        return logging.getLogger(name)
    HAS_CELERY = False

from app.core.celery_app import celery_app

logger = get_task_logger(__name__)


def is_celery_worker_active(timeout: float = 0.5) -> bool:
    """Check whether at least one Celery worker is active and accepting jobs."""
    if not HAS_CELERY or celery_app is None:
        return False
    try:
        inspector = celery_app.control.inspect(timeout=timeout)
        if not inspector:
            return False
        pings = inspector.ping()
        return bool(pings and len(pings) > 0)
    except Exception as e:
        logger.debug(f"Celery liveness ping check failed: {e}")
        return False


def _reap_stale_task(timeout_minutes: int = 5) -> int:
    return asyncio.run(_reap_stale_crawls_async(timeout_minutes))


if HAS_CELERY and celery_app is not None:
    reap_stale_queued_crawls = celery_app.task(
        name="app.tasks.crawl_tasks.reap_stale_queued_crawls"
    )(_reap_stale_task)
else:
    reap_stale_queued_crawls = _reap_stale_task


async def _reap_stale_crawls_async(timeout_minutes: int = 5) -> int:
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.crawl_session import CrawlSession

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
    reaped_count = 0
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(CrawlSession).where(
                CrawlSession.status.in_(["queued", "pending"]),
                CrawlSession.created_at < cutoff,
            )
            result = await db.execute(stmt)
            stale_sessions = result.scalars().all()
            for s in stale_sessions:
                s.status = "failed"
                s.error_message = f"Crawl timed out: no worker picked up this job within {timeout_minutes} minutes."
                reaped_count += 1
            if reaped_count > 0:
                await db.commit()
                logger.warning(f"Reaped {reaped_count} stale queued crawl sessions.")
    except Exception as e:
        logger.error(f"Error executing reap_stale_queued_crawls: {e}")
    return reaped_count


# ── Transient error types that warrant a retry ───────────────────────────────

_TRANSIENT_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


class CrawlTask(Task):
    """Custom Celery Task base class with failure handler for dead-letter path."""

    abstract = True

    def on_failure(self, exc: Exception, task_id: str, args, kwargs, einfo) -> None:
        """Called after all retries are exhausted. Marks crawl as failed in Postgres."""
        session_id: str = kwargs.get("session_id") or (args[0] if args else "unknown")
        error_str: str = f"{type(exc).__name__}: {exc}"
        logger.error(
            f"[CrawlTask] Dead-letter: crawl [{session_id}] failed permanently. "
            f"Reason: {error_str}"
        )
        asyncio.run(_persist_failure(session_id, error_str))


async def _persist_failure(session_id: str, error_message: str) -> None:
    """Persist terminal failure to Postgres and notify WebSocket subscribers."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.repositories.crawl_repo import CrawlRepository
        from app.api.v1.endpoints.crawls import publish_ws_event

        async with AsyncSessionLocal() as db:
            repo = CrawlRepository(db)
            await repo.update_status(
                session_id=session_id,
                status="failed",
                error_message=error_message,
            )

        await publish_ws_event(
            session_id,
            {"type": "error", "message": f"Crawl failed after all retries: {error_message}"},
        )
        logger.info(f"[CrawlTask] Persisted dead-letter failure for crawl [{session_id}].")
    except Exception as persist_err:
        logger.error(f"[CrawlTask] Failed to persist dead-letter for [{session_id}]: {persist_err}")


def _run_crawl_worker_impl(self, session_id: str, payload: Dict[str, Any]) -> None:
    """Core worker logic for run_crawl_task."""
    try:
        from celery.exceptions import SoftTimeLimitExceeded
    except ImportError:
        SoftTimeLimitExceeded = TimeoutError

    logger.info(f"[CrawlTask] Starting crawl [{session_id}]")
    try:
        asyncio.run(_execute_crawl(session_id, payload))
        logger.info(f"[CrawlTask] Crawl [{session_id}] completed successfully.")
    except SoftTimeLimitExceeded:
        msg = "Crawl exceeded time limit (25 min). Scheduling retry."
        logger.warning(f"[CrawlTask] [{session_id}]: {msg}")
        if hasattr(self, "retry"):
            raise self.retry(
                exc=SoftTimeLimitExceeded(msg),
                countdown=60 * (2 ** getattr(getattr(self, "request", None), "retries", 0)),
                max_retries=getattr(self, "max_retries", 2),
            )
    except Exception as exc:
        error_str = f"{type(exc).__name__}: {exc}"
        retries = getattr(getattr(self, "request", None), "retries", 0)
        max_retries = getattr(self, "max_retries", 2)
        if retries < max_retries and hasattr(self, "retry"):
            countdown = 60 * (2 ** retries)
            logger.warning(
                f"[CrawlTask] [{session_id}] failed (attempt {retries + 1}/{max_retries + 1}): "
                f"{error_str}. Retrying in {countdown}s."
            )
            raise self.retry(exc=exc, countdown=countdown, max_retries=max_retries)
        else:
            logger.error(
                f"[CrawlTask] [{session_id}] permanently failed after {max_retries + 1} attempts: {error_str}"
            )
            raise


class _DummyCeleryTask:
    def delay(self, *args, **kwargs):
        raise RuntimeError("Celery is not installed or active in this process.")


if HAS_CELERY and celery_app is not None:
    run_crawl_task = celery_app.task(
        bind=True,
        base=CrawlTask,
        name="app.tasks.crawl_tasks.run_crawl_task",
        queue="crawls",
        max_retries=2,
        default_retry_delay=60,
        acks_late=True,
        reject_on_worker_lost=True,
        time_limit=1800,
        soft_time_limit=1500,
    )(_run_crawl_worker_impl)
else:
    run_crawl_task = _DummyCeleryTask()


async def _execute_crawl(session_id: str, payload: Dict[str, Any]) -> None:
    """
    Thin async wrapper around ``run_background_crawl`` that updates crawl
    status to ``running`` in Postgres/Redis at task start.
    """
    # Mark as running in Redis job meta (for status polling)
    try:
        from app.core.redis import get_redis_client
        import json
        from datetime import datetime, timezone

        redis = await get_redis_client()
        job_key = f"insightapi:job:{session_id}"
        raw = await redis.get(job_key)
        if raw:
            meta = json.loads(raw)
            meta["status"] = "running"
            meta["started_at"] = datetime.now(timezone.utc).isoformat()
            meta["worker"] = "celery"
            await redis.set(job_key, json.dumps(meta), ex=604800)
    except Exception:
        pass  # Non-fatal — Postgres is the source of truth

    from app.api.v1.endpoints.crawls import run_background_crawl
    await run_background_crawl(**payload)
