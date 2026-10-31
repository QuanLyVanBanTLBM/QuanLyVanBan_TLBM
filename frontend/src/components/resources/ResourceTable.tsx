import React, { useState, useEffect, useRef } from 'react';
import { ResourceItem, HieuLucType } from '@app-types/resource';
import { Badge } from '@components/common/Badge';
import { useTranslation } from '@i18n/translate';
import { computeEffectiveStatus } from '@lib/resourceValidity';

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
  canEdit?: (item: ResourceItem) => boolean;
  canDelete?: (item: ResourceItem) => boolean;
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
  canEdit,
  canDelete,
  onPageSizeChange,
  onClearFilters,
  onDrillDown,
}) => {
  const { t } = useTranslation();
  // Dropdown menu "⋯" theo từng dòng
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);
  // Vị trí fixed của dropdown menu — giải quyết lỗi bị clip bởi overflow-x-auto
  const [menuPos, setMenuPos] = useState<{ top: number; right: number } | null>(null);

  const tableContainerRef = useRef<HTMLDivElement>(null);

  // Đóng menu khi click ra ngoài, scroll bất kỳ container nào hoặc resize
  useEffect(() => {
    const handleClose = () => {
      setActiveMenuId(null);
      setMenuPos(null);
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
      right: Math.max(10, Math.min(window.innerWidth - 186, window.innerWidth - rect.right)),
    });
    setActiveMenuId(itemId);
  };

  // Format ngày dd/mm/yyyy
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(dateStr);
    if (match) {
      const [, y, m, d] = match;
      return `${d}/${m}/${y}`;
    }
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
  const getFileExt = (urlOrName?: string, mimeType?: string) => {
    if (mimeType) {
      if (mimeType.includes('pdf')) return 'PDF';
      if (mimeType.includes('word') || mimeType.includes('officedocument.wordprocessingml')) return 'DOCX';
      if (mimeType.includes('sheet') || mimeType.includes('excel') || mimeType.includes('csv')) return 'XLSX';
      if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return 'PPTX';
      if (mimeType.includes('image')) return 'IMG';
      if (mimeType.includes('zip') || mimeType.includes('compressed')) return 'ZIP';
    }

    if (!urlOrName) return 'FILE';

    // Xử lý an toàn blob URL
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
    return 'FILE';
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
      case 'CSV':
        return 'fa-file-excel text-[#107C41] dark:text-emerald-400';
      case 'ZIP':
      case 'RAR':
      case '7Z':
        return 'fa-file-zipper text-amber-500';
      case 'JPG':
      case 'JPEG':
      case 'PNG':
      case 'WEBP':
      case 'IMG':
        return 'fa-file-image text-purple-500';
      default:
        return 'fa-file-lines text-secondary';
    }
  };

  // Hiển thị các badge loại file đính kèm (hiển thị loại đầu tiên, còn lại hiển thị "...")
  const renderFileBadges = (item: ResourceItem) => {
    const fileList: { name: string; ext: string }[] = [];
    if (item.attachments && item.attachments.length > 0) {
      item.attachments
        .filter((att) => !att.is_deleted)
        .forEach((att) => {
          fileList.push({
            name: att.name || t('resourceManagement.attachment'),
            ext: getFileExt(att.name || att.path, att.mime_type),
          });
        });
    } else if (item.file_dinh_kem) {
      fileList.push({
        name: item.file_dinh_kem.split('/').pop() || t('resourceManagement.attachment'),
        ext: getFileExt(item.file_dinh_kem),
      });
    }

    if (fileList.length === 0) {
      return <span className="text-muted text-xs italic">-</span>;
    }

    // Đếm số lượng theo từng loại extension: { PDF: 2, DOCX: 1, ... }
    const counts: Record<string, number> = {};
    const names: Record<string, string[]> = {};
    fileList.forEach((f) => {
      counts[f.ext] = (counts[f.ext] || 0) + 1;
      if (!names[f.ext]) names[f.ext] = [];
      names[f.ext].push(f.name);
    });

    const entries = Object.entries(counts);
    const [firstExt, firstCount] = entries[0];
    const hasMore = entries.length > 1;
    const remainingFiles = fileList.filter((f) => f.ext !== firstExt);

    const getBadgeStyle = (extension: string) => {
      switch (extension) {
        case 'PDF':
          return 'bg-rose-50 text-rose-600 border-rose-200/80 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800/60';
        case 'DOC':
        case 'DOCX':
          return 'bg-blue-50 text-blue-600 border-blue-200/80 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-800/60';
        case 'XLS':
        case 'XLSX':
        case 'CSV':
          return 'bg-emerald-50 text-[#107C41] border-emerald-600/40 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800/60';
        case 'ZIP':
        case 'RAR':
        case '7Z':
          return 'bg-purple-50 text-purple-600 border-purple-200/80 dark:bg-purple-950/40 dark:text-purple-400 dark:border-purple-800/60';
        case 'JPG':
        case 'JPEG':
        case 'PNG':
        case 'WEBP':
        case 'IMG':
          return 'bg-amber-50 text-amber-600 border-amber-200/80 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800/60';
        default:
          return 'bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700';
      }
    };

    const remainingTooltip = hasMore
      ? `Còn ${remainingFiles.length} tệp khác (${entries.slice(1).map(([ext, cnt]) => `${ext}: ${cnt}`).join(', ')}):\n` +
        remainingFiles.map((f) => `• ${f.name}`).join('\n')
      : '';

    return (
      <div
        className="inline-flex items-center justify-center gap-1.5 flex-nowrap cursor-pointer"
        onClick={(e) => {
          e.stopPropagation();
          onViewDetail?.(item);
        }}
        title={fileList.map((f) => f.name).join('\n')}
      >
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold border hover:opacity-80 transition-all whitespace-nowrap ${getBadgeStyle(
            firstExt
          )}`}
        >
          <i className={`fa-solid ${getFileIcon(firstExt)} text-xs`} />
          <span>{firstExt}{firstCount > 1 ? ` (${firstCount})` : ''}</span>
        </span>

        {hasMore && (
          <span
            className="inline-flex items-center justify-center px-1.5 py-0.5 rounded-md text-[11px] font-bold border bg-slate-100 text-slate-600 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-600 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all whitespace-nowrap shadow-2xs"
            title={remainingTooltip}
          >
            ...
          </span>
        )}
      </div>
    );
  };

  const renderStatusBadge = (itemOrStatus: ResourceItem | HieuLucType) => {
    let effectiveStatus: HieuLucType;
    let isScheduled = false;
    let expDate: string | null = null;

    if (typeof itemOrStatus === 'string') {
      effectiveStatus = itemOrStatus;
    } else {
      const validity = computeEffectiveStatus(
        itemOrStatus.hieu_luc,
        itemOrStatus.ngay_het_hieu_luc,
        itemOrStatus.link_thay_the
      );
      effectiveStatus = validity.status;
      isScheduled = validity.isScheduled;
      expDate = validity.expirationDate || null;
    }

    if (isScheduled && expDate) {
      return (
        <div className="inline-flex flex-col items-center gap-0.5">
          <Badge variant="success" size="sm" withDot>
            {t('resourceManagement.statusActive')}
          </Badge>
          <span
            className="text-[10px] text-muted font-medium"
            title={t('resourceManagement.scheduledExpiryNotice', { date: formatDate(expDate) })}
          >
            {t('resourceManagement.expiresOnDate', { date: formatDate(expDate) })}
          </span>
        </div>
      );
    }

    switch (effectiveStatus) {
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
            {effectiveStatus}
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

  // Danh sách phần tử phân trang: rút gọn chỉ hiện 2 số ở đầu/cuối (ví dụ: 1 2 ... 6 hoặc 1 ... 5 6)
  const getPageElements = (): PageItem[] => {
    if (totalPages <= 4) {
      return Array.from({ length: totalPages }, (_, i) => ({
        type: 'page',
        num: i + 1,
      }));
    }

    const items: PageItem[] = [];

    if (currentPage <= 2) {
      // Đang ở gần đầu: 1 2 ... totalPages (Ví dụ: 1 2 ... 6)
      items.push({ type: 'page', num: 1 });
      items.push({ type: 'page', num: 2 });
      items.push({
        type: 'ellipsis',
        direction: 'next',
        targetPage: Math.min(totalPages, currentPage + 2),
      });
      items.push({ type: 'page', num: totalPages });
    } else if (currentPage >= totalPages - 1) {
      // Đang ở gần cuối: 1 ... (totalPages-1) totalPages (Ví dụ: 1 ... 5 6)
      items.push({ type: 'page', num: 1 });
      items.push({
        type: 'ellipsis',
        direction: 'prev',
        targetPage: Math.max(1, currentPage - 2),
      });
      items.push({ type: 'page', num: totalPages - 1 });
      items.push({ type: 'page', num: totalPages });
    } else {
      // Đang ở giữa: 1 ... currentPage ... totalPages
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

  return (
    <div
      className="w-full rounded-xl border border-border-subtle bg-surface shadow-xs overflow-hidden"
      ref={tableContainerRef}
    >
      {/* Khung Bảng dữ liệu chính */}
      <div className="w-full overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse min-w-full">
          <thead className="bg-surface-elevated text-xs font-bold text-muted uppercase tracking-wider border-b border-border-subtle select-none">
            <tr>
              <th className="hidden sm:table-cell px-2.5 sm:px-4 py-3 sm:py-3.5 w-24 sm:w-32 min-w-[80px] whitespace-nowrap">{t('resourceManagement.colCode')}</th>
              <th className="px-2.5 sm:px-4 py-3 sm:py-3.5 min-w-[140px] sm:min-w-[200px]">{t('resourceManagement.colTitle')}</th>
              <th className="hidden lg:table-cell px-2.5 sm:px-4 py-3 sm:py-3.5 w-36 sm:w-44 min-w-[120px]">{t('resourceManagement.colAuthority')}</th>
              <th className="hidden lg:table-cell px-2 sm:px-3.5 py-3 sm:py-3.5 w-24 sm:w-28 min-w-[85px] text-center whitespace-nowrap">{t('resourceManagement.colDate')}</th>
              <th className="hidden sm:table-cell px-2 sm:px-3.5 py-3 sm:py-3.5 w-28 sm:w-36 min-w-[95px] text-center whitespace-nowrap">{t('resourceManagement.colStatus')}</th>
              <th className="hidden sm:table-cell px-2 sm:px-3.5 py-3 sm:py-3.5 w-24 sm:w-32 min-w-[80px] text-center whitespace-nowrap">{t('resourceManagement.colFile')}</th>
              <th className="px-2 sm:px-3 py-3 sm:py-3.5 w-12 sm:w-16 min-w-[44px] text-center whitespace-nowrap">{t('resourceManagement.colActions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {isLoading ? (
              // Trạng thái Loading (Skeleton)
              Array.from({ length: pageSize > 5 ? 5 : pageSize }).map((_, idx) => (
                <tr key={idx} className="animate-pulse">
                  <td className="hidden sm:table-cell px-4 py-4">
                    <div className="h-4 w-20 bg-surface-elevated rounded" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="h-4 w-3/4 bg-surface-elevated rounded mb-1.5" />
                    <div className="h-3 w-1/3 bg-surface-elevated rounded" />
                  </td>
                  <td className="hidden lg:table-cell px-4 py-4">
                    <div className="h-4 w-28 bg-surface-elevated rounded" />
                  </td>
                  <td className="hidden lg:table-cell px-4 py-4 text-center">
                    <div className="h-4 w-16 bg-surface-elevated rounded mx-auto" />
                  </td>
                  <td className="hidden sm:table-cell px-4 py-4 text-center">
                    <div className="h-5 w-24 bg-surface-elevated rounded-full mx-auto" />
                  </td>
                  <td className="hidden sm:table-cell px-4 py-4 text-center">
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
                        {t('resourceManagement.errorLoadDocs')}
                      </p>
                    </div>
                    {onRetry && (
                      <button
                        type="button"
                        onClick={onRetry}
                        className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-white hover:bg-primary-hover transition-colors cursor-pointer"
                      >
                        <i className="fa-solid fa-rotate-right text-[11px]" />
                        <span>{t('resourceManagement.retry')}</span>
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
                const itemCanEdit = Boolean(onEdit && (canEdit ? canEdit(item) : true));
                const itemCanDelete = Boolean(onDelete && (canDelete ? canDelete(item) : true));

                // TÍNH TOÁN HIỆU LỰC THỰC TẾ THEO THỜI GIAN
                const validity = computeEffectiveStatus(
                  item.hieu_luc,
                  item.ngay_het_hieu_luc,
                  item.link_thay_the
                );
                const isExpired = validity.isExpired;

                const rowClass = isExpired
                  ? 'bg-slate-100/70 dark:bg-slate-800/60 text-slate-500 hover:bg-slate-200/50 dark:hover:bg-slate-800/80'
                  : 'hover:bg-slate-50 dark:hover:bg-slate-800/40 text-main';

                return (
                  <tr
                    key={item.id}
                    onClick={() => {
                      // Bấm dòng → Chỉ hiện chi tiết của tài liệu đó
                      onViewDetail?.(item);
                    }}
                    className={`transition-colors duration-fast cursor-pointer select-none ${rowClass}`}
                    title={t('resourceManagement.clickToViewDetail')}
                  >
                    {/* Cột 1: Ký hiệu (Ẩn trên mobile, hiện từ sm: tablet/desktop) */}
                    <td className="hidden sm:table-cell px-2.5 sm:px-4 py-3 sm:py-3.5 align-middle whitespace-nowrap">
                      <span className="text-xs font-semibold text-main tracking-tight">
                        {item.ky_hieu || '-'}
                      </span>
                    </td>

                    {/* Cột 2: Tiêu đề + Loại tài liệu + Link thay thế (Cùng hàng cân đối tuyệt đối) */}
                    <td className="px-2.5 sm:px-4 py-3 sm:py-3.5 align-middle">
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
                      {(item.hieu_luc === 'HET_VA_THAY_THE' || validity.status === 'HET_VA_THAY_THE') && item.link_thay_the && (
                        <div className="mt-1 opacity-100">
                          <a
                            href={item.link_thay_the}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-xs text-primary hover:underline font-medium hover:text-primary-hover"
                            title={t('resourceManagement.viewReplacement')}
                          >
                            <span>{t('resourceManagement.viewReplacement')}</span>
                            <i className="fa-solid fa-arrow-up-right-from-square text-[9px]" />
                          </a>
                        </div>
                      )}
                    </td>

                    {/* Cột 3: Nơi ban hành (Ẩn trên mobile & tablet, hiện từ lg: desktop) */}
                    <td className="hidden lg:table-cell px-2.5 sm:px-4 py-3 sm:py-3.5 align-middle text-xs text-secondary leading-snug">
                      {item.noi_ban_hanh || '-'}
                    </td>

                    {/* Cột 4: Ngày đăng (Ẩn trên mobile & tablet, hiện từ lg: desktop) */}
                    <td className="hidden lg:table-cell px-2 sm:px-3.5 py-3 sm:py-3.5 text-center align-middle whitespace-nowrap text-xs text-secondary leading-snug">
                      {formatDate(item.ngay_dang)}
                    </td>

                    {/* Cột 5: Hiệu lực (Ẩn trên mobile, hiện từ sm: tablet/desktop) */}
                    <td className="hidden sm:table-cell px-2 sm:px-3.5 py-3 sm:py-3.5 text-center align-middle whitespace-nowrap opacity-100">
                      {renderStatusBadge(item)}
                    </td>

                    {/* Cột 6: Tệp đính kèm (Ẩn trên mobile, hiện từ sm: tablet/desktop) */}
                    <td
                      className="hidden sm:table-cell px-2 sm:px-3.5 py-3 sm:py-3.5 text-center align-middle whitespace-nowrap opacity-100"
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewDetail?.(item);
                      }}
                    >
                      {renderFileBadges(item)}
                    </td>

                    {/* Cột 7: Thao tác — Menu "⋯": Xem chi tiết, Chỉnh sửa, Xóa */}
                    <td
                      className="px-2 sm:px-3 py-3 sm:py-3.5 text-center align-middle whitespace-nowrap opacity-100"
                      onClick={(e) => e.stopPropagation()}
                      data-dropdown-root
                    >
                      <div className="relative inline-block text-left" data-dropdown-root>
                        <button
                          type="button"
                          onClick={(e) => openActionMenu(e, item.id)}
                          className="w-8 h-7 rounded-lg inline-flex items-center justify-center text-muted hover:text-main hover:bg-surface-elevated transition-colors cursor-pointer"
                          title={t('resourceManagement.actionMenu')}
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
                            aria-label={t('resourceManagement.viewDetailDoc')}
                          >
                            <i className="fa-solid fa-eye text-muted text-xs" />
                            <span>{t('resourceManagement.viewDetail')}</span>
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
                              aria-label={t('resourceManagement.goToFolder')}
                            >
                              <i className="fa-solid fa-folder-open text-primary text-xs" />
                              <span className="text-primary font-medium">{t('resourceManagement.goToFolder')}</span>
                            </button>
                          )}

                          {/* Phân cách trước nhóm chỉnh sửa/xóa */}
                          {(itemCanEdit || itemCanDelete) && (
                            <div className="my-1 border-t border-border-subtle" />
                          )}

                          {/* Mục 3: Chỉnh sửa */}
                          {itemCanEdit && (
                            <button
                              type="button"
                              onClick={() => {
                                setActiveMenuId(null);
                                setMenuPos(null);
                                onEdit?.(item);
                              }}
                              className="w-full px-3 py-2 text-xs text-left text-main hover:bg-surface-elevated flex items-center gap-2 transition-colors cursor-pointer"
                              aria-label={t('resourceManagement.edit')}
                            >
                              <i className="fa-solid fa-pen-to-square text-muted text-xs" />
                              <span>{t('resourceManagement.edit')}</span>
                            </button>
                          )}

                          {/* Mục 4: Xóa tài liệu */}
                          {itemCanDelete && (
                            <button
                              type="button"
                              onClick={() => {
                                setActiveMenuId(null);
                                setMenuPos(null);
                                onDelete?.(item);
                              }}
                              className="w-full px-3 py-2 text-xs text-left text-danger hover:bg-danger-subtle flex items-center gap-2 transition-colors cursor-pointer font-medium"
                              aria-label={t('resourceManagement.delete')}
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
        className="flex flex-col md:flex-row items-center justify-between gap-3 px-3 sm:px-4 py-3 border-t border-border-subtle text-xs text-secondary bg-surface"
      >
        {/* Bên trái chân bảng: Dropdown chọn số dòng & Thông tin tổng số */}
        <div className="flex items-center gap-2 sm:gap-2.5 shrink-0 select-none">
          <span className="font-medium">{t('resourceManagement.display')}</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
            className="px-2 py-1 bg-surface-elevated border border-border-subtle rounded-md text-main text-xs focus:outline-hidden focus:border-primary cursor-pointer font-medium"
            aria-label={t('resourceManagement.selectRowsPerPageAria')}
          >
            <option value={5}>5 {t('resourceManagement.rows')}</option>
            <option value={10}>10 {t('resourceManagement.rows')}</option>
            <option value={20}>20 {t('resourceManagement.rows')}</option>
            <option value={50}>50 {t('resourceManagement.rows')}</option>
          </select>
          <span className="font-medium">/ {t('resourceManagement.rowsPerPage')}</span>
        </div>

        {/* Cụm điều hướng phân trang hoàn chỉnh */}
        {totalPages > 1 && (
          <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap justify-center select-none">
            <div className="flex items-center gap-0.5 sm:gap-1">
              {/* Nút về trang đầu */}
              <button
                type="button"
                disabled={currentPage <= 1 || isLoading}
                onClick={() => handlePageChange(1)}
                className="min-w-[28px] sm:min-w-[32px] h-7 sm:h-8 px-1.5 sm:px-2 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
                title={t('resourceManagement.firstPageTitle')}
                aria-label={t('resourceManagement.firstPage')}
              >
                <i className="fa-solid fa-angles-left text-[10px] sm:text-[11px]" />
              </button>

              {/* Nút lùi 1 trang */}
              <button
                type="button"
                disabled={currentPage <= 1 || isLoading}
                onClick={() => handlePageChange(currentPage - 1)}
                className="min-w-[28px] sm:min-w-[32px] h-7 sm:h-8 px-1.5 sm:px-2 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
                title={t('resourceManagement.prevPage')}
                aria-label={t('resourceManagement.prevPage')}
              >
                <i className="fa-solid fa-chevron-left text-[10px] sm:text-[11px]" />
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
                      className="group min-w-[28px] sm:min-w-[32px] h-7 sm:h-8 px-1 text-xs font-medium rounded-lg border border-transparent hover:border-border-subtle hover:bg-surface-elevated text-muted hover:text-primary transition-all cursor-pointer flex items-center justify-center"
                      title={
                        item.direction === 'prev'
                          ? t('resourceManagement.jumpBackPages', { page: item.targetPage })
                          : t('resourceManagement.jumpForwardPages', { page: item.targetPage })
                      }
                      aria-label={item.direction === 'prev' ? t('resourceManagement.jumpBackAria') : t('resourceManagement.jumpForwardAria')}
                    >
                      <span className="group-hover:hidden tracking-widest text-[10px] sm:text-[11px] font-bold">•••</span>
                      <i
                        className={`hidden group-hover:inline fa-solid text-[9px] sm:text-[10px] ${
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
                    className={`min-w-[28px] sm:min-w-[32px] h-7 sm:h-8 px-1.5 sm:px-2 text-xs font-semibold rounded-lg transition-all cursor-pointer flex items-center justify-center ${
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

              {/* Nút tiến 1 trang */}
              <button
                type="button"
                disabled={currentPage >= totalPages || isLoading}
                onClick={() => handlePageChange(currentPage + 1)}
                className="min-w-[28px] sm:min-w-[32px] h-7 sm:h-8 px-1.5 sm:px-2 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
                title={t('resourceManagement.nextPage')}
                aria-label={t('resourceManagement.nextPage')}
              >
                <i className="fa-solid fa-chevron-right text-[10px] sm:text-[11px]" />
              </button>

              {/* Nút đến trang cuối */}
              <button
                type="button"
                disabled={currentPage >= totalPages || isLoading}
                onClick={() => handlePageChange(totalPages)}
                className="min-w-[28px] sm:min-w-[32px] h-7 sm:h-8 px-1.5 sm:px-2 text-xs font-medium rounded-lg border border-border-subtle bg-surface hover:bg-surface-elevated text-secondary hover:text-main disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer flex items-center justify-center"
                title={t('resourceManagement.lastPageTitle', { total: totalPages })}
                aria-label={t('resourceManagement.lastPage')}
              >
                <i className="fa-solid fa-angles-right text-[10px] sm:text-[11px]" />
              </button>
            </div>

            {/* Ô nhảy nhanh đến trang (Hiện khi có từ 5 trang trở lên) */}
            {totalPages > 4 && (
              <form
                onSubmit={handleJumpPage}
                className="flex items-center gap-1 sm:gap-1.5 pl-1.5 sm:pl-2 border-l border-border-subtle text-secondary"
              >
                <span className="text-[10px] sm:text-[11px] whitespace-nowrap">{t('resourceManagement.jumpTo')}</span>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  value={jumpPageInput}
                  onChange={(e) => setJumpPageInput(e.target.value.replace(/\D/g, ''))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleJumpPage();
                      (e.target as HTMLInputElement).blur();
                    }
                  }}
                  placeholder={String(currentPage)}
                  title={t('resourceManagement.jumpPageTooltip')}
                  className="w-10 sm:w-12 h-7 sm:h-8 px-1 text-center bg-surface-elevated border border-border-subtle rounded-lg text-main text-xs focus:outline-hidden focus:border-primary font-medium [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                  aria-label={t('resourceManagement.jumpPageAria')}
                />
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
