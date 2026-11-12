import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { Position, PositionFormData } from '@app-types/position';
import { Button } from '@components/common/Button';

interface PositionModalProps {
  onClose: () => void;
  onSubmit: (data: PositionFormData) => Promise<void>;
  initialData?: Position | null;
  isLoading?: boolean;
}

interface FieldErrors {
  stt?: string;
  name?: string;
  general?: string;
}

const inputClass =
  'w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all';

export const PositionModal: React.FC<PositionModalProps> = ({ onClose, onSubmit, initialData, isLoading = false }) => {
  const { t } = useTranslation();
  const [stt, setStt] = useState<string>(initialData ? String(initialData.display_order) : '');
  const [name, setName] = useState<string>(initialData?.name ?? '');
  const [isPublic, setIsPublic] = useState<boolean>(initialData?.is_public ?? true);
  const [note, setNote] = useState<string>(initialData?.note ?? '');
  const [errors, setErrors] = useState<FieldErrors>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = name.trim();
    const cleanStt = stt.trim();
    const next: FieldErrors = {};
    if (!cleanName) next.name = 'positions.messages.nameRequired';
    if (cleanStt && (!/^\d+$/.test(cleanStt) || Number(cleanStt) < 1)) next.stt = 'positions.messages.sttInvalid';
    else if (cleanStt && Number(cleanStt) > 2147483647) next.stt = 'positions.messages.sttTooLarge';
    if (next.name || next.stt) {
      setErrors(next);
      return;
    }

    try {
      await onSubmit({
        display_order: cleanStt ? Number(cleanStt) : undefined,
        name: cleanName,
        is_public: isPublic,
        note: note.trim(),
      });
      onClose();
    } catch (err: unknown) {
      const data =
        err && typeof err === 'object' && 'data' in err
          ? ((err as { data?: Record<string, unknown> }).data ?? {})
          : {};
      const first = (value: unknown): string | undefined =>
        Array.isArray(value) && typeof value[0] === 'string' ? value[0] : undefined;
      const detail = typeof data.detail === 'string' ? data.detail : undefined;
      const fieldName = first(data.name);
      const fieldStt = first(data.display_order);
      setErrors({
        name: fieldName,
        stt: fieldStt,
        general: fieldName || fieldStt ? undefined : detail || 'positions.messages.saveError',
      });
    }
  };

  const clearError = (key: keyof FieldErrors) => {
    if (errors[key] || errors.general) setErrors((prev) => ({ ...prev, [key]: undefined, general: undefined }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={initialData ? t('positions.editTitle') : t('positions.createTitle')}
        className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg overflow-hidden animate-scale-up"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated">
          <h3 className="font-bold text-lg text-main">
            {initialData ? t('positions.editTitle') : t('positions.createTitle')}
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('positions.actions.close')}
            className="text-secondary hover:text-main p-1 rounded-lg transition-colors cursor-pointer"
          >
            <i className="fa-solid fa-xmark text-lg" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4" noValidate>
          {errors.general && (
            <div role="alert" className="p-3 text-sm text-danger bg-danger-subtle border border-danger-border rounded-lg">
              <i className="fa-solid fa-circle-exclamation mr-2" />
              {t(errors.general)}
            </div>
          )}

          <div>
            <label htmlFor="position-stt" className="block text-sm font-semibold text-secondary mb-1.5">
              {t('positions.sttLabel')}
            </label>
            <input
              id="position-stt"
              type="text"
              inputMode="numeric"
              value={stt}
              onChange={(e) => {
                setStt(e.target.value);
                clearError('stt');
              }}
              placeholder={t('positions.sttPlaceholder')}
              className={inputClass}
            />
            {errors.stt ? (
              <p role="alert" className="mt-1 text-xs text-danger">
                {t(errors.stt)}
              </p>
            ) : (
              <p className="mt-1 text-xs text-muted">{t('positions.sttHelp')}</p>
            )}
          </div>

          <div>
            <label htmlFor="position-name" className="block text-sm font-semibold text-secondary mb-1.5">
              {t('positions.nameLabel')} <span className="text-danger">*</span>
            </label>
            <input
              id="position-name"
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                clearError('name');
              }}
              placeholder={t('positions.namePlaceholder')}
              className={inputClass}
              autoFocus
            />
            {errors.name && (
              <p role="alert" className="mt-1 text-xs text-danger">
                {t(errors.name)}
              </p>
            )}
          </div>

          <div>
            <label className="flex items-center gap-2.5 text-sm font-semibold text-secondary cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isPublic}
                onChange={(e) => setIsPublic(e.target.checked)}
                className="w-4 h-4 accent-primary cursor-pointer"
              />
              {t('positions.isPublicLabel')}
            </label>
            <p className="mt-1 text-xs text-muted">{t('positions.isPublicHelp')}</p>
          </div>

          <div>
            <label htmlFor="position-note" className="block text-sm font-semibold text-secondary mb-1.5">
              {t('positions.notesLabel')}
            </label>
            <textarea
              id="position-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={t('positions.notesPlaceholder')}
              rows={3}
              className={inputClass}
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
              {t('positions.actions.cancel')}
            </Button>
            <Button type="submit" variant="primary" isLoading={isLoading}>
              {initialData ? t('positions.actions.save') : t('positions.actions.create')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
