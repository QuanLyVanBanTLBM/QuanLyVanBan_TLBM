import React, { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { ResourceCategory, ResourceType } from '@app-types/resource';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';
import { useTranslation } from '@i18n/translate';
import { ConfirmationModal } from './ConfirmationModal';
import { authService } from '@lib/authService';

export interface CategoryManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  categories: ResourceCategory[];
  types: ResourceType[];
  onSaveCategory: (
    category: ResourceCategory,
    isEdit: boolean,
    childCount?: number,
    childTypes?: string[]
  ) => void | Promise<void>;
  onDeleteCategory: (id: number) => void | Promise<void>;
  onSaveType: (type: ResourceType, isEdit: boolean, silent?: boolean) => void | Promise<void>;
  onDeleteType: (id: number) => void | Promise<void>;
}

// ============================================================================
// COMPONENT PHÂN TRANG NỘI BỘ CHO MODAL (ĐỒNG BỘ PHONG CÁCH VỚI BẢNG TÀI LIỆU)
// ============================================================================
interface ModalPaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (newPageSize: number) => void;
  itemLabel: string;
  pageSizeOptions?: number[];
}

const ModalPagination: React.FC<ModalPaginationProps> = ({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  onPageChange,
  onPageSizeChange,
  itemLabel,
  pageSizeOptions = [5, 10, 20, 50],
}) => {
  const { t } = useTranslation();
  const [jumpPageInput, setJumpPageInput] = useState('');

  const handleJump = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const pageNum = parseInt(jumpPageInput.trim(), 10);
    if (!isNaN(pageNum)) {
      const validPage = Math.max(1, Math.min(pageNum, totalPages));
      onPageChange(validPage);
      setJumpPageInput('');
    }
  };

  type PageItem =
    | { type: 'page'; num: number }
    | { type: 'ellipsis'; direction: 'prev' | 'next'; targetPage: number };

  const getPageElements = (): PageItem[] => {
    if (totalPages <= 4) {
      return Array.from({ length: totalPages }, (_, i) => ({
        type: 'page',
        num: i + 1,
      }));
    }

    const items: PageItem[] = [];

    if (currentPage <= 2) {
      items.push({ type: 'page', num: 1 });
      items.push({ type: 'page', num: 2 });
      items.push({
        type: 'ellipsis',
        direction: 'next',
        targetPage: Math.min(totalPages, currentPage + 2),
      });
      items.push({ type: 'page', num: totalPages });
    } else if (currentPage >= totalPages - 1) {
      items.push({ type: 'page', num: 1 });
      items.push({
        type: 'ellipsis',
        direction: 'prev',
        targetPage: Math.max(1, currentPage - 2),
      });
      items.push({ type: 'page', num: totalPages - 1 });
      items.push({ type: 'page', num: totalPages });
    } else {
      items.push({ type: 'page', num: 1 });
      if (currentPage - 1 > 2) {
        items.push({
          type: 'ellipsis',
          direction: 'prev',
          targetPage: Math.max(1, currentPage - 2),
        });
      } else {
        items.push({ type: 'page', num: 2 });
      }

      items.push({ type: 'page', num: currentPage });

      if (currentPage + 1 < totalPages - 1) {
        items.push({
          type: 'ellipsis',
          direction: 'next',
          targetPage: Math.min(totalPages, currentPage + 2),
        });
      } else {
        items.push({ type: 'page', num: totalPages - 1 });
      }

      items.push({ type: 'page', num: totalPages });
    }

    return items;
  };

  const startRecord = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endRecord = Math.min(currentPage * pageSize, totalItems);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-3 sm:px-4 py-2.5 border-t border-border-subtle text-xs text-secondary bg-surface select-none">
      {/* Bên trái: Chọn số dòng & Tóm tắt phạm vi */}
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 flex-wrap">
        <span className="font-medium text-muted">{t('resourceManagement.display')}</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="px-2 py-1 bg-surface-elevated border border-border-subtle rounded-md text-main text-xs focus:outline-hidden focus:border-primary cursor-pointer font-medium"
          aria-label={t('resourceManagement.selectItemsPerPageAria', { label: itemLabel })}
        >
          {pageSizeOptions.map((opt) => (
            <option key={opt} value={opt}>
              {opt} {t('resourceManagement.rows')}
            </option>
          ))}
        </select>
        <span className="font-medium text-muted">/ {t('resourceManagement.rowsPerPage')}</span>
        <span className="text-muted">·</span>
        <span className="text-secondary font-medium">
          {totalItems === 0 ? (
            `0 ${itemLabel}`
          ) : (
            <>
              {t('resourceManagement.display')} <strong className="text-main font-semibold">{startRecord}–{endRecord}</strong> / <strong className="text-main font-semibold">{totalItems}</strong> {itemLabel}
            </>
          )}
        </span>
      </div>

      {/* Bên phải: Cụm nút điều hướng */}
      {totalPages > 1 ? (
        <div className="flex items-center gap-1 sm:gap-1.5 flex-wrap justify-center">
          {/* Nút về đầu */}
          <button
            type="button"
            disabled={currentPage <= 1}
            onClick={() => onPageChange(1)}
            className="min-w-[28px] sm:min-w-[30px] h-7 sm:h-7.5 px-1.5 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
            title={t('resourceManagement.firstPage')}
            aria-label={t('resourceManagement.firstPage')}
          >
            <i className="fa-solid fa-angles-left text-[10px]" />
          </button>

          {/* Nút trang trước */}
          <button
            type="button"
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
            className="min-w-[28px] sm:min-w-[30px] h-7 sm:h-7.5 px-1.5 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
            title={t('resourceManagement.prevPage')}
            aria-label={t('resourceManagement.prevPage')}
          >
            <i className="fa-solid fa-chevron-left text-[10px]" />
          </button>

          {/* Danh sách các nút số trang */}
          {getPageElements().map((item, idx) => {
            if (item.type === 'ellipsis') {
              return (
                <button
                  key={`ellipsis-${idx}`}
                  type="button"
                  onClick={() => onPageChange(item.targetPage)}
                  className="group min-w-[28px] sm:min-w-[30px] h-7 sm:h-7.5 px-1 text-xs font-medium rounded-lg border border-transparent hover:border-border-subtle hover:bg-surface-elevated text-muted hover:text-primary transition-all cursor-pointer flex items-center justify-center"
                  title={
                    item.direction === 'prev'
                      ? t('resourceManagement.jumpBackPages', { page: item.targetPage })
                      : t('resourceManagement.jumpForwardPages', { page: item.targetPage })
                  }
                  aria-label={item.direction === 'prev' ? t('resourceManagement.jumpBackAria') : t('resourceManagement.jumpForwardAria')}
                >
                  <span className="group-hover:hidden tracking-widest text-[10px] font-bold">•••</span>
                  <i
                    className={`hidden group-hover:inline fa-solid text-[9px] ${
                      item.direction === 'prev' ? 'fa-angles-left' : 'fa-angles-right'
                    }`}
                  />
                </button>
              );
            }

            const isActive = item.num === currentPage;
            return (
              <button
                key={`page-${item.num}`}
                type="button"
                onClick={() => onPageChange(item.num)}
                className={`min-w-[28px] sm:min-w-[30px] h-7 sm:h-7.5 px-2 text-xs font-semibold rounded-lg transition-all cursor-pointer flex items-center justify-center ${
                  isActive
                    ? 'bg-primary text-white shadow-xs font-bold border border-primary'
                    : 'border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main'
                }`}
                aria-label={`${t('resourceManagement.page')} ${item.num}`}
                aria-current={isActive ? 'page' : undefined}
              >
                {item.num}
              </button>
            );
          })}

          {/* Nút trang sau */}
          <button
            type="button"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
            className="min-w-[28px] sm:min-w-[30px] h-7 sm:h-7.5 px-1.5 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
            title={t('resourceManagement.nextPage')}
            aria-label={t('resourceManagement.nextPage')}
          >
            <i className="fa-solid fa-chevron-right text-[10px]" />
          </button>

          {/* Nút đến trang cuối */}
          <button
            type="button"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(totalPages)}
            className="min-w-[28px] sm:min-w-[30px] h-7 sm:h-7.5 px-1.5 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
            title={t('resourceManagement.lastPage')}
            aria-label={t('resourceManagement.lastPage')}
          >
            <i className="fa-solid fa-angles-right text-[10px]" />
          </button>

          {/* Nhập trang nhảy nhanh khi có từ 5 trang trở lên */}
          {totalPages > 4 && (
            <form
              onSubmit={handleJump}
              className="flex items-center gap-1 pl-1.5 border-l border-border-subtle text-secondary"
            >
              <span className="text-[10px] whitespace-nowrap">{t('resourceManagement.jumpTo')}</span>
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={jumpPageInput}
                onChange={(e) => setJumpPageInput(e.target.value.replace(/\D/g, ''))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleJump();
                    (e.target as HTMLInputElement).blur();
                  }
                }}
                placeholder={String(currentPage)}
                title={t('resourceManagement.jumpPageTooltip')}
                className="w-9 h-7 px-1 text-center bg-surface-elevated border border-border-subtle rounded-lg text-main text-xs focus:outline-hidden focus:border-primary font-medium"
                aria-label={t('resourceManagement.jumpPageAria')}
              />
            </form>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] text-muted font-medium px-2 py-0.5 rounded-md bg-surface-elevated border border-border-subtle">
            {t('resourceManagement.page')} 1 / 1
          </span>
        </div>
      )}
    </div>
  );
};

export const CategoryManagementModal: React.FC<CategoryManagementModalProps> = ({
  isOpen,
  onClose,
  categories,
  types,
  onSaveCategory,
  onDeleteCategory,
  onSaveType,
  onDeleteType,
}) => {
  const { t } = useTranslation();

  // 2 tab chính quản lý: "category" (Thư mục) | "type" (Loại tài liệu)
  const [activeTab, setActiveTab] = useState<'category' | 'type'>('category');

  // Menu "⋯" đang mở theo ID
  const [activeMenuCatId, setActiveMenuCatId] = useState<number | null>(null);
  const [activeMenuTypeId, setActiveMenuTypeId] = useState<number | null>(null);

  // Tìm kiếm & Lọc trên bảng
  const [catSearch, setCatSearch] = useState('');
  const [typeSearch, setTypeSearch] = useState('');
  const [filterParentCat, setFilterParentCat] = useState<string>('all');
  const [catDeleteBlockedMsg, setCatDeleteBlockedMsg] = useState<string | null>(null);

  // Phân trang Tab Thư mục (Category)
  const [catPage, setCatPage] = useState(1);
  const [catPageSize, setCatPageSize] = useState(5);

  // Phân trang Tab Loại tài liệu (Type)
  const [typePage, setTypePage] = useState(1);
  const [typePageSize, setTypePageSize] = useState(5);

  // States cho Modal thông báo/xác nhận UI chuẩn
  const [deleteCatTarget, setDeleteCatTarget] = useState<ResourceCategory | null>(null);
  const [deleteTypeTarget, setDeleteTypeTarget] = useState<ResourceType | null>(null);
  const [deleteBlockedCat, setDeleteBlockedCat] = useState<{ cat: ResourceCategory; count: number } | null>(null);

  // ============================================================================
  // UNIFIED SUB-MODAL STATE: Dùng chung cho Tạo mới & Chỉnh sửa
  // ============================================================================
  const [isUnifiedModalOpen, setIsUnifiedModalOpen] = useState(false);
  const [isUnifiedDirty, setIsUnifiedDirty] = useState(false);
  const [isConfirmDiscardUnifiedOpen, setIsConfirmDiscardUnifiedOpen] = useState(false);
  const [unifiedMode, setUnifiedMode] = useState<'create' | 'edit'>('create');
  const [unifiedTarget, setUnifiedTarget] = useState<'category' | 'type'>('category');
  const [isSubmittingUnified, setIsSubmittingUnified] = useState(false);

  const currentSession = authService.getSession();
  const isAdmin = currentSession?.role === 'admin' || currentSession?.username === 'admin';
  const defaultAdminAuthor = currentSession?.fullName || currentSession?.username || t('resourceManagement.defaultAdminAuthor');

  // State Thư mục
  const [editingCatId, setEditingCatId] = useState<number | null>(null);
  const [catForm, setCatForm] = useState<{
    stt_uu_tien: number | string;
    ky_hieu: string;
    ten_tai_lieu: string;
    nguoi_lap_name: string;
    ngay_lap: string;
    ghi_chu: string;
  }>({
    stt_uu_tien: 1,
    ky_hieu: '',
    ten_tai_lieu: '',
    nguoi_lap_name: defaultAdminAuthor,
    ngay_lap: new Date().toISOString().split('T')[0],
    ghi_chu: '',
  });
  const [catError, setCatError] = useState<string | null>(null);
  // Danh sách loại con thêm nhanh khi tạo mới thư mục
  const [catChildTypes, setCatChildTypes] = useState<string[]>([]);
  const [childTypeInput, setChildTypeInput] = useState('');

  // State Loại tài liệu
  const [editingTypeId, setEditingTypeId] = useState<number | null>(null);
  const [typeForm, setTypeForm] = useState({
    dm_tai_lieu: categories.length > 0 ? categories[0].id : 0,
    ten_loai: '',
    is_public: true,
    ghi_chu: '',
  });
  const [typeError, setTypeError] = useState<string | null>(null);

  // Custom Dropdown State cho Lọc Thư mục cha (Tab 2) & Chọn Thư mục cha (Submodal)
  const [isFilterCatDropdownOpen, setIsFilterCatDropdownOpen] = useState(false);
  const filterCatDropdownRef = useRef<HTMLDivElement>(null);
  const [isTypeCatDropdownOpen, setIsTypeCatDropdownOpen] = useState(false);
  const typeCatDropdownRef = useRef<HTMLDivElement>(null);

  // Vị trí fixed của dropdown menu Thao tác — không bị cắt bởi overflow và lật lên khi ở đáy
  const [menuPos, setMenuPos] = useState<{ top: number; right: number } | null>(null);

  const closeAllMenus = () => {
    setActiveMenuCatId(null);
    setActiveMenuTypeId(null);
    setMenuPos(null);
    setIsFilterCatDropdownOpen(false);
    setIsTypeCatDropdownOpen(false);
  };

  // Đóng custom dropdowns khi click ra ngoài
  useEffect(() => {
    const handleOutsideDropdowns = (e: MouseEvent) => {
      const target = e.target as Node;
      if (filterCatDropdownRef.current && !filterCatDropdownRef.current.contains(target)) {
        setIsFilterCatDropdownOpen(false);
      }
      if (typeCatDropdownRef.current && !typeCatDropdownRef.current.contains(target)) {
        setIsTypeCatDropdownOpen(false);
      }
    };
    if (isFilterCatDropdownOpen || isTypeCatDropdownOpen) {
      document.addEventListener('mousedown', handleOutsideDropdowns);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideDropdowns);
    };
  }, [isFilterCatDropdownOpen, isTypeCatDropdownOpen]);

  // Đóng dropdown khi click ngoài, scroll hoặc resize cửa sổ (lắng nghe cả pha capture để không bị cản bởi stopPropagation)
  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (target?.closest?.('[data-menu-trigger]') || target?.closest?.('[data-floating-menu]')) {
        return;
      }
      closeAllMenus();
    };

    const handleScroll = () => {
      closeAllMenus();
    };

    document.addEventListener('click', handleOutside, true);
    window.addEventListener('resize', closeAllMenus);
    window.addEventListener('scroll', handleScroll, true);
    document.addEventListener('scroll', handleScroll, true);
    return () => {
      document.removeEventListener('click', handleOutside, true);
      window.removeEventListener('resize', closeAllMenus);
      window.removeEventListener('scroll', handleScroll, true);
      document.removeEventListener('scroll', handleScroll, true);
    };
  }, []);


  const handleOpenCatMenu = (e: React.MouseEvent<HTMLButtonElement>, catId: number) => {
    e.stopPropagation();
    if (activeMenuCatId === catId) {
      setActiveMenuCatId(null);
      setMenuPos(null);
      return;
    }
    const rect = e.currentTarget.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const top = spaceBelow < 110 ? Math.max(10, rect.top - 84) : rect.bottom + 4;
    setMenuPos({
      top,
      right: Math.max(10, Math.min(window.innerWidth - 130, window.innerWidth - rect.right)),
    });
    setActiveMenuCatId(catId);
    setActiveMenuTypeId(null);
  };

  const handleOpenTypeMenu = (e: React.MouseEvent<HTMLButtonElement>, typeId: number) => {
    e.stopPropagation();
    if (activeMenuTypeId === typeId) {
      setActiveMenuTypeId(null);
      setMenuPos(null);
      return;
    }
    const rect = e.currentTarget.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const top = spaceBelow < 110 ? Math.max(10, rect.top - 84) : rect.bottom + 4;
    setMenuPos({
      top,
      right: Math.max(10, Math.min(window.innerWidth - 130, window.innerWidth - rect.right)),
    });
    setActiveMenuTypeId(typeId);
    setActiveMenuCatId(null);
  };

  // Tính số thứ tự ưu tiên gợi ý lớn nhất + 1 để tự động điền ban đầu khi tạo mới Thư mục
  const nextOrderNumber = () => {
    if (categories.length === 0) return 1;
    const maxOrder = Math.max(...categories.map((c) => c.stt_uu_tien || 0));
    return maxOrder + 1;
  };

  // Mở Popup Tạo mới hợp nhất
  const handleOpenUnifiedCreate = (target: 'category' | 'type') => {
    setUnifiedMode('create');
    setUnifiedTarget(target);
    setEditingCatId(null);
    setEditingTypeId(null);
    setCatError(null);
    setTypeError(null);
    setCatDeleteBlockedMsg(null);
    setCatChildTypes([]);
    setChildTypeInput('');
    setIsUnifiedDirty(false);
    setIsConfirmDiscardUnifiedOpen(false);

    // Khởi tạo form Thư mục: Tự động điền chính xác tài khoản Admin thực hiện tạo
    setCatForm({
      stt_uu_tien: nextOrderNumber(),
      ky_hieu: '',
      ten_tai_lieu: '',
      nguoi_lap_name: defaultAdminAuthor,
      ngay_lap: new Date().toISOString().split('T')[0],
      ghi_chu: '',
    });

    // Khởi tạo form Loại tài liệu
    const defaultCatId =
      filterParentCat !== 'all'
        ? Number(filterParentCat)
        : categories.length > 0
          ? categories[0].id
          : 0;
    setTypeForm({
      dm_tai_lieu: defaultCatId,
      ten_loai: '',
      is_public: true,
      ghi_chu: '',
    });

    setIsUnifiedModalOpen(true);
  };

  // Mở Popup Chỉnh sửa Thư mục
  const handleOpenEditCat = (cat: ResourceCategory) => {
    setUnifiedMode('edit');
    setUnifiedTarget('category');
    setEditingCatId(cat.id);
    setEditingTypeId(null);
    setCatError(null);
    setCatDeleteBlockedMsg(null);
    setCatChildTypes([]);
    setChildTypeInput('');
    setIsUnifiedDirty(false);
    setIsConfirmDiscardUnifiedOpen(false);

    setCatForm({
      stt_uu_tien: cat.stt_uu_tien,
      ky_hieu: cat.ky_hieu || '',
      ten_tai_lieu: cat.ten_tai_lieu,
      nguoi_lap_name: cat.nguoi_lap_name || defaultAdminAuthor,
      ngay_lap: cat.ngay_lap || new Date().toISOString().split('T')[0],
      ghi_chu: cat.ghi_chu || '',
    });

    setIsUnifiedModalOpen(true);
  };

  // Mở Popup Chỉnh sửa Loại tài liệu
  const handleOpenEditType = (typeItem: ResourceType) => {
    setUnifiedMode('edit');
    setUnifiedTarget('type');
    setEditingTypeId(typeItem.id);
    setEditingCatId(null);
    setTypeError(null);
    setIsUnifiedDirty(false);
    setIsConfirmDiscardUnifiedOpen(false);

    setTypeForm({
      dm_tai_lieu: typeItem.dm_tai_lieu,
      ten_loai: typeItem.ten_loai,
      is_public: typeItem.is_public,
      ghi_chu: typeItem.ghi_chu || '',
    });

    setIsUnifiedModalOpen(true);
  };

  // Đóng an toàn Popup Thêm/Sửa Danh mục & Loại tài liệu có xác nhận nếu có dữ liệu/đã chỉnh sửa
  const handleSafeCloseUnified = useCallback(() => {
    const hasData =
      isUnifiedDirty ||
      Boolean(
        catForm.ten_tai_lieu.trim() ||
        catForm.ky_hieu.trim() ||
        catForm.ghi_chu.trim() ||
        catChildTypes.length > 0 ||
        childTypeInput.trim() ||
        typeForm.ten_loai.trim() ||
        typeForm.ghi_chu.trim()
      );

    if (hasData) {
      setIsConfirmDiscardUnifiedOpen(true);
      return;
    }
    setIsUnifiedModalOpen(false);
  }, [
    isUnifiedDirty,
    catForm.ten_tai_lieu,
    catForm.ky_hieu,
    catForm.ghi_chu,
    catChildTypes.length,
    childTypeInput,
    typeForm.ten_loai,
    typeForm.ghi_chu,
    setIsConfirmDiscardUnifiedOpen,
    setIsUnifiedModalOpen,
  ]);

  // Người dùng bấm trực tiếp nút "Hủy" trên footer form -> Luôn bật xác nhận hủy
  const handleCancelBtnClick = () => {
    setIsConfirmDiscardUnifiedOpen(true);
  };

  // Lắng nghe phím ESC để đóng an toàn
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isTypeCatDropdownOpen) {
          setIsTypeCatDropdownOpen(false);
          return;
        }
        if (isFilterCatDropdownOpen) {
          setIsFilterCatDropdownOpen(false);
          return;
        }
        if (isUnifiedModalOpen) {
          if (isConfirmDiscardUnifiedOpen) return;
          handleSafeCloseUnified();
        } else if (!deleteCatTarget && !deleteBlockedCat && !deleteTypeTarget) {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    isOpen,
    isTypeCatDropdownOpen,
    isFilterCatDropdownOpen,
    isUnifiedModalOpen,
    isConfirmDiscardUnifiedOpen,
    handleSafeCloseUnified,
    deleteCatTarget,
    deleteBlockedCat,
    deleteTypeTarget,
    onClose,
  ]);

  // Thêm nhanh Loại con vào Thư mục
  const handleAddChildType = () => {
    const trimmed = childTypeInput.trim();
    if (!trimmed) return;
    if (catChildTypes.includes(trimmed)) return;
    setCatChildTypes([...catChildTypes, trimmed]);
    setChildTypeInput('');
    setIsUnifiedDirty(true);
  };

  const handleRemoveChildType = (index: number) => {
    setCatChildTypes(catChildTypes.filter((_, i) => i !== index));
    setIsUnifiedDirty(true);
  };

  // Submit Form hợp nhất
  const handleUnifiedSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmittingUnified) return;

    if (unifiedTarget === 'category') {
      // Validate Thư mục
      if (!catForm.ten_tai_lieu.trim()) {
        setCatError(t('resourceManagement.errFolderRequired'));
        return;
      }

      if (!catForm.stt_uu_tien || Number(catForm.stt_uu_tien) < 1) {
        setCatError(t('resourceManagement.errOrderMin'));
        return;
      }

      const sttNum = Number(catForm.stt_uu_tien);
      const isDuplicateOrder = categories.some(
        (c) => c.stt_uu_tien === sttNum && c.id !== editingCatId
      );
      if (isDuplicateOrder) {
        setCatError(t('resourceManagement.orderExists'));
        return;
      }

      const categoryId = editingCatId || Date.now();
      const payload: ResourceCategory = {
        id: categoryId,
        stt_uu_tien: sttNum,
        ky_hieu: catForm.ky_hieu.trim(),
        ten_tai_lieu: catForm.ten_tai_lieu.trim(),
        nguoi_lap_name: (catForm.nguoi_lap_name || defaultAdminAuthor).trim(),
        ngay_lap: catForm.ngay_lap,
        ghi_chu: catForm.ghi_chu.trim(),
      };

      // Tự động gom các loại con đã thêm qua chip VÀ nội dung đang gõ dở trong ô input nếu người dùng chưa bấm "+ Thêm"
      const finalChildTypes = [...catChildTypes];
      const pendingChild = childTypeInput.trim();
      if (pendingChild && !finalChildTypes.includes(pendingChild)) {
        finalChildTypes.push(pendingChild);
      }

      try {
        setIsSubmittingUnified(true);
        setCatError(null);
        await onSaveCategory(payload, Boolean(editingCatId), finalChildTypes.length, finalChildTypes);
        setIsUnifiedDirty(false);
        setIsConfirmDiscardUnifiedOpen(false);
        setIsUnifiedModalOpen(false);
      } catch (err: unknown) {
        console.error('Lỗi khi lưu thư mục:', err);
        const errMsg = err instanceof Error ? err.message : t('resourceManagement.errSaveCat');
        setCatError(errMsg);
      } finally {
        setIsSubmittingUnified(false);
      }
    } else {
      // Validate & Lưu Loại tài liệu
      if (categories.length === 0 || !typeForm.dm_tai_lieu) {
        setTypeError(t('resourceManagement.noParentCatWarning'));
        return;
      }

      if (!typeForm.ten_loai.trim()) {
        setTypeError(t('resourceManagement.errTypeNameRequired'));
        return;
      }

      const payload: ResourceType = {
        id: editingTypeId || Date.now(),
        dm_tai_lieu: Number(typeForm.dm_tai_lieu),
        ten_loai: typeForm.ten_loai.trim(),
        is_public: typeForm.is_public,
        ghi_chu: typeForm.ghi_chu.trim(),
        ngay_lap: new Date().toISOString().split('T')[0],
      };

      try {
        setIsSubmittingUnified(true);
        setTypeError(null);
        await onSaveType(payload, Boolean(editingTypeId));
        setIsUnifiedDirty(false);
        setIsConfirmDiscardUnifiedOpen(false);
        setIsUnifiedModalOpen(false);
      } catch (err: unknown) {
        console.error('Lỗi khi lưu loại tài liệu:', err);
        const errMsg = err instanceof Error ? err.message : t('resourceManagement.errSaveType');
        setTypeError(errMsg);
      } finally {
        setIsSubmittingUnified(false);
      }
    }
  };

  // Xóa Thư mục (Chặn xóa nếu còn loại con)
  const handleDeleteCategoryWithCheck = (cat: ResourceCategory) => {
    setCatDeleteBlockedMsg(null);
    const childTypes = types.filter((t) => t.dm_tai_lieu === cat.id);
    if (childTypes.length > 0) {
      setCatDeleteBlockedMsg(`Không thể xóa vì thư mục còn ${childTypes.length} loại tài liệu`);
      setDeleteBlockedCat({ cat, count: childTypes.length });
      return;
    }

    setDeleteCatTarget(cat);
  };

  // Xóa Loại tài liệu có xác nhận
  const handleDeleteTypeConfirm = (typeItem: ResourceType) => {
    setDeleteTypeTarget(typeItem);
  };

  // Thư mục đã lọc và sắp xếp theo STT ưu tiên
  const filteredCategories = useMemo(() => {
    return categories
      .filter((c) => {
        if (!catSearch.trim()) return true;
        const term = catSearch.toLowerCase();
        return (
          c.ten_tai_lieu.toLowerCase().includes(term) ||
          (c.ky_hieu || '').toLowerCase().includes(term)
        );
      })
      .sort((a, b) => a.stt_uu_tien - b.stt_uu_tien);
  }, [categories, catSearch]);

  // Tính toán phân trang cho Thư mục
  const totalCatPages = Math.max(1, Math.ceil(filteredCategories.length / catPageSize));
  const effectiveCatPage = Math.min(Math.max(1, catPage), totalCatPages);
  const paginatedCategories = useMemo(() => {
    const start = (effectiveCatPage - 1) * catPageSize;
    return filteredCategories.slice(start, start + catPageSize);
  }, [filteredCategories, effectiveCatPage, catPageSize]);

  // Loại tài liệu đã lọc
  const filteredTypes = useMemo(() => {
    return types.filter((t) => {
      if (filterParentCat !== 'all' && t.dm_tai_lieu !== Number(filterParentCat)) {
        return false;
      }
      if (typeSearch.trim()) {
        const term = typeSearch.toLowerCase();
        return t.ten_loai.toLowerCase().includes(term);
      }
      return true;
    });
  }, [types, filterParentCat, typeSearch]);

  // Tính toán phân trang cho Loại tài liệu
  const totalTypePages = Math.max(1, Math.ceil(filteredTypes.length / typePageSize));
  const effectiveTypePage = Math.min(Math.max(1, typePage), totalTypePages);
  const paginatedTypes = useMemo(() => {
    const start = (effectiveTypePage - 1) * typePageSize;
    return filteredTypes.slice(start, start + typePageSize);
  }, [filteredTypes, effectiveTypePage, typePageSize]);

  if (!isOpen) return null;
  if (typeof document === 'undefined') return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-2 sm:p-6 bg-black/60 backdrop-blur-xs animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full max-w-4xl max-h-[92vh] sm:max-h-[90vh] bg-surface rounded-2xl border border-border-subtle shadow-2xl flex flex-col overflow-hidden animate-slide-in-bottom"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Modal */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-border-subtle bg-surface-elevated shrink-0">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-main flex items-center gap-2">
              <i className="fa-solid fa-folder-tree text-primary text-base" />
              <span>{t('resourceManagement.catModalTitle')}</span>
            </h2>
            <p className="text-xs text-secondary mt-0.5">
              {t('resourceManagement.catModalSubtitle')}
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface transition-colors cursor-pointer"
            aria-label={t('resourceManagement.close')}
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Tab Switcher (Thư mục | Loại tài liệu) */}
        <div className="flex border-b border-border-subtle px-3 sm:px-6 bg-surface shrink-0">
          <button
            type="button"
            onClick={() => {
              setActiveTab('category');
              setCatDeleteBlockedMsg(null);
              closeAllMenus();
            }}
            className={`py-3 px-3 sm:px-4 text-xs sm:text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer ${
              activeTab === 'category'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-secondary hover:text-main'
            }`}
          >
            <i className="fa-solid fa-folder" />
            <span>{t('resourceManagement.tabFolders')}</span>
            <span
              className={`min-w-[20px] h-5 px-1.5 rounded-full text-[11px] font-bold inline-flex items-center justify-center leading-none shrink-0 ${
                activeTab === 'category'
                  ? 'bg-primary-subtle text-primary'
                  : 'bg-surface-elevated text-secondary'
              }`}
            >
              {categories.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab('type');
              setCatDeleteBlockedMsg(null);
              closeAllMenus();
            }}
            className={`py-3 px-3 sm:px-4 text-xs sm:text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer ${
              activeTab === 'type'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-secondary hover:text-main'
            }`}
          >
            <i className="fa-solid fa-tags" />
            <span>{t('resourceManagement.tabTypes')}</span>
            <span
              className={`min-w-[20px] h-5 px-1.5 rounded-full text-[11px] font-bold inline-flex items-center justify-center leading-none shrink-0 ${
                activeTab === 'type'
                  ? 'bg-primary-subtle text-primary'
                  : 'bg-surface-elevated text-secondary'
              }`}
            >
              {types.length}
            </span>
          </button>
        </div>

        {/* Body Modal */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-3 sm:space-y-4 min-h-0">
          {/* Cảnh báo chế độ chỉ xem nếu không phải Admin */}
          {!isAdmin && (
            <div className="p-3 rounded-xl bg-amber-500/10 text-amber-800 dark:text-amber-200 border border-amber-500/30 text-xs flex items-center gap-2.5 animate-fade-in">
              <i className="fa-solid fa-lock text-amber-500 shrink-0" />
              <span>{t('resourceManagement.readOnlyAdminWarning')}</span>
            </div>
          )}

          {/* Cảnh báo nếu xóa thư mục bị chặn */}
          {catDeleteBlockedMsg && (
            <div className="p-3 rounded-xl bg-danger-subtle text-danger border border-danger/30 text-xs sm:text-sm flex items-center justify-between gap-3 animate-fade-in">
              <div className="flex items-center gap-2">
                <i className="fa-solid fa-circle-exclamation shrink-0" />
                <span>{catDeleteBlockedMsg}</span>
              </div>
              <button
                type="button"
                onClick={() => setCatDeleteBlockedMsg(null)}
                className="p-1 hover:opacity-70 text-xs cursor-pointer"
                aria-label={t('resourceManagement.close')}
              >
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
          )}

          {/* TAB 1: THƯ MỤC */}
          {activeTab === 'category' && (
            <div className="space-y-3 sm:space-y-4">
              {/* Thanh công cụ Tab Thư mục */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 sm:gap-3">
                <div className="relative flex-1 w-full sm:max-w-md">
                  <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none" />
                  <input
                    type="text"
                    placeholder={t('resourceManagement.catSearchPlaceholder')}
                    value={catSearch}
                    onChange={(e) => {
                      setCatSearch(e.target.value);
                      setCatPage(1);
                    }}
                    className="w-full pl-8 pr-8 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary transition-all shadow-2xs"
                  />
                  {catSearch && (
                    <button
                      type="button"
                      onClick={() => {
                        setCatSearch('');
                        setCatPage(1);
                      }}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-main text-xs p-1 cursor-pointer"
                      title={t('resourceManagement.clearSearch')}
                    >
                      <i className="fa-solid fa-xmark" />
                    </button>
                  )}
                </div>

                <Button
                  variant="primary"
                  size="sm"
                  icon="fa-plus"
                  disabled={!isAdmin}
                  onClick={() => {
                    if (!isAdmin) return;
                    handleOpenUnifiedCreate('category');
                  }}
                  className="h-9 px-3.5 rounded-xl text-xs font-bold shrink-0 shadow-sm hover:shadow-glow disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto justify-center"
                  title={isAdmin ? t('resourceManagement.addNew') : t('resourceManagement.adminOnlyFolder')}
                >
                  {t('resourceManagement.addNew')}
                </Button>
              </div>

              {/* Bảng danh sách Thư mục */}
              <div className="w-full overflow-x-auto rounded-xl border border-border-subtle bg-surface shadow-2xs">
                <table className="w-full text-left text-xs border-collapse min-w-full">
                  <thead className="bg-surface-elevated font-bold text-muted uppercase tracking-wider border-b border-border-subtle">
                    <tr>
                      <th className="hidden sm:table-cell px-2 sm:px-3 py-3 w-16 text-center">{t('resourceManagement.colOrder')}</th>
                      <th className="hidden sm:table-cell px-3 py-3 w-24 sm:w-28">{t('resourceManagement.colCatCode')}</th>
                      <th className="px-3 sm:px-4 py-3 min-w-[140px] sm:min-w-[200px]">{t('resourceManagement.colCatName')}</th>
                      <th className="hidden md:table-cell px-3 py-3 w-28 sm:w-32">{t('resourceManagement.colCatDate')}</th>
                      <th className="hidden sm:table-cell px-3 py-3 w-24 sm:w-28 text-center">{t('resourceManagement.colCatSubtypes')}</th>
                      <th className="px-2 sm:px-3 py-3 w-12 sm:w-20 text-center whitespace-nowrap">{t('resourceManagement.colActions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {filteredCategories.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-10 text-center text-muted">
                          <i className="fa-solid fa-folder-open text-2xl mb-2 block opacity-40" />
                          {categories.length === 0
                            ? t('resourceManagement.emptyCategoriesHint')
                            : t('resourceManagement.noMatchingCategories')}
                        </td>
                      </tr>
                    ) : (
                      paginatedCategories.map((cat) => {
                        const childCount = types.filter((t) => t.dm_tai_lieu === cat.id).length;
                        return (
                          <tr key={cat.id} className="hover:bg-surface-elevated/70 transition-colors">
                            <td className="hidden sm:table-cell px-2 sm:px-3 py-3 text-center font-bold text-primary text-xs">
                              {cat.stt_uu_tien}
                            </td>
                            <td className="hidden sm:table-cell px-3 py-3 font-medium text-secondary">
                              {cat.ky_hieu || '-'}
                            </td>
                            <td className="px-3 sm:px-4 py-2.5 sm:py-3">
                              <div className="flex items-start gap-2">
                                <div className="mt-0.5 shrink-0 text-primary/75">
                                  <i className="fa-solid fa-folder text-sm" />
                                </div>
                                <div className="min-w-0 flex-1">
                                  <span className="font-semibold text-main text-xs sm:text-sm block leading-snug">
                                    {cat.ten_tai_lieu}
                                  </span>
                                  <div className="flex items-center gap-1.5 flex-wrap sm:hidden mt-1 text-[11px]">
                                    {cat.ky_hieu && (
                                      <span className="text-[10px] font-medium text-muted bg-surface-elevated px-1.5 py-0.5 rounded border border-border-subtle shrink-0">
                                        {cat.ky_hieu}
                                      </span>
                                    )}
                                    <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-primary/10 text-primary border border-primary/20 shrink-0">
                                      {t('resourceManagement.subtypesCount', { count: childCount })}
                                    </span>
                                  </div>
                                  {cat.ghi_chu && (
                                    <p className="text-[11px] text-muted line-clamp-1 mt-0.5 leading-tight font-normal">
                                      {cat.ghi_chu}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </td>
                            <td className="hidden md:table-cell px-3 py-3 text-secondary">{cat.ngay_lap || '-'}</td>
                            <td className="hidden sm:table-cell px-3 py-3 text-center">
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-surface-elevated text-secondary border border-border-subtle">
                                {t('resourceManagement.subtypesCount', { count: childCount })}
                              </span>
                            </td>
                            <td
                              className="px-2 sm:px-3 py-2.5 sm:py-3 text-center whitespace-nowrap align-middle"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <button
                                type="button"
                                data-menu-trigger="true"
                                onClick={(e) => handleOpenCatMenu(e, cat.id)}
                                className={`w-7 h-7 rounded-lg inline-flex items-center justify-center transition-colors cursor-pointer ${
                                  activeMenuCatId === cat.id
                                    ? 'bg-primary text-white shadow-xs'
                                    : 'text-muted hover:text-main hover:bg-surface-elevated'
                                }`}
                                title={t('resourceManagement.actionMenu')}
                                aria-label={t('resourceManagement.actionsForFolder', { name: cat.ten_tai_lieu })}
                              >
                                <i className="fa-solid fa-ellipsis text-xs" />
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>

                {/* Thanh phân trang Thư mục */}
                {filteredCategories.length > 0 && (
                  <ModalPagination
                    currentPage={effectiveCatPage}
                    totalPages={totalCatPages}
                    pageSize={catPageSize}
                    totalItems={filteredCategories.length}
                    onPageChange={(p) => {
                      setCatPage(p);
                      closeAllMenus();
                    }}
                    onPageSizeChange={(newSize) => {
                      setCatPageSize(newSize);
                      setCatPage(1);
                      closeAllMenus();
                    }}
                    itemLabel={t('resourceManagement.itemLabelFolders')}
                  />
                )}
              </div>
            </div>
          )}

          {/* TAB 2: LOẠI TÀI LIỆU */}
          {activeTab === 'type' && (
            <div className="space-y-3 sm:space-y-4">
              {/* Thanh công cụ Tab Loại tài liệu */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 sm:gap-3">
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 flex-1 w-full">
                  {/* Dropdown lọc Thư mục cha - Custom Responsive Dropdown */}
                  <div className="relative w-full sm:w-auto shrink-0" ref={filterCatDropdownRef}>
                    <button
                      type="button"
                      onClick={() => {
                        setIsFilterCatDropdownOpen((prev) => !prev);
                      }}
                      aria-label={t('resourceManagement.filterByParentFolderAria')}
                      aria-haspopup="listbox"
                      aria-expanded={isFilterCatDropdownOpen}
                      className={`w-full sm:w-56 h-9 px-3 bg-surface border rounded-xl text-xs text-main flex items-center justify-between gap-2 shadow-2xs cursor-pointer font-medium transition-colors ${
                        isFilterCatDropdownOpen
                          ? 'border-primary ring-1 ring-primary/20'
                          : 'border-border-subtle hover:border-primary/50'
                      }`}
                    >
                      <span className="truncate text-left flex-1">
                        {filterParentCat === 'all'
                          ? t('resourceManagement.allFolders')
                          : categories.find((c) => String(c.id) === filterParentCat)?.ten_tai_lieu || t('resourceManagement.allFolders')}
                      </span>
                      <i
                        className={`fa-solid fa-chevron-down text-[10px] text-muted transition-transform duration-200 shrink-0 ${
                          isFilterCatDropdownOpen ? 'rotate-180 text-primary' : ''
                        }`}
                      />
                    </button>

                    {/* Native select ẩn để kiểm thử & trợ năng */}
                    <select
                      value={filterParentCat}
                      onChange={(e) => {
                        setFilterParentCat(e.target.value);
                        setTypePage(1);
                      }}
                      className="sr-only"
                      tabIndex={-1}
                      aria-hidden="true"
                      aria-label={t('resourceManagement.filterByParentFolderAria')}
                    >
                      <option value="all">{t('resourceManagement.allFolders')}</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.ten_tai_lieu}
                        </option>
                      ))}
                    </select>

                    {/* Dropdown popup */}
                    {isFilterCatDropdownOpen && (
                      <div
                        role="listbox"
                        className="absolute left-0 right-0 sm:left-0 sm:right-auto sm:w-64 top-full mt-1.5 w-full max-w-full bg-surface-elevated rounded-xl border border-border-subtle shadow-2xl p-1.5 z-50 max-h-56 overflow-y-auto space-y-0.5 animate-in fade-in zoom-in-95 duration-100"
                      >
                        <button
                          type="button"
                          onClick={() => {
                            setFilterParentCat('all');
                            setTypePage(1);
                            setIsFilterCatDropdownOpen(false);
                          }}
                          className={`w-full px-2.5 py-2 rounded-lg text-left text-xs font-medium flex items-center justify-between gap-2 transition-colors cursor-pointer ${
                            filterParentCat === 'all'
                              ? 'bg-primary/10 text-primary font-bold'
                              : 'text-main hover:bg-surface'
                          }`}
                        >
                          <span className="truncate">{t('resourceManagement.allFolders')}</span>
                          {filterParentCat === 'all' && (
                            <i className="fa-solid fa-check text-primary text-xs shrink-0" />
                          )}
                        </button>

                        <div className="my-1 border-t border-border-subtle" />

                        {categories.map((c) => {
                          const isSelected = String(c.id) === filterParentCat;
                          return (
                            <button
                              key={c.id}
                              type="button"
                              onClick={() => {
                                setFilterParentCat(String(c.id));
                                setTypePage(1);
                                setIsFilterCatDropdownOpen(false);
                              }}
                              className={`w-full px-2.5 py-2 rounded-lg text-left text-xs font-medium flex items-center justify-between gap-2 transition-colors cursor-pointer ${
                                isSelected
                                  ? 'bg-primary/10 text-primary font-bold'
                                  : 'text-main hover:bg-surface'
                              }`}
                            >
                              <span className="truncate flex items-center gap-2">
                                <i className="fa-solid fa-folder text-primary/70 text-xs shrink-0" />
                                <span className="truncate">{c.ten_tai_lieu}</span>
                              </span>
                              {isSelected && (
                                <i className="fa-solid fa-check text-primary text-xs shrink-0" />
                              )}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Ô tìm nhanh theo tên loại */}
                  <div className="relative w-full sm:flex-1 sm:max-w-xs">
                    <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none" />
                    <input
                      type="text"
                      placeholder={t('resourceManagement.typeSearchPlaceholder')}
                      value={typeSearch}
                      onChange={(e) => {
                        setTypeSearch(e.target.value);
                        setTypePage(1);
                      }}
                      className="w-full pl-8 pr-8 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary transition-all shadow-2xs"
                    />
                    {typeSearch && (
                      <button
                        type="button"
                        onClick={() => {
                          setTypeSearch('');
                          setTypePage(1);
                        }}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-main text-xs p-1 cursor-pointer"
                        title={t('resourceManagement.clearSearch')}
                      >
                        <i className="fa-solid fa-xmark" />
                      </button>
                    )}
                  </div>
                </div>

                <Button
                  variant="primary"
                  size="sm"
                  icon="fa-plus"
                  disabled={!isAdmin}
                  onClick={() => {
                    if (!isAdmin) return;
                    handleOpenUnifiedCreate('type');
                  }}
                  className="h-9 px-3.5 rounded-xl text-xs font-bold shrink-0 shadow-sm hover:shadow-glow disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto justify-center"
                  title={isAdmin ? t('resourceManagement.addNewTypeTitle') : t('resourceManagement.adminOnlyType')}
                >
                  {t('resourceManagement.addNew')}
                </Button>
              </div>

              {/* Bảng danh sách Loại tài liệu */}
              <div className="w-full overflow-x-auto rounded-xl border border-border-subtle bg-surface shadow-2xs">
                <table className="w-full text-left text-xs border-collapse min-w-full">
                  <thead className="bg-surface-elevated font-bold text-muted uppercase tracking-wider border-b border-border-subtle">
                    <tr>
                      <th className="px-3 sm:px-4 py-3 min-w-[140px] sm:min-w-[200px]">{t('resourceManagement.colTypeName')}</th>
                      <th className="hidden sm:table-cell px-3 py-3 w-36 sm:w-48">{t('resourceManagement.colParentCat')}</th>
                      <th className="hidden sm:table-cell px-3 py-3 w-24 sm:w-28 text-center">{t('resourceManagement.colScope')}</th>
                      <th className="hidden md:table-cell px-3 py-3 min-w-[160px]">{t('resourceManagement.colNotes')}</th>
                      <th className="px-2 sm:px-3 py-3 w-12 sm:w-20 text-center whitespace-nowrap">{t('resourceManagement.colActions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {filteredTypes.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-10 text-center text-muted">
                          <i className="fa-solid fa-tags text-2xl mb-2 block opacity-40" />
                          {types.length === 0
                            ? t('resourceManagement.emptyTypesHint')
                            : t('resourceManagement.noMatchingTypes')}
                        </td>
                      </tr>
                    ) : (
                      paginatedTypes.map((typeItem) => {
                        const parentCat = categories.find((c) => c.id === typeItem.dm_tai_lieu);
                        return (
                          <tr
                            key={typeItem.id}
                            className="hover:bg-surface-elevated/70 transition-colors"
                          >
                            <td className="px-3 sm:px-4 py-2.5 sm:py-3 font-semibold text-main">
                              <div className="flex items-start gap-2">
                                <div className="mt-0.5 shrink-0">
                                  <i
                                    className={`fa-solid ${
                                      typeItem.is_public ? 'fa-tag text-primary/75' : 'fa-lock text-amber-500'
                                    } text-xs`}
                                  />
                                </div>
                                <div className="min-w-0 flex-1">
                                  <span className="text-xs sm:text-sm font-semibold text-main block leading-snug">
                                    {typeItem.ten_loai}
                                  </span>

                                  {/* Sub-line tinh gọn trên Mobile: Thư mục cha + Badge phạm vi */}
                                  <div className="flex items-center gap-2 mt-1 sm:hidden flex-wrap text-[11px]">
                                    <span className="text-secondary inline-flex items-center gap-1 truncate max-w-[170px]">
                                      <i className="fa-solid fa-folder text-[10px] text-primary/60 shrink-0" />
                                      <span className="truncate">{parentCat?.ten_tai_lieu || `Thư mục #${typeItem.dm_tai_lieu}`}</span>
                                    </span>
                                    {typeItem.is_public ? (
                                      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded-full border border-emerald-500/20 shrink-0">
                                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                                        {t('resourceManagement.scopePublic')}
                                      </span>
                                    ) : (
                                      <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-700 dark:text-amber-400 bg-amber-500/10 px-1.5 py-0.2 rounded-full border border-amber-500/20 shrink-0">
                                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                                        {t('resourceManagement.scopeInternal')}
                                      </span>
                                    )}
                                  </div>

                                  {/* Ghi chú trên mobile nếu có */}
                                  {typeItem.ghi_chu && (
                                    <p className="sm:hidden text-[11px] text-muted line-clamp-1 mt-0.5 leading-tight font-normal">
                                      {typeItem.ghi_chu}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </td>
                            <td className="hidden sm:table-cell px-3 py-3 text-secondary font-medium">
                              {parentCat?.ten_tai_lieu || `Thư mục #${typeItem.dm_tai_lieu}`}
                            </td>
                            <td className="hidden sm:table-cell px-3 py-3 text-center">
                              {typeItem.is_public ? (
                                <Badge variant="success" size="sm">
                                  {t('resourceManagement.scopePublic')}
                                </Badge>
                              ) : (
                                <Badge variant="warning" size="sm">
                                  {t('resourceManagement.scopeInternal')}
                                </Badge>
                              )}
                            </td>
                            <td className="hidden md:table-cell px-3 py-3 text-muted">{typeItem.ghi_chu || '-'}</td>
                            <td
                              className="px-2 sm:px-3 py-2.5 sm:py-3 text-center whitespace-nowrap align-middle"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <button
                                type="button"
                                data-menu-trigger="true"
                                onClick={(e) => handleOpenTypeMenu(e, typeItem.id)}
                                className={`w-7 h-7 rounded-lg inline-flex items-center justify-center transition-colors cursor-pointer ${
                                  activeMenuTypeId === typeItem.id
                                    ? 'bg-primary text-white shadow-xs'
                                    : 'text-muted hover:text-main hover:bg-surface-elevated'
                                }`}
                                title={t('resourceManagement.actionMenu')}
                                aria-label={t('resourceManagement.actionsForType', { name: typeItem.ten_loai })}
                              >
                                <i className="fa-solid fa-ellipsis text-xs" />
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>

                {/* Thanh phân trang Loại tài liệu */}
                {filteredTypes.length > 0 && (
                  <ModalPagination
                    currentPage={effectiveTypePage}
                    totalPages={totalTypePages}
                    pageSize={typePageSize}
                    totalItems={filteredTypes.length}
                    onPageChange={(p) => {
                      setTypePage(p);
                      closeAllMenus();
                    }}
                    onPageSizeChange={(newSize) => {
                      setTypePageSize(newSize);
                      setTypePage(1);
                      closeAllMenus();
                    }}
                    itemLabel={t('resourceManagement.itemLabelTypes')}
                  />
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer Modal */}
        <div className="px-4 sm:px-6 py-3 sm:py-3.5 border-t border-border-subtle bg-surface-elevated flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 sm:gap-3 shrink-0">
          <span className="text-xs text-muted">
            {t('resourceManagement.totalSummary', { catCount: String(categories.length), typeCount: String(types.length) })}
          </span>
          <div className="flex items-center justify-end gap-2">
            <Button variant="outline" size="sm" onClick={onClose} className="text-xs font-semibold">
              {t('resourceManagement.close')}
            </Button>
          </div>
        </div>
      </div>

      {/* ============================================================================ */}
      {/* DIALOG TẠO MỚI / CHỈNH SỬA HỢP NHẤT (POPUP CON RIÊNG BIỆT KHÔNG ĐẨY BẢNG)     */}
      {/* ============================================================================ */}
      {isUnifiedModalOpen && (
        <div
          className="fixed inset-0 z-[10001] flex items-center justify-center p-2 sm:p-5 bg-black/60 backdrop-blur-xs animate-fade-in"
        >
          <div
            className="w-full max-w-xl bg-surface rounded-2xl border border-border-subtle shadow-2xl overflow-hidden animate-zoom-in flex flex-col max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header Dialog */}
            <div className="flex items-center justify-between px-4 sm:px-5 py-3.5 sm:py-4 border-b border-border-subtle bg-surface-elevated shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
                  <i
                    className={`fa-solid ${
                      unifiedTarget === 'category' ? 'fa-folder' : 'fa-tags'
                    } text-sm`}
                  />
                </div>
                <div>
                  <h3 className="text-sm sm:text-base font-bold text-main">
                    {unifiedMode === 'create'
                      ? t('resourceManagement.unifiedCreateTitle')
                      : unifiedTarget === 'category'
                        ? t('resourceManagement.unifiedEditCatTitle')
                        : t('resourceManagement.unifiedEditTypeTitle')}
                  </h3>
                  <p className="text-[11px] text-muted">
                    {unifiedMode === 'create'
                      ? t('resourceManagement.unifiedCreateSubtitle')
                      : t('resourceManagement.unifiedEditSubtitle')}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleSafeCloseUnified}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface transition-colors cursor-pointer"
                aria-label={t('resourceManagement.close')}
              >
                <i className="fa-solid fa-xmark text-sm" />
              </button>
            </div>

            {/* Form Body */}
            <form onSubmit={handleUnifiedSubmit} className="flex flex-col flex-1 min-h-0">
              <div className="flex-1 overflow-y-auto p-3.5 sm:p-5 space-y-3.5 sm:space-y-4">
                {/* Khi ở chế độ Tạo mới: Thanh Segmented Switcher chọn Cấp 1 hoặc Cấp 2 */}
                {unifiedMode === 'create' && (
                  <div className="p-1 bg-surface-elevated rounded-xl flex items-center gap-1 border border-border-subtle">
                    <button
                      type="button"
                      onClick={() => {
                        setUnifiedTarget('category');
                        setIsUnifiedDirty(true);
                      }}
                      className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                        unifiedTarget === 'category'
                          ? 'bg-primary text-white shadow-xs'
                          : 'text-secondary hover:text-main hover:bg-surface'
                      }`}
                    >
                      <i className="fa-solid fa-folder text-xs" />
                      <span>{t('resourceManagement.folderLevel1')}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setUnifiedTarget('type');
                        setIsUnifiedDirty(true);
                      }}
                      className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                        unifiedTarget === 'type'
                          ? 'bg-primary text-white shadow-xs'
                          : 'text-secondary hover:text-main hover:bg-surface'
                      }`}
                    >
                      <i className="fa-solid fa-tags text-xs" />
                      <span>{t('resourceManagement.docTypeLevel2')}</span>
                    </button>
                  </div>
                )}

                {/* NỘI DUNG 1: FORM THƯ MỤC (CẤP 1) */}
                {unifiedTarget === 'category' && (
                  <div className="space-y-3.5">
                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                      {/* STT ưu tiên */}
                      <div className="sm:col-span-4">
                        <label className="text-xs font-semibold text-main block mb-1">
                          {t('resourceManagement.colOrderPriority')} <span className="text-danger">*</span>
                        </label>
                        <input
                          type="number"
                          min={1}
                          value={catForm.stt_uu_tien}
                          onChange={(e) => {
                            const val = e.target.value === '' ? '' : Number(e.target.value);
                            setCatForm({ ...catForm, stt_uu_tien: val });
                            if (catError && catError.includes('STT')) setCatError(null);
                            setIsUnifiedDirty(true);
                          }}
                          placeholder={t('resourceManagement.orderPlaceholder')}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs font-bold text-main focus:outline-hidden focus:border-primary shadow-2xs"
                          required
                        />
                        {catError && catError.includes('STT') && (
                          <p className="text-danger text-[11px] mt-1 font-medium">{catError}</p>
                        )}
                      </div>

                      {/* Ký hiệu thư mục */}
                      <div className="sm:col-span-8">
                        <label className="text-xs font-semibold text-main block mb-1">
                          {t('resourceManagement.catCodeLabel')}
                        </label>
                        <input
                          type="text"
                          placeholder={t('resourceManagement.placeholderCatCode')}
                          value={catForm.ky_hieu}
                          onChange={(e) => {
                            setCatForm({ ...catForm, ky_hieu: e.target.value });
                            setIsUnifiedDirty(true);
                          }}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary shadow-2xs"
                        />
                      </div>

                      {/* Tên thư mục (*) */}
                      <div className="sm:col-span-12">
                        <label className="text-xs font-semibold text-main block mb-1">
                          {t('resourceManagement.colCatName')} <span className="text-danger">*</span>
                        </label>
                        <input
                          type="text"
                          placeholder={t('resourceManagement.placeholderCatName')}
                          value={catForm.ten_tai_lieu}
                          onChange={(e) => {
                            setCatForm({ ...catForm, ten_tai_lieu: e.target.value });
                            if (catError && catError !== 'STT ưu tiên đã tồn tại') setCatError(null);
                            setIsUnifiedDirty(true);
                          }}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary shadow-2xs"
                          required
                        />
                        {catError && catError !== 'STT ưu tiên đã tồn tại' && (
                          <p className="text-danger text-[11px] mt-1 font-medium">{catError}</p>
                        )}
                      </div>

                      {/* Người lập */}
                      <div className="sm:col-span-6">
                        <label className="text-xs font-semibold text-main block mb-1">
                          {t('resourceManagement.catCreatorLabel')}
                        </label>
                        <input
                          type="text"
                          value={catForm.nguoi_lap_name || defaultAdminAuthor}
                          readOnly
                          className="w-full px-3 py-2 bg-surface-elevated/70 border border-border-subtle rounded-xl text-xs text-main font-semibold cursor-not-allowed select-none shadow-2xs"
                          title={t('resourceManagement.adminCreatorTooltip')}
                        />
                      </div>

                      {/* Ngày lập */}
                      <div className="sm:col-span-6">
                        <label className="text-xs font-semibold text-main block mb-1">{t('resourceManagement.colCatDate')}</label>
                        <input
                          type="date"
                          value={catForm.ngay_lap}
                          onChange={(e) => {
                            setCatForm({ ...catForm, ngay_lap: e.target.value });
                            setIsUnifiedDirty(true);
                          }}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary shadow-2xs"
                        />
                      </div>

                      {/* Ghi chú */}
                      <div className="sm:col-span-12">
                        <label className="text-xs font-semibold text-main block mb-1">{t('resourceManagement.colNotes')}</label>
                        <input
                          type="text"
                          placeholder={t('resourceManagement.placeholderCatNotes')}
                          value={catForm.ghi_chu}
                          onChange={(e) => {
                            setCatForm({ ...catForm, ghi_chu: e.target.value });
                            setIsUnifiedDirty(true);
                          }}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary shadow-2xs"
                        />
                      </div>
                    </div>

                    {/* Tùy chọn Thêm nhanh các loại tài liệu con (Khi tạo mới) */}
                    {unifiedMode === 'create' && (
                      <div className="pt-3 border-t border-border-subtle space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-bold text-main flex items-center gap-1.5">
                            <i className="fa-solid fa-sitemap text-primary text-xs" />
                            <span>{t('resourceManagement.quickAddSubtypesLabel')}</span>
                          </label>
                          <span className="text-[11px] text-muted">
                            {t('resourceManagement.addedCount', { count: catChildTypes.length })}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            placeholder={t('resourceManagement.quickAddSubtypesPlaceholder')}
                            value={childTypeInput}
                            onChange={(e) => setChildTypeInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault();
                                handleAddChildType();
                              }
                            }}
                            className="flex-1 px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary shadow-2xs"
                          />
                          <Button
                            type="button"
                            variant={childTypeInput.trim() ? 'primary' : 'secondary'}
                            size="sm"
                            icon="fa-plus"
                            onClick={handleAddChildType}
                            className="text-xs shrink-0 rounded-xl font-semibold shadow-2xs"
                          >
                            {t('resourceManagement.addBtn')}
                          </Button>
                        </div>

                        {catChildTypes.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1 max-h-24 overflow-y-auto">
                            {catChildTypes.map((childName, idx) => (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/25 shadow-2xs"
                              >
                                <i className="fa-solid fa-tag text-[10px]" />
                                <span>{childName}</span>
                                <button
                                  type="button"
                                  onClick={() => handleRemoveChildType(idx)}
                                  className="hover:text-danger ml-0.5 cursor-pointer text-xs"
                                  title={t('resourceManagement.removeThisType')}
                                >
                                  ×
                                </button>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* NỘI DUNG 2: FORM LOẠI TÀI LIỆU (CẤP 2) */}
                {unifiedTarget === 'type' && (
                  <div className="space-y-3.5">
                    {categories.length === 0 && (
                      <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-200 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-1">
                        <div className="flex items-center gap-2">
                          <i className="fa-solid fa-triangle-exclamation text-base text-amber-500 shrink-0" />
                          <span>{t('resourceManagement.noParentCatWarning')}</span>
                        </div>
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          onClick={() => setUnifiedTarget('category')}
                          className="text-xs shrink-0 font-bold"
                        >
                          <i className="fa-solid fa-folder-plus mr-1" />
                          {t('resourceManagement.switchToCreateFolder')}
                        </Button>
                      </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                      {/* Thư mục cha (*) - Custom Responsive Dropdown */}
                      <div className="sm:col-span-8 relative" ref={typeCatDropdownRef}>
                        <label className="text-xs font-semibold text-main block mb-1">
                          {t('resourceManagement.parentFolderRequired')} <span className="text-danger">*</span>
                        </label>
                        <button
                          type="button"
                          onClick={() => {
                            if (categories.length > 0) {
                              setIsTypeCatDropdownOpen((prev) => !prev);
                            }
                          }}
                          disabled={categories.length === 0}
                          aria-haspopup="listbox"
                          aria-expanded={isTypeCatDropdownOpen}
                          className={`w-full px-3 py-2 bg-surface border rounded-xl text-xs text-main flex items-center justify-between gap-2 shadow-2xs font-medium transition-colors cursor-pointer ${
                            categories.length === 0
                              ? 'opacity-60 cursor-not-allowed border-border-subtle'
                              : isTypeCatDropdownOpen
                                ? 'border-primary ring-1 ring-primary/20'
                                : 'border-border-subtle hover:border-primary/50'
                          }`}
                        >
                          <span className={`truncate text-left flex-1 ${!typeForm.dm_tai_lieu ? 'text-muted' : 'text-main'}`}>
                            {categories.length === 0
                              ? t('resourceManagement.noFoldersAvailable')
                              : categories.find((c) => c.id === Number(typeForm.dm_tai_lieu))?.ten_tai_lieu || t('resourceManagement.noFoldersAvailable')}
                          </span>
                          <i
                            className={`fa-solid fa-chevron-down text-xs text-muted transition-transform duration-200 shrink-0 ${
                              isTypeCatDropdownOpen ? 'rotate-180 text-primary' : ''
                            }`}
                          />
                        </button>

                        {/* Native select ẩn để đảm bảo HTML form validation & tests */}
                        <select
                          value={typeForm.dm_tai_lieu}
                          onChange={(e) => {
                            setTypeForm({ ...typeForm, dm_tai_lieu: Number(e.target.value) });
                            setIsUnifiedDirty(true);
                          }}
                          className="sr-only"
                          tabIndex={-1}
                          aria-hidden="true"
                          required
                          disabled={categories.length === 0}
                        >
                          {categories.length === 0 ? (
                            <option value="">{t('resourceManagement.noFoldersAvailable')}</option>
                          ) : (
                            categories.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.ten_tai_lieu}
                              </option>
                            ))
                          )}
                        </select>

                        {/* Popup dropdown menu không bao giờ lòi ra ngoài */}
                        {isTypeCatDropdownOpen && (
                          <div
                            role="listbox"
                            className="absolute left-0 right-0 top-full mt-1.5 w-full max-w-full bg-surface-elevated rounded-xl border border-border-subtle shadow-2xl p-1.5 z-50 max-h-56 overflow-y-auto space-y-0.5 animate-in fade-in zoom-in-95 duration-100"
                          >
                            {categories.map((c) => {
                              const isSelected = typeForm.dm_tai_lieu === c.id;
                              return (
                                <button
                                  key={c.id}
                                  type="button"
                                  onClick={() => {
                                    setTypeForm({ ...typeForm, dm_tai_lieu: c.id });
                                    setIsUnifiedDirty(true);
                                    setIsTypeCatDropdownOpen(false);
                                  }}
                                  className={`w-full px-2.5 py-2 rounded-lg text-left text-xs font-medium flex items-center justify-between gap-2 transition-colors cursor-pointer ${
                                    isSelected
                                      ? 'bg-primary/10 text-primary font-bold'
                                      : 'text-main hover:bg-surface'
                                  }`}
                                >
                                  <span className="truncate flex items-center gap-2">
                                    <i className="fa-solid fa-folder text-primary/70 text-xs shrink-0" />
                                    <span className="truncate">{c.ten_tai_lieu}</span>
                                  </span>
                                  {isSelected && (
                                    <i className="fa-solid fa-check text-primary text-xs shrink-0" />
                                  )}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      {/* Phạm vi: Công khai checkbox */}
                      <div className="sm:col-span-4 flex items-center pt-1 sm:pt-5">
                        <label className="inline-flex items-center gap-2 cursor-pointer text-xs font-semibold text-main select-none">
                          <input
                            type="checkbox"
                            checked={typeForm.is_public}
                            onChange={(e) => {
                              setTypeForm({ ...typeForm, is_public: e.target.checked });
                              setIsUnifiedDirty(true);
                            }}
                            className="rounded border-border-subtle text-primary focus:ring-0 cursor-pointer w-4 h-4"
                          />
                          <span>{t('resourceManagement.publicSharedScope')}</span>
                        </label>
                      </div>

                      {/* Tên loại tài liệu (*) */}
                      <div className="sm:col-span-12">
                        <label className="text-xs font-semibold text-main block mb-1">
                          {t('resourceManagement.colTypeName')} <span className="text-danger">*</span>
                        </label>
                        <input
                          type="text"
                          placeholder={t('resourceManagement.placeholderTypeName')}
                          value={typeForm.ten_loai}
                          onChange={(e) => {
                            setTypeForm({ ...typeForm, ten_loai: e.target.value });
                            setTypeError(null);
                            setIsUnifiedDirty(true);
                          }}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary shadow-2xs"
                          required
                        />
                        {typeError && (
                          <p className="text-danger text-[11px] mt-1 font-medium">{typeError}</p>
                        )}
                      </div>

                      {/* Ghi chú */}
                      <div className="sm:col-span-12">
                        <label className="text-xs font-semibold text-main block mb-1">{t('resourceManagement.colNotes')}</label>
                        <input
                          type="text"
                          placeholder={t('resourceManagement.placeholderTypeNotes')}
                          value={typeForm.ghi_chu}
                          onChange={(e) => {
                            setTypeForm({ ...typeForm, ghi_chu: e.target.value });
                            setIsUnifiedDirty(true);
                          }}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary shadow-2xs"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Dialog Footer */}
              <div className="px-4 sm:px-5 py-3 sm:py-3.5 border-t border-border-subtle bg-surface-elevated flex items-center justify-end flex-wrap sm:flex-nowrap gap-2 sm:gap-2.5 shrink-0">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCancelBtnClick}
                  className="rounded-xl text-xs font-semibold"
                >
                  {t('resourceManagement.cancel')}
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  icon={isSubmittingUnified ? 'fa-spinner fa-spin' : 'fa-check'}
                  disabled={(unifiedTarget === 'type' && categories.length === 0) || isSubmittingUnified}
                  className="rounded-xl text-xs font-bold shadow-sm hover:shadow-glow px-4"
                >
                  {isSubmittingUnified
                    ? t('resourceManagement.saving')
                    : unifiedMode === 'create'
                      ? unifiedTarget === 'category'
                        ? t('resourceManagement.saveFolder')
                        : t('resourceManagement.saveType')
                      : t('resourceManagement.saveChanges')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Dropdown Menu Floating cho Thư mục — chỉ hiện khi đang ở tab Thư mục */}
      {activeTab === 'category' && activeMenuCatId !== null && menuPos && (
        <div
          data-floating-menu="true"
          className="fixed z-[10002] w-28 bg-surface rounded-xl border border-border-subtle shadow-xl py-1 animate-zoom-in"
          style={{ top: `${menuPos.top}px`, right: `${menuPos.right}px` }}
          onClick={(e) => e.stopPropagation()}
        >
          {isAdmin ? (
            <>
              <button
                type="button"
                onClick={() => {
                  const cat = categories.find((c) => c.id === activeMenuCatId);
                  if (cat) handleOpenEditCat(cat);
                  closeAllMenus();
                }}
                className="w-full px-3 py-1.5 text-xs text-left text-main hover:bg-surface-elevated flex items-center gap-2 cursor-pointer font-medium"
              >
                <i className="fa-solid fa-pen-to-square text-primary text-xs" />
                <span>{t('resourceManagement.edit')}</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  const cat = categories.find((c) => c.id === activeMenuCatId);
                  if (cat) handleDeleteCategoryWithCheck(cat);
                  closeAllMenus();
                }}
                className="w-full px-3 py-1.5 text-xs text-left text-danger hover:bg-danger/10 flex items-center gap-2 cursor-pointer font-medium"
              >
                <i className="fa-solid fa-trash-can text-danger text-xs" />
                <span>{t('resourceManagement.delete')}</span>
              </button>
            </>
          ) : (
            <div className="px-3 py-1.5 text-xs text-muted italic text-center">
              {t('resourceManagement.readOnlyBadge')}
            </div>
          )}
        </div>
      )}

      {/* Dropdown Menu Floating cho Loại tài liệu — chỉ hiện khi đang ở tab Loại tài liệu */}
      {activeTab === 'type' && activeMenuTypeId !== null && menuPos && (
        <div
          data-floating-menu="true"
          className="fixed z-[10002] w-28 bg-surface rounded-xl border border-border-subtle shadow-xl py-1 animate-zoom-in"
          style={{ top: `${menuPos.top}px`, right: `${menuPos.right}px` }}
          onClick={(e) => e.stopPropagation()}
        >
          {isAdmin ? (
            <>
              <button
                type="button"
                onClick={() => {
                  const t = types.find((item) => item.id === activeMenuTypeId);
                  if (t) handleOpenEditType(t);
                  closeAllMenus();
                }}
                className="w-full px-3 py-1.5 text-xs text-left text-main hover:bg-surface-elevated flex items-center gap-2 cursor-pointer font-medium"
              >
                <i className="fa-solid fa-pen-to-square text-primary text-xs" />
                <span>{t('resourceManagement.edit')}</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  const t = types.find((item) => item.id === activeMenuTypeId);
                  if (t) handleDeleteTypeConfirm(t);
                  closeAllMenus();
                }}
                className="w-full px-3 py-1.5 text-xs text-left text-danger hover:bg-danger/10 flex items-center gap-2 cursor-pointer font-medium"
              >
                <i className="fa-solid fa-trash-can text-danger text-xs" />
                <span>{t('resourceManagement.delete')}</span>
              </button>
            </>
          ) : (
            <div className="px-3 py-1.5 text-xs text-muted italic text-center">
              {t('resourceManagement.readOnlyBadge')}
            </div>
          )}
        </div>
      )}

      {/* Modal xác nhận xóa Thư mục */}
      <ConfirmationModal
        isOpen={deleteCatTarget !== null}
        onClose={() => setDeleteCatTarget(null)}
        onConfirm={async () => {
          if (deleteCatTarget) {
            const catId = deleteCatTarget.id;
            setDeleteCatTarget(null);
            await onDeleteCategory(catId);
          }
        }}
        variant="danger"
        title={t('resourceManagement.confirmDeleteFolderTitle')}
        message={t('resourceManagement.confirmDeleteFolderMsg', { name: deleteCatTarget?.ten_tai_lieu || '' })}
        subMessage={t('resourceManagement.confirmDeleteFolderSub')}
        confirmText={t('resourceManagement.deleteFolderBtn')}
        cancelText={t('resourceManagement.cancel')}
      />

      {/* Modal thông báo chặn xóa thư mục khi còn loại con */}
      <ConfirmationModal
        isOpen={deleteBlockedCat !== null}
        onClose={() => setDeleteBlockedCat(null)}
        onConfirm={() => setDeleteBlockedCat(null)}
        variant="warning"
        title={t('resourceManagement.cannotDeleteFolderTitle')}
        message={t('resourceManagement.cannotDeleteFolderMsg', {
          name: deleteBlockedCat?.cat.ten_tai_lieu || '',
          count: String(deleteBlockedCat?.count || 0),
        })}
        subMessage={t('resourceManagement.cannotDeleteFolderSub')}
        confirmText={t('resourceManagement.understood')}
        cancelText={t('resourceManagement.close')}
        headerIcon="fa-triangle-exclamation"
        confirmIcon=""
      />

      {/* Modal xác nhận xóa Loại tài liệu */}
      <ConfirmationModal
        isOpen={deleteTypeTarget !== null}
        onClose={() => setDeleteTypeTarget(null)}
        onConfirm={async () => {
          if (deleteTypeTarget) {
            const typeId = deleteTypeTarget.id;
            setDeleteTypeTarget(null);
            await onDeleteType(typeId);
          }
        }}
        variant="danger"
        title={t('resourceManagement.confirmDeleteTypeTitle')}
        message={t('resourceManagement.confirmDeleteTypeMsg', { name: deleteTypeTarget?.ten_loai || '' })}
        subMessage={t('resourceManagement.confirmDeleteTypeSub')}
        confirmText={t('resourceManagement.deleteTypeBtn')}
        cancelText={t('resourceManagement.cancel')}
      />

      {/* Modal xác nhận hủy form Thêm mới / Chỉnh sửa Thư mục & Loại tài liệu */}
      <ConfirmationModal
        isOpen={isConfirmDiscardUnifiedOpen}
        onClose={() => setIsConfirmDiscardUnifiedOpen(false)}
        onConfirm={() => {
          setIsConfirmDiscardUnifiedOpen(false);
          setIsUnifiedDirty(false);
          setIsUnifiedModalOpen(false);
        }}
        title={t('resourceManagement.confirmDiscardTitle')}
        message={t('resourceManagement.confirmDiscardMsg')}
        subMessage={t('resourceManagement.confirmDiscardSub')}
        confirmText={t('resourceManagement.confirmDiscardBtn')}
        cancelText={t('resourceManagement.continueEditingBtn')}
        variant="warning"
        headerIcon="fa-triangle-exclamation"
        confirmIcon="fa-arrow-rotate-left"
      />
    </div>,
    document.body
  );
};
