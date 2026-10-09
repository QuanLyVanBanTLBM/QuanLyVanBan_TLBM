import React, { useState, useEffect, useRef } from 'react';
import { ResourceItem, ResourceAttachment, HieuLucType } from '@app-types/resource';
import { Badge } from '@components/common/Badge';
import { useTranslation } from '@i18n/translate';

export interface ResourceTableProps {
  items: ResourceItem[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalCount: number;
  onPageChange: (page: number) => void;
  onViewDetail: (item: ResourceItem) => void;
  onEdit?: (item: ResourceItem) => void;
  onDelete?: (item: ResourceItem) => void;
  onDownloadFile?: (item: ResourceItem, fileName?: string, filePath?: string) => void;
  onPageSizeChange?: (size: number) => void;
  onClearFilters?: () => void;
  // Khi bấm dòng: chuyển sang xem Thư mục/Loại tài liệu của mục đó
  onDrillDown?: (categoryId: number, typeId?: number) => void;
}

export const ResourceTable: React.FC<ResourceTableProps> = ({
  items,
  isLoading = false,
  error = null,
  onRetry,
  currentPage,
  totalPages,
  pageSize,
  onPageChange,
  onViewDetail,
  onEdit,
  onDelete,
  onDownloadFile,
  onPageSizeChange,
  onClearFilters,
  onDrillDown,
}) => {
  const { t } = useTranslation();
  // Dropdown menu "⋯" theo từng dòng
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);
  // Vị trí fixed của dropdown menu — giải quyết lỗi bị clip bởi overflow-x-auto
  const [menuPos, setMenuPos] = useState<{ top: number; right: number } | null>(null);
  // Dropdown danh sách tệp cho dòng có nhiều tệp
  const [activeFileMenuId, setActiveFileMenuId] = useState<number | null>(null);

  const tableContainerRef = useRef<HTMLDivElement>(null);

  // Đóng menu khi click ra ngoài, scroll bất kỳ container nào hoặc resize
  useEffect(() => {
    const handleClose = () => {
      setActiveMenuId(null);
      setMenuPos(null);
      setActiveFileMenuId(null);
    };

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target?.closest?.('[data-dropdown-root]')) {
        handleClose();
      }
    };

    // Khi cuộn bất kỳ container nào (main viewport, table, window), đóng ngay menu để không bị trôi lơ lửng
    const handleScroll = () => {
      handleClose();
    };

    document.addEventListener('click', handleClickOutside, true);
    window.addEventListener('resize', handleClose);
    window.addEventListener('scroll', handleScroll, true);
    document.addEventListener('scroll', handleScroll, true);

    return () => {
      document.removeEventListener('click', handleClickOutside, true);
      window.removeEventListener('resize', handleClose);
      window.removeEventListener('scroll', handleScroll, true);
      document.removeEventListener('scroll', handleScroll, true);
    };
  }, []);


  // Mở menu ⋯ với vị trí fixed (không bị cắt bởi overflow và lật lên trên nếu gần đáy)
  const openActionMenu = (e: React.MouseEvent<HTMLButtonElement>, itemId: number) => {
    e.stopPropagation();
    if (activeMenuId === itemId) {
      setActiveMenuId(null);
      setMenuPos(null);
      return;
    }
    const rect = e.currentTarget.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const top = spaceBelow < 120 ? Math.max(10, rect.top - 116) : rect.bottom + 4;
    setMenuPos({
      top,
      right: Math.max(10, window.innerWidth - rect.right),
    });
    setActiveMenuId(itemId);
  };

  // Format ngày dd/mm/yyyy
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return dateStr;
      return date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };


  // Trích xuất đuôi tệp
  const getFileExt = (urlOrName?: string, attachments?: ResourceAttachment[]) => {
    if (attachments && attachments.length > 0) {
      const first = attachments[0];
      if (first.name) {
        const cleanName = first.name.split('?')[0].split('#')[0];
        const nameParts = cleanName.split('.');
        if (nameParts.length > 1) {
          const ext = nameParts.pop()?.toUpperCase() || '';
          if (/^[A-Z0-9]{1,6}$/.test(ext)) {
            return ext;
          }
        }
      }
      if (first.mime_type) {
        if (first.mime_type.includes('pdf')) return 'PDF';
        if (first.mime_type.includes('word') || first.mime_type.includes('officedocument.wordprocessingml')) return 'DOCX';
        if (first.mime_type.includes('sheet') || first.mime_type.includes('excel')) return 'XLSX';
        if (first.mime_type.includes('presentation') || first.mime_type.includes('powerpoint')) return 'PPTX';
        if (first.mime_type.includes('image')) return 'IMG';
        if (first.mime_type.includes('zip') || first.mime_type.includes('compressed')) return 'ZIP';
      }
    }

    if (!urlOrName) return 'FILE';

    // Xử lý an toàn blob URL (không split dấu chấm của 127.0.0.1 hay port)
    if (urlOrName.startsWith('blob:')) {
      return 'PDF';
    }

    const clean = urlOrName.split('?')[0].split('#')[0];
    const fileNameOnly = clean.split('/').pop() || '';
    const parts = fileNameOnly.split('.');
    if (parts.length > 1) {
      const ext = parts.pop()?.toUpperCase() || '';
      if (/^[A-Z0-9]{1,6}$/.test(ext)) {
        return ext;
      }
    }
    return 'PDF';
  };

  // Lấy icon font-awesome theo đuôi file
  const getFileIcon = (ext: string) => {
    switch (ext) {
      case 'PDF':
        return 'fa-file-pdf text-rose-500';
      case 'DOC':
      case 'DOCX':
        return 'fa-file-word text-blue-500';
      case 'XLS':
      case 'XLSX':
        return 'fa-file-excel text-emerald-500';
      case 'ZIP':
      case 'RAR':
      case '7Z':
        return 'fa-file-zipper text-amber-500';
      case 'JPG':
      case 'JPEG':
      case 'PNG':
        return 'fa-file-image text-purple-500';
      default:
        return 'fa-file-lines text-secondary';
    }
  };

  const renderStatusBadge = (hieuLuc: HieuLucType) => {
    switch (hieuLuc) {
      case 'CON_HIEU_LUC':
        return (
          <Badge variant="success" size="sm" withDot>
            {t('resourceManagement.statusActive')}
          </Badge>
        );
      case 'CON_HIEU_LUC_1_PHAN':
        return (
          <Badge variant="warning" size="sm" withDot>
            {t('resourceManagement.statusPartial')}
          </Badge>
        );
      case 'HET_HIEU_LUC':
        return (
          <Badge variant="danger" size="sm" withDot>
            {t('resourceManagement.statusExpired')}
          </Badge>
        );
      case 'HET_VA_THAY_THE':
        return (
          <Badge variant="warning" size="sm" withDot>
            {t('resourceManagement.statusExpired')}
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary" size="sm">
            {hieuLuc}
          </Badge>
        );
    }
  };

  // Ô nhập trang nhảy nhanh khi có nhiều trang
  const [jumpPageInput, setJumpPageInput] = useState('');
  const paginationRef = useRef<HTMLDivElement>(null);

  const handlePageChange = (targetPage: number) => {
    onPageChange(targetPage);
    // Giữ vị trí thanh phân trang và bảng dữ liệu ổn định trong tầm nhìn người dùng
    requestAnimationFrame(() => {
      if (typeof paginationRef.current?.scrollIntoView === 'function') {
        paginationRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  };

  const handleJumpPage = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const pageNum = parseInt(jumpPageInput.trim(), 10);
    if (!isNaN(pageNum)) {
      const validPage = Math.max(1, Math.min(pageNum, totalPages));
      handlePageChange(validPage);
      setJumpPageInput('');
    }
  };

  type PageItem =
    | { type: 'page'; num: number }
    | { type: 'ellipsis'; direction: 'prev' | 'next'; targetPage: number };

  // Danh sách phần tử phân trang thông minh: rút gọn chỉ hiện 3 số (ví dụ 1 2 3 ... 9 hoặc 1 ... 7 8 9)
  const getPageElements = (): PageItem[] => {
    if (totalPages <= 5) {
      return Array.from({ length: totalPages }, (_, i) => ({
        type: 'page',
        num: i + 1,
      }));
    }

    const items: PageItem[] = [];

    if (currentPage <= 2) {
      // Đang ở gần đầu: chỉ hiện 3 số đầu 1, 2, 3 ... totalPages
      for (let i = 1; i <= 3; i++) {
        items.push({ type: 'page', num: i });
      }
      items.push({
        type: 'ellipsis',
        direction: 'next',
        targetPage: Math.min(totalPages, currentPage + 3),
      });
      items.push({ type: 'page', num: totalPages });
    } else if (currentPage >= totalPages - 1) {
      // Đang ở gần cuối: 1 ... (totalPages-2) (totalPages-1) totalPages
      items.push({ type: 'page', num: 1 });
      items.push({
        type: 'ellipsis',
        direction: 'prev',
        targetPage: Math.max(1, currentPage - 3),
      });
      for (let i = totalPages - 2; i <= totalPages; i++) {
        items.push({ type: 'page', num: i });
      }
    } else {
      // Đang ở giữa: 1 ... (currentPage-1) (currentPage) (currentPage+1) ... totalPages
      items.push({ type: 'page', num: 1 });

      if (currentPage - 1 > 2) {
        items.push({
          type: 'ellipsis',
          direction: 'prev',
          targetPage: Math.max(1, currentPage - 3),
        });
      }

      // Nếu currentPage === 3 thì currentPage - 1 là 2 (liền kề 1, không cần ellipsis)
      items.push({ type: 'page', num: currentPage - 1 });
      items.push({ type: 'page', num: currentPage });
      items.push({ type: 'page', num: currentPage + 1 });

      // Nếu currentPage === totalPages - 2 thì currentPage + 1 là totalPages - 1 (liền kề totalPages, không cần ellipsis)
      if (currentPage + 1 < totalPages - 1) {
        items.push({
          type: 'ellipsis',
          direction: 'next',
          targetPage: Math.min(totalPages, currentPage + 3),
        });
      }

      items.push({ type: 'page', num: totalPages });
    }

    return items;
  };

  return (
    <div
      className="w-full rounded-xl border border-border-subtle bg-surface shadow-xs overflow-hidden"
      ref={tableContainerRef}
    >
      {/* Khung Bảng dữ liệu chính */}
      <div className="w-full overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse min-w-[850px]">
          <thead className="bg-surface-elevated text-xs font-bold text-muted uppercase tracking-wider border-b border-border-subtle select-none">
            <tr>
              <th className="px-4 py-3.5 w-36 min-w-[130px] whitespace-nowrap">{t('resourceManagement.colCode')}</th>
              <th className="px-4 py-3.5 min-w-[260px]">{t('resourceManagement.colTitle')}</th>
              <th className="px-4 py-3.5 w-48 min-w-[170px]">{t('resourceManagement.colAuthority')}</th>
              <th className="px-3.5 py-3.5 w-32 min-w-[110px] text-center whitespace-nowrap">{t('resourceManagement.colDate')}</th>
              <th className="px-4 py-3.5 w-44 min-w-[150px] text-center whitespace-nowrap">{t('resourceManagement.colStatus')}</th>
              <th className="px-3.5 py-3.5 w-40 min-w-[140px] text-center whitespace-nowrap">{t('resourceManagement.colFile')}</th>
              <th className="px-3.5 py-3.5 w-20 min-w-[80px] text-center whitespace-nowrap">{t('resourceManagement.colActions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {isLoading ? (
              // Trạng thái Loading (Skeleton)
              Array.from({ length: pageSize > 5 ? 5 : pageSize }).map((_, idx) => (
                <tr key={idx} className="animate-pulse">
                  <td className="px-4 py-4">
                    <div className="h-4 w-20 bg-surface-elevated rounded" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="h-4 w-3/4 bg-surface-elevated rounded mb-1.5" />
                    <div className="h-3 w-1/3 bg-surface-elevated rounded" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="h-4 w-28 bg-surface-elevated rounded" />
                  </td>
                  <td className="px-4 py-4 text-center">
                    <div className="h-4 w-16 bg-surface-elevated rounded mx-auto" />
                  </td>
                  <td className="px-4 py-4 text-center">
                    <div className="h-5 w-24 bg-surface-elevated rounded-full mx-auto" />
                  </td>
                  <td className="px-4 py-4 text-center">
                    <div className="h-7 w-20 bg-surface-elevated rounded mx-auto" />
                  </td>
                  <td className="px-4 py-4 text-center">
                    <div className="h-7 w-8 bg-surface-elevated rounded mx-auto" />
                  </td>
                </tr>
              ))
            ) : error ? (
              // Trạng thái Lỗi
              <tr>
                <td colSpan={7} className="py-14 text-center">
                  <div className="flex flex-col items-center justify-center gap-3">
                    <div className="w-14 h-14 rounded-full bg-danger-subtle text-danger flex items-center justify-center text-2xl">
                      <i className="fa-solid fa-triangle-exclamation" />
                    </div>
                    <div className="max-w-sm space-y-1">
                      <h4 className="text-base font-semibold text-main">{error}</h4>
                      <p className="text-xs text-secondary">
                        Đã có lỗi xảy ra khi tải danh sách tài liệu. Vui lòng thử lại.
                      </p>
                    </div>
                    {onRetry && (
                      <button
                        type="button"
                        onClick={onRetry}
                        className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-white hover:bg-primary-hover transition-colors cursor-pointer"
                      >
                        <i className="fa-solid fa-rotate-right text-[11px]" />
                        <span>Thử lại</span>
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : items.length === 0 ? (
              // Trạng thái Rỗng
              <tr>
                <td colSpan={7} className="py-14 text-center">
                  <div className="flex flex-col items-center justify-center gap-3">
                    <div className="w-14 h-14 rounded-full bg-surface-elevated text-muted flex items-center justify-center text-2xl">
                      <i className="fa-solid fa-folder-open" />
                    </div>
                    <div className="max-w-sm space-y-1">
                      <h4 className="text-base font-semibold text-main">
                        {t('resourceManagement.noMatchTitle')}
                      </h4>
                      <p className="text-xs text-secondary">
                        {t('resourceManagement.noMatchDesc')}
                      </p>
                    </div>
                    {onClearFilters && (
                      <button
                        type="button"
                        onClick={onClearFilters}
                        className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary-subtle text-primary border border-primary/30 hover:bg-primary/15 transition-colors cursor-pointer"
                      >
                        <i className="fa-solid fa-rotate-left text-[11px]" />
                        <span>{t('resourceManagement.clearFilter')}</span>
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              // Danh sách dòng tài liệu
              items.map((item) => {
                // RÀNG BUỘC ĐẶC BIỆT: HẾT HIỆU LỰC / HẾT VÀ THAY THẾ LÀM MỜ TOÀN BỘ DÒNG
                const isExpired =
                  item.hieu_luc === 'HET_HIEU_LUC' || item.hieu_luc === 'HET_VA_THAY_THE';

                const rowClass = isExpired
                  ? 'bg-slate-100/70 dark:bg-slate-800/60 text-slate-500 hover:bg-slate-200/50 dark:hover:bg-slate-800/80'
                  : 'hover:bg-slate-50 dark:hover:bg-slate-800/40 text-main';

                const ext = getFileExt(item.file_dinh_kem, item.attachments);
                const hasMultipleFiles = Boolean(item.attachments && item.attachments.length > 1);

                return (
                  <tr
                    key={item.id}
                    onClick={() => {
                      // Bấm dòng → Drill-down vào thư mục + loại tài liệu của mục đó
                      if (onDrillDown) {
                        const firstType = item.loai_tai_lieu?.[0];
                        onDrillDown(item.dm_tai_lieu, firstType);
                      }
                    }}
                    className={`transition-colors duration-fast cursor-pointer select-none ${rowClass}`}
                    title="Bấm để đi vào thư mục của tài liệu"
                  >
                    {/* Cột 1: Ký hiệu (thống nhất font sans chuẩn hệ thống, ngay hàng thẳng lối) */}
                    <td className="px-4 py-3.5 align-middle whitespace-nowrap">
                      <span className="text-xs font-semibold text-main tracking-tight">
                        {item.ky_hieu || '-'}
                      </span>
                    </td>

                    {/* Cột 2: Tiêu đề + Loại tài liệu + Link thay thế (Cùng hàng cân đối tuyệt đối) */}
                    <td className="px-4 py-3.5 align-middle">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-sm text-main hover:text-primary transition-colors leading-snug">
                          {item.tieu_de}
                        </span>

                        {/* Danh sách Loại tài liệu dạng tag nhỏ liền kề tiêu đề */}
                        {item.loai_tai_lieu_names && item.loai_tai_lieu_names.length > 0 && (
                          <span className="inline-flex items-center gap-1.5 flex-wrap">
                            {item.loai_tai_lieu_names.map((name, idx) => (
                              <span
                                key={idx}
                                className="inline-flex items-center text-[10px] font-medium px-2 py-0.5 rounded-md bg-surface-elevated text-secondary border border-border-subtle shadow-2xs whitespace-nowrap"
                              >
                                {name}
                              </span>
                            ))}
                          </span>
                        )}
                      </div>

                      {/* Dòng Link thay thế dưới tiêu đề nếu Hết và thay thế */}
                      {item.hieu_luc === 'HET_VA_THAY_THE' && item.link_thay_the && (
                        <div className="mt-1 opacity-100">
                          <a
                            href={item.link_thay_the}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-xs text-primary hover:underline font-medium hover:text-primary-hover"
                            title="Mở văn bản thay thế mới"
                          >
                            <span>&rarr; Xem văn bản thay thế</span>
                            <i className="fa-solid fa-arrow-up-right-from-square text-[9px]" />
                          </a>
                        </div>
                      )}
                    </td>

                    {/* Cột 3: Nơi ban hành */}
                    <td className="px-4 py-3.5 align-middle text-xs text-secondary leading-snug">
                      {item.noi_ban_hanh || '-'}
                    </td>

                    {/* Cột 4: Ngày đăng (dd/mm/yyyy thường, thẳng hàng giữa) */}
                    <td className="px-3.5 py-3.5 text-center align-middle whitespace-nowrap text-xs text-secondary leading-snug">
                      {formatDate(item.ngay_dang)}
                    </td>

                    {/* Cột 5: Hiệu lực (Badge giữ độ nét 100%, thẳng hàng giữa) */}
                    <td className="px-4 py-3.5 text-center align-middle whitespace-nowrap opacity-100">
                      {renderStatusBadge(item.hieu_luc)}
                    </td>

                    {/* Cột 6: Tệp đính kèm (Icon & Nút tải về cố định độ rộng để thẳng hàng tuyệt đối) */}
                    <td
                      className="px-3.5 py-3.5 text-center align-middle whitespace-nowrap opacity-100"
                      onClick={(e) => e.stopPropagation()}
                      data-dropdown-root
                    >
                      {hasMultipleFiles ? (
                        // Trường hợp nhiều tệp: hiện badge số tệp và dropdown tải từng tệp
                        <div className="relative inline-block text-left">
                          <button
                            type="button"
                            onClick={() =>
                              setActiveFileMenuId(activeFileMenuId === item.id ? null : item.id)
                            }
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg bg-surface-elevated hover:bg-border-subtle/50 text-main border border-border-subtle transition-colors cursor-pointer"
                            title="Xem danh sách tệp đính kèm"
                            aria-label={`Có ${item.attachments?.length} tệp đính kèm`}
                          >
                            <i className="fa-solid fa-paperclip text-primary text-[11px]" />
                            <span>{item.attachments?.length} tệp</span>
                            <i className="fa-solid fa-chevron-down text-[9px] text-muted" />
                          </button>

                          {activeFileMenuId === item.id && (
                            <div className="absolute right-0 mt-1 w-64 rounded-xl bg-surface border border-border-subtle shadow-lg z-20 py-1.5 animate-fade-in text-left">
                              <div className="px-3 py-1.5 text-[11px] font-bold text-muted border-b border-border-subtle uppercase">
                                Danh sách tệp đính kèm
                              </div>
                              <div className="max-h-48 overflow-y-auto divide-y divide-border-subtle/50">
                                {item.attachments?.map((att, attIdx) => {
                                  const attExt = getFileExt(att.name || att.path);
                                  return (
                                    <div
                                      key={attIdx}
                                      className="px-3 py-2 flex items-center justify-between gap-2 hover:bg-surface-elevated transition-colors text-xs"
                                    >
                                      <div className="flex items-center gap-1.5 min-w-0">
                                        <i className={`fa-solid ${getFileIcon(attExt)} text-sm shrink-0`} />
                                        <span className="truncate text-main font-medium" title={att.name}>
                                          {att.name}
                                        </span>
                                      </div>
                                      <button
                                        type="button"
                                        onClick={() => onDownloadFile?.(item, att.name, att.path)}
                                        className="shrink-0 p-1 text-primary hover:text-primary-hover hover:bg-primary-subtle rounded transition-colors"
                                        title="Tải về"
                                        aria-label={`Tải về ${att.name}`}
                                      >
                                        <i className="fa-solid fa-download text-xs" />
                                      </button>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : item.file_dinh_kem ? (
                        // Trường hợp 1 tệp: hiện icon + Ext + nút Tải về với chiều rộng cố định để thẳng hàng
                        <div className="inline-flex items-center justify-center gap-1.5 text-xs">
                          <i className={`fa-solid ${getFileIcon(ext)} text-sm shrink-0`} />
                          <span className="font-semibold text-secondary text-[11px] w-9 inline-block text-left">{ext}</span>
                          <button
                            type="button"
                            onClick={() => onDownloadFile?.(item)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold text-primary hover:text-primary-hover hover:bg-primary-subtle rounded-md transition-colors cursor-pointer"
                            title="Tải về tệp đính kèm"
                            aria-label={`Tải về tệp ${ext}`}
                          >
                            <i className="fa-solid fa-download text-[11px]" />
                            <span>{t('resourceManagement.download')}</span>
                          </button>
                        </div>
                      ) : (
                        <span className="text-muted text-xs italic">-</span>
                      )}
                    </td>

                    {/* Cột 7: Thao tác — Menu "⋯": Xem chi tiết, Chỉnh sửa, Xóa */}
                    <td
                      className="px-3.5 py-3.5 text-center align-middle whitespace-nowrap opacity-100"
                      onClick={(e) => e.stopPropagation()}
                      data-dropdown-root
                    >
                      <div className="relative inline-block text-left" data-dropdown-root>
                        <button
                          type="button"
                          onClick={(e) => openActionMenu(e, item.id)}
                          className="w-8 h-7 rounded-lg inline-flex items-center justify-center text-muted hover:text-main hover:bg-surface-elevated transition-colors cursor-pointer"
                          title="Thao tác"
                          aria-label={`Thao tác với tài liệu ${item.ky_hieu || item.tieu_de}`}
                          aria-haspopup="true"
                          aria-expanded={activeMenuId === item.id}
                        >
                          <i className="fa-solid fa-ellipsis text-sm" />
                        </button>
                      </div>

                      {/* Dropdown fixed — render bên ngoài overflow container qua portal style */}
                      {activeMenuId === item.id && menuPos && (
                        <div
                          data-dropdown-root
                          className="fixed z-50 w-44 rounded-xl bg-surface border border-border-subtle shadow-xl py-1 animate-fade-in text-left"
                          style={{ top: menuPos.top, right: menuPos.right }}
                        >
                          {/* Mục 1: Xem chi tiết */}
                          <button
                            type="button"
                            onClick={() => {
                              setActiveMenuId(null);
                              setMenuPos(null);
                              onViewDetail(item);
                            }}
                            className="w-full px-3 py-2 text-xs text-left text-main hover:bg-surface-elevated flex items-center gap-2 transition-colors cursor-pointer"
                            aria-label="Xem chi tiết tài liệu"
                          >
                            <i className="fa-solid fa-eye text-muted text-xs" />
                            <span>Xem chi tiết</span>
                          </button>

                          {/* Mục 2: Truy cập Thư mục + Loại */}
                          {onDrillDown && (
                            <button
                              type="button"
                              onClick={() => {
                                setActiveMenuId(null);
                                setMenuPos(null);
                                const firstType = item.loai_tai_lieu?.[0];
                                onDrillDown(item.dm_tai_lieu, firstType);
                              }}
                              className="w-full px-3 py-2 text-xs text-left text-main hover:bg-surface-elevated flex items-center gap-2 transition-colors cursor-pointer"
                              aria-label="Truy cập thư mục của tài liệu"
                            >
                              <i className="fa-solid fa-folder-open text-primary text-xs" />
                              <span className="text-primary font-medium">Vào Thư mục</span>
                            </button>
                          )}

                          {/* Phân cách trước nhóm chỉnh sửa/xóa */}
                          {(onEdit || onDelete) && (
                            <div className="my-1 border-t border-border-subtle" />
                          )}

                          {/* Mục 3: Chỉnh sửa */}
                          {onEdit && (
                            <button
                              type="button"
                              onClick={() => {
                                setActiveMenuId(null);
                                setMenuPos(null);
                                onEdit(item);
                              }}
                              className="w-full px-3 py-2 text-xs text-left text-main hover:bg-surface-elevated flex items-center gap-2 transition-colors cursor-pointer"
                              aria-label="Chỉnh sửa tài liệu"
                            >
                              <i className="fa-solid fa-pen-to-square text-muted text-xs" />
                              <span>{t('resourceManagement.edit')}</span>
                            </button>
                          )}

                          {/* Mục 4: Xóa tài liệu */}
                          {onDelete && (
                            <button
                              type="button"
                              onClick={() => {
                                setActiveMenuId(null);
                                setMenuPos(null);
                                onDelete(item);
                              }}
                              className="w-full px-3 py-2 text-xs text-left text-danger hover:bg-danger-subtle flex items-center gap-2 transition-colors cursor-pointer font-medium"
                              aria-label="Xóa tài liệu"
                            >
                              <i className="fa-solid fa-trash-can text-danger text-xs" />
                              <span>{t('resourceManagement.delete')}</span>
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
            {/* Giữ độ cao hàng và chân bảng cố định khi trang cuối có ít dòng hơn pageSize */}
            {totalPages > 1 && !isLoading && !error && items.length > 0 && items.length < pageSize && pageSize <= 10 && (
              Array.from({ length: pageSize - items.length }).map((_, idx) => (
                <tr
                  key={`spacer-${idx}`}
                  data-spacer="true"
                  className="h-[52px] pointer-events-none select-none border-b border-transparent"
                  aria-hidden="true"
                >
                  <td colSpan={7} className="px-4 py-3.5">&nbsp;</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Chân bảng: Chọn số dòng hiển thị + Thanh phân trang thông minh */}
      <div
        ref={paginationRef}
        className="flex flex-col xl:flex-row items-center justify-between gap-3 px-4 py-3 border-t border-border-subtle text-xs text-secondary bg-surface pr-4 sm:pr-28 lg:pr-32"
      >
        {/* Bên trái chân bảng: Dropdown chọn số dòng & Thông tin tổng số */}
        <div className="flex items-center gap-2.5 shrink-0 select-none">
          <span className="font-medium">Hiển thị</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
            className="px-2 py-1 bg-surface-elevated border border-border-subtle rounded-md text-main text-xs focus:outline-hidden focus:border-primary cursor-pointer font-medium"
            aria-label="Chọn số dòng hiển thị trên mỗi trang"
          >
            <option value={5}>5 dòng</option>
            <option value={10}>10 dòng</option>
            <option value={20}>20 dòng</option>
            <option value={50}>50 dòng</option>
          </select>
          <span className="font-medium">/ {t('resourceManagement.rowsPerPage')}</span>
        </div>

        {/* Cụm điều hướng phân trang hoàn chỉnh */}
        {totalPages > 1 && (
          <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap justify-center select-none">
            <div className="flex items-center gap-1">
              {/* Nút về trang đầu (hiện khi có từ 6 trang trở lên) */}
              {totalPages > 5 && (
                <button
                  type="button"
                  disabled={currentPage <= 1 || isLoading}
                  onClick={() => handlePageChange(1)}
                  className="min-w-[32px] h-8 px-2 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
                  title="Về trang đầu (Trang 1)"
                  aria-label="Về trang đầu"
                >
                  <i className="fa-solid fa-angles-left text-[11px]" />
                </button>
              )}

              {/* Nút lùi 1 trang */}
              <button
                type="button"
                disabled={currentPage <= 1 || isLoading}
                onClick={() => handlePageChange(currentPage - 1)}
                className="min-w-[32px] h-8 px-2 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
                title="Trang trước"
                aria-label="Trang trước"
              >
                <i className="fa-solid fa-chevron-left text-[11px]" />
              </button>

              {/* Danh sách các nút số trang + Nút ... rút gọn thông minh */}
              {getPageElements().map((item, idx) => {
                if (item.type === 'ellipsis') {
                  return (
                    <button
                      key={`ellipsis-${idx}`}
                      type="button"
                      disabled={isLoading}
                      onClick={() => handlePageChange(item.targetPage)}
                      className="group min-w-[32px] h-8 px-1 text-xs font-medium rounded-lg border border-transparent hover:border-border-subtle hover:bg-surface-elevated text-muted hover:text-primary transition-all cursor-pointer flex items-center justify-center"
                      title={
                        item.direction === 'prev'
                          ? `Lùi 3 trang (Về trang ${item.targetPage})`
                          : `Tiến 3 trang (Đến trang ${item.targetPage})`
                      }
                      aria-label={item.direction === 'prev' ? 'Lùi 3 trang' : 'Tiến 3 trang'}
                    >
                      <span className="group-hover:hidden tracking-widest text-[11px] font-bold">•••</span>
                      <i
                        className={`hidden group-hover:inline fa-solid text-[10px] ${
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
                    disabled={isLoading}
                    onClick={() => handlePageChange(item.num)}
                    className={`min-w-[32px] h-8 px-2 text-xs font-semibold rounded-lg transition-all cursor-pointer flex items-center justify-center ${
                      isActive
                        ? 'bg-primary text-white shadow-xs font-bold border border-primary'
                        : 'border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main'
                    }`}
                    aria-label={`Trang ${item.num}`}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    {item.num}
                  </button>
                );
              })}

              {/* Nút tiến 1 trang */}
              <button
                type="button"
                disabled={currentPage >= totalPages || isLoading}
                onClick={() => handlePageChange(currentPage + 1)}
                className="min-w-[32px] h-8 px-2 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
                title="Trang sau"
                aria-label="Trang sau"
              >
                <i className="fa-solid fa-chevron-right text-[11px]" />
              </button>

              {/* Nút đến trang cuối (hiện khi có từ 6 trang trở lên) */}
              {totalPages > 5 && (
                <button
                  type="button"
                  disabled={currentPage >= totalPages || isLoading}
                  onClick={() => handlePageChange(totalPages)}
                  className="min-w-[32px] h-8 px-2 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
                  title={`Đến trang cuối (Trang ${totalPages})`}
                  aria-label="Đến trang cuối"
                >
                  <i className="fa-solid fa-angles-right text-[11px]" />
                </button>
              )}
            </div>

            {/* Ô nhảy nhanh đến trang (Hiện khi có nhiều trang: > 5 trang) */}
            {totalPages > 5 && (
              <form
                onSubmit={handleJumpPage}
                className="flex items-center gap-1.5 pl-2 sm:border-l sm:border-border-subtle text-secondary"
              >
                <span className="text-[11px]">Đến trang</span>
                <input
                  type="number"
                  min={1}
                  max={totalPages}
                  value={jumpPageInput}
                  onChange={(e) => setJumpPageInput(e.target.value)}
                  placeholder={String(currentPage)}
                  className="w-12 h-8 px-1.5 text-center bg-surface-elevated border border-border-subtle rounded-lg text-main text-xs focus:outline-hidden focus:border-primary font-medium"
                  aria-label="Nhập số trang muốn chuyển tới"
                />
                <button
                  type="submit"
                  className="h-8 px-2.5 rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-xs font-semibold text-primary cursor-pointer hover:border-primary/40 transition-colors"
                  title="Chuyển đến trang đã nhập"
                >
                  Đi
                </button>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
