from celery import Celery

from app.config import settings

celery_app = Celery("docintel", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_track_started = True
celery_app.conf.task_acks_late = True
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.imports = ("app.workers.pipeline",)
