import React, { useState, useEffect, useMemo } from 'react';
import { MeetingRoom, MeetingBooking, BookingUser } from '@app-types/meeting';
import { apiClient, ApiError } from '@lib/apiClient';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';
import { Card } from '@components/common/Card';
import { BookingModal } from '@components/meetings/BookingModal';
import { RoomModal } from '@components/meetings/RoomModal';
import { MeetingDetailModal } from '@components/meetings/MeetingDetailModal';
import { useTranslation } from '@i18n/translate';
import { usePermissions } from '@lib/permissions';
import { extractFloor, getFloorKey } from '@lib/meetingFloor';

interface PaginatedResponse<T> {
  count?: number;
  results?: T[];
}

// /api/auth/profile/ (hợp đồng chung của layout) vẫn dùng full_name, department, position.
interface UserProfileResponse {
  id: number;
  username: string;
  full_name?: string;
  department?: string;
  position?: string;
}

export const MeetingsPage: React.FC = () => {
  const { t, currentLang } = useTranslation();
  const { can } = usePermissions();

  // Tab hiện tại: 'schedule' (Lịch đặt) | 'rooms' (Danh mục phòng)
  const [activeTab, setActiveTab] = useState<'schedule' | 'rooms'>('schedule');

  // Dữ liệu
  const [rooms, setRooms] = useState<MeetingRoom[]>([]);
  const [bookings, setBookings] = useState<MeetingBooking[]>([]);
  const [currentUser, setCurrentUser] = useState<BookingUser | null>(null);

  const formatLocalDate = (d: Date = new Date()): string => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // Bộ lọc lịch
  const [selectedDate, setSelectedDate] = useState<string>(() => formatLocalDate());
  const [selectedRoomFilter, setSelectedRoomFilter] = useState<string>('all');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('all');
  const [selectedFloorFilter, setSelectedFloorFilter] = useState<string>('all');

  // Lịch đặt của ngày hôm nay cho Tab 2 (Danh mục phòng), hoàn toàn không bị ảnh hưởng bởi bộ lọc của Tab 1
  const [todayBookings, setTodayBookings] = useState<MeetingBooking[]>([]);
  const todayStr = useMemo(() => formatLocalDate(), []);

  // Bộ lọc danh mục phòng
  const [roomSearchTerm, setRoomSearchTerm] = useState('');
  const [roomStatusFilter, setRoomStatusFilter] = useState<string>('all');
  const [roomVisibilityFilter, setRoomVisibilityFilter] = useState<string>('all');

  // Trạng thái tải & lỗi
  const [loadingRooms, setLoadingRooms] = useState(true);
  const [loadingBookings, setLoadingBookings] = useState(true);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Trigger reload
  const [reloadRoomsTrigger, setReloadRoomsTrigger] = useState(0);
  const [reloadBookingsTrigger, setReloadBookingsTrigger] = useState(0);

  // Modals
  const [isBookingModalOpen, setIsBookingModalOpen] = useState(false);
  const [bookingToEdit, setBookingToEdit] = useState<MeetingBooking | null>(null);
  const [selectedRoomForBooking, setSelectedRoomForBooking] = useState<number | null>(null);

  const [isRoomModalOpen, setIsRoomModalOpen] = useState(false);
  const [roomToEdit, setRoomToEdit] = useState<MeetingRoom | null>(null);

  // Modal xem chi tiết cuộc họp
  const [selectedBookingDetail, setSelectedBookingDetail] = useState<MeetingBooking | null>(null);

  // Modal xác nhận hủy lịch
  const [cancellingBooking, setCancellingBooking] = useState<MeetingBooking | null>(null);
  const [cancelReason, setCancelReason] = useState('');
  const [isSubmittingCancel, setIsSubmittingCancel] = useState(false);

  // Modal xác nhận xóa phòng
  const [deletingRoom, setDeletingRoom] = useState<MeetingRoom | null>(null);
  const [isSubmittingDelete, setIsSubmittingDelete] = useState(false);

  const showToast = (type: 'success' | 'error', text: string) => {
    setToastMessage({ type, text });
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  // 1. Tải thông tin người dùng hiện tại
  useEffect(() => {
    let isMounted = true;
    apiClient.get<UserProfileResponse>('/api/auth/profile/')
      .then((res) => {
        if (!isMounted || !res) return;
        setCurrentUser({
          id: res.id,
          username: res.username,
          ho_ten: res.full_name || res.username,
          don_vi_ten: res.department || '',
          chuc_vu_ten: res.position || '',
        });
      })
      .catch(() => {
        if (!isMounted) return;
        try {
          const session = localStorage.getItem('tlbm_session');
          if (session) {
            const parsed = JSON.parse(session) as UserProfileResponse;
            setCurrentUser({
              id: parsed.id || 0,
              username: parsed.username || '',
              ho_ten: parsed.full_name || parsed.username || '',
              don_vi_ten: parsed.department || '',
              chuc_vu_ten: parsed.position || '',
            });
          }
        } catch {
          // ignore
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Tải danh mục phòng họp
  useEffect(() => {
    let isMounted = true;

    apiClient.get<PaginatedResponse<MeetingRoom> | MeetingRoom[]>('/api/meeting-rooms/?page_size=100')
      .then((res) => {
        if (!isMounted) return;
        const list = Array.isArray(res) ? res : res.results || [];
        setRooms(list);
        setLoadingRooms(false);
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        setLoadingRooms(false);
        if (err instanceof ApiError) {
          showToast('error', err.message);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [reloadRoomsTrigger]);

  // 3. Tải lịch đặt phòng theo ngày
  useEffect(() => {
    let isMounted = true;

    let url = `/api/meeting-bookings/?date=${selectedDate}&page_size=100`;
    if (selectedRoomFilter !== 'all') {
      url += `&room=${selectedRoomFilter}`;
    }
    if (selectedStatusFilter !== 'all') {
      url += `&trang_thai=${selectedStatusFilter}`;
    }

    apiClient.get<PaginatedResponse<MeetingBooking> | MeetingBooking[]>(url)
      .then((res) => {
        if (!isMounted) return;
        const list = Array.isArray(res) ? res : res.results || [];
        setBookings(list);
        setLoadingBookings(false);
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        setLoadingBookings(false);
        if (err instanceof ApiError) {
          showToast('error', err.message);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedDate, selectedRoomFilter, selectedStatusFilter, reloadBookingsTrigger]);

  // 4. Tải lịch của ngày hôm nay cho Tab Danh mục phòng (không lọc room hay trang_thai)
  useEffect(() => {
    let isMounted = true;
    apiClient
      .get<PaginatedResponse<MeetingBooking> | MeetingBooking[]>(
        `/api/meeting-bookings/?date=${todayStr}&page_size=100`
      )
      .then((res) => {
        if (!isMounted) return;
        const list = Array.isArray(res) ? res : res.results || [];
        setTodayBookings(list);
      })
      .catch(() => {
        // ignore
      });

    return () => {
      isMounted = false;
    };
  }, [todayStr, reloadBookingsTrigger]);

  // Điều khiển ngày: Hôm nay, trước, sau
  const handleDateChange = (daysDelta: number) => {
    const parts = selectedDate.split('-');
    const current = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    current.setDate(current.getDate() + daysDelta);
    setSelectedDate(formatLocalDate(current));
  };

  const handleSetToday = () => {
    setSelectedDate(formatLocalDate());
  };

  // Xử lý Hủy lịch đặt
  const handleConfirmCancelBooking = async () => {
    if (!cancellingBooking) return;
    setIsSubmittingCancel(true);
    try {
      await apiClient.post(`/api/meeting-bookings/${cancellingBooking.id}/cancel/`, {
        cancel_reason: cancelReason.trim(),
      });
      showToast('success', t('meetings.messages.cancelSuccess'));
      setCancellingBooking(null);
      setCancelReason('');
      setReloadBookingsTrigger((prev) => prev + 1);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        showToast('error', err.message);
      } else {
        showToast('error', t('meetings.messages.cancelError'));
      }
    } finally {
      setIsSubmittingCancel(false);
    }
  };

  // Xử lý Xóa phòng họp
  const handleConfirmDeleteRoom = async () => {
    if (!deletingRoom) return;
    setIsSubmittingDelete(true);
    try {
      await apiClient.delete(`/api/meeting-rooms/${deletingRoom.id}/`);
      showToast('success', t('meetings.messages.deleteRoomSuccess', { name: deletingRoom.name }));
      setDeletingRoom(null);
      setReloadRoomsTrigger((prev) => prev + 1);
      setReloadBookingsTrigger((prev) => prev + 1);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        showToast('error', err.message || (err.data?.detail as string) || t('meetings.messages.deleteRoomError'));
      } else {
        showToast('error', t('meetings.messages.unexpectedError'));
      }
    } finally {
      setIsSubmittingDelete(false);
    }
  };

  const canAddRoom = can('add_phonghop');
  const canChangeRoom = can('change_phonghop');
  const canDeleteRoom = can('delete_phonghop');
  const canAddBooking = can('add_datphonghop');
  const canChangeOwnBooking = can('change_own_datphonghop');
  const canChangeAnyBooking = can('change_any_datphonghop');

  // Danh sách các tầng xuất hiện trong danh mục phòng
  const availableFloors = useMemo(() => {
    const setFloors = new Set<string>();
    rooms.forEach((r) => {
      const f = extractFloor(r.location, currentLang);
      if (f) setFloors.add(f);
    });
    return Array.from(setFloors).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  }, [rooms, currentLang]);

  // Lọc danh mục phòng ở Tab 2
  const filteredRooms = useMemo(() => {
    return rooms.filter((r) => {
      const matchesSearch =
        r.name.toLowerCase().includes(roomSearchTerm.toLowerCase()) ||
        (r.location && r.location.toLowerCase().includes(roomSearchTerm.toLowerCase())) ||
        (r.amenities && r.amenities.toLowerCase().includes(roomSearchTerm.toLowerCase()));

      const currentStatus = r.trang_thai || 'AVAILABLE';
      const matchesStatus =
        roomStatusFilter === 'all'
          ? true
          : currentStatus === roomStatusFilter;

      const matchesVisibility =
        !canChangeRoom || roomVisibilityFilter === 'all'
          ? true
          : roomVisibilityFilter === 'public'
          ? r.is_public
          : !r.is_public;

      const rFloor = extractFloor(r.location, currentLang);
      const rFloorVi = extractFloor(r.location, 'vi');
      const rFloorEn = extractFloor(r.location, 'en');
      const rFloorKey = getFloorKey(r.location);

      const matchesFloor =
        !selectedFloorFilter || selectedFloorFilter.toLowerCase() === 'all'
          ? true
          : selectedFloorFilter === rFloor ||
            selectedFloorFilter === rFloorVi ||
            selectedFloorFilter === rFloorEn ||
            selectedFloorFilter === rFloorKey;

      return matchesSearch && matchesStatus && matchesVisibility && matchesFloor;
    });
  }, [rooms, roomSearchTerm, roomStatusFilter, roomVisibilityFilter, selectedFloorFilter, canChangeRoom, currentLang]);

  // Lọc danh sách cuộc họp theo tầng ở Tab 1
  const displayBookings = useMemo(() => {
    if (!selectedFloorFilter || selectedFloorFilter.toLowerCase() === 'all') return bookings;
    return bookings.filter((b) => {
      const room = rooms.find((r) => r.id === b.room) || b.room_detail;
      const rFloor = extractFloor(room?.location, currentLang);
      const rFloorVi = extractFloor(room?.location, 'vi');
      const rFloorEn = extractFloor(room?.location, 'en');
      const rFloorKey = getFloorKey(room?.location);

      return (
        selectedFloorFilter === rFloor ||
        selectedFloorFilter === rFloorVi ||
        selectedFloorFilter === rFloorEn ||
        selectedFloorFilter === rFloorKey
      );
    });
  }, [bookings, selectedFloorFilter, rooms, currentLang]);

  // Thống kê nhanh trong ngày
  const totalInDay = bookings.length;
  const activeInDay = bookings.filter((b) => b.trang_thai === 'CONFIRMED').length;
  const cancelledInDay = bookings.filter((b) => b.trang_thai === 'CANCELLED').length;
  const completedInDay = bookings.filter((b) => b.trang_thai === 'COMPLETED').length;

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          aria-live="polite"
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-xl text-sm font-semibold transition-all transform animate-fadeIn ${
            toastMessage.type === 'success'
              ? 'bg-success text-white border border-success-hover'
              : 'bg-danger text-white border border-danger-hover'
          }`}
        >
          <i
            className={`fa-solid ${
              toastMessage.type === 'success' ? 'fa-circle-check text-lg' : 'fa-circle-exclamation text-lg'
            }`}
          />
          <span>{toastMessage.text}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-2 hover:opacity-80 transition-opacity"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>
      )}

      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface p-6 rounded-2xl border border-border-subtle shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-primary-subtle text-primary flex items-center justify-center font-bold text-xl shadow-sm">
              <i className="fa-solid fa-people-roof" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-main tracking-tight">{t('meetings.title')}</h1>
              <p className="text-sm text-secondary">
                {t('meetings.subtitle')}
              </p>
            </div>
          </div>
        </div>

        {/* Nút hành động */}
        <div className="flex items-center gap-3 flex-wrap">
          {activeTab === 'schedule' ? (
            canAddBooking && (
              <Button
                variant="primary"
                icon="fa-calendar-plus"
                onClick={() => {
                  setBookingToEdit(null);
                  setIsBookingModalOpen(true);
                }}
              >
                {t('meetings.bookMeetingBtn')}
              </Button>
            )
          ) : (
            canAddRoom && (
              <Button
                variant="primary"
                icon="fa-plus"
                onClick={() => {
                  setRoomToEdit(null);
                  setIsRoomModalOpen(true);
                }}
              >
                {t('meetings.addRoomBtn')}
              </Button>
            )
          )}
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-border-subtle pb-px">
        <button
          onClick={() => setActiveTab('schedule')}
          className={`flex items-center gap-2.5 px-5 py-3 font-bold text-sm rounded-t-xl transition-all border-b-2 ${
            activeTab === 'schedule'
              ? 'text-primary border-primary bg-primary-subtle'
              : 'text-secondary border-transparent hover:text-main hover:bg-surface-hover'
          }`}
        >
          <i className="fa-regular fa-calendar-days text-base" />
          <span>{t('meetings.tabSchedule')}</span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-primary-subtle text-primary font-semibold">
            {activeInDay}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('rooms')}
          className={`flex items-center gap-2.5 px-5 py-3 font-bold text-sm rounded-t-xl transition-all border-b-2 ${
            activeTab === 'rooms'
              ? 'text-primary border-primary bg-primary-subtle'
              : 'text-secondary border-transparent hover:text-main hover:bg-surface-hover'
          }`}
        >
          <i className="fa-solid fa-door-open text-base" />
          <span>{t('meetings.tabRooms')}</span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-surface-elevated text-secondary font-semibold">
            {rooms.length}
          </span>
        </button>
      </div>

      {/* TAB 1: LỊCH ĐẶT PHÒNG HỌP */}
      {activeTab === 'schedule' && (
        <div className="space-y-6 animate-fadeIn">
          {/* Dashboard Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="p-4 bg-surface flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-muted uppercase tracking-wider">{t('meetings.totalToday')}</p>
                <p className="text-2xl font-black text-main mt-1">{totalInDay}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-primary-subtle text-primary flex items-center justify-center">
                <i className="fa-solid fa-calendar-check text-lg" />
              </div>
            </Card>

            <Card className="p-4 bg-surface flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-muted uppercase tracking-wider">{t('meetings.confirmedToday')}</p>
                <p className="text-2xl font-black text-success mt-1">{activeInDay}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-success-subtle text-success flex items-center justify-center">
                <i className="fa-solid fa-clock text-lg" />
              </div>
            </Card>

            <Card className="p-4 bg-surface flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-muted uppercase tracking-wider">{t('meetings.completedToday')}</p>
                <p className="text-2xl font-black text-secondary mt-1">{completedInDay}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-surface-elevated text-secondary flex items-center justify-center">
                <i className="fa-solid fa-circle-check text-lg" />
              </div>
            </Card>

            <Card className="p-4 bg-surface flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-muted uppercase tracking-wider">{t('meetings.cancelledToday')}</p>
                <p className="text-2xl font-black text-danger mt-1">{cancelledInDay}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-danger-subtle text-danger flex items-center justify-center">
                <i className="fa-solid fa-calendar-xmark text-lg" />
              </div>
            </Card>
          </div>

          {/* Date Selector & Filters Bar */}
          <div className="bg-surface p-4 rounded-2xl border border-border-subtle shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Bộ điều khiển ngày */}
            <div className="flex items-center gap-2 w-full md:w-auto">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleDateChange(-1)}
                title={t('meetings.prevDay')}
              >
                <i className="fa-solid fa-chevron-left" />
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleSetToday}
                className="font-bold"
              >
                {t('meetings.today')}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleDateChange(1)}
                title={t('meetings.nextDay')}
              >
                <i className="fa-solid fa-chevron-right" />
              </Button>

              <div className="relative flex items-center">
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-border-subtle text-main font-bold text-sm focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
                />
              </div>
            </div>

            {/* Bộ lọc phòng & Trạng thái */}
            <div className="flex items-center gap-3 w-full md:w-auto flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-secondary">{t('meetings.table.room')}:</span>
                <select
                  value={selectedRoomFilter}
                  onChange={(e) => setSelectedRoomFilter(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-border-subtle text-main text-xs font-bold focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
                >
                  <option value="all">{t('meetings.allRooms')}</option>
                  {rooms.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-secondary">{t('meetings.filterFloor')}:</span>
                <select
                  value={selectedFloorFilter}
                  onChange={(e) => setSelectedFloorFilter(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-border-subtle text-main text-xs font-bold focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
                  aria-label={t('meetings.filterFloorAria')}
                >
                  <option value="all">{t('meetings.allFloors')}</option>
                  {availableFloors.map((floor) => (
                    <option key={floor} value={floor}>
                      {floor}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-secondary">{t('meetings.table.status')}:</span>
                <select
                  value={selectedStatusFilter}
                  onChange={(e) => setSelectedStatusFilter(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-border-subtle text-main text-xs font-bold focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
                >
                  <option value="all">{t('meetings.allStatuses')}</option>
                  <option value="CONFIRMED">{t('meetings.filterConfirmed')}</option>
                  <option value="COMPLETED">{t('meetings.filterCompleted')}</option>
                  <option value="CANCELLED">{t('meetings.filterCancelled')}</option>
                </select>
              </div>
            </div>
          </div>

          {/* Booking List Container */}
          {loadingBookings ? (
            <div className="bg-surface rounded-2xl border border-border-subtle p-12 text-center text-muted">
              <i className="fa-solid fa-spinner fa-spin text-3xl text-primary mb-3" />
              <p className="text-sm font-medium">{t('meetings.loadingBookings')}</p>
            </div>
          ) : displayBookings.length === 0 ? (
            <div className="bg-surface rounded-2xl border border-border-subtle p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-surface-elevated mx-auto flex items-center justify-center text-muted text-2xl mb-4">
                <i className="fa-regular fa-calendar-xmark" />
              </div>
              <h3 className="text-base font-bold text-main">{t('meetings.noBookingsTitle')}</h3>
              <p className="text-xs text-muted max-w-sm mx-auto mt-1 mb-5">
                {t('meetings.noBookingsDesc', {
                  date: new Date(selectedDate).toLocaleDateString('vi-VN'),
                })}
              </p>
              {canAddBooking && (
                <Button
                  variant="primary"
                  icon="fa-calendar-plus"
                  onClick={() => {
                    setBookingToEdit(null);
                    setIsBookingModalOpen(true);
                  }}
                >
                  {t('meetings.bookNowBtn')}
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {displayBookings.map((booking) => {
                const timeRangeStr = `${booking.start_time.slice(0, 5)} - ${booking.end_time.slice(0, 5)}`;

                const isOwner = currentUser && booking.organizer === currentUser.id;
                const canModify = (isOwner && canChangeOwnBooking) || canChangeAnyBooking;

                return (
                  <Card
                    key={booking.id}
                    hoverable
                    className={`p-5 transition-all ${
                      booking.trang_thai === 'CANCELLED'
                        ? 'opacity-70 bg-surface-elevated border-dashed'
                        : 'border-l-4 border-l-primary'
                    }`}
                  >
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                      {/* Cột trái: Khung giờ & Tên phòng */}
                      <div className="flex items-start gap-4">
                        <div className="w-24 shrink-0 text-center bg-surface-elevated p-2.5 rounded-xl border border-border-subtle">
                          <p className="text-xs font-bold text-primary">{timeRangeStr}</p>
                          <p className="text-[10px] text-muted mt-0.5">
                            {`${booking.date.slice(8, 10)}/${booking.date.slice(5, 7)}`}
                          </p>
                        </div>

                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-black text-base text-main">{booking.title}</span>
                            {booking.trang_thai === 'CONFIRMED' && (
                              <Badge variant="success" size="sm" withDot>
                                {t('meetings.status.confirmed')}
                              </Badge>
                            )}
                            {booking.trang_thai === 'COMPLETED' && (
                              <Badge variant="secondary" size="sm">
                                {t('meetings.status.completed')}
                              </Badge>
                            )}
                            {booking.trang_thai === 'CANCELLED' && (
                              <Badge variant="danger" size="sm" withDot>
                                {t('meetings.status.cancelled')}
                              </Badge>
                            )}
                          </div>

                          {/* Thông tin phòng & Người đặt */}
                          <div className="flex items-center gap-4 text-xs text-secondary flex-wrap pt-1">
                            <span className="flex items-center gap-1.5 font-bold text-primary">
                              <i className="fa-solid fa-door-open" />
                              {booking.room_detail?.name || t('meetings.table.roomFallback', { id: booking.room })}
                              {booking.room_detail?.location && ` (${booking.room_detail.location})`}
                            </span>

                            <span className="flex items-center gap-1.5">
                              <i className="fa-solid fa-user-tie text-muted" />
                              {t('meetings.table.organizer')}:{' '}
                              <strong className="text-main font-semibold">
                                {booking.organizer_detail?.ho_ten || booking.organizer_detail?.username || t('meetings.table.staffFallback')}
                              </strong>
                            </span>

                            {booking.department_name && (
                              <span className="flex items-center gap-1.5">
                                <i className="fa-solid fa-building text-muted" />
                                {t('meetings.modalBooking.departmentLabel')}: {booking.department_name}
                              </span>
                            )}

                            <span className="flex items-center gap-1.5">
                              <i className="fa-solid fa-users text-muted" />
                              {t('meetings.table.attendees')}: {booking.attendees_count}
                            </span>
                          </div>

                          {booking.purpose && (() => {
                            const parts = booking.purpose.split('\n---\n');
                            const purposeText = parts[0]?.trim();
                            const cancelReasonText = parts[1]?.trim();
                            return (
                              <div className="mt-2 space-y-1">
                                {purposeText && (
                                  <p className="text-xs text-muted bg-surface-elevated px-2.5 py-1.5 rounded-lg border border-border-subtle inline-block mr-2">
                                    <i className="fa-regular fa-note-sticky mr-1.5" />
                                    {purposeText}
                                  </p>
                                )}
                                {cancelReasonText && (
                                  <p className="text-xs text-danger bg-danger-subtle px-2.5 py-1.5 rounded-lg border border-danger-border inline-block">
                                    <i className="fa-solid fa-ban mr-1.5" />
                                    <strong>{t('meetings.table.cancelReason')}:</strong> {cancelReasonText}
                                  </p>
                                )}
                              </div>
                            );
                          })()}
                        </div>
                      </div>

                      {/* Cột phải: Thao tác */}
                      <div className="flex items-center gap-2 self-end lg:self-center flex-wrap">
                        <Button
                          variant="secondary"
                          size="sm"
                          icon="fa-circle-info"
                          onClick={() => setSelectedBookingDetail(booking)}
                        >
                          {t('meetings.viewDetailBtn')}
                        </Button>

                        {booking.trang_thai !== 'CANCELLED' && booking.trang_thai !== 'COMPLETED' && canModify && (
                          <>
                            <Button
                              variant="secondary"
                              size="sm"
                              icon="fa-pen-to-square"
                              onClick={() => {
                                setBookingToEdit(booking);
                                setIsBookingModalOpen(true);
                              }}
                            >
                              {t('meetings.actions.edit')}
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              icon="fa-ban"
                              onClick={() => {
                                setCancellingBooking(booking);
                                setCancelReason('');
                              }}
                            >
                              {t('meetings.actions.cancel')}
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: DANH MỤC PHÒNG HỌP */}
      {activeTab === 'rooms' && (
        <div className="space-y-6 animate-fadeIn">
          {/* Controls Bar */}
          <div className="bg-surface p-4 rounded-2xl border border-border-subtle shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 w-full md:w-auto flex-1 max-w-md">
              <div className="relative w-full">
                <i className="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-muted text-sm" />
                <input
                  type="text"
                  placeholder={t('meetings.searchRoomPlaceholder')}
                  value={roomSearchTerm}
                  onChange={(e) => setRoomSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-surface-elevated border border-border-subtle text-main placeholder:text-muted text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto flex-wrap">
              {/* Bộ lọc theo tầng */}
              <select
                value={selectedFloorFilter}
                onChange={(e) => setSelectedFloorFilter(e.target.value)}
                className="px-3.5 py-2 rounded-xl bg-surface-elevated border border-border-subtle text-main text-xs font-bold focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
                aria-label={t('meetings.filterFloorAria')}
              >
                <option value="all">{t('meetings.allFloors')}</option>
                {availableFloors.map((floor) => (
                  <option key={floor} value={floor}>
                    {floor}
                  </option>
                ))}
              </select>

              <select
                value={roomStatusFilter}
                onChange={(e) => setRoomStatusFilter(e.target.value)}
                className="px-3.5 py-2 rounded-xl bg-surface-elevated border border-border-subtle text-main text-xs font-bold focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
                aria-label={t('meetings.filterRoomStatusAria')}
              >
                <option value="all">{t('meetings.allStatuses')}</option>
                <option value="AVAILABLE">{t('meetings.status.available')}</option>
                <option value="MAINTENANCE">{t('meetings.status.maintenance')}</option>
                <option value="UNAVAILABLE">{t('meetings.status.unavailable')}</option>
              </select>

              {canChangeRoom && (
                <select
                  value={roomVisibilityFilter}
                  onChange={(e) => setRoomVisibilityFilter(e.target.value)}
                  className="px-3.5 py-2 rounded-xl bg-surface-elevated border border-border-subtle text-main text-xs font-bold focus:outline-none focus:ring-2 focus:ring-primary cursor-pointer"
                  aria-label={t('meetings.filterRoomVisibilityAria')}
                >
                  <option value="all">{t('meetings.allRooms')}</option>
                  <option value="public">{t('meetings.status.public')}</option>
                  <option value="private">{t('meetings.status.private')}</option>
                </select>
              )}
            </div>
          </div>

          {/* Grid Rooms */}
          {loadingRooms ? (
            <div className="bg-surface rounded-2xl border border-border-subtle p-12 text-center text-muted">
              <i className="fa-solid fa-spinner fa-spin text-3xl text-primary mb-3" />
              <p className="text-sm font-medium">{t('meetings.loadingRooms')}</p>
            </div>
          ) : filteredRooms.length === 0 ? (
            <div className="bg-surface rounded-2xl border border-border-subtle p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-surface-elevated mx-auto flex items-center justify-center text-muted text-2xl mb-4">
                <i className="fa-solid fa-door-closed" />
              </div>
              <h3 className="text-base font-bold text-main">{t('meetings.emptyRooms')}</h3>
              <p className="text-xs text-muted max-w-sm mx-auto mt-1 mb-5">
                {t('meetings.emptyRoomsDesc')}
              </p>
              {canAddRoom && (
                <Button
                  variant="primary"
                  icon="fa-plus"
                  onClick={() => {
                    setRoomToEdit(null);
                    setIsRoomModalOpen(true);
                  }}
                >
                  {t('meetings.addRoomBtn')}
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredRooms.map((room) => {
                const isAvailable = (room.trang_thai || 'AVAILABLE') === 'AVAILABLE';
                const relevantBookings = todayBookings.length > 0 ? todayBookings : bookings;
                const roomBookingsToday = relevantBookings.filter(
                  (b) => b.room === room.id && b.trang_thai !== 'CANCELLED'
                );

                const now = new Date();
                const currentTimeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
                const isOccupiedNow = roomBookingsToday.some(
                  (b) => (b.date === todayStr || b.date === selectedDate) && b.start_time.slice(0, 5) <= currentTimeStr && currentTimeStr < b.end_time.slice(0, 5)
                );

                return (
                  <Card
                    key={room.id}
                    hoverable
                    role={isAvailable && canAddBooking ? 'button' : undefined}
                    tabIndex={isAvailable && canAddBooking ? 0 : undefined}
                    aria-label={isAvailable && canAddBooking ? `${room.name} - ${t('meetings.table.bookThisRoom')}` : room.name}
                    className={`p-5 flex flex-col justify-between h-full transition-all ${
                      isAvailable && canAddBooking
                        ? 'cursor-pointer hover:border-primary/60 hover:shadow-lg border-2 border-transparent focus:outline-none focus:ring-2 focus:ring-primary'
                        : ''
                    }`}
                    onClick={(e) => {
                      if ((e.target as HTMLElement).closest('button')) return;
                      if (isAvailable && canAddBooking) {
                        setSelectedRoomForBooking(room.id);
                        setBookingToEdit(null);
                        setIsBookingModalOpen(true);
                      }
                    }}
                    onKeyDown={(e) => {
                      if ((e.key === 'Enter' || e.key === ' ') && isAvailable && canAddBooking) {
                        if ((e.target as HTMLElement).closest('button')) return;
                        e.preventDefault();
                        setSelectedRoomForBooking(room.id);
                        setBookingToEdit(null);
                        setIsBookingModalOpen(true);
                      }
                    }}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-3 mb-3">
                        <div>
                          <h3 className="text-base font-bold text-main">{room.name}</h3>
                          <p className="text-xs text-muted flex items-center gap-1.5 mt-0.5">
                            <i className="fa-solid fa-location-dot text-primary" />
                            {room.location || t('meetings.table.notUpdated')}
                          </p>
                        </div>
                        <div className="flex flex-col items-end gap-1.5">
                          {room.trang_thai === 'MAINTENANCE' ? (
                            <Badge variant="warning" size="sm" withDot>
                              {t('meetings.status.maintenance')}
                            </Badge>
                          ) : room.trang_thai === 'UNAVAILABLE' ? (
                            <Badge variant="danger" size="sm" withDot>
                              {t('meetings.status.unavailable')}
                            </Badge>
                          ) : isOccupiedNow ? (
                            <Badge variant="danger" size="sm" withDot>
                              {t('meetings.occupied')}
                            </Badge>
                          ) : (
                            <div className="flex items-center gap-1.5 flex-wrap justify-end">
                              <Badge variant="success" size="sm" withDot>
                                {t('meetings.status.available')}
                              </Badge>
                              {roomBookingsToday.length > 0 && (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-warning-subtle text-warning-text border border-warning/30 flex items-center gap-1 shadow-2xs">
                                  <i className="fa-solid fa-clock text-[9px]" />
                                  {t('meetings.hasScheduleToday')}
                                </span>
                              )}
                            </div>
                          )}
                          {canChangeRoom && (
                            <Badge variant="secondary" size="sm">
                              {room.is_public ? t('meetings.status.public') : t('meetings.status.private')}
                            </Badge>
                          )}
                        </div>
                      </div>

                      {/* Sức chứa */}
                      <div className="p-3 rounded-xl bg-surface-elevated border border-border-subtle mb-3 flex items-center justify-between">
                        <span className="text-xs text-secondary font-medium">{t('meetings.table.capacityMax')}</span>
                        <span className="text-sm font-black text-primary flex items-center gap-1">
                          <i className="fa-solid fa-users text-xs" />
                          {room.capacity} {t('meetings.table.attendees')}
                        </span>
                      </div>

                      {/* Thiết bị */}
                      <div className="space-y-1 mb-4">
                        <p className="text-[11px] font-bold text-muted uppercase tracking-wider">{t('meetings.table.amenitiesLabel')}</p>
                        <p className="text-xs text-secondary line-clamp-2">
                          {room.amenities || t('meetings.table.noAmenities')}
                        </p>
                      </div>

                      {room.ghi_chu && (
                        <p className="text-[11px] text-muted italic bg-surface-elevated px-2 py-1 rounded">
                          * {room.ghi_chu}
                        </p>
                      )}

                      {/* Trạng thái đặt phòng theo ô trực quan */}
                      <div className="mt-4 pt-3 border-t border-border-subtle space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-secondary uppercase tracking-wider text-[11px] flex items-center gap-1.5">
                            <i className="fa-regular fa-calendar-days text-primary text-xs" />
                            {t('meetings.today')}:
                          </span>
                          {roomBookingsToday.length > 0 ? (
                            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-warning-subtle text-warning-text border border-warning/40 flex items-center gap-1.5 shadow-xs">
                              <i className="fa-solid fa-calendar-check text-[10px] text-warning" />
                              {t('meetings.roomBookedToday', { count: roomBookingsToday.length })}
                            </span>
                          ) : (
                            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-success-subtle text-success border border-success/30 flex items-center gap-1">
                              <i className="fa-regular fa-calendar-check text-[10px]" />
                              {t('meetings.noBookingsToday')}
                            </span>
                          )}
                        </div>

                        {roomBookingsToday.length > 0 ? (
                          <div className="space-y-2 max-h-40 overflow-y-auto pr-0.5">
                            {roomBookingsToday.map((b) => {
                              const isCurrentMeeting = b.date === selectedDate && b.start_time.slice(0, 5) <= currentTimeStr && currentTimeStr < b.end_time.slice(0, 5);
                              const timeRange = `${b.start_time.slice(0, 5)} - ${b.end_time.slice(0, 5)}`;

                              return (
                                <button
                                  key={b.id}
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedBookingDetail(b);
                                  }}
                                  className={`w-full text-left p-2.5 rounded-xl border flex items-center justify-between gap-2.5 group transition-all cursor-pointer shadow-xs ${
                                    isCurrentMeeting
                                      ? 'bg-danger-subtle/40 hover:bg-danger-subtle/70 border-l-4 border-l-danger border-danger/40'
                                      : 'bg-warning-subtle/35 hover:bg-warning-subtle/60 border-l-4 border-l-warning border-warning/35'
                                  }`}
                                  title={t('meetings.viewDetailBtn')}
                                >
                                  <div className="min-w-0 flex-1 space-y-1">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-black shadow-2xs border ${
                                        isCurrentMeeting
                                          ? 'bg-surface text-danger border-danger/30'
                                          : 'bg-surface text-warning-text border-warning/30'
                                      }`}>
                                        <i className={`fa-solid fa-clock text-[10px] ${isCurrentMeeting ? 'text-danger' : 'text-warning'}`} />
                                        <span>{timeRange}</span>
                                      </span>

                                      <span className={`text-[10px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded ${
                                        isCurrentMeeting
                                          ? 'bg-danger text-white flex items-center gap-1'
                                          : 'bg-warning/20 text-warning-text'
                                      }`}>
                                        {isCurrentMeeting && <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />}
                                        {isCurrentMeeting ? t('meetings.inProgress') : t('meetings.bookedBadge')}
                                      </span>
                                    </div>

                                    <p className="text-xs font-bold text-main truncate group-hover:text-primary transition-colors">
                                      {b.title}
                                    </p>
                                    <p className="text-[11px] text-muted flex items-center gap-1">
                                      <i className="fa-solid fa-user-tie text-[10px]" />
                                      <span className="truncate">{b.organizer_detail?.ho_ten || b.organizer_detail?.username || t('meetings.table.staffFallback')}</span>
                                    </p>
                                  </div>

                                  <span className={`text-xs font-bold p-1.5 rounded-lg bg-surface border group-hover:scale-110 transition-transform shadow-2xs ${
                                    isCurrentMeeting
                                      ? 'text-danger border-danger/30'
                                      : 'text-warning-text border-warning/30'
                                  }`}>
                                    <i className="fa-solid fa-circle-info" />
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        ) : isAvailable && canAddBooking ? (
                          <div className="p-2.5 rounded-xl bg-success-subtle/50 border border-success/20 text-center">
                            <p className="text-xs text-success font-semibold flex items-center justify-center gap-1.5">
                              <i className="fa-solid fa-calendar-plus" />
                              {t('meetings.bookDirectPrompt')}
                            </p>
                          </div>
                        ) : null}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="pt-4 mt-4 border-t border-border-subtle flex items-center justify-between">
                      {canAddBooking && isAvailable ? (
                        <Button
                          variant="primary"
                          size="sm"
                          icon="fa-calendar-plus"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedRoomForBooking(room.id);
                            setBookingToEdit(null);
                            setIsBookingModalOpen(true);
                          }}
                        >
                          {t('meetings.table.bookThisRoom')}
                        </Button>
                      ) : <div />}

                      {(canChangeRoom || canDeleteRoom) && (
                        <div className="flex items-center gap-1.5">
                          {canChangeRoom && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                setRoomToEdit(room);
                                setIsRoomModalOpen(true);
                              }}
                              title={t('meetings.actions.edit')}
                            >
                              <i className="fa-solid fa-pen-to-square text-secondary hover:text-main" />
                            </Button>
                          )}
                          {canDeleteRoom && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeletingRoom(room);
                              }}
                              title={t('meetings.actions.delete')}
                            >
                              <i className="fa-solid fa-trash-can text-danger hover:opacity-80" />
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Modal Đặt lịch */}
      <BookingModal
        isOpen={isBookingModalOpen}
        onClose={() => {
          setIsBookingModalOpen(false);
          setBookingToEdit(null);
          setSelectedRoomForBooking(null);
        }}
        onSuccess={() => {
          showToast('success', bookingToEdit ? t('meetings.messages.updateBookingSuccess') : t('meetings.messages.saveBookingSuccess'));
          setReloadBookingsTrigger((prev) => prev + 1);
        }}
        rooms={rooms}
        bookingToEdit={bookingToEdit}
        initialDate={selectedDate}
        initialRoomId={selectedRoomForBooking}
        currentUser={currentUser}
        existingBookings={bookings}
      />

      {/* Modal Xem chi tiết cuộc họp */}
      <MeetingDetailModal
        isOpen={Boolean(selectedBookingDetail)}
        onClose={() => setSelectedBookingDetail(null)}
        booking={selectedBookingDetail}
        room={selectedBookingDetail ? rooms.find((r) => r.id === selectedBookingDetail.room) : null}
        canModify={Boolean(
          selectedBookingDetail && (
            (currentUser && selectedBookingDetail.organizer === currentUser.id && canChangeOwnBooking) ||
            canChangeAnyBooking
          )
        )}
        onEdit={(b) => {
          setSelectedBookingDetail(null);
          setBookingToEdit(b);
          setIsBookingModalOpen(true);
        }}
        onCancel={(b) => {
          setSelectedBookingDetail(null);
          setCancellingBooking(b);
          setCancelReason('');
        }}
      />

      {/* Modal Thêm/Sửa phòng họp */}
      <RoomModal
        isOpen={isRoomModalOpen}
        onClose={() => {
          setIsRoomModalOpen(false);
          setRoomToEdit(null);
        }}
        onSuccess={() => {
          showToast('success', roomToEdit ? t('meetings.messages.updateRoomSuccess') : t('meetings.messages.saveRoomSuccess'));
          setReloadRoomsTrigger((prev) => prev + 1);
        }}
        roomToEdit={roomToEdit}
      />

      {/* Modal Xác nhận hủy lịch đặt */}
      {cancellingBooking && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cancel-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fadeIn"
        >
          <div className="bg-surface border border-border-subtle rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-danger">
              <div className="w-10 h-10 rounded-xl bg-danger-subtle flex items-center justify-center font-bold text-lg">
                <i className="fa-solid fa-triangle-exclamation" />
              </div>
              <div>
                <h3 id="cancel-modal-title" className="text-base font-bold text-main">
                  {t('meetings.modalCancel.title')}
                </h3>
                <p className="text-xs text-muted">{t('meetings.modalCancel.subtitle')}</p>
              </div>
            </div>

            <p className="text-sm text-secondary">
              {t('meetings.modalCancel.desc', { title: cancellingBooking.title })}
            </p>

            <div>
              <label className="block text-xs font-bold text-secondary mb-1">
                {t('meetings.modalCancel.reasonLabel')}
              </label>
              <textarea
                rows={2}
                placeholder={t('meetings.modalCancel.reasonPlaceholder')}
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-border-subtle text-main text-xs focus:outline-none focus:ring-2 focus:ring-danger"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setCancellingBooking(null)}
                disabled={isSubmittingCancel}
              >
                {t('meetings.modalCancel.closeBtn')}
              </Button>
              <Button
                variant="danger"
                size="sm"
                isLoading={isSubmittingCancel}
                onClick={handleConfirmCancelBooking}
              >
                {t('meetings.modalCancel.confirmBtn')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Xác nhận xóa phòng họp */}
      {deletingRoom && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-room-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fadeIn"
        >
          <div className="bg-surface border border-border-subtle rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-danger">
              <div className="w-10 h-10 rounded-xl bg-danger-subtle flex items-center justify-center font-bold text-lg">
                <i className="fa-solid fa-trash-can" />
              </div>
              <div>
                <h3 id="delete-room-modal-title" className="text-base font-bold text-main">
                  {t('meetings.modalDeleteRoom.title')}
                </h3>
                <p className="text-xs text-muted">{t('meetings.modalDeleteRoom.subtitle')}</p>
              </div>
            </div>

            <p className="text-sm text-secondary">
              {t('meetings.modalDeleteRoom.desc', { name: deletingRoom.name })}
            </p>
            <p className="text-xs text-warning-text bg-warning-subtle p-2.5 rounded-lg border border-warning-border">
              <i className="fa-solid fa-circle-info mr-1" />
              {t('meetings.modalDeleteRoom.warning')}
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setDeletingRoom(null)}
                disabled={isSubmittingDelete}
              >
                {t('meetings.modalDeleteRoom.closeBtn')}
              </Button>
              <Button
                variant="danger"
                size="sm"
                isLoading={isSubmittingDelete}
                onClick={handleConfirmDeleteRoom}
              >
                {t('meetings.modalDeleteRoom.confirmBtn')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MeetingsPage;
