import React from 'react';
import { DocumentFilterParams, DocumentStatus } from '@app-types/document';
import { Button } from '@components/common/Button';

export interface FilterBarProps {
  filters: DocumentFilterParams;
  onFilterChange: (newFilters: DocumentFilterParams) => void;
  onSearch: () => void;
  onReset: () => void;
  isLoading?: boolean;
  availableYears?: number[];
}

const CURRENT_YEAR = new Date().getFullYear();

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onFilterChange,
  onSearch,
  onReset,
  isLoading = false,
  availableYears,
}) => {
  // Chỉ hiển thị các năm thực tế có văn bản trong hệ thống
  const yearOptions = (availableYears && availableYears.length > 0)
    ? availableYears
    : [CURRENT_YEAR];
  const handleInputChange = (field: keyof DocumentFilterParams, value: unknown) => {
    onFilterChange({
      ...filters,
      [field]: value,
      page: 1, // Reset về trang 1 khi thay đổi điều kiện lọc
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      onSearch();
    }
  };

  return (
    <div className="bg-surface border border-border-subtle rounded-xl p-4 shadow-sm transition-all duration-normal mb-5">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-3 items-end">
        {/* 1. Ô tìm kiếm từ khóa (Chiếm 4 cột trên màn lớn) */}
        <div className="lg:col-span-4">
          <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center gap-1.5">
            <i className="fa-solid fa-magnifying-glass text-primary text-[0.75rem]" />
            Từ khóa tìm kiếm
          </label>
          <div className="relative">
            <input
              type="text"
              value={filters.q || ''}
              onChange={(e) => handleInputChange('q', e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Số hiệu, trích yếu, nơi ban hành..."
              className="w-full bg-surface-elevated text-main text-sm rounded-lg px-3.5 py-2 pl-9 border border-border-subtle hover:border-primary/40 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/20 transition-all placeholder:text-muted"
            />
            <i className="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none" />
            {filters.q && (
              <button
                type="button"
                onClick={() => handleInputChange('q', '')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-main text-xs p-1"
                title="Xóa từ khóa"
              >
                <i className="fa-solid fa-xmark" />
              </button>
            )}
          </div>
        </div>

        {/* 2. Chọn Năm (Chiếm 2 cột) */}
        <div className="lg:col-span-2">
          <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center gap-1.5">
            <i className="fa-solid fa-calendar-days text-primary text-[0.75rem]" />
            Năm phát hành
          </label>
          <select
            value={filters.nam || ''}
            onChange={(e) => handleInputChange('nam', e.target.value ? Number(e.target.value) : '')}
            className="w-full bg-surface-elevated text-main text-sm rounded-lg px-3 py-2 border border-border-subtle hover:border-primary/40 focus:border-primary focus:outline-none transition-all cursor-pointer"
          >
            <option value="">Tất cả các năm</option>
            {yearOptions.map((year) => (
              <option key={year} value={year}>
                Năm {year}
              </option>
            ))}
          </select>
        </div>

        {/* 3. Khoảng ngày đến (Từ ngày -> Đến ngày) (Chiếm 3 cột) */}
        <div className="lg:col-span-3 grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-semibold text-secondary mb-1.5">Từ ngày đến</label>
            <input
              type="date"
              value={filters.tu_ngay || ''}
              onChange={(e) => handleInputChange('tu_ngay', e.target.value)}
              className="w-full bg-surface-elevated text-main text-xs rounded-lg px-2.5 py-2 border border-border-subtle hover:border-primary/40 focus:border-primary focus:outline-none transition-all"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-secondary mb-1.5">Đến ngày</label>
            <input
              type="date"
              value={filters.den_ngay || ''}
              onChange={(e) => handleInputChange('den_ngay', e.target.value)}
              className="w-full bg-surface-elevated text-main text-xs rounded-lg px-2.5 py-2 border border-border-subtle hover:border-primary/40 focus:border-primary focus:outline-none transition-all"
            />
          </div>
        </div>

        {/* 4. Trạng thái Hiệu lực (Chiếm 3 cột) */}
        <div className="lg:col-span-3">
          <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center gap-1.5">
            <i className="fa-solid fa-shield-halved text-primary text-[0.75rem]" />
            Trạng thái hiệu lực
          </label>
          <select
            value={filters.hieu_luc || ''}
            onChange={(e) => handleInputChange('hieu_luc', e.target.value as DocumentStatus | 'HIEU_LUC' | '')}
            className="w-full bg-surface-elevated text-main text-sm rounded-lg px-3 py-2 border border-border-subtle hover:border-primary/40 focus:border-primary focus:outline-none transition-all cursor-pointer"
          >
            <option value="">Tất cả trạng thái</option>
            <option value="HIEU_LUC">Còn hiệu lực (gồm cả hiệu lực 1 phần)</option>
            <option value="CON_HIEU_LUC">Còn toàn bộ hiệu lực</option>
            <option value="CON_HIEU_LUC_1_PHAN">Còn hiệu lực 1 phần</option>
            <option value="HET_VA_THAY_THE">Đã thay thế</option>
            <option value="HET_HIEU_LUC">Hết hiệu lực</option>
          </select>
        </div>
      </div>

      {/* Dòng nút bấm Tác vụ */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border-subtle/60">
        <span className="text-xs text-muted flex items-center gap-1.5">
          <i className="fa-solid fa-circle-info text-primary/70" />
          Nhấn Enter trong ô tìm kiếm để tra cứu nhanh
        </span>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon="fa-rotate-right"
            onClick={onReset}
            disabled={isLoading}
          >
            Đặt lại
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            icon="fa-magnifying-glass"
            isLoading={isLoading}
            onClick={onSearch}
          >
            Tìm kiếm
          </Button>
        </div>
      </div>
    </div>
  );
};

export default FilterBar;
