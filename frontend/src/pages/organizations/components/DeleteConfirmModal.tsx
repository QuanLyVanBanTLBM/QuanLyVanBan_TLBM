import React from 'react';
import { useTranslation } from '@i18n/translate';
import { Button } from '@components/common/Button';

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  titleKey: string;
  descKey: string;
  name?: string;
  isLoading?: boolean;
  errorKey?: string | null;
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  titleKey,
  descKey,
  name = '',
  isLoading = false,
  errorKey = null,
}) => {
  const { t } = useTranslation();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-md overflow-hidden animate-scale-up">
        <div className="p-6 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-danger-subtle text-danger flex items-center justify-center mx-auto text-xl">
            <i className="fa-solid fa-triangle-exclamation" />
          </div>

          <h3 className="font-bold text-lg text-main">{t(titleKey)}</h3>

          {errorKey ? (
            <div className="p-3 text-sm text-danger bg-danger-subtle border border-danger-border rounded-lg text-left">
              <i className="fa-solid fa-circle-exclamation mr-2" />
              {t(errorKey)}
            </div>
          ) : (
            <p className="text-sm text-secondary leading-relaxed">
              {t(descKey, { name })}
            </p>
          )}

          <div className="flex items-center justify-center gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
              {t('organizations.actions.cancel')}
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={onConfirm}
              isLoading={isLoading}
              icon="fa-trash-can"
            >
              {t('organizations.actions.delete')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
