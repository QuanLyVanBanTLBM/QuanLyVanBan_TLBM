import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RegionModal } from './RegionModal';

const NAME_PLACEHOLDER = /Nhập tên khối hoặc khu vực/;
const ORDER_PLACEHOLDER = /Số nguyên từ 0/;

function setup(initialData?: { id: number; ten: string; thu_tu_hien_thi?: number }) {
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  const onClose = vi.fn();
  render(<RegionModal isOpen onClose={onClose} onSubmit={onSubmit} initialData={initialData} />);
  return { onSubmit, onClose, submit: () => fireEvent.click(screen.getByRole('button', { name: /^(Tạo mới|Lưu thay đổi)$/ })) };
}

describe('RegionModal: thứ tự hiển thị của khối', () => {
  it('gửi thu_tu_hien_thi khi nhập số', async () => {
    const { onSubmit, submit } = setup();
    fireEvent.change(screen.getByPlaceholderText(NAME_PLACEHOLDER), { target: { value: 'KHỐI KẾ TOÁN' } });
    fireEvent.change(screen.getByPlaceholderText(ORDER_PLACEHOLDER), { target: { value: '10' } });
    submit();
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({ ten: 'KHỐI KẾ TOÁN', thu_tu_hien_thi: 10 }));
  });

  it('bỏ trống thì không gửi thu_tu_hien_thi để server xếp khối mới cuối danh sách', async () => {
    const { onSubmit, submit } = setup();
    fireEvent.change(screen.getByPlaceholderText(NAME_PLACEHOLDER), { target: { value: 'Khối mới' } });
    submit();
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({ ten: 'Khối mới' }));
  });

  it('không phải số nguyên không âm thì báo lỗi và không gọi API', async () => {
    const { onSubmit, submit } = setup();
    fireEvent.change(screen.getByPlaceholderText(NAME_PLACEHOLDER), { target: { value: 'Khối mới' } });
    fireEvent.change(screen.getByPlaceholderText(ORDER_PLACEHOLDER), { target: { value: '-3' } });
    submit();
    expect(await screen.findByText(/Thứ tự hiển thị phải là số nguyên/)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('khi sửa thì điền sẵn thứ tự hiện có', () => {
    setup({ id: 3, ten: 'BAN TỔNG GIÁM ĐỐC', thu_tu_hien_thi: 3 });
    expect(screen.getByPlaceholderText(ORDER_PLACEHOLDER)).toHaveValue('3');
  });
});
