import React from 'react';
import { Button } from '@components/common';
import type { Dossier, DossierPayload, DocumentType, DocumentTypePayload } from '@app-types/records';
import { useTranslation } from '@i18n/translate';

const fieldClass =
  'w-full rounded-lg border border-border-subtle bg-surface-elevated px-3 py-2.5 text-sm text-main outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-subtle disabled:opacity-60';

interface BaseProps {
  open: boolean;
  isLoading?: boolean;
  error?: string | null;
  onClose: () => void;
}

interface DossierModalProps extends BaseProps {
  mode: 'dossier';
  value?: Dossier | null;
  onSubmit: (payload: DossierPayload) => void;
}

interface DocumentTypeModalProps extends BaseProps {
  mode: 'documentType';
  value?: DocumentType | null;
  dossierOptions?: Dossier[];
  dossierId?: string;
  isLoadingDossiers?: boolean;
  onDossierChange?: (id: string) => void;
  onSubmit: (payload: DocumentTypePayload) => void;
}

type RecordModalProps = DossierModalProps | DocumentTypeModalProps;

function dateInputValue(value?: string | null): string {
  return value ? value.slice(0, 10) : '';
}

export default function RecordModal(props: RecordModalProps) {
  if (!props.open) return null;

  const entityKey = props.value ? String(props.value.id) : 'new';
  return <RecordModalForm key={`${props.mode}-${entityKey}`} {...props} />;
}

function RecordModalForm(props: RecordModalProps) {
  const { t } = useTranslation();
  const { open, isLoading = false, error, onClose, mode, value } = props;
  const dossier = mode === 'dossier' ? (value as Dossier | null | undefined) : null;
  const documentType = mode === 'documentType' ? (value as DocumentType | null | undefined) : null;
  const [priority, setPriority] = React.useState(dossier?.stt_uu_tien == null ? '' : String(dossier.stt_uu_tien));
  const [code, setCode] = React.useState(dossier?.so_ky_hieu ?? '');
  const [name, setName] = React.useState(dossier?.ten_ho_so ?? documentType?.ten_loai ?? '');
  const [date, setDate] = React.useState(dateInputValue(dossier?.ngay_lap ?? documentType?.ngay_lap));
  const [note, setNote] = React.useState(dossier?.ghi_chu ?? documentType?.ghi_chu ?? '');
  const [validation, setValidation] = React.useState<string | null>(null);
  const dialogRef = React.useRef<HTMLFormElement>(null);
  const initialFocusRef = React.useRef<HTMLInputElement>(null);
  const [previousFocus] = React.useState(() => document.activeElement);
  const typeProps = props.mode === 'documentType' ? props : null;

  React.useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isLoading) onClose();
      if (event.key !== 'Tab') return;
      const controls = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)'
      ) ?? []).filter((element) => !element.matches(':disabled'));
      const first = controls[0];
      const last = controls[controls.length - 1];
      if (!first) {
        event.preventDefault();
        dialogRef.current?.focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, isLoading, onClose]);

  React.useEffect(() => {
    // StrictMode replays setup after cleanup restores the opener's focus.
    initialFocusRef.current?.focus();
    return () => {
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus();
    };
  }, [previousFocus]);

  const isEditing = Boolean(value);
  const title = t(
    `records.modal.titles.${isEditing ? 'edit' : 'add'}${mode === 'dossier' ? 'Dossier' : 'DocumentType'}`
  );

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (isLoading || typeProps?.isLoadingDossiers) return;
    if (typeProps?.dossierOptions && !typeProps.dossierId) {
      setValidation(t('records.modal.validation.dossierRequired'));
      return;
    }
    if (mode === 'dossier' && !code.trim()) {
      setValidation(t('records.modal.validation.referenceRequired'));
      return;
    }
    if (mode === 'dossier' && priority && (!Number.isInteger(Number(priority)) || Number(priority) < 1)) {
      setValidation(t('records.modal.validation.priorityPositive'));
      return;
    }
    if (!name.trim()) {
      setValidation(
        t(
          mode === 'dossier'
            ? 'records.modal.validation.dossierNameRequired'
            : 'records.modal.validation.documentTypeNameRequired'
        )
      );
      return;
    }

    setValidation(null);
    if (mode === 'dossier') {
      (props as DossierModalProps).onSubmit({
        stt_uu_tien: priority === '' ? null : Number(priority),
        so_ky_hieu: code.trim(),
        ten_ho_so: name.trim(),
        ngay_lap: date || null,
        ghi_chu: note.trim(),
      });
    } else {
      (props as DocumentTypeModalProps).onSubmit({
        ten_loai: name.trim(),
        ngay_lap: date || null,
        ghi_chu: note.trim(),
      });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-backdrop p-4" role="presentation">
      <form
        ref={dialogRef}
        tabIndex={-1}
        className="max-h-[90vh] w-full max-w-xl animate-slide-in-bottom overflow-y-auto rounded-xl border border-border-subtle bg-surface shadow-lg"
        onSubmit={handleSubmit}
        role="dialog"
        aria-modal="true"
        aria-labelledby="record-modal-title"
      >
        <div className="flex items-center justify-between border-b border-border-subtle px-5 py-4">
          <div>
            <h2 id="record-modal-title" className="m-0 text-lg font-bold text-main">{title}</h2>
            <p className="m-0 mt-1 text-xs text-muted">{t('records.modal.requiredFields')}</p>
          </div>
          <button
            type="button"
            className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg text-muted transition hover:bg-surface-hover hover:text-main"
            onClick={onClose}
            disabled={isLoading}
            aria-label={t('records.actions.close')}
          >
            <i className="fa-solid fa-xmark" />
          </button>
        </div>

        <fieldset disabled={isLoading} className="m-0 min-w-0 space-y-4 border-0 p-5">
          {typeProps?.dossierOptions && (
            <label className="block text-sm font-semibold text-secondary">
              {t('records.common.dossier')} *
              <select
                className={`${fieldClass} mt-1.5`}
                value={typeProps.dossierId ?? ''}
                disabled={typeProps.isLoadingDossiers}
                onChange={(event) => { setValidation(null); typeProps.onDossierChange?.(event.target.value); }}
              >
                <option value="">{t(typeProps.isLoadingDossiers ? 'records.documentTypes.loadingDossiers' : 'records.documentTypes.chooseDossier')}</option>
                {typeProps.dossierOptions.map((parent) => (
                  <option key={parent.id} value={String(parent.id)}>{parent.so_ky_hieu} — {parent.ten_ho_so}</option>
                ))}
              </select>
              {!typeProps.isLoadingDossiers && typeProps.dossierOptions.length === 0 && (
                <span className="mt-1 block text-xs text-muted">{t('records.documentTypes.noDossiers')}</span>
              )}
            </label>
          )}
          {mode === 'dossier' && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <label className="block text-sm font-semibold text-secondary">
                {t('records.modal.fields.reference')} *
                <input ref={initialFocusRef} className={`${fieldClass} mt-1.5`} value={code} onChange={(e) => setCode(e.target.value)} maxLength={255} />
              </label>
              <label className="block text-sm font-semibold text-secondary">
                {t('records.modal.fields.priority')}
                <input className={`${fieldClass} mt-1.5`} type="number" min="1" value={priority} onChange={(e) => setPriority(e.target.value)} />
              </label>
            </div>
          )}

          <label className="block text-sm font-semibold text-secondary">
            {t(
              mode === 'dossier'
                ? 'records.modal.fields.dossierName'
                : 'records.modal.fields.documentTypeName'
            )} *
            <input
              className={`${fieldClass} mt-1.5`}
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={255}
              ref={mode !== 'dossier' ? initialFocusRef : undefined}
            />
          </label>

          <label className="block text-sm font-semibold text-secondary">
            {t('records.modal.fields.createdDate')}
            <input className={`${fieldClass} mt-1.5`} type="date" value={date}
              onInput={(event) => setDate(event.currentTarget.value)} onChange={(event) => setDate(event.target.value)} />
          </label>

          <label className="block text-sm font-semibold text-secondary">
            {t('records.modal.fields.note')}
            <textarea className={`${fieldClass} mt-1.5 min-h-24 resize-y`} value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
          </label>

          {(validation || error) && (
            <div className="rounded-lg border border-danger-border bg-danger-subtle px-3 py-2 text-sm text-danger" role="alert">
              {validation || error}
            </div>
          )}
        </fieldset>

        <div className="flex justify-end gap-2 border-t border-border-subtle px-5 py-4">
          <Button type="button" variant="secondary" disabled={isLoading} onClick={onClose}>
            {t('records.actions.cancel')}
          </Button>
          <Button type="submit" isLoading={isLoading} disabled={typeProps?.isLoadingDossiers} icon="fa-floppy-disk">
            {t(isEditing ? 'records.actions.saveChanges' : 'records.actions.addNew')}
          </Button>
        </div>
      </form>
    </div>
  );
}
