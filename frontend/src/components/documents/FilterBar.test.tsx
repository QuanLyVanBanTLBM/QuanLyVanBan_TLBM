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

  it('displays corresponding dossier and doc type names when cross-referenced by ID from Group 3', () => {
    render(
      <FilterBar
        filters={{ ...defaultFilters, ho_so: '9', loai_van_ban: '5' }}
        recordDossiers={[{ id: 9, ten_ho_so: 'Hồ sơ Ban Giám đốc' }]}
        recordDocTypes={[{ id: 5, ten_loai: 'Kế hoạch', ho_so: 9, ten_ho_so: 'Hồ sơ Ban Giám đốc' }]}
        onFilterChange={vi.fn()}
        onSearch={vi.fn()}
        onReset={vi.fn()}
      />
    );

    const dossierSelect = screen.getByTitle('Chọn danh mục hồ sơ để lọc văn bản') as HTMLSelectElement;
    expect(dossierSelect.value).toBe('Hồ sơ Ban Giám đốc');
    expect(screen.getAllByText('Hồ sơ Ban Giám đốc').length).toBeGreaterThanOrEqual(1);

    const docTypeSelect = screen.getByTitle('Chọn loại văn bản tương ứng') as HTMLSelectElement;
    expect(docTypeSelect).not.toBeDisabled();
    expect(docTypeSelect.value).toBe('Kế hoạch');
    expect(screen.getAllByText('Kế hoạch').length).toBeGreaterThanOrEqual(1);
  });

  it('automatically resolves dossier name and enables docType select when only loai_van_ban ID is passed', () => {
    render(
      <FilterBar
        filters={{ ...defaultFilters, loai_van_ban: '5' }}
        recordDossiers={[{ id: 9, ten_ho_so: 'Hồ sơ Hội đồng quản trị' }]}
        recordDocTypes={[{ id: 5, ten_loai: 'Quyết định', ho_so: 9, ten_ho_so: 'Hồ sơ Hội đồng quản trị' }]}
        onFilterChange={vi.fn()}
        onSearch={vi.fn()}
        onReset={vi.fn()}
      />
    );

    const dossierSelect = screen.getByTitle('Chọn danh mục hồ sơ để lọc văn bản') as HTMLSelectElement;
    expect(dossierSelect.value).toBe('Hồ sơ Hội đồng quản trị');
    expect(screen.getAllByText('Hồ sơ Hội đồng quản trị').length).toBeGreaterThanOrEqual(1);

    const docTypeSelect = screen.getByTitle('Chọn loại văn bản tương ứng') as HTMLSelectElement;
    expect(docTypeSelect).not.toBeDisabled();
    expect(docTypeSelect.value).toBe('Quyết định');
    expect(screen.getAllByText('Quyết định').length).toBeGreaterThanOrEqual(1);
  });
});
