import React, { useState } from 'react';
import { MeetingRoom } from '@app-types/meeting';
import { apiClient, ApiError } from '@lib/apiClient';
import { Button } from '@components/common/Button';

interface RoomModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  roomToEdit?: MeetingRoom | null;
}

interface RoomFormProps {
  onClose: () => void;
  onSuccess: () => void;
  roomToEdit?: MeetingRoom | null;
}

const RoomForm: React.FC<RoomFormProps> = ({
  onClose,
  onSuccess,
  roomToEdit,
}) => {
  const [name, setName] = useState(roomToEdit?.ten_phong || '');
  const [location, setLocation] = useState(roomToEdit?.vi_tri || '');
  const [capacity, setCapacity] = useState(roomToEdit?.suc_chua || 10);
  const [equipment, setEquipment] = useState(
    roomToEdit?.thiet_bi || 'Máy chiếu, Micro không dây, Bảng trắng'
  );
  const [isPublic, setIsPublic] = useState(roomToEdit ? roomToEdit.is_public : true);
  const [note, setNote] = useState(roomToEdit?.ghi_chu || '');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!name.trim()) {
      setErrorMsg('Vui lòng nhập tên phòng họp.');
      return;
    }
    if (capacity <= 0) {
      setErrorMsg('Sức chứa phòng họp phải lớn hơn 0.');
      return;
    }

    setLoading(true);
    try {
      if (roomToEdit) {
        await apiClient.put(`/api/meeting-rooms/${roomToEdit.id}/`, {
          ten_phong: name.trim(),
          vi_tri: location.trim(),
          suc_chua: Number(capacity),
          thiet_bi: equipment.trim(),
          is_public: isPublic,
          ghi_chu: note.trim(),
        });
      } else {
        await apiClient.post('/api/meeting-rooms/', {
          ten_phong: name.trim(),
          vi_tri: location.trim(),
          suc_chua: Number(capacity),
          thiet_bi: equipment.trim(),
          is_public: isPublic,
          ghi_chu: note.trim(),
        });
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        const errorData = err.data;
        if (errorData.ten_phong && Array.isArray(errorData.ten_phong)) {
          setErrorMsg(errorData.ten_phong.join(' '));
        } else if (errorData.error) {
          setErrorMsg(String(errorData.error));
        } else if (errorData.detail) {
          setErrorMsg(String(errorData.detail));
        } else {
          setErrorMsg(err.message || 'Không thể lưu phòng họp.');
        }
      } else {
        setErrorMsg('Đã có lỗi xảy ra khi lưu phòng họp.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Header */}
      <div className="px-6 py-4 border-b border-border-subtle flex items-center justify-between bg-surface-elevated/40">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold">
            <i className="fa-solid fa-door-open text-lg" />
          </div>
          <div>
            <h2 id="room-modal-title" className="text-lg font-bold text-main">
              {roomToEdit ? 'Chỉnh sửa phòng họp' : 'Thêm phòng họp mới'}
            </h2>
            <p className="text-xs text-muted">
              Khai báo danh mục và các trang thiết bị của phòng họp
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface-elevated transition-colors"
        >
          <i className="fa-solid fa-xmark text-lg" />
        </button>
      </div>

      {/* Form Body */}
      <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1 space-y-4">
        {errorMsg && (
          <div className="p-3.5 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm flex items-start gap-2.5">
            <i className="fa-solid fa-triangle-exclamation mt-0.5 shrink-0" />
            <div className="flex-1">{errorMsg}</div>
          </div>
        )}

        {/* Tên phòng */}
        <div>
          <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
            Tên phòng họp <span className="text-danger">*</span>
          </label>
          <input
            type="text"
            placeholder="VD: Phòng Hội thảo A, Phòng Họp Ban Giám Hiệu"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium transition-all"
          />
        </div>

        {/* Vị trí & Sức chứa */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
              Vị trí
            </label>
            <input
              type="text"
              placeholder="VD: Tầng 2, Tòa A"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
              Sức chứa (người) <span className="text-danger">*</span>
            </label>
            <input
              type="number"
              min="1"
              value={capacity}
              onChange={(e) => setCapacity(Number(e.target.value))}
              required
              className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium transition-all"
            />
          </div>
        </div>

        {/* Trang thiết bị */}
        <div>
          <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
            Trang thiết bị có sẵn
          </label>
          <textarea
            rows={2}
            placeholder="Máy chiếu 4K, 2 Micro không dây, Hội nghị trực tuyến, Bảng trắng..."
            value={equipment}
            onChange={(e) => setEquipment(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium transition-all resize-none"
          />
        </div>

        {/* Trạng thái hiển thị */}
        <div className="p-3.5 rounded-xl bg-surface-elevated/40 border border-border-subtle flex items-center justify-between">
          <div>
            <p className="text-sm font-bold text-main">Sẵn sàng sử dụng (Công khai)</p>
            <p className="text-xs text-muted">
              Cho phép cán bộ nhân viên nhìn thấy và đặt phòng họp này
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-border-subtle peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
          </label>
        </div>

        {/* Ghi chú */}
        <div>
          <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
            Ghi chú
          </label>
          <textarea
            rows={2}
            placeholder="Ghi chú nội bộ dành cho ban quản trị..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium transition-all resize-none"
          />
        </div>

        {/* Footer Actions */}
        <div className="pt-3 border-t border-border-subtle flex items-center justify-end gap-3">
          <Button type="button" variant="secondary" onClick={onClose} disabled={loading}>
            Hủy bỏ
          </Button>
          <Button type="submit" variant="primary" isLoading={loading} icon="fa-check">
            {roomToEdit ? 'Lưu cập nhật' : 'Tạo phòng họp'}
          </Button>
        </div>
      </form>
    </>
  );
};

export const RoomModal: React.FC<RoomModalProps> = ({ isOpen, ...props }) => {
  if (!isOpen) return null;

  const formKey = props.roomToEdit ? `edit-${props.roomToEdit.id}` : 'new';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="room-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn"
    >
      <div className="bg-surface border border-border-subtle rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <RoomForm key={formKey} {...props} />
      </div>
    </div>
  );
};
