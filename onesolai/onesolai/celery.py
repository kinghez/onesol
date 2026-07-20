import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onesolai.settings')

app = Celery('onesolai')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'fetch-vendor-balances-every-hour': {
        'task': 'analytics.tasks.fetch_vendor_balances',
        'schedule': crontab(minute=0, hour='*'), # Run every hour at the top of the hour
    },
}
