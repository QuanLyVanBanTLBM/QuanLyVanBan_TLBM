"""Configuration and Celery Beat schedule builders for automatic AI knowledge sync."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_AI_SYNC_HOUR = 2
DEFAULT_AI_SYNC_MINUTE = 0
DEFAULT_AI_SYNC_TIMEZONE = "Asia/Ho_Chi_Minh"
AI_SYNC_TASK_NAME = "sync_all_ai_documents"
AI_SYNC_BEAT_ENTRY = "ai-sync-all-documents"

_FALSY_VALUES = {"0", "false", "no", "off"}
_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    cleaned = raw.strip().lower()
    if cleaned in _FALSY_VALUES:
        return False
    if cleaned in _TRUTHY_VALUES:
        return True
    return default


def _parse_int_env(name: str, default: int, min_val: int, max_val: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        parsed = int(raw.strip())
    except ValueError:
        return default
    return max(min_val, min(max_val, parsed))


def _resolve_timezone_name() -> str:
    try:
        from django.conf import settings

        if settings.configured:
            tz_name = getattr(settings, "CELERY_TIMEZONE", None) or getattr(
                settings, "TIME_ZONE", None
            )
            if isinstance(tz_name, str) and tz_name.strip():
                return tz_name.strip()
    except Exception:
        pass
    return DEFAULT_AI_SYNC_TIMEZONE


def _resolve_tzinfo(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone(timedelta(hours=7))


def get_ai_sync_schedule_config() -> dict:
    """Return normalized environment settings for periodic AI synchronization."""
    return {
        "enabled": _parse_bool_env("AI_SYNC_SCHEDULE_ENABLED", True),
        "hour": _parse_int_env("AI_SYNC_SCHEDULE_HOUR", DEFAULT_AI_SYNC_HOUR, 0, 23),
        "minute": _parse_int_env("AI_SYNC_SCHEDULE_MINUTE", DEFAULT_AI_SYNC_MINUTE, 0, 59),
        "timezone": _resolve_timezone_name(),
    }


def get_ai_sync_schedule_info(now: datetime | None = None) -> dict:
    """Return telemetry describing event-driven and scheduled AI sync behavior."""
    cfg = get_ai_sync_schedule_config()
    enabled = cfg["enabled"]
    hour = cfg["hour"]
    minute = cfg["minute"]
    tz_name = cfg["timezone"]

    next_run_at = None
    if enabled:
        tz = _resolve_tzinfo(tz_name)
        current = now.astimezone(tz) if now is not None and now.tzinfo is not None else (
            now.replace(tzinfo=tz) if now is not None else datetime.now(tz)
        )
        candidate = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= current:
            candidate += timedelta(days=1)
        next_run_at = candidate.isoformat()

    return {
        "enabled": enabled,
        "mode": "event_and_scheduled" if enabled else "event_only",
        "task": AI_SYNC_TASK_NAME,
        "cron": f"{minute} {hour} * * *",
        "hour": hour,
        "minute": minute,
        "time": f"{hour:02d}:{minute:02d}",
        "timezone": tz_name,
        "next_run_at": next_run_at,
    }


def build_ai_beat_schedule() -> dict:
    """Build the Celery Beat schedule dictionary for full AI knowledge reconciliation."""
    cfg = get_ai_sync_schedule_config()
    if not cfg["enabled"]:
        return {}

    from celery.schedules import crontab

    return {
        AI_SYNC_BEAT_ENTRY: {
            "task": AI_SYNC_TASK_NAME,
            "schedule": crontab(hour=cfg["hour"], minute=cfg["minute"]),
        }
    }
