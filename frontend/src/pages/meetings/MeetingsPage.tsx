import React, { useState, useEffect } from 'react';
import { MeetingRoom, MeetingBooking, BookingUser } from '@app-types/meeting';
import { apiClient, ApiError } from '@lib/apiClient';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';
import { Card } from '@components/common/Card';
import { BookingModal } from '@components/meetings/BookingModal';
import { RoomModal } from '@components/meetings/RoomModal';

interface PaginatedResponse<T> {
  count?: number;
  results?: T[];
}

interface UserProfileResponse {
  id: number;
  username: string;
  full_name?: string;
  department?: string;
  role?: string;
}

export const MeetingsPage: React.FC = () => {
  // Tab hiện tại: 'schedule' (Lịch đặt) | 'rooms' (Danh mục phòng)
  const [activeTab, setActiveTab] = useState<'schedule' | 'rooms'>('schedule');

  // Dữ liệu
  const [rooms, setRooms] = useState<MeetingRoom[]>([]);
  const [bookings, setBookings] = useState<MeetingBooking[]>([]);
  const [currentUser, setCurrentUser] = useState<BookingUser | null>(null);

  // Bộ lọc lịch
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [selectedRoomFilter, setSelectedRoomFilter] = useState<string>('all');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('all');

  // Bộ lọc danh mục phòng
  const [roomSearchTerm, setRoomSearchTerm] = useState('');
  const [roomStatusFilter, setRoomStatusFilter] = useState<string>('all');

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

  const [isRoomModalOpen, setIsRoomModalOpen] = useState(false);
  const [roomToEdit, setRoomToEdit] = useState<MeetingRoom | null>(null);

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
          full_name: res.full_name || res.username,
          department: res.department || '',
          role: res.role || 'staff',
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
              full_name: parsed.full_name || parsed.username || '',
              department: parsed.department || '',
              role: parsed.role || 'staff',
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
      url += `&room_id=${selectedRoomFilter}`;
    }
    if (selectedStatusFilter !== 'all') {
      url += `&status=${selectedStatusFilter}`;
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

  // Điều khiển ngày: Hôm nay, trước, sau
  const handleDateChange = (daysDelta: number) => {
    const current = new Date(selectedDate);
    current.setDate(current.getDate() + daysDelta);
    setSelectedDate(current.toISOString().split('T')[0]);
  };

  const handleSetToday = () => {
    setSelectedDate(new Date().toISOString().split('T')[0]);
  };

  // Xử lý Hủy lịch đặt
  const handleConfirmCancelBooking = async () => {
    if (!cancellingBooking) return;
    setIsSubmittingCancel(true);
    try {
      await apiClient.post(`/api/meeting-bookings/${cancellingBooking.id}/cancel/`, {
        ly_do_huy: cancelReason.trim(),
      });
      showToast('success', 'Đã hủy lịch đặt phòng họp thành công! Khung giờ đã được giải phóng.');
      setCancellingBooking(null);
      setCancelReason('');
      setReloadBookingsTrigger((prev) => prev + 1);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        showToast('error', err.message);
      } else {
        showToast('error', 'Không thể hủy lịch đặt phòng.');
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
      showToast('success', `Đã xóa phòng họp '${deletingRoom.ten_phong}' thành công.`);
      setDeletingRoom(null);
      setReloadRoomsTrigger((prev) => prev + 1);
      setReloadBookingsTrigger((prev) => prev + 1);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        showToast('error', err.message || (err.data?.error as string) || 'Không thể xóa phòng họp.');
      } else {
        showToast('error', 'Đã có lỗi xảy ra khi xóa phòng họp.');
      }
    } finally {
      setIsSubmittingDelete(false);
    }
  };

  const isAdmin = currentUser?.role === 'admin';

  // Lọc danh mục phòng ở Tab 2
  const filteredRooms = rooms.filter((r) => {
    const matchesSearch =
      r.ten_phong.toLowerCase().includes(roomSearchTerm.toLowerCase()) ||
      (r.vi_tri && r.vi_tri.toLowerCase().includes(roomSearchTerm.toLowerCase())) ||
      (r.thiet_bi && r.thiet_bi.toLowerCase().includes(roomSearchTerm.toLowerCase()));

    const matchesStatus =
      roomStatusFilter === 'all'
        ? true
        : roomStatusFilter === 'public'
        ? r.is_public
        : !r.is_public;

    return matchesSearch && matchesStatus;
  });

  // Thống kê nhanh trong ngày
  const totalInDay = bookings.length;
  const activeInDay = bookings.filter((b) => b.trang_thai === 'da_dat').length;
  const cancelledInDay = bookings.filter((b) => b.trang_thai === 'da_huy').length;
  const completedInDay = bookings.filter((b) => b.trang_thai === 'hoan_thanh').length;

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
            <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center font-bold text-xl shadow-sm">
              <i className="fa-solid fa-people-roof" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-main tracking-tight">Phân hệ Quản lý Phòng họp</h1>
              <p className="text-sm text-secondary">
                Xem lịch trực quan, giữ chỗ tự động và quản lý danh mục phòng họp ITC
              </p>
            </div>
          </div>
        </div>

        {/* Nút hành động */}
        <div className="flex items-center gap-3 flex-wrap">
          {activeTab === 'schedule' ? (
            <Button
              variant="primary"
              icon="fa-calendar-plus"
              onClick={() => {
                setBookingToEdit(null);
                setIsBookingModalOpen(true);
              }}
            >
              Đặt phòng họp mới
            </Button>
          ) : (
            isAdmin && (
              <Button
                variant="primary"
                icon="fa-plus"
                onClick={() => {
                  setRoomToEdit(null);
                  setIsRoomModalOpen(true);
                }}
              >
                Thêm phòng họp mới
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
              ? 'text-primary border-primary bg-primary/5'
              : 'text-secondary border-transparent hover:text-main hover:bg-surface-elevated/40'
          }`}
        >
          <i className="fa-regular fa-calendar-days text-base" />
          <span>Lịch đặt phòng họp theo ngày</span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-primary/10 text-primary font-semibold">
            {activeInDay}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('rooms')}
          className={`flex items-center gap-2.5 px-5 py-3 font-bold text-sm rounded-t-xl transition-all border-b-2 ${
            activeTab === 'rooms'
              ? 'text-primary border-primary bg-primary/5'
              : 'text-secondary border-transparent hover:text-main hover:bg-surface-elevated/40'
          }`}
        >
          <i className="fa-solid fa-door-open text-base" />
          <span>Danh mục phòng họp</span>
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
                <p className="text-xs font-bold text-muted uppercase tracking-wider">Tổng cuộc họp</p>
                <p className="text-2xl font-black text-main mt-1">{totalInDay}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <i className="fa-solid fa-calendar-check text-lg" />
              </div>
            </Card>

            <Card className="p-4 bg-surface flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-muted uppercase tracking-wider">Có hiệu lực</p>
                <p className="text-2xl font-black text-success mt-1">{activeInDay}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-success/10 text-success flex items-center justify-center">
                <i className="fa-solid fa-clock text-lg" />
              </div>
            </Card>

            <Card className="p-4 bg-surface flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-muted uppercase tracking-wider">Đã hoàn thành</p>
                <p className="text-2xl font-black text-secondary mt-1">{completedInDay}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-surface-elevated text-secondary flex items-center justify-center">
                <i className="fa-solid fa-circle-check text-lg" />
              </div>
            </Card>

            <Card className="p-4 bg-surface flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-muted uppercase tracking-wider">Đã hủy</p>
                <p className="text-2xl font-black text-danger mt-1">{cancelledInDay}</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-danger/10 text-danger flex items-center justify-center">
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
                title="Ngày trước"
              >
                <i className="fa-solid fa-chevron-left" />
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleSetToday}
                className="font-bold"
              >
                Hôm nay
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleDateChange(1)}
                title="Ngày sau"
              >
                <i className="fa-solid fa-chevron-right" />
              </Button>

              <div className="relative flex items-center">
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-border-subtle text-main font-bold text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 cursor-pointer"
                />
              </div>
            </div>

            {/* Bộ lọc phòng & Trạng thái */}
            <div className="flex items-center gap-3 w-full md:w-auto flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-secondary">Phòng:</span>
                <select
                  value={selectedRoomFilter}
                  onChange={(e) => setSelectedRoomFilter(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-border-subtle text-main text-xs font-bold focus:outline-none focus:ring-2 focus:ring-primary/40 cursor-pointer"
                >
                  <option value="all">Tất cả các phòng</option>
                  {rooms.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.ten_phong}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-secondary">Trạng thái:</span>
                <select
                  value={selectedStatusFilter}
                  onChange={(e) => setSelectedStatusFilter(e.target.value)}
                  className="px-3 py-1.5 rounded-lg bg-surface-elevated border border-border-subtle text-main text-xs font-bold focus:outline-none focus:ring-2 focus:ring-primary/40 cursor-pointer"
                >
                  <option value="all">Tất cả trạng thái</option>
                  <option value="da_dat">Đã đặt (Hiệu lực)</option>
                  <option value="hoan_thanh">Đã hoàn thành</option>
                  <option value="da_huy">Đã hủy (Giải phóng)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Booking List Container */}
          {loadingBookings ? (
            <div className="bg-surface rounded-2xl border border-border-subtle p-12 text-center text-muted">
              <i className="fa-solid fa-spinner fa-spin text-3xl text-primary mb-3" />
              <p className="text-sm font-medium">Đang tải lịch đặt phòng họp...</p>
            </div>
          ) : bookings.length === 0 ? (
            <div className="bg-surface rounded-2xl border border-border-subtle p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-surface-elevated mx-auto flex items-center justify-center text-muted text-2xl mb-4">
                <i className="fa-regular fa-calendar-xmark" />
              </div>
              <h3 className="text-base font-bold text-main">Không có lịch đặt phòng họp</h3>
              <p className="text-xs text-muted max-w-sm mx-auto mt-1 mb-5">
                Chưa có cuộc họp nào được đăng ký trong ngày{' '}
                <span className="font-semibold text-main">
                  {new Date(selectedDate).toLocaleDateString('vi-VN')}
                </span>
                . Bạn có thể bấm nút dưới đây để giữ chỗ.
              </p>
              <Button
                variant="primary"
                icon="fa-calendar-plus"
                onClick={() => {
                  setBookingToEdit(null);
                  setIsBookingModalOpen(true);
                }}
              >
                Đặt phòng ngay
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {bookings.map((booking) => {
                const start = new Date(booking.thoi_gian_bat_dau);
                const end = new Date(booking.thoi_gian_ket_thuc);
                const timeRangeStr = `${start.toLocaleTimeString('vi-VN', {
                  hour: '2-digit',
                  minute: '2-digit',
                })} - ${end.toLocaleTimeString('vi-VN', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}`;

                const isOwner = currentUser && booking.nguoi_dat === currentUser.id;
                const canModify = isOwner || isAdmin;

                return (
                  <Card
                    key={booking.id}
                    hoverable
                    className={`p-5 transition-all ${
                      booking.trang_thai === 'da_huy'
                        ? 'opacity-70 bg-surface-elevated/30 border-dashed'
                        : 'border-l-4 border-l-primary'
                    }`}
                  >
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                      {/* Cột trái: Khung giờ & Tên phòng */}
                      <div className="flex items-start gap-4">
                        <div className="w-24 shrink-0 text-center bg-surface-elevated p-2.5 rounded-xl border border-border-subtle">
                          <p className="text-xs font-bold text-primary">{timeRangeStr}</p>
                          <p className="text-[10px] text-muted mt-0.5">
                            {start.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })}
                          </p>
                        </div>

                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-black text-base text-main">{booking.tieu_de}</span>
                            {booking.trang_thai === 'da_dat' && (
                              <Badge variant="success" size="sm" withDot>
                                Đã giữ chỗ
                              </Badge>
                            )}
                            {booking.trang_thai === 'hoan_thanh' && (
                              <Badge variant="secondary" size="sm">
                                Đã hoàn thành
                              </Badge>
                            )}
                            {booking.trang_thai === 'da_huy' && (
                              <Badge variant="danger" size="sm" withDot>
                                Đã hủy
                              </Badge>
                            )}
                          </div>

                          {/* Thông tin phòng & Người đặt */}
                          <div className="flex items-center gap-4 text-xs text-secondary flex-wrap pt-1">
                            <span className="flex items-center gap-1.5 font-bold text-primary">
                              <i className="fa-solid fa-door-open" />
                              {booking.phong_hop_detail?.ten_phong || `Phòng #${booking.phong_hop}`}
                              {booking.phong_hop_detail?.vi_tri && ` (${booking.phong_hop_detail.vi_tri})`}
                            </span>

                            <span className="flex items-center gap-1.5">
                              <i className="fa-solid fa-user-tie text-muted" />
                              Người đặt:{' '}
                              <strong className="text-main font-semibold">
                                {booking.nguoi_dat_detail?.full_name || booking.nguoi_dat_detail?.username || 'CBNV'}
                              </strong>
                            </span>

                            {booking.don_vi_to_chuc && (
                              <span className="flex items-center gap-1.5">
                                <i className="fa-solid fa-building text-muted" />
                                Đơn vị: {booking.don_vi_to_chuc}
                              </span>
                            )}

                            <span className="flex items-center gap-1.5">
                              <i className="fa-solid fa-users text-muted" />
                              Tham gia: {booking.so_nguoi_tham_gia} người
                            </span>
                          </div>

                          {booking.ghi_chu && (
                            <p className="text-xs text-muted bg-surface-elevated/50 px-2.5 py-1.5 rounded-lg border border-border-subtle mt-2 inline-block">
                              <i className="fa-regular fa-note-sticky mr-1.5" />
                              {booking.ghi_chu}
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Cột phải: Thao tác */}
                      {booking.trang_thai !== 'da_huy' && canModify && (
                        <div className="flex items-center gap-2 self-end lg:self-center">
                          <Button
                            variant="secondary"
                            size="sm"
                            icon="fa-pen-to-square"
                            onClick={() => {
                              setBookingToEdit(booking);
                              setIsBookingModalOpen(true);
                            }}
                          >
                            Sửa
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
                            Hủy lịch
                          </Button>
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
                  placeholder="Tìm phòng theo tên, vị trí, thiết bị..."
                  value={roomSearchTerm}
                  onChange={(e) => setRoomSearchTerm(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-surface-elevated border border-border-subtle text-main placeholder:text-muted text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <select
                value={roomStatusFilter}
                onChange={(e) => setRoomStatusFilter(e.target.value)}
                className="px-3.5 py-2 rounded-xl bg-surface-elevated border border-border-subtle text-main text-xs font-bold focus:outline-none focus:ring-2 focus:ring-primary/40 cursor-pointer"
              >
                <option value="all">Tất cả trạng thái</option>
                <option value="public">Đang hoạt động (Công khai)</option>
                <option value="hidden">Tạm ẩn (Bảo trì/Khóa)</option>
              </select>
            </div>
          </div>

          {/* Grid Rooms */}
          {loadingRooms ? (
            <div className="bg-surface rounded-2xl border border-border-subtle p-12 text-center text-muted">
              <i className="fa-solid fa-spinner fa-spin text-3xl text-primary mb-3" />
              <p className="text-sm font-medium">Đang tải danh mục phòng họp...</p>
            </div>
          ) : filteredRooms.length === 0 ? (
            <div className="bg-surface rounded-2xl border border-border-subtle p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-surface-elevated mx-auto flex items-center justify-center text-muted text-2xl mb-4">
                <i className="fa-solid fa-door-closed" />
              </div>
              <h3 className="text-base font-bold text-main">Không tìm thấy phòng họp phù hợp</h3>
              <p className="text-xs text-muted max-w-sm mx-auto mt-1 mb-5">
                Thử thay đổi từ khóa tìm kiếm hoặc bấm nút bên dưới để tạo phòng mới.
              </p>
              {isAdmin && (
                <Button
                  variant="primary"
                  icon="fa-plus"
                  onClick={() => {
                    setRoomToEdit(null);
                    setIsRoomModalOpen(true);
                  }}
                >
                  Thêm phòng họp
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {filteredRooms.map((room) => (
                <Card key={room.id} hoverable className="p-5 flex flex-col justify-between h-full">
                  <div>
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div>
                        <h3 className="text-base font-bold text-main">{room.ten_phong}</h3>
                        <p className="text-xs text-muted flex items-center gap-1.5 mt-0.5">
                          <i className="fa-solid fa-location-dot text-primary" />
                          {room.vi_tri || 'Chưa cập nhật vị trí'}
                        </p>
                      </div>
                      {room.is_public ? (
                        <Badge variant="success" size="sm" withDot>
                          Hoạt động
                        </Badge>
                      ) : (
                        <Badge variant="secondary" size="sm">
                          Tạm ẩn
                        </Badge>
                      )}
                    </div>

                    {/* Sức chứa */}
                    <div className="p-3 rounded-xl bg-surface-elevated/60 border border-border-subtle mb-3 flex items-center justify-between">
                      <span className="text-xs text-secondary font-medium">Sức chứa tối đa:</span>
                      <span className="text-sm font-black text-primary flex items-center gap-1">
                        <i className="fa-solid fa-users text-xs" />
                        {room.suc_chua} người
                      </span>
                    </div>

                    {/* Thiết bị */}
                    <div className="space-y-1 mb-4">
                      <p className="text-[11px] font-bold text-muted uppercase tracking-wider">Trang thiết bị:</p>
                      <p className="text-xs text-secondary line-clamp-2">
                        {room.thiet_bi || 'Chưa có thông tin trang thiết bị'}
                      </p>
                    </div>

                    {room.ghi_chu && (
                      <p className="text-[11px] text-muted italic bg-surface-elevated px-2 py-1 rounded">
                        * {room.ghi_chu}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="pt-4 mt-4 border-t border-border-subtle flex items-center justify-between">
                    <Button
                      variant="outline"
                      size="sm"
                      icon="fa-calendar-plus"
                      onClick={() => {
                        setSelectedRoomFilter(String(room.id));
                        setActiveTab('schedule');
                        setIsBookingModalOpen(true);
                      }}
                    >
                      Đặt phòng này
                    </Button>

                    {isAdmin && (
                      <div className="flex items-center gap-1.5">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setRoomToEdit(room);
                            setIsRoomModalOpen(true);
                          }}
                          title="Sửa thông tin phòng"
                        >
                          <i className="fa-solid fa-pen-to-square text-secondary hover:text-main" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeletingRoom(room)}
                          title="Xóa phòng"
                        >
                          <i className="fa-solid fa-trash-can text-danger/80 hover:text-danger" />
                        </Button>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
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
        }}
        onSuccess={() => {
          showToast('success', bookingToEdit ? 'Đã cập nhật lịch đặt phòng!' : 'Đặt phòng họp thành công!');
          setReloadBookingsTrigger((prev) => prev + 1);
        }}
        rooms={rooms}
        bookingToEdit={bookingToEdit}
        initialDate={selectedDate}
        currentUser={currentUser}
      />

      {/* Modal Thêm/Sửa phòng họp */}
      <RoomModal
        isOpen={isRoomModalOpen}
        onClose={() => {
          setIsRoomModalOpen(false);
          setRoomToEdit(null);
        }}
        onSuccess={() => {
          showToast('success', roomToEdit ? 'Đã cập nhật phòng họp!' : 'Tạo phòng họp mới thành công!');
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
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn"
        >
          <div className="bg-surface border border-border-subtle rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-danger">
              <div className="w-10 h-10 rounded-xl bg-danger/10 flex items-center justify-center font-bold text-lg">
                <i className="fa-solid fa-triangle-exclamation" />
              </div>
              <div>
                <h3 id="cancel-modal-title" className="text-base font-bold text-main">
                  Xác nhận hủy lịch họp
                </h3>
                <p className="text-xs text-muted">Hành động này sẽ giải phóng khung giờ</p>
              </div>
            </div>

            <p className="text-sm text-secondary">
              Bạn có chắc chắn muốn hủy cuộc họp:{' '}
              <strong className="text-main font-semibold">'{cancellingBooking.tieu_de}'</strong>?
            </p>

            <div>
              <label className="block text-xs font-bold text-secondary mb-1">
                Lý do hủy lịch:
              </label>
              <textarea
                rows={2}
                placeholder="VD: Thay đổi lịch công tác, hoãn cuộc họp..."
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-surface-elevated border border-border-subtle text-main text-xs focus:outline-none focus:ring-2 focus:ring-danger/40"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setCancellingBooking(null)}
                disabled={isSubmittingCancel}
              >
                Giữ lại
              </Button>
              <Button
                variant="danger"
                size="sm"
                isLoading={isSubmittingCancel}
                onClick={handleConfirmCancelBooking}
              >
                Xác nhận hủy
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
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn"
        >
          <div className="bg-surface border border-border-subtle rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-danger">
              <div className="w-10 h-10 rounded-xl bg-danger/10 flex items-center justify-center font-bold text-lg">
                <i className="fa-solid fa-trash-can" />
              </div>
              <div>
                <h3 id="delete-room-modal-title" className="text-base font-bold text-main">
                  Xác nhận xóa phòng họp
                </h3>
                <p className="text-xs text-muted">Kiểm tra bảo toàn lịch sử đặt phòng</p>
              </div>
            </div>

            <p className="text-sm text-secondary">
              Bạn có chắc muốn xóa phòng họp{' '}
              <strong className="text-main font-semibold">'{deletingRoom.ten_phong}'</strong>?
            </p>
            <p className="text-xs text-warning-text bg-warning-subtle p-2.5 rounded-lg border border-warning-border">
              <i className="fa-solid fa-circle-info mr-1" />
              Nếu phòng đã từng có lịch đặt, hệ thống sẽ ngăn chặn xóa để bảo toàn dữ liệu lịch sử.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setDeletingRoom(null)}
                disabled={isSubmittingDelete}
              >
                Hủy bỏ
              </Button>
              <Button
                variant="danger"
                size="sm"
                isLoading={isSubmittingDelete}
                onClick={handleConfirmDeleteRoom}
              >
                Xóa phòng họp
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MeetingsPage;
