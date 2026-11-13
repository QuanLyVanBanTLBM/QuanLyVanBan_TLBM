from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from .models import BirthdaySchedulerRun, BirthdaySchedulerStatus


VIETNAM_TIME_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")
# A missing completion after the Actions job timeout has an unknown outcome.
SCHEDULER_TIMEOUT = timedelta(hours=2)


def run_status(run, now):
    if run.status == BirthdaySchedulerStatus.RUNNING and now - run.started_at >= SCHEDULER_TIMEOUT:
        return BirthdaySchedulerStatus.UNKNOWN
    return run.status


def scheduler_history(processing_date):
    now = timezone.now()
    runs = list(BirthdaySchedulerRun.objects.filter(processing_date=processing_date))
    slots = []
    for slot in BirthdaySchedulerRun.Slot.values:
        scheduled_at = datetime.combine(processing_date, time.fromisoformat(slot), VIETNAM_TIME_ZONE)
        latest = next((run for run in runs if run.scheduled_slot == slot), None)
        if latest is not None:
            status = run_status(latest, now)
        else:
            status = "UPCOMING" if now < scheduled_at else "MISSING"
        slots.append({"slot": slot, "status": status, "run_id": latest.pk if latest else None})

    return {
        "slots": slots,
        "runs": [
            {
                "id": run.pk,
                "trigger_source": run.trigger_source,
                "scheduled_slot": run.scheduled_slot,
                "started_at": run.started_at.astimezone(VIETNAM_TIME_ZONE).isoformat(),
                "ended_at": run.ended_at.astimezone(VIETNAM_TIME_ZONE).isoformat() if run.ended_at else None,
                "status": run_status(run, now),
                "total_eligible": run.total_eligible,
                "sent_count": run.sent_count,
                "failed_count": run.failed_count,
                "skipped_count": run.skipped_count,
                "retry_count": run.retry_count,
                "error_reason": run.error_reason or (
                    "MISSING_COMPLETION" if run_status(run, now) != run.status else None
                ),
                "github_run_id": run.github_run_id,
            }
            for run in runs
        ],
    }
