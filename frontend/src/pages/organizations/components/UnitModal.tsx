import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { Unit, Region, UnitFormData } from '@app-types/organization';
import { Button } from '@components/common/Button';
import { Select } from '@components/common/Select';

interface UnitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: UnitFormData) => Promise<void>;
  initialData?: Unit | null;
  regions: Region[];
  isLoading?: boolean;
}

export const UnitModal: React.FC<UnitModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  initialData,
  regions,
  isLoading = false,
}) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState<UnitFormData>(() => {
    if (initialData) {
      return {
        khoi: initialData.khoi,
        stt_uu_tien: initialData.stt_uu_tien,
        ten: initialData.ten || '',
        dia_chi: initialData.dia_chi || '',
        dien_thoai: initialData.dien_thoai || '',
        email: initialData.email || '',
        is_public: initialData.is_public ?? true,
        ghi_chu: initialData.ghi_chu || '',
      };
    }
    return {
      khoi: regions.length > 0 ? regions[0].id : '',
      stt_uu_tien: '',
      ten: '',
      dia_chi: '',
      dien_thoai: '',
      email: '',
      is_public: true,
      ghi_chu: '',
    };
  });
  const [errorKey, setErrorKey] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData((prev) => ({ ...prev, [name]: checked }));
    } else if (name === 'stt_uu_tien') {
      setFormData((prev) => ({
        ...prev,
        [name]: value === '' ? '' : parseInt(value, 10) || '',
      }));
    } else if (name === 'khoi') {
      setFormData((prev) => ({
        ...prev,
        [name]: value === '' ? '' : parseInt(value, 10),
      }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
    if (errorKey) setErrorKey(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.khoi) {
      setErrorKey('organizations.unit.regionPlaceholder');
      return;
    }
    if (!formData.ten.trim()) {
      setErrorKey('organizations.messages.nameRequired');
      return;
    }

    try {
      const sanitizedData: UnitFormData = {
        ...formData,
        stt_uu_tien: formData.stt_uu_tien === '' ? (undefined as unknown as '') : formData.stt_uu_tien,
      };
      await onSubmit(sanitizedData);
      onClose();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'data' in err) {
        const apiErr = (err as { data?: Record<string, string[] | string> }).data;
        const fieldKey = (['khoi', 'ten', 'stt_uu_tien', 'dia_chi', 'dien_thoai', 'email'] as const).find((f) => apiErr?.[f]);
        if (fieldKey && apiErr) {
          const value = apiErr[fieldKey];
          setErrorKey(Array.isArray(value) ? value[0] : value);
        } else if (apiErr?.detail) {
          setErrorKey(apiErr.detail as string);
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
      <div className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg overflow-hidden animate-scale-up max-h-[90vh] flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated shrink-0">
          <h3 className="font-bold text-lg text-main">
            {initialData ? t('organizations.unit.editTitle') : t('organizations.unit.createTitle')}
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
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4">
          {errorKey && (
            <div className="p-3 text-sm text-danger bg-danger-subtle border border-danger-border rounded-lg">
              <i className="fa-solid fa-circle-exclamation mr-2" />
              {t(errorKey)}
            </div>
          )}

          {/* Thuộc Khối / Khu vực */}
          <div>
            <Select
              label={t('organizations.unit.regionLabel')}
              required
              name="khoi"
              value={formData.khoi ? String(formData.khoi) : ''}
              onChange={(val) => {
                setFormData((prev) => ({
                  ...prev,
                  khoi: val === '' ? '' : parseInt(val, 10),
                }));
                if (errorKey) setErrorKey(null);
              }}
              placeholder={t('organizations.unit.regionPlaceholder')}
              leftIcon="fa-layer-group"
              searchable={regions.length > 7}
              clearable
              options={regions.map((reg) => ({
                value: String(reg.id),
                label: reg.ten,
              }))}
            />
          </div>

          {/* Tên Đơn vị & STT ưu tiên */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2">
              <label className="block text-sm font-semibold text-secondary mb-1.5">
                {t('organizations.unit.nameLabel')} <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                name="ten"
                value={formData.ten}
                onChange={handleChange}
                placeholder={t('organizations.unit.namePlaceholder')}
                className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-secondary mb-1.5">
                {t('organizations.unit.priorityLabel')}
              </label>
              <input
                type="number"
                name="stt_uu_tien"
                value={formData.stt_uu_tien}
                onChange={handleChange}
                placeholder={t('organizations.unit.priorityPlaceholder')}
                min={1}
                className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
          </div>

          {/* Số điện thoại & Email */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-semibold text-secondary mb-1.5">
                {t('organizations.unit.phoneLabel')}
              </label>
              <input
                type="text"
                name="dien_thoai"
                value={formData.dien_thoai}
                onChange={handleChange}
                placeholder={t('organizations.unit.phonePlaceholder')}
                className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-secondary mb-1.5">
                {t('organizations.unit.emailLabel')}
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder={t('organizations.unit.emailPlaceholder')}
                className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
          </div>

          {/* Địa chỉ */}
          <div>
            <label className="block text-sm font-semibold text-secondary mb-1.5">
              {t('organizations.unit.addressLabel')}
            </label>
            <input
              type="text"
              name="dia_chi"
              value={formData.dia_chi}
              onChange={handleChange}
              placeholder={t('organizations.unit.addressPlaceholder')}
              className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
            />
          </div>

          {/* Ghi chú */}
          <div>
            <label className="block text-sm font-semibold text-secondary mb-1.5">
              {t('organizations.unit.notesLabel')}
            </label>
            <textarea
              name="ghi_chu"
              rows={2}
              value={formData.ghi_chu}
              onChange={handleChange}
              placeholder={t('organizations.unit.notesPlaceholder')}
              className="w-full px-3.5 py-2 text-sm bg-surface-elevated border border-border-subtle rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all resize-none"
            />
          </div>

          {/* Trạng thái công khai is_public */}
          <div className="flex items-start gap-3 p-3 bg-surface-elevated border border-border-subtle rounded-lg">
            <input
              type="checkbox"
              id="is_public_checkbox"
              name="is_public"
              checked={formData.is_public}
              onChange={handleChange}
              className="mt-1 h-4 w-4 rounded border-border-subtle text-primary focus:ring-primary cursor-pointer"
            />
            <label htmlFor="is_public_checkbox" className="text-sm cursor-pointer select-none">
              <span className="font-semibold text-main block">{t('organizations.unit.isPublicLabel')}</span>
              <span className="text-muted text-xs block">{t('organizations.unit.isPublicHelp')}</span>
            </label>
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
