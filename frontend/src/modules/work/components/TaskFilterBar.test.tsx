import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import TaskFilterBar, { FilterDraft } from './TaskFilterBar';

const EMPTY: FilterDraft = { search: '', status: '', createdFrom: '', createdTo: '' };

function renderBar(value: FilterDraft = EMPTY) {
  const onSearch = vi.fn();
  const onCreate = vi.fn();
  render(<TaskFilterBar value={value} onSearch={onSearch} onCreate={onCreate} />);
  return { onSearch, onCreate };
}

describe('TaskFilterBar — tìm kiếm tự động (debounce)', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('không gọi tìm kiếm khi vừa mở trang', () => {
    const { onSearch } = renderBar();
    act(() => vi.advanceTimersByTime(1000));
    expect(onSearch).not.toHaveBeenCalled();
  });

  it('tự tìm sau khi ngừng gõ, có cắt khoảng trắng', () => {
    const { onSearch } = renderBar();
    const box = screen.getByRole('searchbox');

    fireEvent.change(box, { target: { value: '  hợp đồng  ' } });
    expect(onSearch).not.toHaveBeenCalled(); // chưa tới hạn debounce

    act(() => vi.advanceTimersByTime(350));
    expect(onSearch).toHaveBeenCalledTimes(1);
    expect(onSearch).toHaveBeenCalledWith(expect.objectContaining({ search: 'hợp đồng' }));
  });

  it('gõ liên tục chỉ gọi một lần ở lần ngừng cuối', () => {
    const { onSearch } = renderBar();
    const box = screen.getByRole('searchbox');

    fireEvent.change(box, { target: { value: 'a' } });
    act(() => vi.advanceTimersByTime(200));
    fireEvent.change(box, { target: { value: 'ab' } });
    act(() => vi.advanceTimersByTime(200));
    fireEvent.change(box, { target: { value: 'abc' } });
    expect(onSearch).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(350));
    expect(onSearch).toHaveBeenCalledTimes(1);
    expect(onSearch).toHaveBeenCalledWith(expect.objectContaining({ search: 'abc' }));
  });

  it('xóa trắng ô cũng tự tìm lại để danh sách trở về đầy đủ', () => {
    const { onSearch } = renderBar({ ...EMPTY, search: 'hợp đồng' });
    const box = screen.getByRole('searchbox');

    fireEvent.change(box, { target: { value: '' } });
    act(() => vi.advanceTimersByTime(350));

    expect(onSearch).toHaveBeenCalledTimes(1);
    expect(onSearch).toHaveBeenCalledWith(expect.objectContaining({ search: '' }));
  });

  it('nhấn Enter thì tìm ngay, không chờ debounce', () => {
    const { onSearch } = renderBar();
    const box = screen.getByRole('searchbox');

    fireEvent.change(box, { target: { value: 'ngay' } });
    fireEvent.keyDown(box, { key: 'Enter' });
    expect(onSearch).toHaveBeenCalledWith(expect.objectContaining({ search: 'ngay' }));
  });

  it('chọn trạng thái thì tự lọc ngay lập tức', () => {
    const { onSearch } = renderBar();
    const statusSelect = screen.getByLabelText('Tình trạng');

    fireEvent.change(statusSelect, { target: { value: 'QUA_HAN' } });

    expect(onSearch).toHaveBeenCalledTimes(1);
    expect(onSearch).toHaveBeenCalledWith(expect.objectContaining({ status: 'QUA_HAN' }));
  });
});
