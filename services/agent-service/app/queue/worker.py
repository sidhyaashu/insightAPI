"""
Crawl Job Queue Worker.
Pulls queued crawl jobs from Redis, executes them in isolated worker tasks,
manages retries, and records execution status.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.core.redis import get_redis_client
from app.queue.client import QUEUE_NAME, JOB_PREFIX

logger = logging.getLogger("queue.worker")


class CrawlJobWorker:
    """Async background worker consuming and processing crawl jobs from Redis."""

    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self._running = False

    async def process_job(self, session_id: str) -> bool:
        """Executes a single crawl job and records results."""
        redis = await get_redis_client()
        job_key = f"{JOB_PREFIX}{session_id}"

        data = await redis.get(job_key)
        if not data:
            logger.warning(f"Worker {self.worker_id}: Job key {job_key} not found.")
            return False

        meta: Dict[str, Any] = json.loads(data)
        if meta.get("status") == "cancelled":
            logger.info(f"Worker {self.worker_id}: Skipping cancelled job {session_id}.")
            return False

        # Mark job as running
        meta["status"] = "running"
        meta["started_at"] = datetime.now(timezone.utc).isoformat()
        meta["worker_id"] = self.worker_id
        await redis.set(job_key, json.dumps(meta), ex=604800)

        payload = meta.get("payload", {})

        try:
            from app.api.v1.endpoints.crawls import run_background_crawl
            logger.info(f"Worker {self.worker_id}: Starting execution of crawl job [{session_id}]")
            await run_background_crawl(**payload)

            meta["status"] = "completed"
            meta["completed_at"] = datetime.now(timezone.utc).isoformat()
            await redis.set(job_key, json.dumps(meta), ex=604800)
            logger.info(f"Worker {self.worker_id}: Successfully completed crawl job [{session_id}]")
            return True

        except Exception as e:
            error_str = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Worker {self.worker_id}: Error processing job [{session_id}]: {error_str}")

            retries = meta.get("retry_count", 0)
            max_retries = meta.get("max_retries", 2)

            if retries < max_retries:
                meta["retry_count"] = retries + 1
                meta["status"] = "queued"
                meta["last_error"] = error_str
                await redis.set(job_key, json.dumps(meta), ex=604800)
                await redis.lpush(QUEUE_NAME, session_id)
                logger.info(f"Worker {self.worker_id}: Re-queued job [{session_id}] (attempt {retries + 2}/{max_retries + 1})")
            else:
                meta["status"] = "failed"
                meta["error_message"] = error_str
                meta["failed_at"] = datetime.now(timezone.utc).isoformat()
                await redis.set(job_key, json.dumps(meta), ex=604800)
            return False

    async def run_once(self) -> bool:
        """Pulls and executes one job if available. Returns True if a job was processed."""
        try:
            redis = await get_redis_client()
            job_id_bytes = await redis.rpop(QUEUE_NAME)
            if job_id_bytes:
                job_id = job_id_bytes.decode("utf-8") if isinstance(job_id_bytes, bytes) else str(job_id_bytes)
                return await self.process_job(job_id)
        except Exception as e:
            logger.warning(f"Worker {self.worker_id}: Poll error: {e}")
        return False

    async def start(self, poll_interval: float = 1.0) -> None:
        """Starts continuous worker loop polling Redis queue."""
        self._running = True
        logger.info(f"🚀 CrawlJobWorker [{self.worker_id}] started listening on '{QUEUE_NAME}'")
        while self._running:
            did_work = await self.run_once()
            if not did_work:
                await asyncio.sleep(poll_interval)

    def stop(self) -> None:
        """Signals the worker to stop processing jobs."""
        self._running = False
        logger.info(f"CrawlJobWorker [{self.worker_id}] stop requested.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = CrawlJobWorker()
    asyncio.run(worker.start())
