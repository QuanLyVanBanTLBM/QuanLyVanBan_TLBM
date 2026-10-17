import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RoomModal } from './RoomModal';
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

describe('RoomModal Component', () => {
  const mockRoom1 = {
    id: 1,
    name: 'Phòng Hội Thảo A',
    location: 'Tầng 2, Tòa A',
    capacity: 30,
    amenities: 'Máy chiếu, micro',
    is_public: true,
    trang_thai: 'AVAILABLE',
    ghi_chu: 'Ghi chú phòng 1',
    created_at: '2026-09-20T08:00:00Z',
    updated_at: '2026-09-20T08:00:00Z',
  };

  const mockRoom2 = {
    id: 2,
    name: 'Phòng Họp B',
    location: 'Tầng 3, Tòa B',
    capacity: 15,
    amenities: 'Bảng trắng',
    is_public: false,
    trang_thai: 'MAINTENANCE',
    ghi_chu: 'Đang bảo trì',
    created_at: '2026-09-20T08:00:00Z',
    updated_at: '2026-09-20T08:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('không render gì khi isOpen là false', () => {
    const { container } = render(
      <RoomModal
        isOpen={false}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
        roomToEdit={null}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('render form tạo mới với các giá trị mặc định khi roomToEdit là null', () => {
    render(
      <RoomModal
        isOpen={true}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
        roomToEdit={null}
      />
    );

    const nameInput = screen.getByPlaceholderText('VD: Phòng Hội thảo A, Phòng Họp Ban Giám Đốc');
    const locationInput = screen.getByPlaceholderText('VD: Tầng 2, Tòa Nhà A');
    const capacityInput = screen.getByPlaceholderText('10');

    expect(nameInput).toHaveValue('');
    expect(locationInput).toHaveValue('');
    expect(capacityInput).toHaveValue(10);
  });

  it('hiển thị đúng dữ liệu của phòng khi chọn sửa (edit mode)', () => {
    render(
      <RoomModal
        isOpen={true}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
        roomToEdit={mockRoom1}
      />
    );

    const nameInput = screen.getByPlaceholderText('VD: Phòng Hội thảo A, Phòng Họp Ban Giám Đốc');
    const locationInput = screen.getByPlaceholderText('VD: Tầng 2, Tòa Nhà A');
    const capacityInput = screen.getByPlaceholderText('10');

    expect(nameInput).toHaveValue('Phòng Hội Thảo A');
    expect(locationInput).toHaveValue('Tầng 2, Tòa A');
    expect(capacityInput).toHaveValue(30);
  });

  it('tự động cập nhật dữ liệu form khi chuyển từ sửa phòng này sang sửa phòng khác', () => {
    const { rerender } = render(
      <RoomModal
        isOpen={true}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
        roomToEdit={mockRoom1}
      />
    );

    const nameInput = screen.getByPlaceholderText('VD: Phòng Hội thảo A, Phòng Họp Ban Giám Đốc');
    const locationInput = screen.getByPlaceholderText('VD: Tầng 2, Tòa Nhà A');
    const capacityInput = screen.getByPlaceholderText('10');

    expect(nameInput).toHaveValue('Phòng Hội Thảo A');
    expect(locationInput).toHaveValue('Tầng 2, Tòa A');
    expect(capacityInput).toHaveValue(30);

    // Chuyển sang sửa mockRoom2
    rerender(
      <RoomModal
        isOpen={true}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
        roomToEdit={mockRoom2}
      />
    );

    const updatedNameInput = screen.getByPlaceholderText('VD: Phòng Hội thảo A, Phòng Họp Ban Giám Đốc');
    const updatedLocationInput = screen.getByPlaceholderText('VD: Tầng 2, Tòa Nhà A');
    const updatedCapacityInput = screen.getByPlaceholderText('10');

    expect(updatedNameInput).toHaveValue('Phòng Họp B');
    expect(updatedLocationInput).toHaveValue('Tầng 3, Tòa B');
    expect(updatedCapacityInput).toHaveValue(15);
  });

  it('tự động reset về rỗng khi chuyển từ sửa phòng sang thêm mới', () => {
    const { rerender } = render(
      <RoomModal
        isOpen={true}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
        roomToEdit={mockRoom1}
      />
    );

    const nameInput = screen.getByPlaceholderText('VD: Phòng Hội thảo A, Phòng Họp Ban Giám Đốc');
    expect(nameInput).toHaveValue('Phòng Hội Thảo A');

    // Chuyển sang thêm mới (roomToEdit = null)
    rerender(
      <RoomModal
        isOpen={true}
        onClose={vi.fn()}
        onSuccess={vi.fn()}
        roomToEdit={null}
      />
    );

    const newNameInput = screen.getByPlaceholderText('VD: Phòng Hội thảo A, Phòng Họp Ban Giám Đốc');
    expect(newNameInput).toHaveValue('');
  });

  it('gửi PUT request khi sửa phòng thành công', async () => {
    apiClient.put = vi.fn().mockResolvedValue({ id: 1, ...mockRoom1 });
    const onSuccess = vi.fn();
    const onClose = vi.fn();

    render(
      <RoomModal
        isOpen={true}
        onClose={onClose}
        onSuccess={onSuccess}
        roomToEdit={mockRoom1}
      />
    );

    const nameInput = screen.getByPlaceholderText('VD: Phòng Hội thảo A, Phòng Họp Ban Giám Đốc');
    fireEvent.change(nameInput, { target: { value: 'Phòng Hội Thảo A Mới' } });

    const submitBtn = screen.getByRole('button', { name: /Lưu thay đổi/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith(
        '/api/meeting-rooms/1/',
        expect.objectContaining({
          name: 'Phòng Hội Thảo A Mới',
          location: 'Tầng 2, Tòa A',
          capacity: 30,
        })
      );
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });
});
