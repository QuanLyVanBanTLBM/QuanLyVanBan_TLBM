import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import ImportExcelModal from './ImportExcelModal';

describe('ImportExcelModal - Khóa nghiệp vụ phân hệ và phạm vi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('cảnh báo và khóa nút nhập khi chọn file Hạn chế trong phân hệ Nội bộ', () => {
    render(<ImportExcelModal open={true} onClose={vi.fn()} loai="DI" phamVi="NOI_BO" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test data'], 'Mau_Nhap_Van_Ban_Di_Han_Che.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText(/Cảnh báo không đúng phân hệ/i)).toBeInTheDocument();
    expect(screen.getByText(/Văn bản Hạn chế/i)).toBeInTheDocument();
    expect(screen.getByText(/Bạn đang ở phân hệ Văn bản Nội bộ/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Bắt đầu Nhập/i });
    expect(submitBtn).toBeDisabled();
  });

  it('cảnh báo và khóa nút nhập khi chọn file Nội bộ trong phân hệ Hạn chế', () => {
    render(<ImportExcelModal open={true} onClose={vi.fn()} loai="DI" phamVi="HAN_CHE" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test data'], 'Mau_Nhap_Van_Ban_Di_Noi_Bo.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText(/Cảnh báo không đúng phân hệ/i)).toBeInTheDocument();
    expect(screen.getByText(/Văn bản Nội bộ/i)).toBeInTheDocument();
    expect(screen.getByText(/Bạn đang ở phân hệ Văn bản Hạn chế/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Bắt đầu Nhập/i });
    expect(submitBtn).toBeDisabled();
  });

  it('cảnh báo và khóa nút nhập khi chọn file Văn bản Đến trong phân hệ Văn bản Đi', () => {
    render(<ImportExcelModal open={true} onClose={vi.fn()} loai="DI" phamVi="NOI_BO" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test data'], 'Mau_Nhap_Van_Ban_Den_Noi_Bo.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.getByText(/Cảnh báo không đúng phân hệ/i)).toBeInTheDocument();
    expect(screen.getByText(/File bạn chọn là biểu mẫu Văn bản Đến/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Bắt đầu Nhập/i });
    expect(submitBtn).toBeDisabled();
  });

  it('chấp nhận file hợp lệ khớp đúng phân hệ và mở khóa nút nhập', () => {
    render(<ImportExcelModal open={true} onClose={vi.fn()} loai="DI" phamVi="HAN_CHE" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['test data'], 'Mau_Nhap_Van_Ban_Di_Han_Che.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    fireEvent.change(fileInput, { target: { files: [file] } });

    expect(screen.queryByText(/Cảnh báo không đúng phân hệ/i)).toBeNull();
    const submitBtn = screen.getByRole('button', { name: /Bắt đầu Nhập/i });
    expect(submitBtn).not.toBeDisabled();
  });

  it('hiển thị quy tắc dữ liệu phân biệt VB Nội bộ (cho phép để trống đơn vị/cán bộ nhận & Năm) và VB Hạn chế (bắt buộc)', () => {
    const { rerender } = render(
      <ImportExcelModal open={true} onClose={vi.fn()} loai="DEN" phamVi="NOI_BO" />
    );

    const noticeNoibo = screen.getByText(/Quy tắc dữ liệu:/i).parentElement?.textContent || '';
    expect(noticeNoibo).toMatch(/Năm.*Đơn vị nhận.*Cán bộ xử lý.*được phép để trống/i);
    expect(noticeNoibo).toMatch(/nếu nhập Cán bộ xử lý thì phải nhập Đơn vị nhận/i);
    expect(noticeNoibo).toMatch(/, hoặc ;/);

    rerender(<ImportExcelModal open={true} onClose={vi.fn()} loai="DI" phamVi="HAN_CHE" />);
    const noticeHanChe = screen.getByText(/Quy tắc dữ liệu:/i).parentElement?.textContent || '';
    expect(noticeHanChe).toMatch(/Đơn vị nhận.*Cán bộ xử lý.*là bắt buộc/i);
    expect(noticeHanChe).toMatch(/bỏ trống Năm sẽ tự lấy năm hiện tại/i);
  });

  it('hiển thị đầy đủ mọi dòng lỗi không cắt bớt, không lặp tiền tố Dòng X và lưu danh sách lỗi sau khi đóng popup', async () => {
    const backendErrors = [
      { row: 1, message: 'Thiếu cột ghi chú phụ.' },
      { row: 2, message: "Dòng 2: Đơn vị nhận 'Phòng Không Tồn Tại' không tồn tại trong hệ thống." },
      { row: 4, message: "Dòng 4: Cán bộ xử lý 'canbo_sai' không tồn tại trong hệ thống." },
      { row: 5, message: "Dòng 5: Cán bộ 'a' không thuộc biên chế đơn vị 'Ban CNTT'." },
      { row: 6, message: "Dòng 6: Cột 'Năm' ('abc') không hợp lệ." },
    ];

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({
          error: backendErrors[0].message,
          message: backendErrors[0].message,
          created: 0,
          errors: backendErrors,
        }),
      })
    );

    render(<ImportExcelModal open={true} onClose={vi.fn()} loai="DEN" phamVi="NOI_BO" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['xlsx'], 'Mau_Nhap_Van_Ban_Den_Noi_Bo.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    fireEvent.change(fileInput, { target: { files: [file] } });

    fireEvent.click(screen.getByRole('button', { name: /Bắt đầu Nhập/i }));

    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByText(/Không thể nhập file Excel \(5 lỗi\)/i)).toBeInTheDocument();

    // Hiển thị đủ cả 5 lỗi trong khung có thanh cuộn (không bị ẩn bởi !data.error hay slice(0, 3))
    expect(within(dialog).getByText('Dòng 1: Thiếu cột ghi chú phụ.')).toBeInTheDocument();
    expect(within(dialog).getByText(/Dòng 2: Đơn vị nhận 'Phòng Không Tồn Tại'/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/Dòng 4: Cán bộ xử lý 'canbo_sai'/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/Dòng 5: Cán bộ 'a'/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/Dòng 6: Cột 'Năm' \('abc'\)/i)).toBeInTheDocument();
    expect(within(dialog).queryByText(/Dòng 2:\s*Dòng 2:/i)).toBeNull();

    // Đảm bảo popup hỗ trợ cuộn và xuống dòng thân thiện trên màn hình mobile hẹp
    const list = within(dialog).getByRole('list', { name: /Chi tiết thông báo/i });
    expect(list.parentElement?.className).toMatch(/overflow-y-auto/);
    expect(within(dialog).getByRole('button', { name: /Đã hiểu/i }).className).toMatch(/w-full sm:w-auto/);

    // Đóng popup -> danh sách lỗi vẫn được giữ lại ngay trong modal để người dùng đối chiếu sửa file
    fireEvent.click(within(dialog).getByRole('button', { name: /Đã hiểu/i }));
    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).toBeNull();
    });

    const inlinePanel = screen.getByRole('region', { name: /Danh sách lỗi dữ liệu file Excel/i });
    expect(within(inlinePanel).getByText(/Phát hiện 5 lỗi trong file/i)).toBeInTheDocument();
    expect(within(inlinePanel).getByText(/Dòng 6: Cột 'Năm' \('abc'\)/i)).toBeInTheDocument();

    // Bấm "Mở rộng" mở lại popup chi tiết
    fireEvent.click(within(inlinePanel).getByRole('button', { name: /Mở rộng/i }));
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();

    // Đóng lại rồi chọn file mới -> xóa sạch danh sách lỗi cũ
    fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: /Đã hiểu/i }));
    const fixedFile = new File(['xlsx2'], 'Mau_Nhap_Van_Ban_Den_Noi_Bo_v2.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    fireEvent.change(fileInput, { target: { files: [fixedFile] } });
    expect(screen.queryByRole('region', { name: /Danh sách lỗi dữ liệu file Excel/i })).toBeNull();
  });

  it('hiển thị fallback error đơn lẻ khi server không trả mảng errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({
          error: 'Tệp Excel bị hỏng cấu trúc.',
        }),
      })
    );

    render(<ImportExcelModal open={true} onClose={vi.fn()} loai="DI" phamVi="NOI_BO" />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['bad'], 'Mau_Nhap_Van_Ban_Di_Noi_Bo.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Bắt đầu Nhập/i }));

    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByText(/Tệp Excel bị hỏng cấu trúc\./i)).toBeInTheDocument();
  });
});
