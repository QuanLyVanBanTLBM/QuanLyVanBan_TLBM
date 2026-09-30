import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { Role } from '@app-types/authorization';
import { Button } from '@components/common/Button';

interface RoleModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string }) => Promise<void>;
  initialData?: Role | null;
  isLoading?: boolean;
}

export const RoleModal: React.FC<RoleModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const [name, setName] = useState(initialData?.name || '');
  const [errorKey, setErrorKey] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanName = name.trim();
    if (!cleanName) {
      setErrorKey('roles.messages.nameRequired');
      return;
    }

    try {
      await onSubmit({ name: cleanName });
      onClose();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'data' in err) {
        const apiErr = (err as { data?: { name?: string[] | string; detail?: string } }).data;
        if (apiErr?.name) {
          setErrorKey(Array.isArray(apiErr.name) ? apiErr.name[0] : apiErr.name);
        } else if (apiErr?.detail) {
          setErrorKey(apiErr.detail);
        } else {
          setErrorKey('roles.messages.fetchError');
        }
      } else {
        setErrorKey('roles.messages.fetchError');
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-md overflow-hidden animate-scale-up">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated">
          <h3 className="font-bold text-lg text-main">
            {initialData ? t('roles.editTitle') : t('roles.createTitle')}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-secondary hover:text-main p-1 rounded-lg transition-colors cursor-pointer"
          >
            <i className="fa-solid fa-xmark text-lg" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {errorKey && (
            <div className="p-3 text-sm text-danger bg-danger-subtle border border-danger-border rounded-lg">
              <i className="fa-solid fa-circle-exclamation mr-2" />
              {t(errorKey)}
            </div>
          )}

          <div>
            <label className="block text-sm font-semibold text-secondary mb-1.5">
              {t('roles.nameLabel')} <span className="text-danger">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (errorKey) setErrorKey(null);
              }}
              placeholder={t('roles.namePlaceholder')}
              className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              autoFocus
            />
          </div>

          {/* Modal Footer */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
              {t('roles.actions.cancel')}
            </Button>
            <Button type="submit" variant="primary" isLoading={isLoading}>
              {initialData ? t('roles.actions.save') : t('roles.actions.create')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
