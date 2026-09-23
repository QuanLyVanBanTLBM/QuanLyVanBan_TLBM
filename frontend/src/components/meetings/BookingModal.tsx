import React, { useState } from 'react';
import { MeetingRoom, MeetingBooking, BookingUser } from '@app-types/meeting';
import { apiClient, ApiError } from '@lib/apiClient';
import { Button } from '@components/common/Button';

interface BookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  rooms: MeetingRoom[];
  bookingToEdit?: MeetingBooking | null;
  initialDate?: string;
  currentUser?: BookingUser | null;
}

interface BookingFormProps {
  onClose: () => void;
  onSuccess: () => void;
  rooms: MeetingRoom[];
  bookingToEdit?: MeetingBooking | null;
  initialDate?: string;
  currentUser?: BookingUser | null;
}

const BookingForm: React.FC<BookingFormProps> = ({
  onClose,
  onSuccess,
  rooms,
  bookingToEdit,
  initialDate,
  currentUser,
}) => {
  const getInitialTimes = () => {
    if (bookingToEdit) {
      try {
        const start = new Date(bookingToEdit.thoi_gian_bat_dau);
        const end = new Date(bookingToEdit.thoi_gian_ket_thuc);
        return {
          date: start.toISOString().split('T')[0],
          start: start.toTimeString().slice(0, 5),
          end: end.toTimeString().slice(0, 5),
        };
      } catch {
        // fallback
      }
    }
    return {
      date: initialDate || new Date().toISOString().split('T')[0],
      start: '09:00',
      end: '10:00',
    };
  };

  const initialTimes = getInitialTimes();
  const [roomId, setRoomId] = useState<number | ''>(
    bookingToEdit ? bookingToEdit.phong_hop : rooms.length > 0 ? rooms[0].id : ''
  );
  const [title, setTitle] = useState(bookingToEdit?.tieu_de || '');
  const [department, setDepartment] = useState(
    bookingToEdit?.don_vi_to_chuc || currentUser?.department || ''
  );
  const [date, setDate] = useState(initialTimes.date);
  const [startTime, setStartTime] = useState(initialTimes.start);
  const [endTime, setEndTime] = useState(initialTimes.end);
  const [attendees, setAttendees] = useState(bookingToEdit?.so_nguoi_tham_gia || 5);
  const [note, setNote] = useState(bookingToEdit?.ghi_chu || '');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!roomId) {
      setErrorMsg('Vui lòng chọn phòng họp.');
      return;
    }
    if (!title.trim()) {
      setErrorMsg('Vui lòng nhập tiêu đề cuộc họp.');
      return;
    }
    if (!date) {
      setErrorMsg('Vui lòng chọn ngày họp.');
      return;
    }
    if (startTime >= endTime) {
      setErrorMsg('Thời gian kết thúc phải lớn hơn thời gian bắt đầu.');
      return;
    }
    if (attendees <= 0) {
      setErrorMsg('Số người tham gia phải lớn hơn 0.');
      return;
    }

    const selectedRoom = rooms.find((r) => r.id === Number(roomId));
    if (selectedRoom && attendees > selectedRoom.suc_chua) {
      setErrorMsg(`Số người tham gia (${attendees}) vượt quá sức chứa của phòng (${selectedRoom.suc_chua} người).`);
      return;
    }

    const startIso = `${date}T${startTime}:00`;
    const endIso = `${date}T${endTime}:00`;

    setLoading(true);
    try {
      if (bookingToEdit) {
        await apiClient.put(`/api/meeting-bookings/${bookingToEdit.id}/`, {
          phong_hop: Number(roomId),
          tieu_de: title.trim(),
          don_vi_to_chuc: department.trim(),
          thoi_gian_bat_dau: startIso,
          thoi_gian_ket_thuc: endIso,
          so_nguoi_tham_gia: Number(attendees),
          ghi_chu: note.trim(),
        });
      } else {
        await apiClient.post('/api/meeting-bookings/', {
          phong_hop: Number(roomId),
          tieu_de: title.trim(),
          don_vi_to_chuc: department.trim(),
          thoi_gian_bat_dau: startIso,
          thoi_gian_ket_thuc: endIso,
          so_nguoi_tham_gia: Number(attendees),
          ghi_chu: note.trim(),
        });
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        const errorData = err.data;
        if (errorData.non_field_errors && Array.isArray(errorData.non_field_errors)) {
          setErrorMsg(errorData.non_field_errors.join(' '));
        } else if (errorData.error) {
          setErrorMsg(String(errorData.error));
        } else if (errorData.detail) {
          setErrorMsg(String(errorData.detail));
        } else {
          setErrorMsg(err.message || 'Không thể lưu lịch đặt phòng họp. Vui lòng thử lại!');
        }
      } else {
        setErrorMsg('Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau.');
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
            <i className="fa-solid fa-calendar-plus text-lg" />
          </div>
          <div>
            <h2 id="booking-modal-title" className="text-lg font-bold text-main">
              {bookingToEdit ? 'Chỉnh sửa lịch đặt phòng' : 'Đặt phòng họp mới'}
            </h2>
            <p className="text-xs text-muted">
              Điền thông tin khung giờ và nội dung cuộc họp để khóa phòng
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

        {/* Chọn phòng */}
        <div>
          <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
            Phòng họp <span className="text-danger">*</span>
          </label>
          <select
            value={roomId}
            onChange={(e) => setRoomId(Number(e.target.value))}
            required
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium transition-all"
          >
            <option value="" disabled>-- Chọn phòng họp --</option>
            {rooms.map((r) => (
              <option key={r.id} value={r.id} disabled={!r.is_public}>
                {r.ten_phong} (Sức chứa: {r.suc_chua} người) {r.vi_tri ? `- ${r.vi_tri}` : ''} {!r.is_public ? '[Tạm ẩn]' : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Tiêu đề cuộc họp */}
        <div>
          <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
            Tiêu đề cuộc họp <span className="text-danger">*</span>
          </label>
          <input
            type="text"
            placeholder="VD: Họp giao ban phòng Kế hoạch tuần 40"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium transition-all"
          />
        </div>

        {/* Đơn vị tổ chức & Số người */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
              Đơn vị tổ chức
            </label>
            <input
              type="text"
              placeholder="VD: Phòng Hành chính"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
              Số người tham gia <span className="text-danger">*</span>
            </label>
            <input
              type="number"
              min="1"
              value={attendees}
              onChange={(e) => setAttendees(Number(e.target.value))}
              required
              className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary text-sm font-medium transition-all"
            />
          </div>
        </div>

        {/* Ngày họp & Khung giờ */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-surface-elevated/40 p-3.5 rounded-xl border border-border-subtle">
          <div>
            <label className="block text-xs font-bold text-secondary mb-1">
              Ngày họp <span className="text-danger">*</span>
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border-subtle text-main text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 font-medium"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-secondary mb-1">
              Giờ bắt đầu <span className="text-danger">*</span>
            </label>
            <input
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border-subtle text-main text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 font-medium"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-secondary mb-1">
              Giờ kết thúc <span className="text-danger">*</span>
            </label>
            <input
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg bg-surface border border-border-subtle text-main text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 font-medium"
            />
          </div>
        </div>

        {/* Ghi chú */}
        <div>
          <label className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5">
            Ghi chú thêm
          </label>
          <textarea
            rows={2}
            placeholder="Chuẩn bị máy chiếu, micro không dây, nước uống..."
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
            {bookingToEdit ? 'Lưu thay đổi' : 'Xác nhận đặt phòng'}
          </Button>
        </div>
      </form>
    </>
  );
};

export const BookingModal: React.FC<BookingModalProps> = ({ isOpen, ...props }) => {
  if (!isOpen) return null;

  const formKey = props.bookingToEdit ? `edit-${props.bookingToEdit.id}` : 'new';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="booking-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn"
    >
      <div className="bg-surface border border-border-subtle rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <BookingForm key={formKey} {...props} />
      </div>
    </div>
  );
};
