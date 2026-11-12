import React from 'react';
import { useTranslation } from '@i18n/translate';
import { Button } from '@components/common/Button';

interface DeleteConfirmModalProps {
  onClose: () => void;
  onConfirm: () => Promise<void>;
  name: string;
  isLoading?: boolean;
  errorKey?: string | null;
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  onClose,
  onConfirm,
  name,
  isLoading = false,
  errorKey = null,
}) => {
  const { t } = useTranslation();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('positions.deleteConfirmTitle')}
        className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-md overflow-hidden animate-scale-up"
      >
        <div className="p-6 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-danger-subtle text-danger flex items-center justify-center mx-auto text-xl">
            <i className="fa-solid fa-triangle-exclamation" />
          </div>

          <h3 className="font-bold text-lg text-main">{t('positions.deleteConfirmTitle')}</h3>

          {errorKey ? (
            <div
              role="alert"
              className="p-3 text-sm text-danger bg-danger-subtle border border-danger-border rounded-lg text-left"
            >
              <i className="fa-solid fa-circle-exclamation mr-2" />
              {t(errorKey)}
            </div>
          ) : (
            <p className="text-sm text-secondary leading-relaxed">{t('positions.deleteConfirmDesc', { name })}</p>
          )}

          <div className="flex items-center justify-center gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
              {t('positions.actions.cancel')}
            </Button>
            <Button type="button" variant="danger" onClick={onConfirm} isLoading={isLoading} icon="fa-trash-can">
              {t('positions.actions.delete')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
