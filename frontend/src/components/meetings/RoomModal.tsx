import React, { useState, useEffect } from 'react';
import { MeetingRoom, CreateMeetingRoomDTO } from '@app-types/meeting';
import { apiClient, ApiError } from '@lib/apiClient';
import { Button } from '@components/common/Button';
import { useTranslation } from '@i18n/translate';

interface RoomFormProps {
  onClose: () => void;
  onSuccess: () => void;
  roomToEdit: MeetingRoom | null;
}

const RoomForm: React.FC<RoomFormProps> = ({
  onClose,
  onSuccess,
  roomToEdit,
}) => {
  const { t } = useTranslation();
  const [tenPhong, setTenPhong] = useState(roomToEdit?.name || '');
  const [viTri, setViTri] = useState(roomToEdit?.location || '');
  const [sucChua, setSucChua] = useState<number>(roomToEdit?.capacity ?? 10);
  const [thietBi, setThietBi] = useState(roomToEdit?.amenities || '');
  const [isPublic, setIsPublic] = useState(roomToEdit?.is_public ?? true);
  const [trangThai, setTrangThai] = useState<string>(roomToEdit?.trang_thai || 'AVAILABLE');
  const [ghiChu, setGhiChu] = useState(roomToEdit?.ghi_chu || '');

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!tenPhong.trim()) {
      newErrors.name = t('meetings.messages.roomNameRequired');
    }
    if (!sucChua || sucChua < 1) {
      newErrors.capacity = t('meetings.messages.capacityMustBePositive');
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setErrors({});

    const payload: CreateMeetingRoomDTO = {
      name: tenPhong.trim(),
      location: viTri.trim(),
      capacity: Number(sucChua),
      amenities: thietBi.trim(),
      is_public: isPublic,
      trang_thai: trangThai,
      ghi_chu: ghiChu.trim(),
    };

    try {
      if (roomToEdit) {
        await apiClient.put(`/api/meeting-rooms/${roomToEdit.id}/`, payload);
      } else {
        await apiClient.post('/api/meeting-rooms/', payload);
      }
      onSuccess();
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.data) {
        const fieldErrors: Record<string, string> = {};
        for (const [key, value] of Object.entries(err.data)) {
          if (Array.isArray(value)) {
            fieldErrors[key] = value.map((v) => typeof v === 'string' && v.startsWith('meetings.messages.') ? t(v) : v).join(' ');
          } else if (typeof value === 'string') {
            fieldErrors[key] = value.startsWith('meetings.messages.') ? t(value) : value;
          }
        }
        setErrors(fieldErrors);
      } else {
        setErrors({ general: t('meetings.messages.saveRoomError') });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Modal Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated">
        <div>
          <h3 className="text-lg font-bold text-main">
            {roomToEdit ? t('meetings.modalRoom.editTitle') : t('meetings.modalRoom.createTitle')}
          </h3>
          <p className="text-xs text-muted mt-0.5">
            {roomToEdit
              ? t('meetings.modalRoom.editSubtitle', { name: roomToEdit.name })
              : t('meetings.modalRoom.createSubtitle')}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-muted hover:text-main transition-colors p-1.5 rounded-lg hover:bg-surface-elevated"
          aria-label={t('meetings.modalRoom.cancelBtn')}
        >
          <i className="fa-solid fa-xmark text-lg" />
        </button>
      </div>

      {/* Modal Body */}
      <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
        {errors.general && (
          <div className="p-3 text-sm text-danger bg-danger-subtle rounded-xl border border-danger-border">
            {errors.general}
          </div>
        )}

        {/* Tên phòng */}
        <div>
          <label className="block text-xs font-semibold text-secondary uppercase tracking-wider mb-1">
            {t('meetings.modalRoom.nameLabel')} <span className="text-danger">*</span>
          </label>
          <input
            type="text"
            value={tenPhong}
            onChange={(e) => setTenPhong(e.target.value)}
            placeholder={t('meetings.modalRoom.namePlaceholder')}
            className={`w-full px-3.5 py-2 text-sm rounded-xl border transition-all focus:outline-none focus:ring-2 bg-surface text-main placeholder:text-muted ${
              errors.name
                ? 'border-danger focus:ring-danger'
                : 'border-border focus:ring-primary focus:border-primary'
            }`}
          />
          {errors.name && (
            <p className="mt-1 text-xs text-danger">{errors.name}</p>
          )}
        </div>

        {/* Vị trí & Sức chứa */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-secondary uppercase tracking-wider mb-1">
              {t('meetings.modalRoom.locationLabel')}
            </label>
            <input
              type="text"
              value={viTri}
              onChange={(e) => setViTri(e.target.value)}
              placeholder={t('meetings.modalRoom.locationPlaceholder')}
              className="w-full px-3.5 py-2 text-sm rounded-xl border border-border bg-surface text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
            />
            {errors.location && (
              <p className="mt-1 text-xs text-danger">{errors.location}</p>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-secondary uppercase tracking-wider mb-1">
              {t('meetings.modalRoom.capacityLabel')} <span className="text-danger">*</span>
            </label>
            <input
              type="number"
              min="1"
              value={sucChua}
              onChange={(e) => setSucChua(parseInt(e.target.value, 10) || 0)}
              placeholder="10"
              className={`w-full px-3.5 py-2 text-sm rounded-xl border transition-all focus:outline-none focus:ring-2 bg-surface text-main ${
                errors.capacity
                  ? 'border-danger focus:ring-danger'
                  : 'border-border focus:ring-primary focus:border-primary'
              }`}
            />
            {errors.capacity && (
              <p className="mt-1 text-xs text-danger">{errors.capacity}</p>
            )}
          </div>
        </div>

        {/* Trạng thái phòng (AVAILABLE / MAINTENANCE / UNAVAILABLE) */}
        <div>
          <label className="block text-xs font-semibold text-secondary uppercase tracking-wider mb-1">
            {t('meetings.modalRoom.statusLabel')}
          </label>
          <select
            value={trangThai}
            onChange={(e) => setTrangThai(e.target.value)}
            className="w-full px-3.5 py-2 text-sm rounded-xl border border-border bg-surface text-main focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary cursor-pointer font-medium"
          >
            <option value="AVAILABLE">{t('meetings.status.available')}</option>
            <option value="MAINTENANCE">{t('meetings.status.maintenance')}</option>
            <option value="UNAVAILABLE">{t('meetings.status.unavailable')}</option>
          </select>
        </div>

        {/* Thiết bị */}
        <div>
          <label className="block text-xs font-semibold text-secondary uppercase tracking-wider mb-1">
            {t('meetings.modalRoom.amenitiesLabel')}
          </label>
          <textarea
            rows={2}
            value={thietBi}
            onChange={(e) => setThietBi(e.target.value)}
            placeholder={t('meetings.modalRoom.amenitiesPlaceholder')}
            className="w-full px-3.5 py-2 text-sm rounded-xl border border-border bg-surface text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
          />
          {errors.amenities && (
            <p className="mt-1 text-xs text-danger">{errors.amenities}</p>
          )}
        </div>

        {/* Trạng thái công khai cho cán bộ đặt */}
        <div className="flex items-center justify-between p-3.5 rounded-xl border border-border bg-surface-elevated">
          <div>
            <span className="text-sm font-semibold text-main">
              {t('meetings.modalRoom.isPublicLabel')}
            </span>
            <p className="text-xs text-muted">
              {t('meetings.modalRoom.isPublicDesc')}
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-surface border border-border peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-border after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
          </label>
        </div>

        {/* Ghi chú */}
        <div>
          <label className="block text-xs font-semibold text-secondary uppercase tracking-wider mb-1">
            {t('meetings.modalRoom.notesLabel')}
          </label>
          <textarea
            rows={2}
            value={ghiChu}
            onChange={(e) => setGhiChu(e.target.value)}
            placeholder={t('meetings.modalRoom.notesPlaceholder')}
            className="w-full px-3.5 py-2 text-sm rounded-xl border border-border bg-surface text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
          />
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end space-x-3 pt-3 border-t border-border">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={loading}
          >
            {t('meetings.modalRoom.cancelBtn')}
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center space-x-1.5">
                <i className="fa-solid fa-spinner fa-spin mr-1" />
                <span>{t('meetings.modalRoom.savingBtn')}</span>
              </span>
            ) : roomToEdit ? (
              t('meetings.modalRoom.updateBtn')
            ) : (
              t('meetings.modalRoom.saveBtn')
            )}
          </Button>
        </div>
      </form>
    </>
  );
};

interface RoomModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  roomToEdit: MeetingRoom | null;
}

export const RoomModal: React.FC<RoomModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  roomToEdit,
}) => {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Sử dụng key dựa trên roomToEdit để React tự động khởi tạo lại hoàn toàn state cho từng phòng hoặc khi thêm mới
  const formKey = roomToEdit ? `edit-room-${roomToEdit.id}` : 'create-new-room';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fadeIn"
      role="dialog"
      aria-modal="true"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="relative w-full max-w-lg bg-surface rounded-2xl shadow-2xl border border-border overflow-hidden transform transition-all duration-200">
        <RoomForm
          key={formKey}
          onClose={onClose}
          onSuccess={onSuccess}
          roomToEdit={roomToEdit}
        />
      </div>
    </div>
  );
};

export default RoomModal;
