import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FilterBar from './FilterBar';
import { DocumentFilterParams } from '@app-types/document';

describe('FilterBar Component', () => {
  const defaultFilters: DocumentFilterParams = {
    q: '',
    nam: '',
    tu_ngay: '',
    den_ngay: '',
    hieu_luc: '',
    page: 1,
    page_size: 10,
  };

  it('renders all filter fields correctly', () => {
    render(
      <FilterBar
        filters={defaultFilters}
        onFilterChange={vi.fn()}
        onSearch={vi.fn()}
        onReset={vi.fn()}
      />
    );

    expect(screen.getByPlaceholderText(/Số hiệu, trích yếu, nơi ban hành/i)).toBeInTheDocument();
    expect(screen.getByText(/Năm phát hành/i)).toBeInTheDocument();
    expect(screen.getByText(/Từ ngày đến/i)).toBeInTheDocument();
    expect(screen.getByText(/Đến ngày/i)).toBeInTheDocument();
    expect(screen.getByText(/Trạng thái hiệu lực/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Tìm kiếm/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Đặt lại/i })).toBeInTheDocument();
  });

  it('calls onFilterChange when typing in search input', () => {
    const onFilterChange = vi.fn();
    render(
      <FilterBar
        filters={defaultFilters}
        onFilterChange={onFilterChange}
        onSearch={vi.fn()}
        onReset={vi.fn()}
      />
    );

    const searchInput = screen.getByPlaceholderText(/Số hiệu, trích yếu, nơi ban hành/i);
    fireEvent.change(searchInput, { target: { value: 'Nghị quyết' } });

    expect(onFilterChange).toHaveBeenCalledWith(
      expect.objectContaining({
        q: 'Nghị quyết',
        page: 1,
      })
    );
  });

  it('calls onSearch when clicking Tìm kiếm button', () => {
    const onSearch = vi.fn();
    render(
      <FilterBar
        filters={defaultFilters}
        onFilterChange={vi.fn()}
        onSearch={onSearch}
        onReset={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Tìm kiếm/i }));
    expect(onSearch).toHaveBeenCalledTimes(1);
  });

  it('calls onReset when clicking Đặt lại button', () => {
    const onReset = vi.fn();
    render(
      <FilterBar
        filters={{ ...defaultFilters, q: 'test' }}
        onFilterChange={vi.fn()}
        onSearch={vi.fn()}
        onReset={onReset}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Đặt lại/i }));
    expect(onReset).toHaveBeenCalledTimes(1);
  });
});
