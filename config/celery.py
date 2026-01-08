import os
import logging
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.base')

app = Celery('casino_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Log Celery Redis configuration for debugging
logger = logging.getLogger(__name__)
celery_broker = getattr(settings, 'CELERY_BROKER_URL', 'NOT SET')
celery_backend = getattr(settings, 'CELERY_RESULT_BACKEND', 'NOT SET')
redis_url = getattr(settings, 'REDIS_URL', 'NOT SET')
print("=" * 60)
print("CELERY CONFIGURATION:")
print(f"  CELERY_BROKER_URL: {celery_broker}")
print(f"  CELERY_RESULT_BACKEND: {celery_backend}")
print(f"  REDIS_URL: {redis_url}")
print("=" * 60)
logger.info("=" * 60)
logger.info("CELERY CONFIGURATION:")
logger.info(f"  CELERY_BROKER_URL: {celery_broker}")
logger.info(f"  CELERY_RESULT_BACKEND: {celery_backend}")
logger.info(f"  REDIS_URL: {redis_url}")
logger.info("=" * 60)

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')