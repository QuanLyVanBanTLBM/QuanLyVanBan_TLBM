import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MeetingDetailModal } from './MeetingDetailModal';
import { MeetingBooking, MeetingRoom } from '@app-types/meeting';

describe('MeetingDetailModal Component (Issue #22 / QA #4)', () => {
  const mockRoom: MeetingRoom = {
    id: 1,
    name: 'Phòng Hội thảo VIP',
    location: 'Tầng 2, Tòa Nhà A',
    capacity: 20,
    amenities: 'Máy chiếu, Loa, Micro',
    is_public: true,
    trang_thai: 'AVAILABLE',
    ghi_chu: '',
    created_at: '2026-10-20T00:00:00Z',
    updated_at: '2026-10-20T00:00:00Z',
  };

  const baseBooking: MeetingBooking = {
    id: 101,
    room: 1,
    room_detail: mockRoom,
    organizer: 2,
    organizer_detail: {
      id: 2,
      username: 'quantri',
      ho_ten: 'Quản trị hệ thống',
      don_vi_ten: 'Ban công nghệ thông tin',
      chuc_vu_ten: 'Chuyên viên',
    },
    department: 3,
    department_name: 'Ban công nghệ thông tin',
    title: 'QA Thịnh 2610 phòng kiểm thử',
    date: '2026-10-26',
    start_time: '09:00:00',
    end_time: '10:00:00',
    attendees_count: 5,
    purpose: null,
    trang_thai: 'CANCELLED',
    created_at: '2026-10-26T08:00:00Z',
  };

  it('không render gì khi isOpen là false', () => {
    const { container } = render(
      <MeetingDetailModal
        isOpen={false}
        onClose={vi.fn()}
        booking={baseBooking}
        room={mockRoom}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('QA #4: Hiển thị đúng Lý do hủy và KHÔNG hiển thị Mục đích khi lịch hủy không có ghi chú ban đầu (định dạng mới \\n---\\n)', () => {
    const bookingWithoutInitialPurpose: MeetingBooking = {
      ...baseBooking,
      purpose: '\n---\nKết thúc kiểm thử nhóm 3, giải phóng lịch thử.',
      trang_thai: 'CANCELLED',
    };

    render(
      <MeetingDetailModal
        isOpen={true}
        onClose={vi.fn()}
        booking={bookingWithoutInitialPurpose}
        room={mockRoom}
      />
    );

    // Xác nhận có hiển thị nội dung lý do hủy
    expect(screen.getByText('Kết thúc kiểm thử nhóm 3, giải phóng lịch thử.')).toBeInTheDocument();
    // Tiêu đề nhãn "Lý do hủy:" phải xuất hiện
    expect(screen.getByText(/Lý do hủy:/i)).toBeInTheDocument();

    // Tiêu đề nhãn "Mục đích" KHÔNG được xuất hiện
    expect(screen.queryByText(/^Mục đích$/i)).not.toBeInTheDocument();
  });

  it('QA #4 (Backward Compatibility): Lịch hủy cũ trong DB không có dấu phân tách \\n---\\n vẫn hiển thị dưới Lý do hủy, không hiển thị dưới Mục đích', () => {
    const legacyBooking: MeetingBooking = {
      ...baseBooking,
      purpose: 'Kết thúc kiểm thử nhóm 3, giải phóng lịch thử.',
      trang_thai: 'CANCELLED',
    };

    render(
      <MeetingDetailModal
        isOpen={true}
        onClose={vi.fn()}
        booking={legacyBooking}
        room={mockRoom}
      />
    );

    expect(screen.getByText('Kết thúc kiểm thử nhóm 3, giải phóng lịch thử.')).toBeInTheDocument();
    expect(screen.getByText(/Lý do hủy:/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Mục đích$/i)).not.toBeInTheDocument();
  });

  it('QA #4 (API trực tiếp): Nhận cancel_reason từ API và hiển thị đúng khối Lý do hủy', () => {
    const apiBooking: MeetingBooking = {
      ...baseBooking,
      purpose: '',
      cancel_reason: 'Phòng cần sửa máy lạnh đột xuất',
      trang_thai: 'CANCELLED',
    };

    render(
      <MeetingDetailModal
        isOpen={true}
        onClose={vi.fn()}
        booking={apiBooking}
        room={mockRoom}
      />
    );

    expect(screen.getByText('Phòng cần sửa máy lạnh đột xuất')).toBeInTheDocument();
    expect(screen.getByText(/Lý do hủy:/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Mục đích$/i)).not.toBeInTheDocument();
  });

  it('Hiển thị cả Mục đích và Lý do hủy khi lịch có mục đích ban đầu và bị hủy', () => {
    const bookingWithBoth: MeetingBooking = {
      ...baseBooking,
      purpose: 'Họp rà soát tiến độ quý 4\n---\nĐổi lịch họp sang ngày mai',
      trang_thai: 'CANCELLED',
    };

    render(
      <MeetingDetailModal
        isOpen={true}
        onClose={vi.fn()}
        booking={bookingWithBoth}
        room={mockRoom}
      />
    );

    expect(screen.getByText('Họp rà soát tiến độ quý 4')).toBeInTheDocument();
    expect(screen.getByText(/^Mục đích$/i)).toBeInTheDocument();

    expect(screen.getByText('Đổi lịch họp sang ngày mai')).toBeInTheDocument();
    expect(screen.getByText(/Lý do hủy:/i)).toBeInTheDocument();
  });

  it('Cuộc họp bình thường (CONFIRMED) chỉ hiển thị Mục đích, không hiển thị Lý do hủy', () => {
    const normalBooking: MeetingBooking = {
      ...baseBooking,
      title: 'Họp nội bộ bình thường',
      purpose: 'Trao đổi về kiến trúc microservices',
      trang_thai: 'CONFIRMED',
    };

    render(
      <MeetingDetailModal
        isOpen={true}
        onClose={vi.fn()}
        booking={normalBooking}
        room={mockRoom}
      />
    );

    expect(screen.getByText('Trao đổi về kiến trúc microservices')).toBeInTheDocument();
    expect(screen.getByText(/^Mục đích$/i)).toBeInTheDocument();
    expect(screen.queryByText(/Lý do hủy:/i)).not.toBeInTheDocument();
  });

  it('Gọi onClose khi bấm nút đóng hoặc phím Escape', () => {
    const onCloseMock = vi.fn();
    render(
      <MeetingDetailModal
        isOpen={true}
        onClose={onCloseMock}
        booking={baseBooking}
        room={mockRoom}
      />
    );

    // Bấm Escape
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onCloseMock).toHaveBeenCalledTimes(1);

    // Bấm nút Đóng (icon X)
    const closeBtn = screen.getByLabelText('Đóng');
    fireEvent.click(closeBtn);
    expect(onCloseMock).toHaveBeenCalledTimes(2);
  });
});
