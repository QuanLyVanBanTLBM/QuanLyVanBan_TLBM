import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ImportExcelModal from './ImportExcelModal';

describe('ImportExcelModal - Khóa nghiệp vụ phân hệ và phạm vi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
});
