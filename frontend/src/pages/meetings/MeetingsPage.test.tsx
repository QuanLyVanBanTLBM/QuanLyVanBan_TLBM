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
      ten_phong: 'Phòng Hội thảo A',
      vi_tri: 'Tầng 2, Tòa A',
      suc_chua: 30,
      thiet_bi: 'Máy chiếu 4K, 2 Micro không dây',
      is_public: true,
      ghi_chu: '',
      created_at: '2026-09-20T08:00:00Z',
      updated_at: '2026-09-20T08:00:00Z',
    },
    {
      id: 2,
      ten_phong: 'Phòng Họp B',
      vi_tri: 'Tầng 3, Tòa B',
      suc_chua: 10,
      thiet_bi: 'Bảng trắng',
      is_public: false,
      ghi_chu: 'Bảo trì',
      created_at: '2026-09-20T08:00:00Z',
      updated_at: '2026-09-20T08:00:00Z',
    },
  ];

  const mockBookings = [
    {
      id: 101,
      phong_hop: 1,
      phong_hop_detail: mockRooms[0],
      nguoi_dat: 1,
      nguoi_dat_detail: {
        id: 1,
        username: 'hieu_staff',
        full_name: 'Nguyễn Phan Minh Hiệu',
        department: 'Phòng Hành chính - Tổng hợp',
        role: 'staff',
      },
      don_vi_to_chuc: 'Phòng Hành chính - Tổng hợp',
      tieu_de: 'Họp giao ban tuần 40',
      thoi_gian_bat_dau: '2026-09-23T09:00:00Z',
      thoi_gian_ket_thuc: '2026-09-23T10:30:00Z',
      so_nguoi_tham_gia: 15,
      trang_thai: 'da_dat',
      ghi_chu: 'Chuẩn bị micro và trà nước',
      created_at: '2026-09-22T08:00:00Z',
      updated_at: '2026-09-22T08:00:00Z',
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
      if (url.includes('/api/meeting-rooms/')) {
        return Promise.resolve({ results: mockRooms, count: 2 });
      }
      if (url.includes('/api/meeting-bookings/')) {
        return Promise.resolve({ results: mockBookings, count: 1 });
      }
      return Promise.resolve({});
    });
  });

  it('renders page header and schedule tab by default', async () => {
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );

    expect(screen.getByText('Phân hệ Quản lý Phòng họp')).toBeInTheDocument();
    expect(screen.getByText('Đặt phòng họp mới')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Họp giao ban tuần 40')).toBeInTheDocument();
      expect(screen.getByText('Phòng Hội thảo A (Tầng 2, Tòa A)')).toBeInTheDocument();
    });
  });

  it('switches between Schedule tab and Rooms tab', async () => {
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Họp giao ban tuần 40')).toBeInTheDocument();
    });

    // Switch to Danh mục phòng họp
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

    const openBtn = screen.getByText('Đặt phòng họp mới');
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
      if (url.includes('/api/meeting-rooms/')) return Promise.resolve({ results: mockRooms, count: 2 });
      if (url.includes('/api/meeting-bookings/')) return Promise.resolve({ results: [], count: 0 });
      return Promise.resolve({});
    });

    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>
    );

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
        expect.objectContaining({ ly_do_huy: '' })
      );
    });
  });
});
