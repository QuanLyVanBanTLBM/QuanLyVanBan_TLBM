import React, { useState, useMemo, useEffect, useCallback } from 'react';
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
  onSaveCategory: (category: ResourceCategory, isEdit: boolean, childCount?: number) => void;
  onDeleteCategory: (id: number) => void;
  onSaveType: (type: ResourceType, isEdit: boolean, silent?: boolean) => void;
  onDeleteType: (id: number) => void;
}

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
    nguoi_lap_name: 'Thượng Mạnh Quỳnh',
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

  // Vị trí fixed của dropdown menu Thao tác — không bị cắt bởi overflow và lật lên khi ở đáy
  const [menuPos, setMenuPos] = useState<{ top: number; right: number } | null>(null);

  const closeAllMenus = () => {
    setActiveMenuCatId(null);
    setActiveMenuTypeId(null);
    setMenuPos(null);
  };

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
      right: Math.max(10, window.innerWidth - rect.right),
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
      right: Math.max(10, window.innerWidth - rect.right),
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

    // Khởi tạo form Thư mục: Tự động điền giá trị gợi ý mặc định ban đầu, cho phép chỉnh sửa tự do cả 3 trường
    const defaultAuthor = authService.getSession()?.fullName || 'Thượng Mạnh Quỳnh';
    setCatForm({
      stt_uu_tien: nextOrderNumber(),
      ky_hieu: '',
      ten_tai_lieu: '',
      nguoi_lap_name: defaultAuthor,
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
      nguoi_lap_name: cat.nguoi_lap_name || authService.getSession()?.fullName || 'Thượng Mạnh Quỳnh',
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
  const handleUnifiedSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (unifiedTarget === 'category') {
      // Validate Thư mục
      if (!catForm.ten_tai_lieu.trim()) {
        setCatError('Vui lòng nhập tên thư mục');
        return;
      }

      if (!catForm.stt_uu_tien || Number(catForm.stt_uu_tien) < 1) {
        setCatError('Vui lòng nhập STT ưu tiên hợp lệ (tối thiểu là 1)');
        return;
      }

      const sttNum = Number(catForm.stt_uu_tien);
      const isDuplicateOrder = categories.some(
        (c) => c.stt_uu_tien === sttNum && c.id !== editingCatId
      );
      if (isDuplicateOrder) {
        setCatError('STT ưu tiên đã tồn tại');
        return;
      }

      const categoryId = editingCatId || Date.now();
      const payload: ResourceCategory = {
        id: categoryId,
        stt_uu_tien: sttNum,
        ky_hieu: catForm.ky_hieu.trim(),
        ten_tai_lieu: catForm.ten_tai_lieu.trim(),
        nguoi_lap_name: catForm.nguoi_lap_name.trim(),
        ngay_lap: catForm.ngay_lap,
        ghi_chu: catForm.ghi_chu.trim(),
      };

      // Tự động gom các loại con đã thêm qua chip VÀ nội dung đang gõ dở trong ô input nếu người dùng chưa bấm "+ Thêm"
      const finalChildTypes = [...catChildTypes];
      const pendingChild = childTypeInput.trim();
      if (pendingChild && !finalChildTypes.includes(pendingChild)) {
        finalChildTypes.push(pendingChild);
      }

      onSaveCategory(payload, Boolean(editingCatId), finalChildTypes.length);

      // Nếu tạo mới thư mục và có thêm kèm các loại con
      if (!editingCatId && finalChildTypes.length > 0) {
        finalChildTypes.forEach((typeName, idx) => {
          onSaveType(
            {
              id: Date.now() + idx + 1,
              dm_tai_lieu: categoryId,
              ten_loai: typeName.trim(),
              is_public: true,
              ghi_chu: `Khởi tạo cùng thư mục ${catForm.ten_tai_lieu.trim()}`,
              ngay_lap: catForm.ngay_lap,
            },
            false,
            true
          );
        });
      }

      setIsUnifiedDirty(false);
      setIsConfirmDiscardUnifiedOpen(false);
      setIsUnifiedModalOpen(false);
    } else {
      // Validate & Lưu Loại tài liệu
      if (categories.length === 0 || !typeForm.dm_tai_lieu) {
        setTypeError('Chưa có Thư mục Cấp 1 nào. Vui lòng tạo Thư mục Cấp 1 trước khi tạo Loại tài liệu.');
        return;
      }

      if (!typeForm.ten_loai.trim()) {
        setTypeError('Vui lòng nhập tên loại tài liệu');
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

      onSaveType(payload, Boolean(editingTypeId));
      setIsUnifiedDirty(false);
      setIsConfirmDiscardUnifiedOpen(false);
      setIsUnifiedModalOpen(false);
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

  if (!isOpen) return null;
  if (typeof document === 'undefined') return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-xs animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full max-w-4xl max-h-[90vh] bg-surface rounded-2xl border border-border-subtle shadow-2xl flex flex-col overflow-hidden animate-slide-in-bottom"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Modal */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle bg-surface-elevated shrink-0">
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
            aria-label="Đóng popup"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Tab Switcher (Thư mục | Loại tài liệu) */}
        <div className="flex border-b border-border-subtle px-6 bg-surface shrink-0">
          <button
            type="button"
            onClick={() => {
              setActiveTab('category');
              setCatDeleteBlockedMsg(null);
              closeAllMenus();
            }}
            className={`py-3 px-4 text-xs sm:text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer ${
              activeTab === 'category'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-secondary hover:text-main'
            }`}
          >
            <i className="fa-solid fa-folder" />
            <span>{t('resourceManagement.tabFolders')}</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
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
            className={`py-3 px-4 text-xs sm:text-sm font-semibold border-b-2 flex items-center gap-2 transition-colors cursor-pointer ${
              activeTab === 'type'
                ? 'border-primary text-primary font-bold'
                : 'border-transparent text-secondary hover:text-main'
            }`}
          >
            <i className="fa-solid fa-tags" />
            <span>{t('resourceManagement.tabTypes')}</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
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
        <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0">
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
                aria-label="Đóng cảnh báo"
              >
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
          )}

          {/* TAB 1: THƯ MỤC */}
          {activeTab === 'category' && (
            <div className="space-y-4">
              {/* Thanh công cụ Tab Thư mục */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                <div className="relative flex-1 max-w-md">
                  <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none" />
                  <input
                    type="text"
                    placeholder={t('resourceManagement.catSearchPlaceholder')}
                    value={catSearch}
                    onChange={(e) => setCatSearch(e.target.value)}
                    className="w-full pl-8 pr-8 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary transition-all shadow-2xs"
                  />
                  {catSearch && (
                    <button
                      type="button"
                      onClick={() => setCatSearch('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-main text-xs p-1 cursor-pointer"
                      title="Xóa tìm kiếm"
                    >
                      <i className="fa-solid fa-xmark" />
                    </button>
                  )}
                </div>

                <Button
                  variant="primary"
                  size="sm"
                  icon="fa-plus"
                  onClick={() => handleOpenUnifiedCreate('category')}
                  className="h-9 px-3.5 rounded-xl text-xs font-bold shrink-0 shadow-sm hover:shadow-glow"
                  title={t('resourceManagement.addNew')}
                >
                  {t('resourceManagement.addNew')}
                </Button>
              </div>

              {/* Bảng danh sách Thư mục */}
              <div className="w-full overflow-x-auto rounded-xl border border-border-subtle bg-surface shadow-2xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-surface-elevated font-bold text-muted uppercase tracking-wider border-b border-border-subtle">
                    <tr>
                      <th className="px-3 py-3 w-16 text-center">{t('resourceManagement.colOrder')}</th>
                      <th className="px-3 py-3 w-28">{t('resourceManagement.colCatCode')}</th>
                      <th className="px-4 py-3 min-w-[200px]">{t('resourceManagement.colCatName')}</th>
                      <th className="px-3 py-3 w-32">{t('resourceManagement.colCatDate')}</th>
                      <th className="px-3 py-3 w-28 text-center">{t('resourceManagement.colCatSubtypes')}</th>
                      <th className="px-3 py-3 w-24 text-center whitespace-nowrap">{t('resourceManagement.colActions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {filteredCategories.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-10 text-center text-muted">
                          <i className="fa-solid fa-folder-open text-2xl mb-2 block opacity-40" />
                          {categories.length === 0
                            ? 'Chưa có Thư mục Cấp 1 nào. Bấm "Thêm mới" để tạo thư mục đầu tiên.'
                            : 'Không tìm thấy thư mục nào phù hợp'}
                        </td>
                      </tr>
                    ) : (
                      filteredCategories.map((cat) => {
                        const childCount = types.filter((t) => t.dm_tai_lieu === cat.id).length;
                        return (
                          <tr key={cat.id} className="hover:bg-surface-elevated/70 transition-colors">
                            <td className="px-3 py-3 text-center font-bold text-primary font-mono">
                              {cat.stt_uu_tien}
                            </td>
                            <td className="px-3 py-3 font-mono font-medium text-secondary">
                              {cat.ky_hieu || '-'}
                            </td>
                            <td className="px-4 py-3">
                              <span className="font-semibold text-main block">{cat.ten_tai_lieu}</span>
                              {cat.ghi_chu && (
                                <span className="text-[11px] text-muted truncate block max-w-sm mt-0.5">
                                  {cat.ghi_chu}
                                </span>
                              )}
                            </td>
                            <td className="px-3 py-3 text-secondary">{cat.ngay_lap || '-'}</td>
                            <td className="px-3 py-3 text-center">
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-surface-elevated text-secondary border border-border-subtle">
                                {childCount} loại
                              </span>
                            </td>
                            <td
                              className="px-3 py-3 text-center whitespace-nowrap"
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
                                title="Thao tác"
                                aria-label={`Thao tác với thư mục ${cat.ten_tai_lieu}`}
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
              </div>
            </div>
          )}

          {/* TAB 2: LOẠI TÀI LIỆU */}
          {activeTab === 'type' && (
            <div className="space-y-4">
              {/* Thanh công cụ Tab Loại tài liệu */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2 flex-1">
                  {/* Dropdown lọc Thư mục cha */}
                  <select
                    value={filterParentCat}
                    onChange={(e) => setFilterParentCat(e.target.value)}
                    className="h-9 px-3 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary cursor-pointer shrink-0 shadow-2xs font-medium"
                    aria-label="Lọc theo thư mục cha"
                  >
                    <option value="all">Tất cả thư mục</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.ten_tai_lieu}
                      </option>
                    ))}
                  </select>

                  {/* Ô tìm nhanh theo tên loại */}
                  <div className="relative flex-1 max-w-xs">
                    <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none" />
                    <input
                      type="text"
                      placeholder="Tìm tên loại tài liệu..."
                      value={typeSearch}
                      onChange={(e) => setTypeSearch(e.target.value)}
                      className="w-full pl-8 pr-8 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary transition-all shadow-2xs"
                    />
                    {typeSearch && (
                      <button
                        type="button"
                        onClick={() => setTypeSearch('')}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-main text-xs p-1 cursor-pointer"
                        title="Xóa tìm kiếm"
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
                  onClick={() => handleOpenUnifiedCreate('type')}
                  className="h-9 px-3.5 rounded-xl text-xs font-bold shrink-0 shadow-sm hover:shadow-glow"
                  title="Thêm mới Thư mục hoặc Loại tài liệu"
                >
                  Thêm mới
                </Button>
              </div>

              {/* Bảng danh sách Loại tài liệu */}
              <div className="w-full overflow-x-auto rounded-xl border border-border-subtle bg-surface shadow-2xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-surface-elevated font-bold text-muted uppercase tracking-wider border-b border-border-subtle">
                    <tr>
                      <th className="px-4 py-3 min-w-[200px]">{t('resourceManagement.colTypeName')}</th>
                      <th className="px-3 py-3 w-48">{t('resourceManagement.colParentCat')}</th>
                      <th className="px-3 py-3 w-28 text-center">{t('resourceManagement.colScope')}</th>
                      <th className="px-3 py-3 min-w-[160px]">{t('resourceManagement.colNotes')}</th>
                      <th className="px-3 py-3 w-24 text-center whitespace-nowrap">{t('resourceManagement.colActions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle">
                    {filteredTypes.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-10 text-center text-muted">
                          <i className="fa-solid fa-tags text-2xl mb-2 block opacity-40" />
                          {types.length === 0
                            ? 'Chưa có Loại tài liệu Cấp 2 nào. Bấm "Thêm mới" để tạo loại đầu tiên.'
                            : 'Không tìm thấy loại tài liệu nào phù hợp'}
                        </td>
                      </tr>
                    ) : (
                      filteredTypes.map((t) => {
                        const parentCat = categories.find((c) => c.id === t.dm_tai_lieu);
                        return (
                          <tr
                            key={t.id}
                            className="hover:bg-surface-elevated/70 transition-colors"
                          >
                            <td className="px-4 py-3 font-semibold text-main">
                              <span className="flex items-center gap-2">
                                <i
                                  className={`fa-solid ${
                                    t.is_public ? 'fa-tag text-primary/70' : 'fa-lock text-amber-500'
                                  } text-[11px]`}
                                />
                                <span>{t.ten_loai}</span>
                              </span>
                            </td>
                            <td className="px-3 py-3 text-secondary font-medium">
                              {parentCat?.ten_tai_lieu || `Thư mục #${t.dm_tai_lieu}`}
                            </td>
                            <td className="px-3 py-3 text-center">
                              {t.is_public ? (
                                <Badge variant="success" size="sm">
                                  Công khai
                                </Badge>
                              ) : (
                                <Badge variant="warning" size="sm">
                                  Nội bộ
                                </Badge>
                              )}
                            </td>
                            <td className="px-3 py-3 text-muted">{t.ghi_chu || '-'}</td>
                            <td
                              className="px-3 py-3 text-center whitespace-nowrap"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <button
                                type="button"
                                data-menu-trigger="true"
                                onClick={(e) => handleOpenTypeMenu(e, t.id)}
                                className={`w-7 h-7 rounded-lg inline-flex items-center justify-center transition-colors cursor-pointer ${
                                  activeMenuTypeId === t.id
                                    ? 'bg-primary text-white shadow-xs'
                                    : 'text-muted hover:text-main hover:bg-surface-elevated'
                                }`}
                                title="Thao tác"
                                aria-label={`Thao tác với loại ${t.ten_loai}`}
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
              </div>
            </div>
          )}
        </div>

        {/* Footer Modal */}
        <div className="px-6 py-3.5 border-t border-border-subtle bg-surface-elevated flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 shrink-0">
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
          className="fixed inset-0 z-[10001] flex items-center justify-center p-3 sm:p-5 bg-black/60 backdrop-blur-xs animate-fade-in"
        >
          <div
            className="w-full max-w-xl bg-surface rounded-2xl border border-border-subtle shadow-2xl overflow-hidden animate-zoom-in flex flex-col max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header Dialog */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle bg-surface-elevated shrink-0">
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
                      ? 'Thêm Mới Danh Mục / Loại Tài Liệu'
                      : unifiedTarget === 'category'
                        ? 'Chỉnh Sửa Thư Mục'
                        : 'Chỉnh Sửa Loại Tài Liệu'}
                  </h3>
                  <p className="text-[11px] text-muted">
                    {unifiedMode === 'create'
                      ? 'Lựa chọn cấp phân loại và nhập thông tin để tạo mới'
                      : 'Cập nhật lại thông tin cấu hình'}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleSafeCloseUnified}
                className="w-7 h-7 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface transition-colors cursor-pointer"
                aria-label="Đóng form"
              >
                <i className="fa-solid fa-xmark text-sm" />
              </button>
            </div>

            {/* Form Body */}
            <form onSubmit={handleUnifiedSubmit} className="flex flex-col flex-1 min-h-0">
              <div className="flex-1 overflow-y-auto p-5 space-y-4">
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
                      <span>Thư mục (Cấp 1)</span>
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
                      <span>Loại tài liệu (Cấp 2)</span>
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
                          STT ưu tiên <span className="text-danger">*</span>
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
                          placeholder="VD: 1, 2, 3..."
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs font-mono font-bold text-main focus:outline-hidden focus:border-primary shadow-2xs"
                          required
                        />
                        {catError && catError.includes('STT') && (
                          <p className="text-danger text-[11px] mt-1 font-medium">{catError}</p>
                        )}
                      </div>

                      {/* Ký hiệu thư mục */}
                      <div className="sm:col-span-8">
                        <label className="text-xs font-semibold text-main block mb-1">
                          Ký hiệu thư mục
                        </label>
                        <input
                          type="text"
                          placeholder="VD: TLBM-CHUNG"
                          value={catForm.ky_hieu}
                          onChange={(e) => {
                            setCatForm({ ...catForm, ky_hieu: e.target.value });
                            setIsUnifiedDirty(true);
                          }}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs font-mono text-main focus:outline-hidden focus:border-primary shadow-2xs"
                        />
                      </div>

                      {/* Tên thư mục (*) */}
                      <div className="sm:col-span-12">
                        <label className="text-xs font-semibold text-main block mb-1">
                          Tên thư mục <span className="text-danger">*</span>
                        </label>
                        <input
                          type="text"
                          placeholder="VD: Tài liệu, Biểu mẫu chung"
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
                          Người lập thư mục
                        </label>
                        <input
                          type="text"
                          value={catForm.nguoi_lap_name}
                          onChange={(e) => {
                            setCatForm({ ...catForm, nguoi_lap_name: e.target.value });
                            setIsUnifiedDirty(true);
                          }}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary shadow-2xs"
                        />
                      </div>

                      {/* Ngày lập */}
                      <div className="sm:col-span-6">
                        <label className="text-xs font-semibold text-main block mb-1">Ngày lập</label>
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
                        <label className="text-xs font-semibold text-main block mb-1">Ghi chú</label>
                        <input
                          type="text"
                          placeholder="Mô tả phạm vi áp dụng của thư mục..."
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
                            <span>Thêm nhanh loại tài liệu con thuộc thư mục này (Tùy chọn)</span>
                          </label>
                          <span className="text-[11px] text-muted">
                            Đã thêm: {catChildTypes.length}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            placeholder="Nhập tên loại (VD: Quy chế, Biểu mẫu...) rồi bấm Thêm hoặc Enter"
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
                            Thêm
                          </Button>
                        </div>

                        {catChildTypes.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 pt-1 max-h-24 overflow-y-auto">
                            {catChildTypes.map((t, idx) => (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/25 shadow-2xs"
                              >
                                <i className="fa-solid fa-tag text-[10px]" />
                                <span>{t}</span>
                                <button
                                  type="button"
                                  onClick={() => handleRemoveChildType(idx)}
                                  className="hover:text-danger ml-0.5 cursor-pointer text-xs"
                                  title="Xóa loại này"
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
                          <span>Chưa có Thư mục Cấp 1 nào. Vui lòng tạo Thư mục Cấp 1 trước khi tạo Loại tài liệu.</span>
                        </div>
                        <Button
                          type="button"
                          variant="primary"
                          size="sm"
                          onClick={() => setUnifiedTarget('category')}
                          className="text-xs shrink-0 font-bold"
                        >
                          <i className="fa-solid fa-folder-plus mr-1" />
                          Chuyển sang tạo Thư mục
                        </Button>
                      </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                      {/* Thư mục cha (*) */}
                      <div className="sm:col-span-8">
                        <label className="text-xs font-semibold text-main block mb-1">
                          Thư mục cha <span className="text-danger">*</span>
                        </label>
                        <select
                          value={typeForm.dm_tai_lieu}
                          onChange={(e) => {
                            setTypeForm({ ...typeForm, dm_tai_lieu: Number(e.target.value) });
                            setIsUnifiedDirty(true);
                          }}
                          className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-xl text-xs text-main focus:outline-hidden focus:border-primary cursor-pointer shadow-2xs font-medium"
                          required
                          disabled={categories.length === 0}
                        >
                          {categories.length === 0 ? (
                            <option value="">-- Chưa có thư mục nào --</option>
                          ) : (
                            categories.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.ten_tai_lieu}
                              </option>
                            ))
                          )}
                        </select>
                      </div>

                      {/* Phạm vi: Công khai checkbox */}
                      <div className="sm:col-span-4 flex items-center pt-5">
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
                          <span>Công khai dùng chung</span>
                        </label>
                      </div>

                      {/* Tên loại tài liệu (*) */}
                      <div className="sm:col-span-12">
                        <label className="text-xs font-semibold text-main block mb-1">
                          Tên loại tài liệu <span className="text-danger">*</span>
                        </label>
                        <input
                          type="text"
                          placeholder="VD: Biểu mẫu bảo hiểm, Tờ trình..."
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
                        <label className="text-xs font-semibold text-main block mb-1">Ghi chú</label>
                        <input
                          type="text"
                          placeholder="Mô tả mục đích sử dụng..."
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
              <div className="px-5 py-3.5 border-t border-border-subtle bg-surface-elevated flex items-center justify-end gap-2.5 shrink-0">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCancelBtnClick}
                  className="rounded-xl text-xs font-semibold"
                >
                  Hủy
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  icon="fa-check"
                  disabled={unifiedTarget === 'type' && categories.length === 0}
                  className="rounded-xl text-xs font-bold shadow-sm hover:shadow-glow px-4"
                >
                  {unifiedMode === 'create'
                    ? unifiedTarget === 'category'
                      ? 'Lưu thư mục'
                      : 'Lưu loại tài liệu'
                    : 'Cập nhật thay đổi'}
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
        </div>
      )}

      {/* Modal xác nhận xóa Thư mục */}
      <ConfirmationModal
        isOpen={deleteCatTarget !== null}
        onClose={() => setDeleteCatTarget(null)}
        onConfirm={() => {
          if (deleteCatTarget) {
            onDeleteCategory(deleteCatTarget.id);
            setDeleteCatTarget(null);
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
        onConfirm={() => {
          if (deleteTypeTarget) {
            onDeleteType(deleteTypeTarget.id);
            setDeleteTypeTarget(null);
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
