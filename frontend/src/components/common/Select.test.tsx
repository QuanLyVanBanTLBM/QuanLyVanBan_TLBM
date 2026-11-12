import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Select, SelectOption } from './Select';

const sampleOptions: SelectOption[] = [
  { value: '1', label: 'Hội đồng quản trị', group: 'HỘI ĐỒNG QUẢN TRỊ' },
  { value: '2', label: 'Ban kiểm toán nội bộ', group: 'HỘI ĐỒNG QUẢN TRỊ' },
  { value: '3', label: 'Ban công nghệ thông tin', group: 'KHỐI HỖ TRỢ' },
  { value: '4', label: 'Ban nhân sự', group: 'KHỐI HỖ TRỢ' },
  { value: '5', label: 'Ban pháp chế', group: 'KHỐI HỖ TRỢ' },
  { value: '6', label: 'Ban đầu tư', group: 'KHỐI TÀI CHÍNH' },
  { value: '7', label: 'Ban kế toán', group: 'KHỐI KẾ TOÁN' },
  { value: '8', label: 'Sở giao dịch Bảo Long', group: 'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH' },
];

describe('Select Component', () => {
  it('renders with placeholder when no value is selected', () => {
    render(
      <Select
        value=""
        onChange={vi.fn()}
        options={sampleOptions}
        placeholder="Chọn đơn vị..."
      />
    );
    expect(screen.getByText('Chọn đơn vị...')).toBeInTheDocument();
  });

  it('renders selected option label when value matches', () => {
    render(
      <Select
        value="3"
        onChange={vi.fn()}
        options={sampleOptions}
        placeholder="Chọn đơn vị..."
      />
    );
    expect(screen.getByText('Ban công nghệ thông tin')).toBeInTheDocument();
  });

  it('opens dropdown popover when clicked', () => {
    render(
      <Select
        value=""
        onChange={vi.fn()}
        options={sampleOptions}
        placeholder="Chọn đơn vị..."
      />
    );

    const trigger = screen.getByRole('button', { name: /chọn đơn vị/i });
    fireEvent.click(trigger);

    expect(screen.getByRole('listbox')).toBeInTheDocument();
    expect(screen.getByText('HỘI ĐỒNG QUẢN TRỊ')).toBeInTheDocument();
    expect(screen.getByText('KHỐI HỖ TRỢ')).toBeInTheDocument();
  });

  it('filters options by search query in real time', () => {
    render(
      <Select
        value=""
        onChange={vi.fn()}
        options={sampleOptions}
        placeholder="Chọn đơn vị..."
      />
    );

    const trigger = screen.getByRole('button', { name: /chọn đơn vị/i });
    fireEvent.click(trigger);

    const searchInput = screen.getByPlaceholderText('Tìm kiếm nhanh...');
    fireEvent.change(searchInput, { target: { value: 'công nghệ' } });

    expect(screen.getByText('Ban công nghệ thông tin')).toBeInTheDocument();
    expect(screen.queryByText('Ban kiểm toán nội bộ')).not.toBeInTheDocument();
  });

  it('calls onChange with selected value when option is clicked', () => {
    const handleChange = vi.fn();
    render(
      <Select
        value=""
        onChange={handleChange}
        options={sampleOptions}
        placeholder="Chọn đơn vị..."
      />
    );

    const trigger = screen.getByRole('button', { name: /chọn đơn vị/i });
    fireEvent.click(trigger);

    const option = screen.getByText('Ban kiểm toán nội bộ');
    fireEvent.click(option);

    expect(handleChange).toHaveBeenCalledWith('2');
  });

  it('clears selection when clear button is clicked', () => {
    const handleChange = vi.fn();
    render(
      <Select
        value="3"
        onChange={handleChange}
        options={sampleOptions}
        clearable
        placeholder="Chọn đơn vị..."
      />
    );

    const clearBtn = screen.getByTitle('Xóa lựa chọn');
    fireEvent.click(clearBtn);

    expect(handleChange).toHaveBeenCalledWith('');
  });

  it('closes dropdown when Escape key is pressed', () => {
    render(
      <Select
        value=""
        onChange={vi.fn()}
        options={sampleOptions}
        placeholder="Chọn đơn vị..."
      />
    );

    const trigger = screen.getByRole('button', { name: /chọn đơn vị/i });
    fireEvent.click(trigger);
    expect(screen.getByRole('listbox')).toBeInTheDocument();

    fireEvent.keyDown(trigger, { key: 'Escape' });
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });
});
