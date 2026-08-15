"""
Redis-backed Crawl Job Queue Client.
Enqueues crawl jobs for decoupled worker execution, supporting retries,
status checks, cancellation, and graceful fallback.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.core.redis import get_redis_client

logger = logging.getLogger("queue.client")

QUEUE_NAME = "insightapi:queue:crawls"
JOB_PREFIX = "insightapi:job:"


class CrawlQueueClient:
    """Client for enqueueing and querying background crawl jobs in Redis."""

    @classmethod
    async def enqueue_crawl_job(cls, session_id: str, payload: Dict[str, Any]) -> str:
        """
        Pushes a new crawl task onto the Redis job queue.
        Returns the job_id (matching session_id).
        """
        redis = await get_redis_client()
        job_key = f"{JOB_PREFIX}{session_id}"

        job_meta = {
            "job_id": session_id,
            "status": "queued",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "retry_count": 0,
            "max_retries": 2,
        }

        # Store job metadata with 7-day TTL
        await redis.set(job_key, json.dumps(job_meta), ex=604800)
        # Push to work queue list
        await redis.lpush(QUEUE_NAME, session_id)
        logger.info(f"Enqueued crawl job [{session_id}] to Redis queue '{QUEUE_NAME}'")
        return session_id

    @classmethod
    async def get_job_status(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves current job status and metadata from Redis."""
        try:
            redis = await get_redis_client()
            job_key = f"{JOB_PREFIX}{session_id}"
            data = await redis.get(job_key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Failed to fetch job status for {session_id}: {e}")
        return None

    @classmethod
    async def cancel_job(cls, session_id: str) -> bool:
        """Cancels a pending or queued job in Redis."""
        try:
            redis = await get_redis_client()
            job_key = f"{JOB_PREFIX}{session_id}"
            data = await redis.get(job_key)
            if data:
                meta = json.loads(data)
                meta["status"] = "cancelled"
                meta["cancelled_at"] = datetime.now(timezone.utc).isoformat()
                await redis.set(job_key, json.dumps(meta), ex=604800)
                return True
        except Exception as e:
            logger.error(f"Failed to cancel job {session_id}: {e}")
        return False
