import { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { apiClient } from '@lib/apiClient';
import { Button } from '@components/common/Button';
import { birthdayEmailError, type DeliveryResult } from './emailDelivery';

interface Draft {
  layout: string;
  subject: string;
  message: string;
}

interface EmailTemplate extends Draft {
  id: string;
  name: string | null;
}

interface Recipient {
  id: number;
  name: string;
  position: string;
  email: string | null;
  role_group?: string;
  recommended_layouts?: string[];
}

interface Preview {
  recipient: string;
  birthday_date: string;
  subject: string;
  html: string;
  card_url: string;
  preview_token: string;
}

const fieldStyle = 'w-full rounded-xs border border-border bg-surface px-3 py-2 text-main';
const fieldLabelStyle = 'flex flex-col gap-1 text-sm font-medium';

interface Props {
  initialYear: string;
  onClose: () => void;
  onDelivered: (log: DeliveryResult) => void;
}

export default function BirthdayEmailComposer({ initialYear, onClose, onDelivered }: Props) {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const busyRef = useRef(false);
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [templateId, setTemplateId] = useState('');
  const [draft, setDraft] = useState<Draft>({ layout: '', subject: '', message: '' });
  const [query, setQuery] = useState('');
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [employeeId, setEmployeeId] = useState('');
  const [year, setYear] = useState(initialYear);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [instruction, setInstruction] = useState('');
  const [showAgent, setShowAgent] = useState(false);
  const [aiDraft, setAiDraft] = useState<Draft | null>(null);
  const [name, setName] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => { dialog?.close(); };
  }, []);

  useEffect(() => {
    let active = true;
    apiClient.get<{ templates: EmailTemplate[] }>('/api/birthdays/templates/')
      .then((response) => {
        if (!active) return;
        setTemplates(response.templates);
        const first = response.templates[0];
        if (first) {
          setTemplateId(first.id);
          setDraft(first);
        }
      })
      .catch((reason: unknown) => { if (active) setError(birthdayEmailError(reason)); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      const search = new URLSearchParams({ q: query });
      apiClient.get<{ recipients: Recipient[] }>(`/api/birthdays/recipients/?${search}`)
        .then((response) => { if (active) setRecipients(response.recipients); })
        .catch((reason: unknown) => { if (active) setError(birthdayEmailError(reason)); });
    }, query ? 250 : 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [query]);

  const selectedRecipient = recipients.find((item) => String(item.id) === employeeId);

  const handleRecipientChange = (selectedId: string) => {
    setEmployeeId(selectedId);
    setPreview(null);
    if (!selectedId) return;
    const recipient = recipients.find((item) => String(item.id) === selectedId);
    if (recipient?.recommended_layouts && recipient.recommended_layouts.length > 0) {
      if (!recipient.recommended_layouts.includes(draft.layout)) {
        const topLayout = recipient.recommended_layouts[0];
        const match = templates.find((t) => t.layout === topLayout && !t.name) || templates.find((t) => t.layout === topLayout);
        if (match) {
          chooseTemplate(match);
        }
      }
    }
  };

  const payload = {
    layout: draft.layout,
    subject: draft.subject,
    message: draft.message,
    template_id: templateId,
    employee_id: Number(employeeId),
    year: Number(year),
  };
  const ready = Boolean(employeeId && year && draft.subject.trim() && draft.message.trim());

  const request = async (action: () => Promise<void>) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
    } catch (reason) {
      setError(birthdayEmailError(reason));
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const chooseTemplate = (template: EmailTemplate) => {
    setTemplateId(template.id);
    setDraft(template);
    setPreview(null);
  };

  const applyAiDraft = () => {
    if (!aiDraft) return;
    setTemplateId(`layout:${aiDraft.layout}`);
    setDraft(aiDraft);
    setAiDraft(null);
    setPreview(null);
  };

  const saveTemplate = () => request(async () => {
    const { template } = await apiClient.post<{ template: EmailTemplate }>(
      '/api/birthdays/templates/', { layout: draft.layout, subject: draft.subject, message: draft.message, name },
    );
    setTemplates((items) => [...items, template]);
    chooseTemplate(template);
    setName('');
    setNotice('birthdayPage.manualEmail.saved');
  });

  const previewEmail = () => request(async () => {
    setPreview(null);
    setPreview(await apiClient.post<Preview>('/api/birthdays/manual/preview/', payload));
  });

  const send = () => request(async () => {
    if (!preview) return;
    const { log } = await apiClient.post<{ log: DeliveryResult }>('/api/birthdays/manual/send/', {
      ...payload, preview_token: preview.preview_token,
    });
    onDelivered(log);
  });

  const makeDraft = () => request(async () => {
    setAiDraft(null);
    const response = await apiClient.post<{ draft: Draft }>('/api/birthdays/templates/draft/', { instruction });
    setAiDraft(response.draft);
  });

  const layoutName = (layout: string) => t(`birthdayPage.manualEmail.layouts.${layout}`);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="birthday-email-composer-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      className="m-auto max-h-[90dvh] w-full max-w-4xl overflow-y-auto rounded-xl border border-border bg-surface p-5 text-main shadow-xl backdrop:bg-backdrop sm:p-6"
    >
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 id="birthday-email-composer-title" className="text-lg font-bold">
            {t('birthdayPage.manualEmail.title')}
          </h2>
          <p className="mt-1 text-sm text-secondary">{t('birthdayPage.manualEmail.description')}</p>
        </div>
        <Button variant="secondary" size="sm" onClick={onClose} disabled={busy}>
          {t('birthdayPage.manualEmail.close')}
        </Button>
      </header>

      <fieldset disabled={busy} className="grid gap-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className={fieldLabelStyle}>
            {t('birthdayPage.manualEmail.search')}
            <input
              className={fieldStyle} value={query} maxLength={100}
              onChange={(event) => {
                setQuery(event.target.value);
                setRecipients([]);
                setEmployeeId('');
                setPreview(null);
              }}
            />
          </label>
          <label className={fieldLabelStyle}>
            {t('birthdayPage.manualEmail.recipient')}
            <select
              className={fieldStyle} value={employeeId}
              onChange={(event) => handleRecipientChange(event.target.value)}
            >
              <option value="">{t('birthdayPage.manualEmail.selectRecipient')}</option>
              {recipients.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {item.position} · {item.email || t('birthdayPage.manualEmail.noEmail')}
                </option>
              ))}
            </select>
          </label>
          <label className={fieldLabelStyle}>
            {t('birthdayPage.manualEmail.year')}
            <input
              type="number" min={Number(initialYear) - 1} max={Number(initialYear) + 1}
              className={fieldStyle} value={year}
              onChange={(event) => { setYear(event.target.value); setPreview(null); }}
            />
          </label>
          <label className={fieldLabelStyle}>
            {t('birthdayPage.manualEmail.template')}
            <select
              className={fieldStyle} value={templateId}
              onChange={(event) => {
                const template = templates.find((item) => item.id === event.target.value);
                if (template) chooseTemplate(template);
              }}
            >
              {templates.map((item) => {
                const isRecommended = selectedRecipient?.recommended_layouts?.includes(item.layout);
                const title = item.name
                  ? t('birthdayPage.manualEmail.savedOption', { name: item.name, layout: layoutName(item.layout) })
                  : layoutName(item.layout);
                return (
                  <option value={item.id} key={item.id}>
                    {isRecommended ? `★ ${title} (${t('birthdayPage.manualEmail.recommended')})` : title}
                  </option>
                );
              })}
            </select>
          </label>

          {selectedRecipient?.role_group && selectedRecipient?.recommended_layouts && (
            <div className="flex items-center gap-2 rounded-xs border border-primary/20 bg-primary/5 px-3 py-2 text-xs text-primary sm:col-span-2">
              <span className="font-semibold">💡 {t('birthdayPage.manualEmail.hybridRecommendation')}:</span>
              <span>
                {t(`birthdayPage.manualEmail.roleGroups.${selectedRecipient.role_group}`, { defaultValue: selectedRecipient.role_group })} ·{' '}
                {t('birthdayPage.manualEmail.recommendedHint', { layouts: selectedRecipient.recommended_layouts.join(', ') })}
              </span>
            </div>
          )}
        </div>
        <label className={fieldLabelStyle}>
          {t('birthdayPage.manualEmail.subject')}
          <input
            className={fieldStyle} maxLength={255} value={draft.subject}
            onChange={(event) => { setDraft({ ...draft, subject: event.target.value }); setPreview(null); }}
          />
        </label>
        <label className={fieldLabelStyle}>
          {t('birthdayPage.manualEmail.message')}
          <textarea
            className={fieldStyle} rows={7} maxLength={6000} value={draft.message}
            onChange={(event) => { setDraft({ ...draft, message: event.target.value }); setPreview(null); }}
          />
        </label>
        <p className="text-xs text-secondary">{t('birthdayPage.manualEmail.variables')}</p>

        <div className="flex flex-wrap items-end gap-2">
          <Button variant="secondary" size="sm" aria-expanded={showAgent} disabled={!templates.length}
            onClick={() => setShowAgent(!showAgent)}>
            {t('birthdayPage.manualEmail.agent')}
          </Button>
          <label className={`${fieldLabelStyle} grow`}>
            {t('birthdayPage.manualEmail.templateName')}
            <input className={fieldStyle} maxLength={120} value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <Button
            variant="secondary" size="sm" onClick={saveTemplate}
            disabled={!name.trim() || !draft.layout || !draft.subject.trim() || !draft.message.trim()}
          >
            {t('birthdayPage.manualEmail.save')}
          </Button>
        </div>

        {showAgent && (
          <section className="grid gap-3 rounded-xs border border-border bg-surface-subtle p-3">
            <label className={fieldLabelStyle}>
              {t('birthdayPage.manualEmail.instruction')}
              <textarea className={fieldStyle} rows={3} maxLength={1500} value={instruction}
                onChange={(event) => { setInstruction(event.target.value); setAiDraft(null); }} />
            </label>
            <p className="text-xs text-secondary">{t('birthdayPage.manualEmail.instructionHint')}</p>
            <div>
              <Button variant="secondary" size="sm" onClick={makeDraft} disabled={!instruction.trim()}>
                {t('birthdayPage.manualEmail.generate')}
              </Button>
            </div>
            {aiDraft && (
              <div className="grid gap-2 text-sm">
                <p className="font-semibold">{layoutName(aiDraft.layout)} · {aiDraft.subject}</p>
                <p className="whitespace-pre-wrap">{aiDraft.message}</p>
                <div><Button variant="secondary" size="sm" onClick={applyAiDraft}>
                  {t('birthdayPage.manualEmail.apply')}
                </Button></div>
              </div>
            )}
          </section>
        )}

        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="secondary" onClick={previewEmail} disabled={!ready}>
            {t('birthdayPage.manualEmail.preview')}
          </Button>
        </div>
      </fieldset>

      {busy && <p className="mt-3 text-sm text-secondary" role="status">{t('birthdayPage.manualEmail.busy')}</p>}
      {notice && <p className="mt-3 text-sm text-success" role="status">{t(notice)}</p>}
      {error && <p className="mt-3 text-sm text-danger" role="alert">{t(error)}</p>}
      {preview && (
        <section className="mt-4 grid gap-2 text-sm">
          <p className="font-semibold">{preview.subject}</p>
          <p>{t('birthdayPage.manualEmail.previewRecipient', {
            email: preview.recipient,
            date: preview.birthday_date.split('-').reverse().join('/'),
          })}</p>
          {preview.card_url && (
            <a href={preview.card_url} target="_blank" rel="noreferrer" className="text-primary underline">
              {t('birthdayPage.manualEmail.openCard')}
            </a>
          )}
          <iframe
            title={t('birthdayPage.manualEmail.preview')} srcDoc={preview.html} sandbox=""
            className="min-h-96 w-full rounded-xs border border-border bg-surface"
          />
          <div className="flex justify-end">
            <Button variant="primary" onClick={send} disabled={busy}>
              {t('birthdayPage.manualEmail.send')}
            </Button>
          </div>
        </section>
      )}
    </dialog>
  );
}
