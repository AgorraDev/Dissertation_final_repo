from celery import Celery
from app.core.config import settings

# Creates the Celery app with connection to Redis
celery_app = Celery(
    "energy_background",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

# Updates configuration of the Celery app
celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    task_default_retry_delay=5,
    task_max_retries=3,
)

@celery_app.task(name="ping")
def ping():
    return "pong"
