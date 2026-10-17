import React, { useState, useEffect, useMemo } from 'react';
import {
  MeetingRoom,
  MeetingBooking,
  BookingUser,
  CreateBookingDTO,
  UpdateBookingDTO,
} from '@app-types/meeting';
import { apiClient, ApiError } from '@lib/apiClient';
import { Button } from '@components/common/Button';
import { useTranslation } from '@i18n/translate';

export interface BookingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  rooms: MeetingRoom[];
  bookingToEdit?: MeetingBooking | null;
  initialDate?: string;
  currentUser?: BookingUser | null;
  initialRoomId?: number | null;
  existingBookings?: MeetingBooking[];
}

interface BookingFormProps {
  onClose: () => void;
  onSuccess: () => void;
  rooms: MeetingRoom[];
  bookingToEdit?: MeetingBooking | null;
  initialDate?: string;
  currentUser?: BookingUser | null;
  initialRoomId?: number | null;
  existingBookings?: MeetingBooking[];
}

const padZero = (n: number): string => n.toString().padStart(2, '0');

const toHHMM = (value: string): string => (value || '').slice(0, 5);

interface FormInitialValues {
  roomId: number | '';
  title: string;
  department: string;
  date: string;
  startTime: string;
  endTime: string;
  attendees: number;
  note: string;
}

const BookingForm: React.FC<BookingFormProps> = ({
  onClose,
  onSuccess,
  rooms,
  bookingToEdit,
  initialDate,
  currentUser,
  initialRoomId,
  existingBookings,
}) => {
  const { t } = useTranslation();
  // Tính toán giá trị mặc định ban đầu
  const initialValues = useMemo<FormInitialValues>(() => {
    if (bookingToEdit) {
      return {
        roomId: bookingToEdit.room,
        title: bookingToEdit.title || '',
        department: bookingToEdit.department_name || '',
        date: bookingToEdit.date || initialDate || (() => {
          const now = new Date();
          return `${now.getFullYear()}-${padZero(now.getMonth() + 1)}-${padZero(now.getDate())}`;
        })(),
        startTime: toHHMM(bookingToEdit.start_time) || '09:00',
        endTime: toHHMM(bookingToEdit.end_time) || '10:00',
        attendees: bookingToEdit.attendees_count || 5,
        note: bookingToEdit.purpose || '',
      };
    }

    const todayStr = initialDate || (() => {
      const now = new Date();
      return `${now.getFullYear()}-${padZero(now.getMonth() + 1)}-${padZero(now.getDate())}`;
    })();

    // Mặc định chọn phòng được truyền vào hoặc phòng đầu tiên có trạng thái sẵn sàng (AVAILABLE)
    const targetRoom = initialRoomId
      ? rooms.find((r) => r.id === Number(initialRoomId))
      : null;
    const defaultRoom = targetRoom || rooms.find((r) => (r.trang_thai || 'AVAILABLE') === 'AVAILABLE') || rooms[0];

    return {
      roomId: defaultRoom ? defaultRoom.id : '',
      title: '',
      department: currentUser?.don_vi_ten || '',
      date: todayStr,
      startTime: '09:00',
      endTime: '10:00',
      attendees: 5,
      note: '',
    };
  }, [bookingToEdit, rooms, initialDate, currentUser, initialRoomId]);

  const [roomId, setRoomId] = useState<number | ''>(initialValues.roomId);
  const [title, setTitle] = useState(initialValues.title);
  const department = initialValues.department;
  const [date, setDate] = useState(initialValues.date);
  const [startTime, setStartTime] = useState(initialValues.startTime);
  const [endTime, setEndTime] = useState(initialValues.endTime);
  const [attendees, setAttendees] = useState(initialValues.attendees);
  const [note, setNote] = useState(initialValues.note);

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const selectedRoom = useMemo(() => {
    return rooms.find((r) => r.id === Number(roomId));
  }, [rooms, roomId]);

  const [dateBookings, setDateBookings] = useState<MeetingBooking[]>(existingBookings || []);

  // Tải lịch của ngày được chọn trong form để phát hiện xung đột chính xác khi đổi ngày
  useEffect(() => {
    let isMounted = true;
    if (!date) return;

    apiClient
      .get<{ results?: MeetingBooking[] } | MeetingBooking[]>(
        `/api/meeting-bookings/?date=${date}&page_size=100`
      )
      .then((res) => {
        if (!isMounted) return;
        const list = Array.isArray(res) ? res : res?.results || [];
        setDateBookings(list);
      })
      .catch(() => {
        if (isMounted && existingBookings) {
          setDateBookings(existingBookings);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [date, existingBookings]);

  // Các khung giờ đã có lịch đặt ở phòng này trong ngày được chọn
  const bookedSlotsInRoom = useMemo(() => {
    if (!roomId) return [];
    return dateBookings.filter(
      (b) =>
        b.room === Number(roomId) &&
        b.date === date &&
        b.trang_thai !== 'CANCELLED' &&
        b.id !== bookingToEdit?.id
    );
  }, [roomId, date, dateBookings, bookingToEdit]);

  // Kiểm tra xung đột khung giờ theo thời gian thực (Real-time conflict detection)
  const conflictingSlot = useMemo(() => {
    if (!startTime || !endTime || startTime >= endTime) return null;
    return bookedSlotsInRoom.find(
      (b) => b.start_time.slice(0, 5) < endTime && b.end_time.slice(0, 5) > startTime
    );
  }, [startTime, endTime, bookedSlotsInRoom]);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!roomId) {
      errors.room = t('meetings.messages.roomRequired');
    }
    if (!title.trim()) {
      errors.title = t('meetings.messages.titleRequired');
    }
    if (!date) {
      errors.date = t('meetings.messages.dateRequired');
    }

    if (!startTime) {
      errors.start_time = t('meetings.messages.startTimeRequired');
    }
    if (!endTime) {
      errors.end_time = t('meetings.messages.endTimeRequired');
    } else if (startTime && startTime >= endTime) {
      errors.end_time = t('meetings.messages.invalidTimeRange');
    } else if (conflictingSlot) {
      errors.start_time = t('meetings.conflictWarning', {
        title: conflictingSlot.title,
        start: conflictingSlot.start_time.slice(0, 5),
        end: conflictingSlot.end_time.slice(0, 5),
      });
    }

    if (!attendees || attendees <= 0) {
      errors.attendees_count = t('meetings.messages.attendeesRequired');
    } else if (selectedRoom && attendees > selectedRoom.capacity) {
      errors.attendees_count = t('meetings.messages.capacityExceeded', {
        room: selectedRoom.name,
        max: selectedRoom.capacity,
      });
    }

    setFieldErrors(errors);

    if (Object.keys(errors).length > 0) {
      const firstError = Object.values(errors)[0];
      setErrorMsg(firstError);
      return false;
    }

    setErrorMsg(null);
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setErrorMsg(null);
    setFieldErrors({});

    setLoading(true);
    try {
      if (bookingToEdit) {
        const updatePayload: UpdateBookingDTO = {
          room: Number(roomId),
          title: title.trim(),
          date,
          start_time: startTime,
          end_time: endTime,
          attendees_count: Number(attendees),
          purpose: note.trim(),
        };
        await apiClient.put(`/api/meeting-bookings/${bookingToEdit.id}/`, updatePayload);
      } else {
        const createPayload: CreateBookingDTO = {
          room: Number(roomId),
          title: title.trim(),
          date,
          start_time: startTime,
          end_time: endTime,
          attendees_count: Number(attendees),
          purpose: note.trim(),
        };
        await apiClient.post('/api/meeting-bookings/', createPayload);
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        const errorData = err.data as Record<string, unknown> | undefined;
        if (errorData) {
          const errKey = String(errorData.error || errorData.detail || '');
          if (errKey && errKey.startsWith('meetings.messages.')) {
            setErrorMsg(t(errKey));
          } else if (Array.isArray(errorData.non_field_errors)) {
            setErrorMsg(errorData.non_field_errors.map((e) => typeof e === 'string' && e.startsWith('meetings.messages.') ? t(e) : e).join(' '));
          } else if (typeof errorData.non_field_errors === 'string') {
            const nfe = errorData.non_field_errors;
            setErrorMsg(nfe.startsWith('meetings.messages.') ? t(nfe) : nfe);
          } else if (errorData.error) {
            const errStr = String(errorData.error);
            setErrorMsg(errStr.startsWith('meetings.messages.') ? t(errStr) : errStr);
          } else if (errorData.detail) {
            const dtStr = String(errorData.detail);
            setErrorMsg(dtStr.startsWith('meetings.messages.') ? t(dtStr) : dtStr);
          } else {
            // Map individual field errors
            const fErrors: Record<string, string> = {};
            for (const [key, value] of Object.entries(errorData)) {
              if (Array.isArray(value)) {
                fErrors[key] = value.map((v) => typeof v === 'string' && v.startsWith('meetings.messages.') ? t(v) : v).join(' ');
              } else if (typeof value === 'string') {
                fErrors[key] = value.startsWith('meetings.messages.') ? t(value) : value;
              }
            }
            setFieldErrors(fErrors);
            const firstKey = Object.keys(fErrors)[0];
            if (firstKey) {
              setErrorMsg(fErrors[firstKey]);
            } else {
              setErrorMsg(err.message || t('meetings.messages.saveBookingError'));
            }
          }
        } else {
          setErrorMsg(err.message || t('meetings.messages.saveBookingError'));
        }
      } else {
        setErrorMsg(t('meetings.messages.unexpectedError'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Header Modal */}
      <div className="px-6 py-4 border-b border-border-subtle flex items-center justify-between bg-surface-elevated">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-subtle text-primary flex items-center justify-center font-bold">
            <i className="fa-solid fa-calendar-plus text-lg" />
          </div>
          <div>
            <h2 id="booking-modal-title" className="text-lg font-bold text-main">
              {bookingToEdit ? t('meetings.modalBooking.editTitle') : t('meetings.modalBooking.createTitle')}
            </h2>
            <p className="text-xs text-muted">
              {t('meetings.modalBooking.subtitle')}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface-elevated transition-colors"
          aria-label={t('meetings.modalBooking.cancelBtn')}
        >
          <i className="fa-solid fa-xmark text-lg" />
        </button>
      </div>

      {/* Form Body */}
      <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1 space-y-4">
        {/* Banner cảnh báo lỗi / trùng lịch */}
        {errorMsg && (
          <div
            className="p-3.5 rounded-xl bg-danger-subtle border border-danger-border text-danger text-sm flex items-start gap-2.5 animate-fadeIn"
            role="alert"
          >
            <i className="fa-solid fa-triangle-exclamation mt-0.5 shrink-0" />
            <div className="flex-1 font-medium">{errorMsg}</div>
          </div>
        )}

        {/* Chọn phòng họp */}
        <div>
          <label
            htmlFor="booking-room-select"
            className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5"
          >
            {t('meetings.modalBooking.roomLabel')} <span className="text-danger">*</span>
          </label>
          <select
            id="booking-room-select"
            value={roomId}
            onChange={(e) => {
              setRoomId(e.target.value ? Number(e.target.value) : '');
              if (fieldErrors.room) {
                setFieldErrors((prev) => ({ ...prev, room: '' }));
              }
            }}
            required
            className={`w-full px-3.5 py-2.5 rounded-xl bg-surface border text-main focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary text-sm font-medium transition-all ${
              fieldErrors.room ? 'border-danger' : 'border-border-subtle'
            }`}
          >
            <option value="" disabled>{t('meetings.modalBooking.roomPlaceholder')}</option>
            {rooms.map((r) => {
              const isAvailable = (r.trang_thai || 'AVAILABLE') === 'AVAILABLE';
              const isDisabled = !isAvailable && r.id !== bookingToEdit?.room;

              let statusLabel = '';
              if (r.trang_thai === 'MAINTENANCE') {
                statusLabel = ` [${t('meetings.status.maintenance')}]`;
              } else if (r.trang_thai === 'UNAVAILABLE') {
                statusLabel = ` [${t('meetings.status.unavailable')}]`;
              }

              const visibilityLabel = !r.is_public ? ` [${t('meetings.status.private')}]` : '';

              return (
                <option key={r.id} value={r.id} disabled={isDisabled}>
                  {r.name} ({t('meetings.fields.capacity')}: {r.capacity} {t('meetings.fields.people')}) {r.location ? `- ${r.location}` : ''}{statusLabel}{visibilityLabel}
                </option>
              );
            })}
          </select>
          {fieldErrors.room && (
            <p className="mt-1 text-xs text-danger">{fieldErrors.room}</p>
          )}

          {/* Room quick details preview */}
          {selectedRoom && (
            <div className="mt-2 p-2.5 rounded-lg bg-surface-elevated border border-border-subtle text-xs text-secondary flex flex-wrap items-center gap-x-4 gap-y-1">
              <span>
                <i className="fa-solid fa-users text-primary mr-1" /> {t('meetings.fields.capacity')}:{' '}
                <strong className="text-main">{selectedRoom.capacity} {t('meetings.fields.people')}</strong>
              </span>
              {selectedRoom.location && (
                <span>
                  <i className="fa-solid fa-location-dot text-primary mr-1" /> {t('meetings.fields.location')}:{' '}
                  <strong className="text-main">{selectedRoom.location}</strong>
                </span>
              )}
              {selectedRoom.amenities && (
                <span className="truncate max-w-full">
                  <i className="fa-solid fa-tv text-primary mr-1" /> {t('meetings.fields.amenities')}:{' '}
                  <span className="text-main">{selectedRoom.amenities}</span>
                </span>
              )}
            </div>
          )}

          {/* Danh sách các khung giờ đã bận tại phòng này */}
          {bookedSlotsInRoom.length > 0 && (
            <div className="mt-2.5 p-3 rounded-xl bg-warning-subtle/40 border border-warning/35 space-y-1.5 animate-fadeIn">
              <div className="flex items-center gap-1.5 text-xs font-bold text-warning-text">
                <i className="fa-solid fa-clock-rotate-left" />
                <span>{t('meetings.existingSlotsNotice')}</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {bookedSlotsInRoom.map((slot) => (
                  <span
                    key={slot.id}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-surface text-warning-text border border-warning/30 shadow-2xs"
                  >
                    <i className="fa-solid fa-clock text-[10px] text-warning" />
                    <span>{slot.start_time.slice(0, 5)} - {slot.end_time.slice(0, 5)}</span>
                    <span className="text-muted font-normal truncate max-w-[150px]">({slot.title})</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Tiêu đề cuộc họp */}
        <div>
          <label
            htmlFor="booking-title-input"
            className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5"
          >
            {t('meetings.modalBooking.titleLabel')} <span className="text-danger">*</span>
          </label>
          <input
            id="booking-title-input"
            type="text"
            placeholder={t('meetings.modalBooking.titlePlaceholder')}
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (fieldErrors.title) {
                setFieldErrors((prev) => ({ ...prev, title: '' }));
              }
            }}
            required
            className={`w-full px-3.5 py-2.5 rounded-xl bg-surface border text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary text-sm font-medium transition-all ${
              fieldErrors.title ? 'border-danger' : 'border-border-subtle'
            }`}
          />
          {fieldErrors.title && (
            <p className="mt-1 text-xs text-danger">{fieldErrors.title}</p>
          )}
        </div>

        {/* Đơn vị tổ chức & Số người tham gia */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="booking-department-input"
              className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5"
            >
              {t('meetings.modalBooking.departmentLabel')}
            </label>
            <input
              id="booking-department-input"
              type="text"
              placeholder={t('meetings.modalBooking.departmentPlaceholder')}
              value={department}
              readOnly
              className="w-full px-3.5 py-2.5 rounded-xl bg-surface-elevated border border-border-subtle text-main placeholder:text-muted focus:outline-none text-sm font-medium transition-all"
            />
          </div>

          <div>
            <label
              htmlFor="booking-attendees-input"
              className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5"
            >
              {t('meetings.modalBooking.attendeesLabel')} <span className="text-danger">*</span>
            </label>
            <input
              id="booking-attendees-input"
              type="number"
              min="1"
              value={attendees}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10) || 0;
                setAttendees(val);
                if (fieldErrors.attendees_count) {
                  setFieldErrors((prev) => ({ ...prev, attendees_count: '' }));
                }
              }}
              required
              className={`w-full px-3.5 py-2.5 rounded-xl bg-surface border text-main focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary text-sm font-medium transition-all ${
                fieldErrors.attendees_count ? 'border-danger' : 'border-border-subtle'
              }`}
            />
            {fieldErrors.attendees_count && (
              <p className="mt-1 text-xs text-danger">{fieldErrors.attendees_count}</p>
            )}
          </div>
        </div>

        {/* Ngày họp & Khung giờ */}
        <div className="p-3.5 rounded-xl bg-surface-elevated border border-border-subtle space-y-3">
          <div className="text-xs font-bold text-main uppercase tracking-wider flex items-center gap-1.5">
            <i className="fa-regular fa-clock text-primary" /> {t('meetings.modalBooking.timeSlotLabel')}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label
                htmlFor="booking-date-input"
                className="block text-xs font-semibold text-secondary mb-1"
              >
                {t('meetings.modalBooking.dateLabel')} <span className="text-danger">*</span>
              </label>
              <input
                id="booking-date-input"
                type="date"
                min={initialDate && initialDate < new Date().toLocaleDateString('en-CA') ? undefined : new Date().toLocaleDateString('en-CA')}
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-surface border border-border-subtle text-main text-sm focus:outline-none focus:ring-2 focus:ring-primary font-medium"
              />
            </div>

            <div>
              <label
                htmlFor="booking-start-time-input"
                className="block text-xs font-semibold text-secondary mb-1"
              >
                {t('meetings.modalBooking.startTimeLabel')} <span className="text-danger">*</span>
              </label>
              <input
                id="booking-start-time-input"
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                required
                className={`w-full px-3 py-2 rounded-lg bg-surface border text-main text-sm focus:outline-none focus:ring-2 focus:ring-primary font-medium ${
                  fieldErrors.start_time ? 'border-danger' : 'border-border-subtle'
                }`}
              />
            </div>

            <div>
              <label
                htmlFor="booking-end-time-input"
                className="block text-xs font-semibold text-secondary mb-1"
              >
                {t('meetings.modalBooking.endTimeLabel')} <span className="text-danger">*</span>
              </label>
              <input
                id="booking-end-time-input"
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                required
                className={`w-full px-3 py-2 rounded-lg bg-surface border text-main text-sm focus:outline-none focus:ring-2 focus:ring-primary font-medium ${
                  fieldErrors.end_time ? 'border-danger' : 'border-border-subtle'
                }`}
              />
            </div>
          </div>
          {fieldErrors.end_time && (
            <p className="text-xs text-danger font-medium">{fieldErrors.end_time}</p>
          )}

          {/* Cảnh báo xung đột khung giờ trực quan */}
          {conflictingSlot && (
            <div className="mt-2 p-3 rounded-xl bg-danger-subtle/50 border border-danger/40 text-danger text-xs flex items-start gap-2.5 animate-fadeIn">
              <i className="fa-solid fa-triangle-exclamation text-base shrink-0 mt-0.5 text-danger" />
              <div>
                <p className="font-bold">
                  {t('meetings.conflictWarning', {
                    title: conflictingSlot.title,
                    start: conflictingSlot.start_time.slice(0, 5),
                    end: conflictingSlot.end_time.slice(0, 5),
                  })}
                </p>
                <p className="text-[11px] opacity-80 mt-0.5">
                  {t('meetings.conflictHint')}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Ghi chú */}
        <div>
          <label
            htmlFor="booking-note-textarea"
            className="block text-xs font-bold text-secondary uppercase tracking-wider mb-1.5"
          >
            {t('meetings.modalBooking.purposeLabel')}
          </label>
          <textarea
            id="booking-note-textarea"
            rows={2}
            placeholder={t('meetings.modalBooking.purposePlaceholder')}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-border-subtle text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary text-sm font-medium transition-all resize-none"
          />
        </div>

        {/* Footer Actions */}
        <div className="pt-3 border-t border-border-subtle flex items-center justify-end gap-3">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={loading}
          >
            {t('meetings.modalBooking.cancelBtn')}
          </Button>
          <Button
            type="submit"
            variant="primary"
            isLoading={loading}
            icon="fa-check"
          >
            {bookingToEdit ? t('meetings.modalBooking.updateBtn') : t('meetings.modalBooking.saveBtn')}
          </Button>
        </div>
      </form>
    </>
  );
};

export const BookingModal: React.FC<BookingModalProps> = ({ isOpen, ...props }) => {
  // Lắng nghe phím Escape để đóng modal
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        props.onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, props]);

  if (!isOpen) return null;

  // Sử dụng key để reset state hoàn toàn khi mở lại modal hoặc chuyển đổi booking / phòng chọn trước
  const formKey = props.bookingToEdit
    ? `edit-${props.bookingToEdit.id}`
    : `new-${props.initialDate || 'default'}-${props.initialRoomId || 'any'}`;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="booking-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          props.onClose();
        }
      }}
    >
      <div className="bg-surface border border-border-subtle rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <BookingForm key={formKey} {...props} />
      </div>
    </div>
  );
};

export default BookingModal;
