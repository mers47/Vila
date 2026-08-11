from celery import Celery

from app.core.config import get_settings

s = get_settings()

celery_app = Celery(
    "lead_platform",
    broker=s.redis_url,
    backend=s.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_queues={
        "control": {"exchange": "control", "routing_key": "control"},
        "outbound": {"exchange": "outbound", "routing_key": "outbound"},
        "discovery": {"exchange": "discovery", "routing_key": "discovery"},
    },
    task_routes={
        "app.workers.tasks.process_outbox": {"queue": "control"},
        "app.workers.tasks.dispatch_outbound": {"queue": "outbound"},
        "app.workers.tasks.run_discovery": {"queue": "discovery"},
    },
    beat_schedule={
        "tick-outbox": {"task": "app.workers.tasks.process_outbox", "schedule": 10.0},
        "tick-housekeeping": {"task": "app.workers.tasks.run_housekeeping", "schedule": 3600.0},
        "tick-discovery": {"task": "app.workers.tasks.tick_discovery", "schedule": 60.0},
    },
)