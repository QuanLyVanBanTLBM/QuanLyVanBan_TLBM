import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { Region, RegionFormData } from '@app-types/organization';
import { Button } from '@components/common/Button';

interface RegionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: RegionFormData) => Promise<void>;
  initialData?: Region | null;
  isLoading?: boolean;
}

export const RegionModal: React.FC<RegionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const [ten, setTen] = useState(initialData?.ten || '');
  const [displayOrder, setDisplayOrder] = useState(
    initialData?.thu_tu_hien_thi !== undefined ? String(initialData.thu_tu_hien_thi) : ''
  );
  const [errorKey, setErrorKey] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanTen = ten.trim();
    if (!cleanTen) {
      setErrorKey('organizations.messages.nameRequired');
      return;
    }
    const cleanOrder = displayOrder.trim();
    if (cleanOrder && !/^\d+$/.test(cleanOrder)) {
      setErrorKey('organizations.messages.displayOrderInvalid');
      return;
    }

    try {
      await onSubmit(cleanOrder ? { ten: cleanTen, thu_tu_hien_thi: Number(cleanOrder) } : { ten: cleanTen });
      onClose();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'data' in err) {
        const apiErr = (err as { data?: { ten?: string[]; thu_tu_hien_thi?: string[]; detail?: string; error?: string } }).data;
        if (apiErr?.ten?.[0]) {
          setErrorKey(apiErr.ten[0]);
        } else if (apiErr?.thu_tu_hien_thi?.[0]) {
          setErrorKey(apiErr.thu_tu_hien_thi[0]);
        } else if (apiErr?.detail) {
          setErrorKey(apiErr.detail);
        } else {
          setErrorKey('organizations.messages.fetchError');
        }
      } else {
        setErrorKey('organizations.messages.fetchError');
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-md overflow-hidden animate-scale-up">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated">
          <h3 className="font-bold text-lg text-main">
            {initialData ? t('organizations.region.editTitle') : t('organizations.region.createTitle')}
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
              {t('organizations.region.nameLabel')} <span className="text-danger">*</span>
            </label>
            <input
              type="text"
              value={ten}
              onChange={(e) => {
                setTen(e.target.value);
                if (errorKey) setErrorKey(null);
              }}
              placeholder={t('organizations.region.namePlaceholder')}
              className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-secondary mb-1.5">
              {t('organizations.region.displayOrderLabel')}
            </label>
            <input
              type="text"
              inputMode="numeric"
              value={displayOrder}
              onChange={(e) => {
                setDisplayOrder(e.target.value);
                if (errorKey) setErrorKey(null);
              }}
              placeholder={t('organizations.region.displayOrderPlaceholder')}
              className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
          </div>

          {/* Modal Footer */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
            <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
              {t('organizations.actions.cancel')}
            </Button>
            <Button type="submit" variant="primary" isLoading={isLoading}>
              {initialData ? t('organizations.actions.save') : t('organizations.actions.create')}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
