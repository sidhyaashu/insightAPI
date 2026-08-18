"""
celery_app.py — Celery application for InsightAPI AI agent-service.

Broker  : Redis (reuses existing redis infra from app/core/redis.py config)
Backend : Redis (job result storage with 7-day TTL)
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
    )
else:
    celery_app = None

if celery_app is not None:
    celery_app.conf.update(
        broker_url=_broker_url,
        result_backend=_result_backend,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        result_expires=604800,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
    )
