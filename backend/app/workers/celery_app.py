from celery import Celery

from app.core.config import get_settings

s = get_settings()
# Redis is transport only. Durable business intent lives in PostgreSQL Outbox, so task
# results are not persisted in Redis and cannot create unbounded result-backend growth.
celery_app = Celery("lead_platform", broker=s.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
    task_soft_time_limit=110,
    task_time_limit=120,
    task_default_queue="control",
    task_routes={
        "app.workers.tasks.deliver_outbox_event": {"queue": "outbound"},
        "app.workers.tasks.run_discovery_job": {"queue": "discovery"},
        "app.workers.tasks.process_campaign_queue": {"queue": "control"},
        "app.workers.tasks.scan_discovery_jobs": {"queue": "control"},
        "app.workers.tasks.drain_outbox": {"queue": "control"},
        "app.workers.tasks.housekeeping": {"queue": "control"},
    },
    timezone="UTC",
    beat_schedule={
        "outbox-drain-every-2-seconds": {
            "task": "app.workers.tasks.drain_outbox",
            "schedule": 2.0,
        },
        "campaign-queue-every-15-seconds": {
            "task": "app.workers.tasks.process_campaign_queue",
            "schedule": 15.0,
        },
        "discovery-jobs-every-minute": {
            "task": "app.workers.tasks.scan_discovery_jobs",
            "schedule": 60.0,
        },
        "housekeeping-daily": {
            "task": "app.workers.tasks.housekeeping",
            "schedule": 86400.0,
        },
    },
)
celery_app.autodiscover_tasks(["app.workers"])
