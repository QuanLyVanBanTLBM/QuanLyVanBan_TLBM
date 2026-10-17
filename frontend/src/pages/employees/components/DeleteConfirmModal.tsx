import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { Button } from '@components/common/Button';

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (confirmLastClerk?: boolean) => Promise<void> | void;
  name?: string;
  unitName?: string;
  isLastClerk?: boolean;
  isLoading?: boolean;
  errorMessage?: string | null;
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  name = '',
  unitName = '',
  isLastClerk = false,
  isLoading = false,
  errorMessage = null,
}) => {
  const { t } = useTranslation();
  const [confirmRisk, setConfirmRisk] = useState<boolean>(false);

  const handleClose = () => {
    setConfirmRisk(false);
    onClose();
  };

  if (!isOpen) return null;

  const isDeleteDisabled = isLoading || (isLastClerk && !confirmRisk);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fade-in">
      <div className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden animate-scale-up">
        <div className="p-6 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-danger-subtle text-danger flex items-center justify-center mx-auto text-xl">
            <i className="fa-solid fa-triangle-exclamation" />
          </div>

          <h3 className="font-bold text-lg text-main">
            {t('employees.delete.confirmTitle')}
          </h3>

          {errorMessage ? (
            <div className="p-3 text-sm text-danger bg-danger-subtle border border-danger-border rounded-lg text-left">
              <i className="fa-solid fa-circle-exclamation mr-2" />
              {errorMessage}
            </div>
          ) : (
            <p className="text-sm text-secondary leading-relaxed">
              {t('employees.delete.confirmDesc', { name })}
            </p>
          )}

          {/* Cảnh báo cấp cao: Văn thư duy nhất của đơn vị */}
          {isLastClerk && (
            <div className="p-3.5 bg-warning-subtle border border-warning-border rounded-xl text-left space-y-2.5">
              <div className="flex items-center gap-2 text-warning font-semibold text-sm">
                <i className="fa-solid fa-triangle-exclamation" />
                <span>{t('employees.delete.lastUnitClerkWarningTitle')}</span>
              </div>
              <p className="text-xs text-secondary leading-relaxed">
                {t('employees.delete.lastUnitClerkWarningDesc', { unitName: unitName || t('employees.fields.unit') })}
              </p>
              <label className="flex items-start gap-2 pt-1 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={confirmRisk}
                  onChange={(e) => setConfirmRisk(e.target.checked)}
                  className="mt-0.5 rounded border-border text-primary focus:ring-primary cursor-pointer"
                />
                <span className="text-xs font-semibold text-warning leading-snug">
                  {t('employees.delete.confirmLastClerkCheckbox')}
                </span>
              </label>
            </div>
          )}

          <div className="flex items-center justify-center gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={handleClose} disabled={isLoading}>
              {t('employees.actions.cancel')}
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={() => onConfirm(confirmRisk)}
              isLoading={isLoading}
              disabled={isDeleteDisabled}
              icon="fa-trash-can"
            >
              {t('employees.actions.delete')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
