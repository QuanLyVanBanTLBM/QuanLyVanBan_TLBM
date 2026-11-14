import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MeetingsPage from './MeetingsPage';
import { apiClient } from '@lib/apiClient';

vi.mock('@lib/apiClient', () => {
  const getMock = vi.fn();
  const postMock = vi.fn();
  const putMock = vi.fn();
  const deleteMock = vi.fn();

  const mockApi = vi.fn().mockImplementation((url: string) => getMock(url)) as unknown as {
    (endpoint: string, options?: RequestInit): Promise<unknown>;
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
    put: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
  };
  mockApi.get = getMock;
  mockApi.post = postMock;
  mockApi.put = putMock;
  mockApi.delete = deleteMock;

  return {
    apiClient: mockApi,
    default: mockApi,
    ApiError: class ApiError extends Error {
      status: number;
      data: Record<string, unknown>;
      constructor(status: number, data: Record<string, unknown>) {
        super((data.error as string) || (data.detail as string) || 'API Error');
        this.status = status;
        this.data = data;
      }
    },
  };
});

describe('MeetingsPage Component (Issue #22)', () => {
  const mockRooms = [
    {
      id: 1,
      name: 'Phòng Hội thảo A',
      location: 'Tầng 2, Tòa A',
      capacity: 30,
      amenities: 'Máy chiếu 4K, 2 Micro không dây',
      is_public: true,
      trang_thai: 'AVAILABLE',
      ghi_chu: '',
      created_at: '2026-09-20T08:00:00Z',
      updated_at: '2026-09-20T08:00:00Z',
    },
    {
      id: 2,
      name: 'Phòng Họp B',
      location: 'Tầng 3, Tòa B',
      capacity: 10,
      amenities: 'Bảng trắng',
      is_public: false,
      trang_thai: 'MAINTENANCE',
      ghi_chu: 'Bảo trì',
      created_at: '2026-09-20T08:00:00Z',
      updated_at: '2026-09-20T08:00:00Z',
    },
  ];

  const mockBookings = [
    {
      id: 101,
      room: 1,
      room_detail: mockRooms[0],
      organizer: 1,
      organizer_detail: {
        id: 1,
        username: 'hieu_staff',
        ho_ten: 'Nguyễn Phan Minh Hiệu',
        don_vi_ten: 'Phòng Hành chính - Tổng hợp',
        chuc_vu_ten: 'Chuyên viên',
      },
      department: 1,
      department_name: 'Phòng Hành chính - Tổng hợp',
      title: 'Họp giao ban tuần 40',
      date: '2026-09-23',
      start_time: '09:00:00',
      end_time: '10:30:00',
      attendees_count: 15,
      trang_thai: 'CONFIRMED',
      purpose: 'Chuẩn bị micro và trà nước',
      created_at: '2026-09-22T08:00:00Z',
    },
  ];

  const mockProfile = {
    id: 1,
    username: 'hieu_staff',
    full_name: 'Nguyễn Phan Minh Hiệu',
    department: 'Phòng Hành chính - Tổng hợp',
    role: 'admin',
  };

  const getMockFn = () => apiClient.get as unknown as ReturnType<typeof vi.fn>;
  const postMockFn = () => apiClient.post as unknown as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    getMockFn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/profile/')) {
        return Promise.resolve(mockProfile);
      }
      if (url.includes('/api/auth/me/permissions/')) {
        return Promise.resolve({
          is_superuser: true,
          permissions: [
            'add_phonghop',
            'change_phonghop',
            'delete_phonghop',
            'add_datphonghop',
            'change_own_datphonghop',
            'change_any_datphonghop',
          ],
        });
      }
      if (url.includes('/api/meeting-rooms/')) {
        return Promise.resolve({ results: mockRooms, count: 2 });
      }
      if (url.includes('/api/meeting-bookings/')) {
        return Promise.resolve({ results: mockBookings, count: 1 });
      }
      return Promise.resolve({});
    });
  });

  it('renders page header and rooms tab by default', async () => {
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    expect(screen.getByText('Phân hệ Quản lý Phòng họp')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Phòng Hội thảo A')).toBeInTheDocument();
      expect(screen.getByText('Phòng Họp B')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Tìm phòng theo tên, vị trí, thiết bị...')).toBeInTheDocument();
    });
  });

  it('switches between Rooms tab and Schedule tab', async () => {
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Phòng Hội thảo A')).toBeInTheDocument();
    });
    // Switch to Lịch đặt phòng họp
    const scheduleTabBtn = screen.getByText('Lịch đặt phòng họp theo ngày');
    fireEvent.click(scheduleTabBtn);
    await waitFor(() => {
      expect(screen.getByText('Họp giao ban tuần 40')).toBeInTheDocument();
    });
    // Switch back to Danh mục phòng họp
    const roomsTabBtn = screen.getByText('Danh mục phòng họp');
    fireEvent.click(roomsTabBtn);
    await waitFor(() => {
      expect(screen.getByText('Phòng Hội thảo A')).toBeInTheDocument();
      expect(screen.getByText('Phòng Họp B')).toBeInTheDocument();
    });
  });

  it('opens and closes booking modal when clicking "Đặt phòng họp mới"', async () => {
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    // Chuyển sang Tab Lịch đặt phòng họp
    fireEvent.click(screen.getByText('Lịch đặt phòng họp theo ngày'));
    const openBtn = await screen.findByText('Đặt phòng họp mới');
    fireEvent.click(openBtn);
    await waitFor(() => {
      expect(screen.getByText('Điền thông tin khung giờ và nội dung cuộc họp để khóa phòng')).toBeInTheDocument();
    });
    const closeBtn = screen.getByText('Hủy bỏ');
    fireEvent.click(closeBtn);
    await waitFor(() => {
      expect(
        screen.queryByText('Điền thông tin khung giờ và nội dung cuộc họp để khóa phòng')
      ).not.toBeInTheDocument();
    });
  });

  it('displays empty state when there are no bookings on the selected date', async () => {
    getMockFn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/profile/')) return Promise.resolve(mockProfile);
      if (url.includes('/api/auth/me/permissions/')) return Promise.resolve({ is_superuser: true, permissions: ['add_datphonghop'] });
      if (url.includes('/api/meeting-rooms/')) return Promise.resolve({ results: mockRooms, count: 2 });
      if (url.includes('/api/meeting-bookings/')) return Promise.resolve({ results: [], count: 0 });
      return Promise.resolve({});
    });
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    // Chuyển sang Tab Lịch đặt phòng họp
    fireEvent.click(screen.getByText('Lịch đặt phòng họp theo ngày'));
    await waitFor(() => {
      expect(screen.getByText('Không có lịch đặt phòng họp')).toBeInTheDocument();
      expect(screen.getByText('Đặt phòng ngay')).toBeInTheDocument();
    });
  });

  it('allows opening cancel confirmation modal and calls cancel API', async () => {
    postMockFn().mockResolvedValueOnce({ detail: 'Hủy thành công' });
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    // Chuyển sang Tab Lịch đặt phòng họp
    fireEvent.click(screen.getByText('Lịch đặt phòng họp theo ngày'));
    await waitFor(() => {
      expect(screen.getByText('Họp giao ban tuần 40')).toBeInTheDocument();
    });
    const cancelBtn = screen.getByText('Hủy lịch');
    fireEvent.click(cancelBtn);
    await waitFor(() => {
      expect(screen.getByText('Xác nhận hủy lịch họp')).toBeInTheDocument();
    });
    const confirmCancelBtn = screen.getByText('Xác nhận hủy');
    fireEvent.click(confirmCancelBtn);
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/meeting-bookings/101/cancel/',
        expect.objectContaining({ cancel_reason: '' })
      );
    });
  });

  it('hides Edit and Cancel action buttons for completed bookings', async () => {
    const completedBooking = {
      ...mockBookings[0],
      id: 102,
      trang_thai: 'COMPLETED',
      date: '2026-09-20',
      start_time: '08:00:00',
      end_time: '09:00:00',
    };
    getMockFn().mockImplementation((url: string) => {
      if (url.includes('/api/auth/profile/')) return Promise.resolve(mockProfile);
      if (url.includes('/api/auth/me/permissions/')) {
        return Promise.resolve({
          is_superuser: true,
          permissions: ['add_phonghop', 'change_phonghop', 'change_any_datphonghop'],
        });
      }
      if (url.includes('/api/meeting-rooms/')) return Promise.resolve({ results: mockRooms, count: 2 });
      if (url.includes('/api/meeting-bookings/')) return Promise.resolve({ results: [completedBooking], count: 1 });
      return Promise.resolve({});
    });
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    // Chuyển sang Tab Lịch đặt phòng họp
    fireEvent.click(screen.getByText('Lịch đặt phòng họp theo ngày'));
    await waitFor(() => {
      expect(screen.getByText('Họp giao ban tuần 40')).toBeInTheDocument();
    });
    // For completed bookings, neither "Chỉnh sửa" nor "Hủy lịch" buttons should be rendered
    expect(screen.queryByText('Hủy lịch')).not.toBeInTheDocument();
    expect(screen.queryByText('Chỉnh sửa')).not.toBeInTheDocument();
  });

  it('phòng MAINTENANCE hiện đúng huy hiệu Bảo trì và không có nút Đặt phòng này', async () => {
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Họp giao ban tuần 40')).toBeInTheDocument();
    });
    // Chuyển sang Tab Danh mục phòng họp
    const roomsTabBtn = screen.getByText('Danh mục phòng họp');
    fireEvent.click(roomsTabBtn);
    await waitFor(() => {
      expect(screen.getByText('Phòng Hội thảo A')).toBeInTheDocument();
      expect(screen.getByText('Phòng Họp B')).toBeInTheDocument();
    });
    // Thẻ Phòng 1 (AVAILABLE): có huy hiệu "Sẵn sàng" và nút "Đặt phòng này"
    const room1Title = screen.getByText('Phòng Hội thảo A');
    const room1Card = room1Title.closest('.p-5');
    expect(room1Card).toHaveTextContent('Sẵn sàng');
    expect(room1Card).toHaveTextContent('Đặt phòng này');
    // Thẻ Phòng 2 (MAINTENANCE): có huy hiệu "Bảo trì" và KHÔNG có nút "Đặt phòng này"
    const room2Title = screen.getByText('Phòng Họp B');
    const room2Card = room2Title.closest('.p-5');
    expect(room2Card).toHaveTextContent('Bảo trì');
    expect(room2Card).not.toHaveTextContent('Đặt phòng này');
    // Toàn bộ trang chỉ có 1 nút "Đặt phòng này"
    const bookButtons = screen.getAllByText('Đặt phòng này');
    expect(bookButtons).toHaveLength(1);
  });

  it('lọc danh sách phòng theo tầng (floor filter) chính xác', async () => {
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    // Chuyển sang Tab Danh mục phòng họp
    fireEvent.click(screen.getByText('Danh mục phòng họp'));
    await waitFor(() => {
      expect(screen.getByText('Phòng Hội thảo A')).toBeInTheDocument();
      expect(screen.getByText('Phòng Họp B')).toBeInTheDocument();
    });
    // Tìm select lọc tầng
    const floorSelects = screen.getAllByRole('combobox');
    const floorSelect = floorSelects[0]; // Filter combobox in Rooms tab
    expect(floorSelect).toBeInTheDocument();
    // Lọc theo Tầng 2
    fireEvent.change(floorSelect, { target: { value: 'Tầng 2' } });
    expect(screen.getByText('Phòng Hội thảo A')).toBeInTheDocument();
    expect(screen.queryByText('Phòng Họp B')).not.toBeInTheDocument();
    // Lọc theo Tầng 3
    fireEvent.change(floorSelect, { target: { value: 'Tầng 3' } });
    expect(screen.queryByText('Phòng Hội thảo A')).not.toBeInTheDocument();
    expect(screen.getByText('Phòng Họp B')).toBeInTheDocument();
    // Reset về Tất cả các tầng
    fireEvent.change(floorSelect, { target: { value: 'all' } });
    expect(screen.getByText('Phòng Hội thảo A')).toBeInTheDocument();
    expect(screen.getByText('Phòng Họp B')).toBeInTheDocument();
  });

  it('mở modal chi tiết khi nhấn Xem chi tiết ở danh sách lịch đặt', async () => {
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    // Chuyển sang Tab Lịch đặt phòng họp
    fireEvent.click(screen.getByText('Lịch đặt phòng họp theo ngày'));
    await waitFor(() => {
      expect(screen.getByText('Họp giao ban tuần 40')).toBeInTheDocument();
    });
    const detailBtn = screen.getByText('Xem chi tiết');
    fireEvent.click(detailBtn);
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: 'Họp giao ban tuần 40' })).toBeInTheDocument();
      expect(screen.getByText('Chi tiết cuộc họp')).toBeInTheDocument();
    });
  });

  it('sắp xếp danh sách phòng họp theo Tầng tăng dần (Trệt -> Tầng 1 -> Tầng 2 -> ...)', async () => {
    const unsortedRooms = [
      {
        id: 10,
        name: 'Phòng VIP 601',
        location: 'Tầng 6, Tòa Nhà A',
        capacity: 20,
        amenities: '',
        is_public: true,
        trang_thai: 'AVAILABLE',
        ghi_chu: '',
      },
      {
        id: 11,
        name: 'Phòng Hội thảo G',
        location: 'Tầng trệt',
        capacity: 50,
        amenities: '',
        is_public: true,
        trang_thai: 'AVAILABLE',
        ghi_chu: '',
      },
      {
        id: 12,
        name: 'Phòng 201',
        location: 'Tầng 2, Tòa Nhà B',
        capacity: 15,
        amenities: '',
        is_public: true,
        trang_thai: 'AVAILABLE',
        ghi_chu: '',
      },
      {
        id: 13,
        name: 'Phòng 102',
        location: 'Tầng 1',
        capacity: 10,
        amenities: '',
        is_public: true,
        trang_thai: 'AVAILABLE',
        ghi_chu: '',
      },
    ];
    apiClient.get = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/meeting-rooms/')) {
        return Promise.resolve({ results: unsortedRooms });
      }
      if (url.includes('/api/meeting-bookings/')) {
        return Promise.resolve({ results: [] });
      }
      if (url.includes('/api/auth/profile/')) {
        return Promise.resolve(mockProfile);
      }
      return Promise.resolve({});
    });
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText('Danh mục phòng họp'));
    await waitFor(() => {
      expect(screen.getByText('Phòng Hội thảo G')).toBeInTheDocument();
      expect(screen.getByText('Phòng 102')).toBeInTheDocument();
      expect(screen.getByText('Phòng 201')).toBeInTheDocument();
      expect(screen.getByText('Phòng VIP 601')).toBeInTheDocument();
    });
    const roomHeadings = screen.getAllByRole('heading', { level: 3 });
    const renderedRoomNames = roomHeadings.map((h) => h.textContent);
    expect(renderedRoomNames).toEqual([
      'Phòng Hội thảo G',
      'Phòng 102',
      'Phòng 201',
      'Phòng VIP 601',
    ]);
  });

  it('thẻ phòng ở Tab Danh mục luôn dùng lịch hôm nay (todayBookings), không dùng nhầm lịch ngày khác của tab Lịch', async () => {
    const singleRoom = [
      {
        id: 1,
        name: 'Phòng Hội Thảo A',
        location: 'Tầng 2, Tòa A',
        capacity: 30,
        amenities: 'Máy chiếu',
        is_public: true,
        trang_thai: 'AVAILABLE',
        ghi_chu: '',
      },
    ];
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    const tomorrowStr = `${tomorrow.getFullYear()}-${pad(tomorrow.getMonth() + 1)}-${pad(tomorrow.getDate())}`;
    const tomorrowBooking = [
      {
        id: 999,
        room: 1,
        room_detail: singleRoom[0],
        title: 'Họp ngày mai',
        date: tomorrowStr,
        start_time: '08:00:00',
        end_time: '18:00:00',
        attendees_count: 10,
        trang_thai: 'CONFIRMED',
      },
    ];
    apiClient.get = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/meeting-rooms/')) {
        return Promise.resolve({ results: singleRoom });
      }
      if (url.includes('/api/meeting-bookings/')) {
        // Phân biệt chính xác bằng tham số date=:
        // - Request lịch hôm nay (cho Tab Danh mục hoặc khi Tab 1 xem hôm nay): trả về [] (hôm nay không có lịch)
        if (url.includes(`date=${todayStr}`)) {
          return Promise.resolve({ results: [] });
        }
        // - Request lịch ngày khác (khi Tab 1 xem ngày mai): trả về có lịch
        return Promise.resolve({ results: tomorrowBooking });
      }
      if (url.includes('/api/auth/profile/')) {
        return Promise.resolve(mockProfile);
      }
      return Promise.resolve({});
    });
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    // 1. Chuyển sang Tab 1 (Lịch đặt phòng họp), chuyển bộ lọc ngày sang ngày mai
    fireEvent.click(screen.getByText('Lịch đặt phòng họp theo ngày'));
    const dateInput = screen.getByDisplayValue(todayStr);
    fireEvent.change(dateInput, { target: { value: tomorrowStr } });
    // 2. Chuyển sang Tab 2 (Danh mục phòng họp)
    fireEvent.click(screen.getByText('Danh mục phòng họp'));
    await waitFor(() => {
      expect(screen.getByText('Phòng Hội Thảo A')).toBeInTheDocument();
    });
    const roomTitle = screen.getByText('Phòng Hội Thảo A');
    const roomCard = roomTitle.closest('.p-5');
    // Hôm nay không có lịch => Thẻ phòng phải hiển thị Sẵn sàng & Trống lịch trong ngày,
    // tuyệt đối không dùng nhầm lịch ngày mai của Tab 1
    expect(roomCard).toHaveTextContent('Sẵn sàng');
    expect(roomCard).toHaveTextContent('Trống lịch trong ngày');
    expect(roomCard).not.toHaveTextContent('Có lịch trong ngày');
    expect(roomCard).not.toHaveTextContent('Đang họp');
  });

  it('thẻ phòng hiển thị đầy đủ Họ tên, Chức vụ và Phòng ban của người đặt lịch hôm nay', async () => {
    const singleRoom = [
      {
        id: 1,
        name: 'Phòng Hội Thảo A',
        location: 'Tầng 2, Tòa A',
        capacity: 30,
        amenities: 'Máy chiếu',
        is_public: true,
        trang_thai: 'AVAILABLE',
        ghi_chu: '',
      },
    ];
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    const todayBooking = [
      {
        id: 105,
        room: 1,
        room_detail: singleRoom[0],
        title: 'Họp thẩm định kiến trúc hệ thống',
        date: todayStr,
        start_time: '14:00:00',
        end_time: '15:30:00',
        attendees_count: 8,
        trang_thai: 'CONFIRMED',
        organizer: 5,
        organizer_detail: {
          id: 5,
          username: 'tranvanha',
          ho_ten: 'Trần Văn Hà',
          don_vi_ten: 'Ban Công nghệ Thông tin',
          chuc_vu_ten: 'Trưởng phòng QA',
        },
        department_name: 'Ban Công nghệ Thông tin',
      },
    ];
    apiClient.get = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/meeting-rooms/')) {
        return Promise.resolve({ results: singleRoom });
      }
      if (url.includes('/api/meeting-bookings/')) {
        return Promise.resolve({ results: todayBooking });
      }
      if (url.includes('/api/auth/profile/')) {
        return Promise.resolve(mockProfile);
      }
      return Promise.resolve({});
    });
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    // Mặc định tab Danh mục phòng họp
    await waitFor(() => {
      expect(screen.getByText('Phòng Hội Thảo A')).toBeInTheDocument();
      expect(screen.getByText('Họp thẩm định kiến trúc hệ thống')).toBeInTheDocument();
    });
    const roomCard = screen.getByText('Phòng Hội Thảo A').closest('.p-5');
    // Kiểm tra render đủ họ tên, chức vụ, phòng ban
    expect(roomCard).toHaveTextContent('Trần Văn Hà');
    expect(roomCard).toHaveTextContent('Trưởng phòng QA');
    expect(roomCard).toHaveTextContent('Ban Công nghệ Thông tin');
  });

  it('khử trùng lặp khi họ tên trùng với chức vụ và xử lý an toàn khi khuyết phòng ban', async () => {
    const singleRoom = [
      {
        id: 2,
        name: 'Phòng Họp B',
        location: 'Tầng 3',
        capacity: 10,
        amenities: 'TV',
        is_public: true,
        trang_thai: 'AVAILABLE',
        ghi_chu: '',
      },
    ];
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    const dedupeBooking = [
      {
        id: 106,
        room: 2,
        room_detail: singleRoom[0],
        title: 'Họp rà soát QA',
        date: todayStr,
        start_time: '09:00:00',
        end_time: '10:00:00',
        attendees_count: 4,
        trang_thai: 'CONFIRMED',
        organizer: 6,
        organizer_detail: {
          id: 6,
          username: 'truongphongqa',
          ho_ten: 'Trưởng phòng QA',
          chuc_vu_ten: 'Trưởng phòng QA',
          don_vi_ten: '',
        },
        department_name: '',
      },
    ];
    apiClient.get = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/meeting-rooms/')) {
        return Promise.resolve({ results: singleRoom });
      }
      if (url.includes('/api/meeting-bookings/')) {
        return Promise.resolve({ results: dedupeBooking });
      }
      if (url.includes('/api/auth/profile/')) {
        return Promise.resolve(mockProfile);
      }
      return Promise.resolve({});
    });
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText('Phòng Họp B')).toBeInTheDocument();
      expect(screen.getByText('Họp rà soát QA')).toBeInTheDocument();
    });
    const roomCard = screen.getByText('Phòng Họp B').closest('.p-5');
    // Chỉ xuất hiện 'Trưởng phòng QA' đúng 1 lần (không lặp lại badge)
    const matches = roomCard?.textContent?.match(/Trưởng phòng QA/g);
    expect(matches).toHaveLength(1);
  });

  it('thẻ phòng ở Tab Danh mục cho phép chọn ngày và hiển thị lịch của ngày được chọn', async () => {
    const singleRoom = [
      {
        id: 1,
        name: 'Phòng Hội Thảo A',
        location: 'Tầng 2, Tòa A',
        capacity: 30,
        amenities: 'Máy chiếu',
        is_public: true,
        trang_thai: 'AVAILABLE',
        ghi_chu: '',
      },
    ];
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    const tomorrowStr = `${tomorrow.getFullYear()}-${pad(tomorrow.getMonth() + 1)}-${pad(tomorrow.getDate())}`;

    const tomorrowBooking = [
      {
        id: 107,
        room: 1,
        room_detail: singleRoom[0],
        title: 'Họp chiến lược kinh doanh ngày mai',
        date: tomorrowStr,
        start_time: '08:30:00',
        end_time: '11:00:00',
        attendees_count: 12,
        trang_thai: 'CONFIRMED',
        organizer: 7,
        organizer_detail: {
          id: 7,
          username: 'giamdoc',
          ho_ten: 'Nguyễn Giám Đốc',
          don_vi_ten: 'Ban Lãnh Đạo',
          chuc_vu_ten: 'Giám đốc',
        },
        department_name: 'Ban Lãnh Đạo',
      },
    ];

    apiClient.get = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/meeting-rooms/')) {
        return Promise.resolve({ results: singleRoom });
      }
      if (url.includes('/api/meeting-bookings/')) {
        if (url.includes(`date=${tomorrowStr}`)) {
          return Promise.resolve({ results: tomorrowBooking });
        }
        return Promise.resolve({ results: [] });
      }
      if (url.includes('/api/auth/profile/')) {
        return Promise.resolve(mockProfile);
      }
      return Promise.resolve({});
    });

    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );

    // Mặc định ở Tab 2, hôm nay không có lịch
    await waitFor(() => {
      expect(screen.getByText('Phòng Hội Thảo A')).toBeInTheDocument();
      expect(screen.getByText('Trống lịch trong ngày')).toBeInTheDocument();
    });

    // Chọn ngày mai trên bộ chọn ngày của Tab Danh mục
    const roomsDateInput = screen.getByLabelText('Chọn ngày xem danh mục phòng');
    fireEvent.change(roomsDateInput, { target: { value: tomorrowStr } });

    // Sau khi đổi ngày sang ngày mai, danh mục phòng hiển thị lịch của ngày mai
    await waitFor(() => {
      expect(screen.getByText('Họp chiến lược kinh doanh ngày mai')).toBeInTheDocument();
      expect(screen.getByText('Đã có 1 lịch đặt')).toBeInTheDocument();
    });

    const roomCard = screen.getByText('Phòng Hội Thảo A').closest('.p-5');
    expect(roomCard).toHaveTextContent('Nguyễn Giám Đốc');
    expect(roomCard).not.toHaveTextContent('Đang họp');
  });

  it('sắp xếp danh sách lịch đặt theo thời gian tăng dần và đẩy lịch bị hủy xuống cuối danh sách', async () => {
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

    const mixedBookings = [
      {
        id: 1,
        room: 1,
        title: 'Cuộc họp 1 - Đã hủy sớm',
        date: todayStr,
        start_time: '08:00:00',
        end_time: '09:00:00',
        attendees_count: 5,
        purpose: 'Họp sáng sớm',
        trang_thai: 'CANCELLED',
        organizer: 1,
        organizer_detail: { id: 1, username: 'user1', ho_ten: 'Cán bộ A' },
      },
      {
        id: 2,
        room: 1,
        title: 'Cuộc họp 2 - Chiều hợp lệ',
        date: todayStr,
        start_time: '14:00:00',
        end_time: '15:30:00',
        attendees_count: 5,
        purpose: 'Họp chiều',
        trang_thai: 'CONFIRMED',
        organizer: 1,
        organizer_detail: { id: 1, username: 'user1', ho_ten: 'Cán bộ A' },
      },
      {
        id: 3,
        room: 1,
        title: 'Cuộc họp 3 - Sáng hợp lệ',
        date: todayStr,
        start_time: '09:30:00',
        end_time: '11:00:00',
        attendees_count: 5,
        purpose: 'Họp giữa sáng',
        trang_thai: 'CONFIRMED',
        organizer: 1,
        organizer_detail: { id: 1, username: 'user1', ho_ten: 'Cán bộ A' },
      },
      {
        id: 4,
        room: 1,
        title: 'Cuộc họp 4 - Trưa hoàn thành',
        date: todayStr,
        start_time: '11:00:00',
        end_time: '12:00:00',
        attendees_count: 5,
        purpose: 'Họp trưa',
        trang_thai: 'COMPLETED',
        organizer: 1,
        organizer_detail: { id: 1, username: 'user1', ho_ten: 'Cán bộ A' },
      },
      {
        id: 5,
        room: 1,
        title: 'Cuộc họp 5 - Đã hủy muộn',
        date: todayStr,
        start_time: '16:00:00',
        end_time: '17:00:00',
        attendees_count: 5,
        purpose: 'Họp chiều muộn',
        trang_thai: 'CANCELLED',
        organizer: 1,
        organizer_detail: { id: 1, username: 'user1', ho_ten: 'Cán bộ A' },
      },
    ];

    apiClient.get = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/meeting-rooms/')) {
        return Promise.resolve({ results: mockRooms });
      }
      if (url.includes('/api/meeting-bookings/')) {
        return Promise.resolve({ results: mixedBookings });
      }
      if (url.includes('/api/auth/profile/')) {
        return Promise.resolve(mockProfile);
      }
      return Promise.resolve({});
    });

    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );

    // Chuyển sang Tab Lịch
    const scheduleTabBtn = screen.getByRole('button', { name: /Lịch đặt phòng họp theo ngày/i });
    fireEvent.click(scheduleTabBtn);

    await waitFor(() => {
      expect(screen.getByText('Cuộc họp 3 - Sáng hợp lệ')).toBeInTheDocument();
      expect(screen.getByText('Cuộc họp 1 - Đã hủy sớm')).toBeInTheDocument();
    });

    // Lấy danh sách các tiêu đề cuộc họp theo thứ tự xuất hiện trên giao diện
    const renderedTitles = screen.getAllByText(/Cuộc họp \d/i).map((el) => el.textContent);

    // Thứ tự mong đợi:
    // 1. Cuộc họp 3 (09:30 - CONFIRMED)
    // 2. Cuộc họp 4 (11:00 - COMPLETED)
    // 3. Cuộc họp 2 (14:00 - CONFIRMED)
    // 4. Cuộc họp 1 (08:00 - CANCELLED: Đẩy xuống cuối)
    // 5. Cuộc họp 5 (16:00 - CANCELLED: Đẩy xuống cuối)
    expect(renderedTitles).toEqual([
      'Cuộc họp 3 - Sáng hợp lệ',
      'Cuộc họp 4 - Trưa hoàn thành',
      'Cuộc họp 2 - Chiều hợp lệ',
      'Cuộc họp 1 - Đã hủy sớm',
      'Cuộc họp 5 - Đã hủy muộn',
    ]);
  });

  it('giữ cụm nút thao tác (Xem chi tiết, Sửa, Hủy lịch) cố định trên 1 dòng kể cả khi tên phòng rất dài', async () => {
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;

    const longNameBookings = [
      {
        id: 201,
        room: 1,
        room_detail: {
          id: 1,
          name: 'QA Thịnh 2610 phòng kiểm thử siêu dài chuyên dụng',
          location: 'Tầng 99 - dữ liệu kiểm thử nhóm 3 mở rộng rất dài',
        },
        title: 'Họp kiểm thử bố cục giao diện Desktop',
        date: todayStr,
        start_time: '09:00:00',
        end_time: '10:00:00',
        attendees_count: 5,
        purpose: 'Kiểm tra không nhảy dòng cụm nút thao tác',
        trang_thai: 'CONFIRMED',
        organizer: 1,
        organizer_detail: {
          id: 1,
          username: 'user1',
          ho_ten: 'Đặng Thị Mai',
          chuc_vu_ten: 'Trưởng phòng',
          don_vi_ten: 'Bảo Long Tân Sơn Nhất',
        },
      },
    ];

    apiClient.get = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/meeting-rooms/')) {
        return Promise.resolve({ results: mockRooms });
      }
      if (url.includes('/api/meeting-bookings/')) {
        return Promise.resolve({ results: longNameBookings });
      }
      if (url.includes('/api/auth/profile/')) {
        return Promise.resolve(mockProfile);
      }
      return Promise.resolve({});
    });

    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );

    const scheduleTabBtn = screen.getByRole('button', { name: /Lịch đặt phòng họp theo ngày/i });
    fireEvent.click(scheduleTabBtn);

    await waitFor(() => {
      expect(screen.getByText('Họp kiểm thử bố cục giao diện Desktop')).toBeInTheDocument();
    });

    const detailBtn = screen.getByRole('button', { name: /Xem chi tiết/i });
    const editBtn = screen.getByRole('button', { name: /Sửa/i });
    const cancelBtn = screen.getByRole('button', { name: /Hủy lịch/i });

    expect(detailBtn.className).toContain('whitespace-nowrap');
    expect(editBtn.className).toContain('whitespace-nowrap');
    expect(cancelBtn.className).toContain('whitespace-nowrap');

    const actionsContainer = detailBtn.parentElement;
    expect(actionsContainer?.className).toContain('shrink-0');
    expect(actionsContainer?.className).toContain('lg:w-80');
    expect(actionsContainer?.className).toContain('sm:flex-nowrap');

    const leftContainer = actionsContainer?.previousElementSibling;
    expect(leftContainer?.className).toContain('flex-1');
    expect(leftContainer?.className).toContain('min-w-0');
  });
});
