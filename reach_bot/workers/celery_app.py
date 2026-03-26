from celery import Celery

from config import settings

celery_app = Celery(
    "reach_bot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.analysis_worker", "workers.cleanup_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
