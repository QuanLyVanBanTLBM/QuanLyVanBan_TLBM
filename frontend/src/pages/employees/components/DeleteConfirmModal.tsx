import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { Button } from '@components/common/Button';

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (password: string) => Promise<void> | void;
  name?: string;
  isLoading?: boolean;
  errorMessage?: string | null;
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  name = '',
  isLoading = false,
  errorMessage = null,
}) => {
  const { t } = useTranslation();
  const [password, setPassword] = useState<string>('');
  const [confirmDelete, setConfirmDelete] = useState<boolean>(false);

  const handleClose = () => {
    setPassword('');
    setConfirmDelete(false);
    onClose();
  };

  if (!isOpen) return null;

  const isDeleteDisabled = isLoading || !password.trim() || !confirmDelete;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isDeleteDisabled) {
      onConfirm(password.trim());
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fade-in">
      <div className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden animate-scale-up">
        <form onSubmit={handleSubmit} className="p-6 text-center space-y-4">
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

          {/* Bắt buộc nhập mật khẩu của tài khoản đang thao tác */}
          <div className="text-left space-y-1.5 pt-1">
            <label className="block text-xs font-semibold text-main">
              {t('employees.delete.passwordLabel')} <span className="text-danger">*</span>
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t('employees.delete.passwordPlaceholder')}
              className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-danger focus:ring-1 focus:ring-danger transition-all"
              disabled={isLoading}
              autoFocus
              required
            />
          </div>

          {/* Bắt buộc tích xác nhận xóa cán bộ */}
          <label className="flex items-start gap-2.5 text-left cursor-pointer select-none p-2.5 bg-surface-elevated border border-border rounded-lg hover:border-danger-border transition-colors">
            <input
              type="checkbox"
              checked={confirmDelete}
              onChange={(e) => setConfirmDelete(e.target.checked)}
              className="mt-0.5 rounded border-border text-danger focus:ring-danger cursor-pointer"
              disabled={isLoading}
            />
            <span className="text-xs font-medium text-main leading-snug">
              {t('employees.delete.confirmCheckbox')}
            </span>
          </label>

          <div className="flex items-center justify-center gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={handleClose} disabled={isLoading}>
              {t('employees.actions.cancel')}
            </Button>
            <Button
              type="submit"
              variant="danger"
              isLoading={isLoading}
              disabled={isDeleteDisabled}
              icon="fa-trash-can"
            >
              {t('employees.actions.delete')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
