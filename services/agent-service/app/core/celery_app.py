"""
celery_app.py — Celery application for InsightAPI AI agent-service.

Broker  : Redis (reuses existing redis infra from app/core/redis.py config)
Backend : Redis (job result storage with 7-day TTL)

Task routing
------------
All crawl tasks land on the ``crawls`` queue, consumed exclusively by
``agent-worker`` containers. This lets API capacity and crawl capacity
scale independently via docker-compose replica counts.

Usage in tasks::

    from app.core.celery_app import celery_app

    @celery_app.task(...)
    def my_task():
        ...

Launch worker::

    celery -A app.core.celery_app worker --loglevel=info --concurrency=2
"""
try:
    from celery import Celery
    HAS_CELERY = True
except ImportError:
    Celery = None
    HAS_CELERY = False

from app.core.config import settings

# ── Build broker / backend URLs ──────────────────────────────────────────────

_broker_url: str = getattr(settings, "CELERY_BROKER_URL", None) or settings.get_redis_url()
_result_backend: str = getattr(settings, "CELERY_RESULT_BACKEND", None) or settings.get_redis_url()

# ── Celery application ────────────────────────────────────────────────────────

if HAS_CELERY and Celery:
    celery_app = Celery(
        "insightapi",
        broker=_broker_url,
        backend=_result_backend,
        include=["app.tasks.crawl_tasks"],  # auto-discover task modules
    )
else:
    celery_app = None

if celery_app is not None:
    celery_app.conf.update(
        broker_url=_broker_url,
        result_backend=_result_backend,
        # Serialisation
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Result TTL — 7 days (matches existing Redis job metadata TTL)
    result_expires=604800,

    # Task acknowledgement: acknowledge after task starts so Celery can redeliver
    # on unexpected worker crash (requires idempotent tasks).
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Worker prefetch — set to 1 so long-running crawl tasks don't starve others
    worker_prefetch_multiplier=1,

    # Retry policy for transient broker connectivity issues
    broker_transport_options={
        "visibility_timeout": 3600,  # 1 hour — longer than max crawl duration
    },

    # Queue routing: all tasks → "crawls" queue by default
    task_default_queue="crawls",
    task_routes={
        "app.tasks.crawl_tasks.run_crawl_task": {"queue": "crawls"},
    },
)
