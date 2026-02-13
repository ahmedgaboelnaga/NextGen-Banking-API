from celery import Celery
from backend.app.core.config import settings

celery_app = Celery(
    "worker",
    broker=f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}//",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
)

celery_app.conf.update(
    # Serialization settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["application/json"],
    # Task/result handling:
    task_track_started=True,
    task_send_sent_event=True,
    result_extended=True,
    result_backend_always_retry=True,
    result_backend_max_retries=10,
    result_expires=3600,
    # Task execution:
    task_time_limit=5 * 60,
    task_soft_time_limit=5 * 60,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=30,
    task_maximum_retries=3,
    # Queues:
    task_default_queue="nextgen_tasks",
    task_create_missing_queues=True,
    # Worker process control:
    worker_send_task_events=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=50000,
    worker_log_format="[%(asctime)s: %(levelname)s/$(processName)s] [%(taskname)s(%(taskid)s)] %(message)s",
)

celery_app.autodiscover_tasks(
    packages=["backend.app.core.emails"],
    related_name="tasks",
    force=True,
)
