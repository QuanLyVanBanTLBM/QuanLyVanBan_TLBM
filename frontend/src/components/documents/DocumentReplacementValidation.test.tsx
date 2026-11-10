import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import DocumentFormModal from './DocumentFormModal';
import DocumentTable from './DocumentTable';
import apiClient from '@lib/apiClient';
import type { DocumentItem } from '@/types/document';

vi.mock('@lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('Nghiệp Vụ Khóa Thay Thế Văn Bản (Replacement Guard - Theo Chỉ Đạo Của Hậu)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. Chặn người dùng tự gõ số hiệu không tồn tại trong hệ thống (ví dụ: gõ "12")', async () => {
    // Giả lập API tìm kiếm trả về rỗng khi tìm kiếm số "12"
    vi.mocked(apiClient.get).mockResolvedValue({ results: [] });

    render(<DocumentFormModal open={true} onClose={vi.fn()} />);

    // Nhập các trường bắt buộc
    fireEvent.change(screen.getByPlaceholderText('VD: 125/BGDDT-VP'), {
      target: { value: '112/TB-SGDĐT' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Hồ sơ công văn đến/i), {
      target: { value: 'Hồ sơ công văn đến' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Nhập loại văn bản/i), {
      target: { value: 'Thông báo' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Bộ Giáo dục và Đào tạo/i), {
      target: { value: 'Sở Giáo dục và Đào tạo' },
    });
    fireEvent.change(screen.getByPlaceholderText(/mục đích và nội dung cốt lõi/i), {
      target: { value: 'Thông báo phân công lịch trực tiếp nhận' },
    });

    // Tick chọn văn bản thay thế
    const replaceCheckbox = screen.getByLabelText(/Văn bản này thay thế cho văn bản khác trong hệ thống/i);
    fireEvent.click(replaceCheckbox);

    // Gõ số "12" vào ô văn bản thay thế
    const input = await screen.findByPlaceholderText(/Nhập số hiệu văn bản.*trích yếu/i);
    fireEvent.change(input, { target: { value: '12' } });

    // Bấm nút Lưu văn bản
    const submitBtn = screen.getByRole('button', { name: /Lưu văn bản/i });
    fireEvent.click(submitBtn);

    // Kỳ vọng: Hệ thống chặn lại và hiển thị cảnh báo không tồn tại trong modal Alert
    await waitFor(() => {
      expect(screen.getByText(/Văn bản mục tiêu "12" không tồn tại trong hệ thống/i)).toBeInTheDocument();
    });

    // Tuyệt đối không được gọi API POST lưu
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('2. Chặn văn bản tự thiết lập thay thế chính nó (A -> A)', async () => {
    render(<DocumentFormModal open={true} onClose={vi.fn()} />);

    // Nhập số hiệu văn bản hiện tại
    fireEvent.change(screen.getByPlaceholderText('VD: 125/BGDDT-VP'), {
      target: { value: '112/TB-SGDĐT' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Hồ sơ công văn đến/i), {
      target: { value: 'Hồ sơ công văn đến' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Nhập loại văn bản/i), {
      target: { value: 'Thông báo' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Bộ Giáo dục và Đào tạo/i), {
      target: { value: 'Sở Giáo dục và Đào tạo' },
    });
    fireEvent.change(screen.getByPlaceholderText(/mục đích và nội dung cốt lõi/i), {
      target: { value: 'Trích yếu test' },
    });

    // Tick chọn thay thế
    const replaceCheckbox = screen.getByLabelText(/Văn bản này thay thế cho văn bản khác trong hệ thống/i);
    fireEvent.click(replaceCheckbox);

    // Gõ đúng số hiệu của chính nó
    const input = await screen.findByPlaceholderText(/Nhập số hiệu văn bản.*trích yếu/i);
    fireEvent.change(input, { target: { value: '112/TB-SGDĐT' } });

    // Bấm nút Lưu văn bản
    const submitBtn = screen.getByRole('button', { name: /Lưu văn bản/i });
    fireEvent.click(submitBtn);

    // Kỳ vọng: Báo lỗi tự thay thế chính mình
    await waitFor(() => {
      expect(screen.getByText(/Văn bản không thể tự thiết lập thay thế chính nó/i)).toBeInTheDocument();
    });
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('3. Dropdown gợi ý hiển thị thông báo đúng khi không tìm thấy văn bản phù hợp', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ results: [] });

    render(<DocumentFormModal open={true} onClose={vi.fn()} />);

    const replaceCheckbox = screen.getByLabelText(/Văn bản này thay thế cho văn bản khác trong hệ thống/i);
    fireEvent.click(replaceCheckbox);

    const input = await screen.findByPlaceholderText(/Nhập số hiệu văn bản.*trích yếu/i);
    fireEvent.change(input, { target: { value: 'KHONG_TON_TAI' } });

    await waitFor(() => {
      expect(screen.getByText(/Không tìm thấy văn bản phù hợp trong hệ thống/i)).toBeInTheDocument();
    });
  });

  it('4. Bảng danh sách: Văn bản hết hiệu lực hiển thị badge "Bị thay bởi", văn bản mới hiển thị "Thay thế cho"', () => {
    const mockDocs: DocumentItem[] = [
      {
        id: 11,
        so_thu_tu: 11,
        so_hieu: '112/TB-SGDĐT',
        nam: 2026,
        loai: 'DEN',
        loai_display: 'Văn bản Đến',
        trich_yeu: 'Thông báo phân công lịch trực',
        noi_ban_hanh: 'Sở Giáo dục và Đào tạo',
        hieu_luc: 'HET_HIEU_LUC',
        hieu_luc_display: 'Hết hiệu lực',
        hien_thi: true,
        attachment_count: 0,
        created_at: '2026-09-25T08:00:00Z',
        thay_the_cho: [],
        bi_thay_boi: ['127/TB-SGDĐT'], // Văn bản cũ bị văn bản 127 thay thế
      },
      {
        id: 12,
        so_thu_tu: 12,
        so_hieu: '127/TB-SGDĐT',
        nam: 2026,
        loai: 'DEN',
        loai_display: 'Văn bản Đến',
        trich_yeu: 'Quyết định thay thế lịch trực mới',
        noi_ban_hanh: 'Sở Giáo dục và Đào tạo',
        hieu_luc: 'CON_HIEU_LUC',
        hieu_luc_display: 'Còn hiệu lực',
        hien_thi: true,
        attachment_count: 0,
        created_at: '2026-09-26T08:00:00Z',
        thay_the_cho: ['112/TB-SGDĐT'], // Văn bản mới chủ động thay thế cho văn bản cũ
        bi_thay_boi: [],
      },
    ];

    render(
      <DocumentTable
        documents={mockDocs}
        totalCount={2}
        page={1}
        pageSize={10}
        onPageChange={vi.fn()}
        onViewDetail={vi.fn()}
        onViewHistory={vi.fn()}
      />
    );

    // Văn bản #11 (hết hiệu lực) phải mang badge "Bị thay bởi: 127/TB-SGDĐT"
    expect(screen.getByTitle(/Văn bản này đã bị thay thế bởi: 127\/TB-SGDĐT/i)).toBeInTheDocument();

    // Văn bản #12 (còn hiệu lực) phải mang badge "Thay thế cho: 112/TB-SGDĐT"
    expect(screen.getByTitle(/Văn bản này thay thế cho văn bản cũ: 112\/TB-SGDĐT/i)).toBeInTheDocument();
  });
});
