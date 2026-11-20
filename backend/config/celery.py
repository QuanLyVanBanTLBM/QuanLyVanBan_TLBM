import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

try:
    from backend.services.ai_sync_schedule import build_ai_beat_schedule
except ImportError:
    from services.ai_sync_schedule import build_ai_beat_schedule

_beat_schedule = dict(getattr(app.conf, "beat_schedule", None) or {})
_beat_schedule.update(build_ai_beat_schedule())
app.conf.beat_schedule = _beat_schedule
