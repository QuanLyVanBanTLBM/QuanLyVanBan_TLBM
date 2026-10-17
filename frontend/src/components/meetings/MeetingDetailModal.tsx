import React, { useEffect } from 'react';
import { MeetingBooking, MeetingRoom } from '@app-types/meeting';
import { Badge } from '@components/common/Badge';
import { Button } from '@components/common/Button';
import { useTranslation } from '@i18n/translate';

export interface MeetingDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  booking: MeetingBooking | null;
  room?: MeetingRoom | null;
  canModify?: boolean;
  onEdit?: (booking: MeetingBooking) => void;
  onCancel?: (booking: MeetingBooking) => void;
}

export const MeetingDetailModal: React.FC<MeetingDetailModalProps> = ({
  isOpen,
  onClose,
  booking,
  room,
  canModify = false,
  onEdit,
  onCancel,
}) => {
  const { t } = useTranslation();

  // Đóng bằng phím Escape
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

  if (!isOpen || !booking) return null;

  const roomInfo = room || booking.room_detail;
  const timeRangeStr = `${booking.start_time.slice(0, 5)} - ${booking.end_time.slice(0, 5)}`;
  const dateFormatted = booking.date.split('-').reverse().join('/');

  // Phân tích nội dung mục đích và lý do hủy (nếu có)
  const purposeParts = (booking.purpose || '').split('\n---\n');
  const purposeText = purposeParts[0]?.trim();
  const cancelReasonText = purposeParts[1]?.trim();

  const isCompleted = booking.trang_thai === 'COMPLETED';
  const isCancelled = booking.trang_thai === 'CANCELLED';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="meeting-detail-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="bg-surface border border-border-subtle rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-6 border-b border-border-subtle flex items-start justify-between gap-4">
          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-primary-subtle text-primary">
                <i className="fa-regular fa-calendar-check mr-1.5" />
                {t('meetings.modalDetail.title')}
              </span>
              {booking.trang_thai === 'CONFIRMED' && (
                <Badge variant="success" size="sm" withDot>
                  {t('meetings.status.confirmed')}
                </Badge>
              )}
              {isCompleted && (
                <Badge variant="secondary" size="sm">
                  {t('meetings.status.completed')}
                </Badge>
              )}
              {isCancelled && (
                <Badge variant="danger" size="sm" withDot>
                  {t('meetings.status.cancelled')}
                </Badge>
              )}
            </div>
            <h2 id="meeting-detail-title" className="text-xl font-black text-main tracking-tight truncate">
              {booking.title}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-xl bg-surface-elevated hover:bg-surface-hover text-secondary hover:text-main flex items-center justify-center transition-colors"
            aria-label={t('meetings.modalDetail.close')}
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-sm">
          {/* Card: Thông tin phòng & Thời gian */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="p-4 rounded-xl bg-surface-elevated border border-border-subtle space-y-1">
              <p className="text-[11px] font-bold text-muted uppercase tracking-wider">
                <i className="fa-solid fa-door-open mr-1.5 text-primary" />
                {t('meetings.modalDetail.roomInfo')}
              </p>
              <p className="font-bold text-main text-sm">
                {roomInfo?.name || t('meetings.table.roomFallback', { id: booking.room })}
              </p>
              {roomInfo?.location && (
                <p className="text-xs text-secondary flex items-center gap-1">
                  <i className="fa-solid fa-location-dot text-xs text-muted" />
                  {roomInfo.location}
                </p>
              )}
              {roomInfo?.capacity && (
                <p className="text-[11px] text-muted">
                  {t('meetings.table.capacity')}: {roomInfo.capacity} {t('meetings.table.attendees')}
                </p>
              )}
            </div>

            <div className="p-4 rounded-xl bg-surface-elevated border border-border-subtle space-y-1">
              <p className="text-[11px] font-bold text-muted uppercase tracking-wider">
                <i className="fa-regular fa-clock mr-1.5 text-primary" />
                {t('meetings.modalDetail.timeInfo')}
              </p>
              <p className="font-bold text-primary text-base">
                {timeRangeStr}
              </p>
              <p className="text-xs text-secondary flex items-center gap-1 font-medium">
                <i className="fa-regular fa-calendar text-xs text-muted" />
                {dateFormatted}
              </p>
            </div>
          </div>

          {/* Người chủ trì & Đơn vị */}
          <div className="p-4 rounded-xl bg-surface-elevated border border-border-subtle space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-secondary">
                <i className="fa-solid fa-user-tie mr-1.5 text-muted" />
                {t('meetings.modalDetail.organizerInfo')}:
              </span>
              <strong className="text-main font-semibold">
                {booking.organizer_detail?.ho_ten || booking.organizer_detail?.username || t('meetings.table.staffFallback')}
              </strong>
            </div>

            {(booking.department_name || booking.organizer_detail?.don_vi_ten) && (
              <div className="flex items-center justify-between border-t border-border-subtle pt-2">
                <span className="text-xs font-bold text-secondary">
                  <i className="fa-solid fa-building mr-1.5 text-muted" />
                  {t('meetings.modalDetail.department')}:
                </span>
                <span className="text-main text-xs font-medium">
                  {booking.department_name || booking.organizer_detail?.don_vi_ten}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between border-t border-border-subtle pt-2">
              <span className="text-xs font-bold text-secondary">
                <i className="fa-solid fa-users mr-1.5 text-muted" />
                {t('meetings.modalDetail.attendees')}:
              </span>
              <span className="text-main text-xs font-bold px-2 py-0.5 rounded-md bg-surface border border-border-subtle">
                {booking.attendees_count}
              </span>
            </div>
          </div>

          {/* Mục đích cuộc họp */}
          {purposeText && (
            <div className="space-y-1.5">
              <p className="text-xs font-bold text-secondary uppercase tracking-wider">
                <i className="fa-regular fa-note-sticky mr-1.5 text-primary" />
                {t('meetings.modalDetail.purpose')}
              </p>
              <div className="p-3.5 rounded-xl bg-surface-elevated border border-border-subtle text-xs text-main font-medium whitespace-pre-wrap leading-relaxed">
                {purposeText}
              </div>
            </div>
          )}

          {/* Trang thiết bị phòng nếu có */}
          {roomInfo?.amenities && (
            <div className="space-y-1.5">
              <p className="text-xs font-bold text-secondary uppercase tracking-wider">
                <i className="fa-solid fa-tv mr-1.5 text-primary" />
                {t('meetings.modalDetail.amenities')}
              </p>
              <p className="text-xs text-muted bg-surface-elevated p-3 rounded-xl border border-border-subtle">
                {roomInfo.amenities}
              </p>
            </div>
          )}

          {/* Thông báo hủy lịch nếu có */}
          {cancelReasonText && (
            <div className="p-3.5 rounded-xl bg-danger-subtle border border-danger-border text-xs text-danger space-y-1">
              <p className="font-bold flex items-center gap-1.5">
                <i className="fa-solid fa-ban text-sm" />
                {t('meetings.modalDetail.cancelReason')}:
              </p>
              <p className="whitespace-pre-wrap font-medium">{cancelReasonText}</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-border-subtle flex items-center justify-between gap-3 bg-surface">
          <div>
            {!isCompleted && !isCancelled && canModify && onCancel && (
              <Button
                variant="danger"
                size="sm"
                icon="fa-ban"
                onClick={() => {
                  onClose();
                  onCancel(booking);
                }}
              >
                {t('meetings.actions.cancel')}
              </Button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {!isCompleted && !isCancelled && canModify && onEdit && (
              <Button
                variant="secondary"
                size="sm"
                icon="fa-pen-to-square"
                onClick={() => {
                  onClose();
                  onEdit(booking);
                }}
              >
                {t('meetings.actions.edit')}
              </Button>
            )}
            <Button
              variant="primary"
              size="sm"
              onClick={onClose}
            >
              {t('meetings.modalDetail.close')}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
