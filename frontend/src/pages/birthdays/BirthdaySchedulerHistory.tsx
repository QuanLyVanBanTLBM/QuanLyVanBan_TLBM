import { useTranslation } from '@i18n/translate';

type RunStatus = 'RUNNING' | 'SUCCESS' | 'FAILED' | 'UNKNOWN';
type Slot = '07:00' | '07:37';

interface SchedulerRun {
  id: number;
  trigger_source: 'SCHEDULED' | 'RECOVERY';
  scheduled_slot: Slot | null;
  started_at: string;
  ended_at: string | null;
  status: RunStatus;
  total_eligible: number | null;
  sent_count: number | null;
  failed_count: number | null;
  skipped_count: number | null;
  retry_count: number | null;
  error_reason: string | null;
  github_run_id: string | null;
}

export interface SchedulerHistory {
  slots: { slot: Slot; status: RunStatus | 'UPCOMING' | 'MISSING'; run_id: number | null }[];
  runs: SchedulerRun[];
}

const formatTimestamp = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Ho_Chi_Minh', dateStyle: 'short', timeStyle: 'medium',
});

export default function BirthdaySchedulerHistory({ history, today }: { history: SchedulerHistory; today: boolean }) {
  const { t } = useTranslation();
  return (
    <section aria-labelledby="birthday-scheduler-title" className="grid gap-3 rounded-lg border border-border bg-surface p-4">
      <h3 id="birthday-scheduler-title" className="text-sm font-semibold">
        {today ? t('birthdayPage.scheduler.todayTitle') : t('birthdayPage.scheduler.historyTitle')}
      </h3>
      <ul className="grid gap-2 sm:grid-cols-2">
        {history.slots.map(({ slot, status, run_id }) => {
          const run = history.runs.find((entry) => entry.id === run_id);
          return (
            <li key={slot} className="rounded-xs border border-border p-2 text-sm">
              <p className="font-semibold">{t('birthdayPage.scheduler.slot', { slot })}</p>
              <p>{t(`birthdayPage.scheduler.status.${status}`)}</p>
              {run && <p>{t('birthdayPage.scheduler.started', { time: formatTimestamp.format(new Date(run.started_at)) })}</p>}
            </li>
          );
        })}
      </ul>
      {history.runs.length > 0 && (
        <ul className="grid gap-2">
          {history.runs.map((run) => (
            <li key={run.id} className="rounded-xs border border-border p-2 text-sm">
              <p className="font-semibold">
                {t(`birthdayPage.scheduler.trigger.${run.trigger_source}`)}{run.scheduled_slot && ` · ${run.scheduled_slot}`}
                {' · '}{t('birthdayPage.scheduler.runId', { id: String(run.id) })}
                {' · '}{t(`birthdayPage.scheduler.status.${run.status}`)}
              </p>
              <p>{t('birthdayPage.scheduler.started', { time: formatTimestamp.format(new Date(run.started_at)) })}</p>
              {run.ended_at && <p>{t('birthdayPage.scheduler.ended', { time: formatTimestamp.format(new Date(run.ended_at)) })}</p>}
              {run.total_eligible !== null && (
                <p>{t('birthdayPage.scheduler.counts', {
                  eligible: String(run.total_eligible),
                  sent: String(run.sent_count),
                  failed: String(run.failed_count),
                  skipped: String(run.skipped_count),
                  retried: String(run.retry_count),
                })}</p>
              )}
              {run.error_reason && (
                <p>{t('birthdayPage.scheduler.error', {
                  reason: t(`birthdayPage.scheduler.errors.${run.error_reason}`, { defaultValue: run.error_reason }),
                })}</p>
              )}
              {run.github_run_id && <p>{t('birthdayPage.scheduler.githubId', { id: run.github_run_id })}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
