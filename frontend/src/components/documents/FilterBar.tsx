import React from 'react';
import { DocumentFilterParams, DocumentStatus } from '@app-types/document';
import { Button, Select, SelectOption } from '@components/common';
import { useTranslation } from '@i18n/translate';

export interface FilterBarProps {
  filters: DocumentFilterParams;
  onFilterChange: (newFilters: DocumentFilterParams) => void;
  onSearch: () => void;
  onReset: () => void;
  isLoading?: boolean;
  availableYears?: number[];
  availableFolders?: string[];
  availableDocTypes?: string[];
  folderDocTypesMap?: Record<string, string[]>;
  documentType?: 'DEN' | 'DI' | 'MAT';
}

const CURRENT_YEAR = new Date().getFullYear();

// Danh mục loại văn bản mặc định phổ biến
const DEFAULT_DOC_TYPES = [
  'Công văn',
  'Quyết định',
  'Thông báo',
  'Kế hoạch',
  'Hướng dẫn',
  'Báo cáo',
  'Tờ trình',
  'Chỉ thị',
  'Nghị quyết',
];

// Bảng ánh xạ nghiệp vụ phân cấp dự phòng: Danh mục hồ sơ -> Loại văn bản tương ứng
const FOLDER_TO_DOC_TYPES_MAP: Record<string, string[]> = {
  'Hồ sơ Hành chính - Quản trị': ['Công văn', 'Thông báo', 'Tờ trình'],
  'Hồ sơ Tổ chức - Cán bộ': ['Quyết định', 'Thông báo', 'Hướng dẫn'],
  'Hồ sơ Kế hoạch - Tài chính': ['Kế hoạch', 'Quyết định', 'Báo cáo'],
  'Hồ sơ Chuyên môn - Nghiệp vụ': ['Hướng dẫn', 'Công văn', 'Kế hoạch'],
  'Hồ sơ Thanh tra - Pháp chế': ['Quyết định', 'Chỉ thị', 'Nghị quyết'],
  'Hồ sơ Kế hoạch - Dự án': ['Kế hoạch', 'Báo cáo', 'Quyết định'],
  'Hồ sơ Lưu trữ cơ quan': ['Công văn', 'Quyết định', 'Thông báo'],
};

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onFilterChange,
  onSearch,
  onReset,
  isLoading = false,
  availableYears,
  availableFolders,
  availableDocTypes,
  folderDocTypesMap,
  documentType = 'DEN',
}) => {
  const { t } = useTranslation();

  // Kiểm tra tính hợp lệ của khoảng ngày (Từ ngày không được lớn hơn Đến ngày)
  const isDateRangeInvalid = Boolean(
    filters.tu_ngay && filters.den_ngay && filters.tu_ngay > filters.den_ngay
  );

  // Chỉ hiển thị các năm thực tế có văn bản trong hệ thống
  const yearOptions = React.useMemo(() => {
    return availableYears && availableYears.length > 0 ? availableYears : [CURRENT_YEAR];
  }, [availableYears]);
  
  // Danh sách hồ sơ hiển thị: ưu tiên hồ sơ thực tế có văn bản trong hệ thống
  const folderOptions = React.useMemo(() => {
    if (availableFolders && availableFolders.length > 0) {
      return availableFolders;
    }
    return Object.keys(FOLDER_TO_DOC_TYPES_MAP);
  }, [availableFolders]);

  // Lọc Loại văn bản tương ứng theo Danh mục hồ sơ được chọn
  const filteredDocTypeOptions = React.useMemo(() => {
    const allDocTypes = (availableDocTypes && availableDocTypes.length > 0)
      ? availableDocTypes
      : DEFAULT_DOC_TYPES;

    if (!filters.ho_so) {
      // Chưa chọn hồ sơ: hiển thị tất cả loại văn bản có trong hệ thống
      return allDocTypes;
    }

    // 1. Ưu tiên lấy từ bản đồ động các văn bản thực tế trong CSDL
    const dynamicTypes = folderDocTypesMap?.[filters.ho_so];
    if (dynamicTypes && dynamicTypes.length > 0) {
      return dynamicTypes;
    }

    // 2. Dự phòng lấy từ bảng ánh xạ nghiệp vụ chuẩn
    const fallbackTypes = FOLDER_TO_DOC_TYPES_MAP[filters.ho_so];
    if (fallbackTypes && fallbackTypes.length > 0) {
      return fallbackTypes;
    }

    // 3. Nếu hồ sơ tự do chưa phân loại: hiển thị tất cả loại văn bản
    return allDocTypes;
  }, [filters.ho_so, availableDocTypes, folderDocTypesMap]);

  const handleFolderChange = (folderValue: string) => {
    const nextFilters: DocumentFilterParams = {
      ...filters,
      ho_so: folderValue || undefined,
      page: 1,
    };
    // Khóa nghiệp vụ: Phải chọn danh mục hồ sơ rồi mới được chọn loại văn bản.
    // Nếu bỏ chọn hồ sơ (chọn "Tất cả") -> tự động reset loại văn bản về undefined.
    if (!folderValue) {
      nextFilters.loai_van_ban = undefined;
    } else if (filters.loai_van_ban) {
      const allowedDynamic = folderDocTypesMap?.[folderValue];
      const allowedStatic = FOLDER_TO_DOC_TYPES_MAP[folderValue];
      const allowedList = allowedDynamic || allowedStatic;
      if (allowedList && !allowedList.includes(String(filters.loai_van_ban))) {
        nextFilters.loai_van_ban = undefined;
      }
    }
    onFilterChange(nextFilters);
  };

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
      if (!isDateRangeInvalid && !isLoading) {
        onSearch();
      }
    }
  };

  // Options cho Select Danh mục Hồ sơ
  const dossierSelectOptions: SelectOption[] = React.useMemo(() => [
    { value: '', label: t('documents_ui.filter.allDossiers') || 'Tất cả danh mục hồ sơ' },
    ...folderOptions.map((folder) => ({ value: folder, label: folder })),
  ], [folderOptions, t]);

  // Options cho Select Loại văn bản
  const docTypeSelectOptions: SelectOption[] = React.useMemo(() => [
    {
      value: '',
      label: filters.ho_so
        ? (t('documents_ui.filter.allTypesInDossier') || 'Tất cả loại văn bản trong hồ sơ')
        : (t('documents_ui.filter.selectDossierPrompt') || '— Vui lòng chọn danh mục hồ sơ trước —'),
    },
    ...filteredDocTypeOptions.map((docType) => ({ value: docType, label: docType })),
  ], [filters.ho_so, filteredDocTypeOptions, t]);

  // Options cho Select Năm
  const yearSelectOptions: SelectOption[] = React.useMemo(() => [
    { value: '', label: t('documents_ui.filter.allYears') || 'Tất cả các năm' },
    ...yearOptions.map((year) => ({
      value: String(year),
      label: t('documents_ui.filter.yearLabel', { year: String(year) }) || `Năm ${year}`,
    })),
  ], [yearOptions, t]);

  // Options cho Select Trạng thái Hiệu lực
  const statusSelectOptions: SelectOption[] = React.useMemo(() => [
    { value: '', label: t('documents_ui.filter.allStatuses') || 'Tất cả trạng thái' },
    { value: 'CON_HIEU_LUC', label: t('documents_ui.filter.statusActive') || 'Còn hiệu lực' },
    { value: 'CON_HIEU_LUC_1_PHAN', label: t('documents_ui.filter.statusPartiallyActive') || 'Còn hiệu lực 1 phần' },
    { value: 'HET_HIEU_LUC', label: t('documents_ui.filter.statusExpired') || 'Hết hiệu lực' },
  ], [t]);

  return (
    <div className="w-full max-w-full box-border bg-surface border border-border-subtle rounded-xl p-3.5 sm:p-4 shadow-sm transition-all duration-normal mb-5 space-y-3.5 relative">
      {/* Hàng 1: Từ khóa + Danh mục Hồ sơ + Loại văn bản */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-3 items-end">
        {/* 1. Ô tìm kiếm từ khóa (4 cột) */}
        <div className="lg:col-span-4 min-w-0">
          <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center gap-1.5">
            <i className="fa-solid fa-magnifying-glass text-primary text-[0.75rem]" />
            {t('documents_ui.filter.searchKeyword') || 'Từ khóa tìm kiếm'}
          </label>
          <div className="relative">
            <input
              type="text"
              value={filters.q || ''}
              onChange={(e) => handleInputChange('q', e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('documents_ui.filter.searchPlaceholder') || 'Số hiệu, trích yếu, nơi ban hành...'}
              className="w-full bg-surface-elevated text-main text-sm rounded-lg px-3.5 py-2 pl-9 border border-border-subtle hover:border-primary/40 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/20 transition-all placeholder:text-muted"
            />
            <i className="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none" />
            {filters.q && (
              <button
                type="button"
                onClick={() => handleInputChange('q', '')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-main text-xs p-1"
                title={t('documents_ui.filter.clearKeyword') || 'Xóa từ khóa'}
              >
                <i className="fa-solid fa-xmark" />
              </button>
            )}
          </div>
        </div>

        {/* 2. Dropdown Danh mục Hồ sơ (4 cột - Bước 1) */}
        <div className="lg:col-span-4 min-w-0">
          <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <span className="w-4 h-4 rounded-full bg-primary/10 text-primary text-[10px] inline-flex items-center justify-center font-bold">1</span>
              <i className="fa-solid fa-folder text-primary text-[0.75rem]" />
              <span className="text-secondary font-semibold">{t('documents_ui.filter.dossierCatalog') || 'Danh mục hồ sơ'}</span>
            </span>
            <span className="text-[10px] text-muted italic flex items-center gap-1">
              {t('documents_ui.filter.dossierStep') || 'Phân cấp theo hồ sơ'}
            </span>
          </label>
          <div className="relative w-full max-w-full min-w-0">
            <Select
              value={filters.ho_so || ''}
              onChange={handleFolderChange}
              options={dossierSelectOptions}
              placeholder={t('documents_ui.filter.allDossiers') || 'Tất cả danh mục hồ sơ'}
              size="md"
              searchable={folderOptions.length > 5}
            />
          </div>
        </div>

        {/* 3. Dropdown Loại văn bản (4 cột - tương ứng theo Danh mục hồ sơ, Khóa khi chưa chọn hồ sơ) */}
        <div className="lg:col-span-4 min-w-0">
          <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <span className={`w-4 h-4 rounded-full text-[10px] inline-flex items-center justify-center font-bold ${
                filters.ho_so ? 'bg-primary/10 text-primary' : 'bg-hover text-muted'
              }`}>2</span>
              <i className={`fa-solid fa-file-lines text-[0.75rem] ${filters.ho_so ? 'text-primary' : 'text-muted'}`} />
              <span className={filters.ho_so ? 'text-secondary font-semibold' : 'text-muted font-normal'}>{t('documents_ui.filter.docType') || 'Loại văn bản'}</span>
            </span>
            {filters.ho_so ? (
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium italic flex items-center gap-1">
                <i className="fa-solid fa-arrow-turn-down text-[9px]" /> {t('documents_ui.filter.bySelectedDossier') || 'Theo hồ sơ đã chọn'}
              </span>
            ) : (
              <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium italic flex items-center gap-1">
                <i className="fa-solid fa-lock text-[9px]" /> {t('documents_ui.filter.selectDossierFirst') || 'Khóa (Cần chọn hồ sơ trước)'}
              </span>
            )}
          </label>
          <div className="relative w-full max-w-full min-w-0">
            <Select
              disabled={!filters.ho_so}
              value={filters.loai_van_ban !== undefined ? String(filters.loai_van_ban) : ''}
              onChange={(val) => handleInputChange('loai_van_ban', val || undefined)}
              options={docTypeSelectOptions}
              placeholder={
                filters.ho_so
                  ? (t('documents_ui.filter.allTypesInDossier') || 'Tất cả loại văn bản trong hồ sơ')
                  : (t('documents_ui.filter.selectDossierPrompt') || '— Vui lòng chọn danh mục hồ sơ trước —')
              }
              size="md"
              searchable={filteredDocTypeOptions.length > 5}
            />
          </div>
        </div>
      </div>

      {/* Hàng 2: Năm phát hành + Khoảng ngày đến + Trạng thái hiệu lực (3 trạng thái) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-3 items-end">
        {/* 4. Chọn Năm (3 cột) */}
        <div className="lg:col-span-3 min-w-0">
          <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center gap-1.5">
            <i className="fa-solid fa-calendar-days text-primary text-[0.75rem]" />
            {t('documents_ui.filter.releaseYear') || 'Năm phát hành'}
          </label>
          <div className="relative w-full max-w-full min-w-0">
            <Select
              value={filters.nam ? String(filters.nam) : ''}
              onChange={(val) => handleInputChange('nam', val ? Number(val) : '')}
              options={yearSelectOptions}
              placeholder={t('documents_ui.filter.allYears') || 'Tất cả các năm'}
              size="md"
            />
          </div>
        </div>

        {/* 5. Khoảng ngày (Từ ngày -> Đến ngày) (5 cột - Responsive: 1 cột trên mobile xs, 2 cột từ sm trở lên) */}
        <div className="lg:col-span-5 min-w-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-semibold text-secondary mb-1.5 truncate">
                {documentType === 'DEN' 
                  ? (t('documents_ui.filter.dateFromInbound') || 'Từ ngày đến') 
                  : (t('documents_ui.filter.dateFromOutbound') || 'Từ ngày ban hành')}
                <span className="text-[10px] text-muted font-normal ml-1">
                  {t('documents_ui.filter.dateFormatHint') || '(ngày/tháng/năm)'}
                </span>
              </label>
              <input
                type="date"
                max={filters.den_ngay || undefined}
                value={filters.tu_ngay || ''}
                onChange={(e) => handleInputChange('tu_ngay', e.target.value)}
                className={`w-full bg-surface-elevated text-main text-xs rounded-lg px-2.5 py-2 border transition-all ${
                  isDateRangeInvalid 
                    ? 'border-rose-500 focus:border-rose-500 ring-1 ring-rose-500/20' 
                    : 'border-border-subtle hover:border-primary/40 focus:border-primary focus:outline-none'
                }`}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-secondary mb-1.5 truncate">
                {documentType === 'DEN' 
                  ? (t('documents_ui.filter.dateToInbound') || 'Đến ngày') 
                  : (t('documents_ui.filter.dateToOutbound') || 'Đến ngày ban hành')}
                <span className="text-[10px] text-muted font-normal ml-1">
                  {t('documents_ui.filter.dateFormatHint') || '(ngày/tháng/năm)'}
                </span>
              </label>
              <input
                type="date"
                min={filters.tu_ngay || undefined}
                value={filters.den_ngay || ''}
                onChange={(e) => handleInputChange('den_ngay', e.target.value)}
                className={`w-full bg-surface-elevated text-main text-xs rounded-lg px-2.5 py-2 border transition-all ${
                  isDateRangeInvalid 
                    ? 'border-rose-500 focus:border-rose-500 ring-1 ring-rose-500/20' 
                    : 'border-border-subtle hover:border-primary/40 focus:border-primary focus:outline-none'
                }`}
              />
            </div>
          </div>
          {isDateRangeInvalid && (
            <p className="text-xs text-rose-600 dark:text-rose-400 font-medium mt-1 flex items-center gap-1.5 animate-in fade-in duration-150">
              <i className="fa-solid fa-triangle-exclamation text-[11px]" />
              <span>{t('documents_ui.filter.dateRangeError') || 'Từ ngày không được lớn hơn Đến ngày'}</span>
            </p>
          )}
        </div>

        {/* 6. Trạng thái Hiệu lực (Đúng 3 trạng thái theo xác nhận của Thầy) (4 cột) */}
        <div className="lg:col-span-4 min-w-0">
          <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center gap-1.5">
            <i className="fa-solid fa-shield-halved text-primary text-[0.75rem]" />
            {t('documents_ui.filter.validityStatus') || 'Trạng thái hiệu lực'}
          </label>
          <div className="relative w-full max-w-full min-w-0">
            <Select
              value={filters.hieu_luc || ''}
              onChange={(val) => handleInputChange('hieu_luc', (val || '') as DocumentStatus | 'HIEU_LUC' | '')}
              options={statusSelectOptions}
              placeholder={t('documents_ui.filter.allStatuses') || 'Tất cả trạng thái'}
              size="md"
            />
          </div>
        </div>
      </div>

      {/* Dòng nút bấm Tác vụ */}
      <div className="flex flex-wrap items-center justify-between pt-2 border-t border-border-subtle/60 gap-2">
        <span className="text-xs text-muted flex items-center gap-1.5">
          <i className="fa-solid fa-circle-info text-primary/70" />
          {t('documents_ui.filter.enterHint') || 'Nhấn Enter trong ô tìm kiếm để tra cứu nhanh'}
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
            {t('documents_ui.filter.resetBtn') || 'Đặt lại'}
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            icon="fa-magnifying-glass"
            isLoading={isLoading}
            disabled={isLoading || isDateRangeInvalid}
            onClick={onSearch}
            title={isDateRangeInvalid ? (t('documents_ui.filter.dateRangeError') || 'Từ ngày không được lớn hơn Đến ngày') : undefined}
          >
            {t('documents_ui.filter.searchBtn') || 'Tìm kiếm'}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default FilterBar;
