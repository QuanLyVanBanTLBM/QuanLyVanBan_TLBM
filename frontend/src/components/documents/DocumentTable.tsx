import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { DocumentItem, DocumentDetail } from '@app-types/document';
import { Button } from '@components/common/Button';
import { formatDate } from '@lib/dateUtils';
import { authService } from '@lib/authService';
import apiClient from '@lib/apiClient';
import { getAbsoluteFileUrl } from '@lib/fileUtils';
import { resolveDocumentApiUrl } from '@lib/routes';
import { useTranslation } from '@i18n/translate';
import { useIsMobile } from '@hooks/useIsMobile';

export interface DocumentTableProps {
  documents: DocumentItem[];
  totalCount: number;
  page: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  onPageSizeChange?: (newPageSize: number) => void;
  isLoading?: boolean;
  onViewDetail: (id: number) => void;
  onViewHistory: (id: number) => void;
  onEdit?: (doc: DocumentItem) => void;
  onDelete?: (id: number, soHieu: string) => void;
  isConfidential?: boolean;
  loai?: 'DEN' | 'DI' | 'MAT';
}

/**
 * Lấy style cho tag "Thay thế cho" đồng bộ tông màu với cột Hiệu lực bên tay phải:
 * - Còn hiệu lực / Hết hiệu lực và thay thế: Màu xanh lá (emerald)
 * - Hiệu lực 1 phần: Màu tím (purple)
 * - Hết hiệu lực: Màu đỏ (rose/danger)
 */
const getReplacementBadgeClass = (hieuLuc?: string) => {
  switch (hieuLuc) {
    case 'CON_HIEU_LUC':
    case 'HET_VA_THAY_THE':
      return {
        badge: 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 dark:bg-emerald-500/20 border-emerald-500/30',
        icon: 'text-emerald-600 dark:text-emerald-400',
      };
    case 'CON_HIEU_LUC_1_PHAN':
      return {
        badge: 'text-purple-700 dark:text-purple-400 bg-purple-500/10 dark:bg-purple-500/20 border-purple-500/30',
        icon: 'text-purple-600 dark:text-purple-400',
      };
    case 'HET_HIEU_LUC':
      return {
        badge: 'text-rose-700 dark:text-rose-400 bg-rose-500/10 dark:bg-rose-500/20 border-rose-500/30',
        icon: 'text-rose-600 dark:text-rose-400',
      };
    default:
      return {
        badge: 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 dark:bg-emerald-500/20 border-emerald-500/30',
        icon: 'text-emerald-600 dark:text-emerald-400',
      };
  }
};

/**
 * Render badge hiển thị văn bản thay thế hoặc bị thay thế.
 * Rút gọn khi 1 văn bản thay thế nhiều văn bản khác: hiển thị số hiệu đầu + "... (+X)"
 * Rê chuột vào sẽ xem đầy đủ tooltip toàn bộ danh sách số hiệu tránh vỡ bảng.
 */
const renderReplacementBadgeGroup = (
  items: string[],
  type: 'thay_the' | 'bi_thay',
  hieuLuc?: string,
  isFallback: boolean = false,
  t?: (key: string, params?: Record<string, string>) => string
) => {
  if (!items || items.length === 0) return null;
  const isThayThe = type === 'thay_the';
  const repStyle = isThayThe ? getReplacementBadgeClass(hieuLuc) : null;
  const count = items.length;
  const replacesLabel = t ? (t('documents_ui.table.replaces') || 'Thay thế cho:') : 'Thay thế cho:';
  const replacedByLabel = t ? (t('documents_ui.table.replacedBy') || 'Bị thay bởi:') : 'Bị thay bởi:';
  const label = isThayThe ? `${replacesLabel} ` : `${replacedByLabel} `;

  if (count === 1) {
    const targetSoHieu = items[0];
    const singleTitle = isFallback
      ? (t ? t('documents_ui.table.replacesFallbackTitle', { doc: targetSoHieu }) : `Thay thế cho văn bản: ${targetSoHieu}`)
      : isThayThe
      ? (t ? t('documents_ui.table.replacesSingleTitle', { doc: targetSoHieu }) : `Văn bản này thay thế cho văn bản cũ: ${targetSoHieu}`)
      : (t ? t('documents_ui.table.replacedBySingleTitle', { doc: targetSoHieu }) : `Văn bản này đã bị thay thế bởi: ${targetSoHieu}`);

    return (
      <div
        className={
          isThayThe
            ? `inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-md border ${repStyle?.badge} max-w-full transition-all duration-150 hover:-translate-y-[0.5px] hover:shadow-xs cursor-default`
            : 'inline-flex items-center gap-1 text-xs font-medium text-warning-text bg-warning/10 px-2 py-0.5 rounded-md border border-warning/30 max-w-full transition-all duration-150 hover:-translate-y-[0.5px] hover:shadow-xs cursor-default'
        }
        title={singleTitle}
      >
        <i
          className={
            isThayThe
              ? `fa-solid fa-repeat text-xs ${repStyle?.icon}`
              : 'fa-solid fa-triangle-exclamation text-warning text-xs'
          }
        />
        <span className="truncate">
          {label}
          <strong className="font-mono">{targetSoHieu}</strong>
        </span>
      </div>
    );
  }

  // Khi có nhiều hơn 1 văn bản:
  // Nếu 2 văn bản đầu ngắn (tổng <= 20 ký tự), hiển thị cả 2; nếu dài thì hiển thị 1
  const canShowTwo = count >= 2 && items[0].length + items[1].length <= 20;
  const visibleCount = canShowTwo ? 2 : 1;
  const displayedItems = items.slice(0, visibleCount);
  const remainingCount = count - visibleCount;
  const allListStr = items.join(', ');

  const multiTitle = isThayThe
    ? (t ? t('documents_ui.table.replacesMultiTitle', { docs: allListStr }) : `Văn bản này thay thế cho các văn bản: ${allListStr}`)
    : (t ? t('documents_ui.table.replacedByMultiTitle', { docs: allListStr }) : `Văn bản này đã bị thay thế bởi các văn bản: ${allListStr}`);

  return (
    <div
      className={
        isThayThe
          ? `inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-md border ${repStyle?.badge} max-w-full transition-all duration-150 hover:-translate-y-[0.5px] hover:shadow-xs cursor-default`
          : 'inline-flex items-center gap-1 text-xs font-medium text-warning-text bg-warning/10 px-2 py-0.5 rounded-md border border-warning/30 max-w-full transition-all duration-150 hover:-translate-y-[0.5px] hover:shadow-xs cursor-default'
      }
      title={multiTitle}
    >
      <i
        className={
          isThayThe
            ? `fa-solid fa-repeat text-xs ${repStyle?.icon}`
            : 'fa-solid fa-triangle-exclamation text-warning text-xs'
        }
      />
      <span className="truncate">
        {label}
        <strong className="font-mono">{displayedItems.join(', ')}</strong>
      </span>
      {remainingCount > 0 && (
        <span
          className="shrink-0 font-semibold text-[11px] px-1.5 py-0.2 rounded bg-black/5 dark:bg-white/10 ml-0.5 transition-colors hover:bg-black/10 dark:hover:bg-white/20"
          title={`Còn ${remainingCount} văn bản: ${items.slice(visibleCount).join(', ')}`}
        >
          ... (+{remainingCount})
        </span>
      )}
    </div>
  );
};

/**
 * Định dạng mốc thời gian hiển thị (Đi / Đến / Lưu).
 * Nếu trường ngày có giờ là 00:00:00 (do nhập bằng input date không kèm giờ)
 * và có fallbackDateStr (created_at), hệ thống sẽ mượn giờ:phút:giây từ created_at
 * để bảo đảm không hiển thị "00:00:00" cho người dùng.
 */
const formatDocumentEventTime = (primaryDateStr?: string | null, fallbackDateStr?: string | null): string => {
  if (!primaryDateStr && !fallbackDateStr) return '—';
  const targetStr = primaryDateStr || fallbackDateStr!;
  const d = new Date(targetStr);
  if (isNaN(d.getTime())) return '—';

  if (d.getHours() === 0 && d.getMinutes() === 0 && d.getSeconds() === 0 && fallbackDateStr) {
    const fallbackD = new Date(fallbackDateStr);
    if (!isNaN(fallbackD.getTime()) && (fallbackD.getHours() !== 0 || fallbackD.getMinutes() !== 0 || fallbackD.getSeconds() !== 0)) {
      d.setHours(fallbackD.getHours(), fallbackD.getMinutes(), fallbackD.getSeconds());
    }
  }

  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const seconds = String(d.getSeconds()).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();

  return `${hours}:${minutes}:${seconds} ${day}/${month}/${year}`;
};

export const DocumentTable: React.FC<DocumentTableProps> = ({
  documents,
  totalCount,
  page,
  pageSize,
  onPageChange,
  isLoading = false,
  onViewDetail,
  onViewHistory,
  onEdit,
  onDelete,
  isConfidential = false,
  loai = 'DEN',
}) => {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  // Lấy thông tin phiên làm việc hiện tại để phân quyền hiển thị tác vụ
  const currentSession = useMemo(() => authService.getSession(), []);

  // Helper tính quyền sửa và xóa trên từng văn bản
  const getDocPermissions = useCallback((doc: DocumentItem) => {
    const isExpired = doc.hieu_luc === 'HET_HIEU_LUC';
    const isDocConfidential = isConfidential || doc.pham_vi === 'HAN_CHE' || doc.loai === 'MAT' || loai === 'MAT';
    const isAdmin =
      currentSession?.role === 'admin' ||
      currentSession?.username === 'admin';
    const isCreator = Boolean(
      currentSession?.username &&
      doc.nguoi_tao_username &&
      currentSession.username === doc.nguoi_tao_username
    );

    let defaultCanEdit = false;
    let defaultCanDelete = false;

    if (!currentSession) {
      if (!isDocConfidential && !isExpired) {
        defaultCanEdit = true;
        defaultCanDelete = true;
      }
    } else if (isAdmin) {
      defaultCanEdit = true;
      defaultCanDelete = true;
    } else if (!isDocConfidential && isCreator && !isExpired) {
      defaultCanEdit = true;
      defaultCanDelete = true;
    }

    let userCanEdit = doc.can_edit !== undefined ? doc.can_edit : defaultCanEdit;
    let userCanDelete = doc.can_delete !== undefined ? doc.can_delete : defaultCanDelete;

    if (isDocConfidential && !isAdmin) {
      userCanEdit = false;
      userCanDelete = false;
    }

    return {
      canEdit: Boolean(onEdit) && userCanEdit,
      canDelete: Boolean(onDelete) && userCanDelete,
    };
  }, [currentSession, isConfidential, loai, onDelete, onEdit]);

  // Quản lý menu 3 chấm ⋮ mở trên dòng nào
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Đóng menu khi click ra ngoài hoặc nhấn phím ESC
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setActiveMenuId(null);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveMenuId(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const startIdx = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const endIdx = Math.min(page * pageSize, totalCount);

  // Tạo mảng số trang hiển thị
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    if (totalPages <= 5) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (page > 3) pages.push('...');
      const start = Math.max(2, page - 1);
      const end = Math.min(totalPages - 1, page + 1);
      for (let i = start; i <= end; i++) pages.push(i);
      if (page < totalPages - 2) pages.push('...');
      pages.push(totalPages);
    }
    return pages;
  };

  // Mở tệp đính kèm trực tiếp trong tab mới
  const handleOpenAttachment = async (e: React.MouseEvent, doc: DocumentItem) => {
    e.stopPropagation();
    if (doc.first_attachment_url) {
      const fullUrl = getAbsoluteFileUrl(doc.first_attachment_url);
      window.open(fullUrl, '_blank', 'noopener,noreferrer');
      return;
    }
    try {
      const apiUrl = resolveDocumentApiUrl(doc.id, loai || doc.loai);
      const res = await apiClient.get<DocumentDetail>(apiUrl);
      if (res && res.attachments && res.attachments.length > 0 && res.attachments[0].file) {
        const fullUrl = getAbsoluteFileUrl(res.attachments[0].file);
        window.open(fullUrl, '_blank', 'noopener,noreferrer');
      } else {
        onViewDetail(doc.id);
      }
    } catch {
      onViewDetail(doc.id);
    }
  };

  return (
    <div className="bg-surface border border-border-subtle rounded-xl shadow-sm overflow-hidden transition-all duration-normal">
      {!isMobile ? (
        /* Bảng Dữ Liệu (Desktop & Tablet >= md) */
        <div className="overflow-x-auto min-h-[380px] pb-24 touch-pan-x overscroll-x-contain">
          <table className="w-full text-left text-sm border-separate border-spacing-0 min-w-[950px]">
          <thead>
            <tr className="bg-surface-elevated/70 text-xs font-bold text-muted uppercase tracking-wider border-b border-border-subtle">
              <th className="px-4 py-3 text-center w-16">{t('documents_ui.table.colStt') || 'STT'}</th>
              <th className="px-4 py-3 w-40">{t('documents_ui.table.colCode') || 'Số, ký hiệu'}</th>
              <th className="px-4 py-3 w-48">{t('documents_ui.table.colTimestamp') || 'Mốc thời gian'}</th>
              <th className="px-4 py-3 min-w-[280px]">{t('documents_ui.table.colSummary') || 'Trích yếu nội dung'}</th>
              <th className="px-4 py-3 w-48">{loai === 'DI' || loai === 'MAT' ? (t('documents_ui.table.colSigner') || 'Người ký') : (t('documents_ui.table.colIssuer') || 'Nơi ban hành')}</th>
              <th className="px-4 py-3 w-40 text-center">{t('documents_ui.table.colStatus') || 'Hiệu lực'}</th>
              <th className="px-4 py-3 w-20 text-center">{t('documents_ui.table.colActions') || 'Tác vụ'}</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-border-subtle/70">
            {/* Trạng thái Loading Shimmer */}
            {isLoading ? (
              Array.from({ length: 5 }).map((_, idx) => (
                <tr key={idx} className="animate-pulse">
                  <td className="px-4 py-3.5 text-center">
                    <div className="h-4 bg-muted/20 rounded w-8 mx-auto" />
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="h-4 bg-muted/20 rounded w-28" />
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="h-3.5 bg-muted/20 rounded w-32 mb-1.5" />
                    <div className="h-3 bg-muted/15 rounded w-24" />
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="h-4 bg-muted/20 rounded w-full mb-1" />
                    <div className="h-3 bg-muted/15 rounded w-3/4" />
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="h-4 bg-muted/20 rounded w-28" />
                  </td>
                  <td className="px-4 py-3.5 text-center">
                    <div className="h-6 bg-muted/20 rounded-full w-24 mx-auto" />
                  </td>
                  <td className="px-4 py-3.5 text-center">
                    <div className="h-7 w-7 bg-muted/20 rounded mx-auto" />
                  </td>
                </tr>
              ))
            ) : documents.length === 0 ? (
              /* Trạng thái Không có dữ liệu (Empty State) */
              <tr>
                <td colSpan={7} className="py-12 text-center">
                  <div className="flex flex-col items-center justify-center gap-2">
                    <div className="w-12 h-12 rounded-full bg-surface-elevated flex items-center justify-center text-muted text-xl mb-1 border border-border-subtle">
                      <i className="fa-solid fa-folder-open text-muted" />
                    </div>
                    <span className="text-sm font-semibold text-secondary">
                      {loai === 'MAT' ? (t('documents_ui.table.emptyConfidentialTitle') || 'Không tìm thấy văn bản mật nào') : loai === 'DI' ? (t('documents_ui.table.emptyOutboundTitle') || 'Không tìm thấy văn bản đi nào') : (t('documents_ui.table.emptyInboundTitle') || 'Không tìm thấy văn bản đến nào')}
                    </span>
                    <span className="text-xs text-muted max-w-sm">
                      {t('documents_ui.table.emptyDesc') || 'Không có văn bản nào phù hợp với điều kiện tìm kiếm. Hãy thử chọn năm khác hoặc đặt lại bộ lọc.'}
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              /* Danh sách văn bản */
              documents.map((doc, index) => {
                const isExpired = doc.hieu_luc === 'HET_HIEU_LUC';
                const isActiveRow = activeMenuId === doc.id;
                const isNearBottom = documents.length >= 5 && index >= documents.length - 2 && index >= 3;
                const { canEdit, canDelete } = getDocPermissions(doc);

                // Tông màu hàng theo yêu cầu:
                // - Toàn bộ hàng trắng đồng nhất, di chuột vào sáng trắng/xám nhẹ
                // - Trừ văn bản hết hiệu lực để màu xám cho dễ nhận biết
                const rowHighlightClass = isExpired
                  ? 'bg-slate-100/90 dark:bg-slate-800/40 text-muted hover:bg-slate-200/90 hover:shadow-md hover:relative hover:z-20 hover:-translate-y-[1px]'
                  : 'bg-white dark:bg-surface hover:bg-blue-50/80 dark:hover:bg-slate-800/80 hover:shadow-[0_6px_20px_rgba(37,99,235,0.09)] dark:hover:shadow-[0_6px_20px_rgba(0,0,0,0.5)] hover:-translate-y-[1.5px] hover:relative hover:z-20';

                return (
                  <tr
                    key={doc.id}
                    onClick={() => onViewDetail(doc.id)}
                    className={`${rowHighlightClass} cursor-pointer transition-all duration-150 ease-out group ${
                      isActiveRow ? 'relative z-30 ring-2 ring-primary/40' : ''
                    }`}
                    title={t('documents_ui.table.clickToView') || 'Bấm vào hàng để xem chi tiết văn bản'}
                  >
                    {/* 1. STT dòng */}
                    <td className="px-4 py-3.5 text-center font-bold text-primary whitespace-nowrap text-sm">
                      #{(page - 1) * pageSize + index + 1}
                    </td>

                    {/* 2. Số, ký hiệu */}
                    <td className="px-4 py-3.5 font-semibold text-main whitespace-nowrap text-sm">
                      <div className="flex flex-col items-start gap-1">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => onViewDetail(doc.id)}
                            className="text-left font-semibold text-main group-hover:text-primary transition-colors flex items-center gap-1.5"
                            title={t('documents_ui.table.clickDocToView') || 'Bấm để xem chi tiết văn bản'}
                          >
                            <i className="fa-solid fa-file-contract text-primary/70 group-hover:text-primary group-hover:scale-110 text-xs shrink-0 transition-transform duration-150" />
                            <span>{doc.so_hieu}</span>
                          </button>
                          {doc.pham_vi === 'HAN_CHE' && (
                            <span
                              className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/25 shrink-0 transition-all duration-150 hover:-translate-y-[0.5px] hover:shadow-xs cursor-default"
                              title={t('documents_ui.table.restrictedTooltip') || 'Văn bản hạn chế (Bảo mật)'}
                            >
                              <i className="fa-solid fa-shield-halved text-[11px] text-rose-600 dark:text-rose-400" />
                              <span>{t('documents_ui.table.restrictedBadge') || 'Hạn chế'}</span>
                            </span>
                          )}
                        </div>

                        {/* Badge Số đi / Số đến (Số vào sổ CSDL) */}
                        {doc.so_thu_tu ? (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-secondary border border-border-subtle tracking-tight">
                            {loai === 'DI'
                              ? (t('documents_ui.table.outboundNumSub', { num: String(doc.so_thu_tu) }) || `Số đi: #${doc.so_thu_tu}`)
                              : (t('documents_ui.table.inboundNumSub', { num: String(doc.so_thu_tu) }) || `Số đến: #${doc.so_thu_tu}`)}
                          </span>
                        ) : null}
                      </div>
                    </td>

                    {/* 3. Mốc thời gian (Đồng bộ đẹp 14px: Đi/Đến/Lưu & Ký ngày) */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      {loai === 'DI' ? (
                        <div className="text-sm font-semibold text-main flex items-center gap-1.5">
                          <i className="fa-regular fa-clock text-primary text-xs" />
                          <span>{t('documents_ui.table.timeOutbound') || 'Đi:'} {formatDocumentEventTime(doc.ngay_ban_hanh, doc.created_at)}</span>
                        </div>
                      ) : (
                        <div className="text-sm font-semibold text-main flex items-center gap-1.5">
                          <i className="fa-regular fa-clock text-primary text-xs" />
                          <span>{loai === 'MAT' ? (t('documents_ui.table.timeSaved') || 'Lưu:') : (t('documents_ui.table.timeInbound') || 'Đến:')} {formatDocumentEventTime(doc.ngay_den || doc.ngay_ban_hanh, doc.created_at)}</span>
                        </div>
                      )}
                      <div className="text-sm text-muted flex items-center gap-1.5 mt-0.5">
                        <i className="fa-regular fa-calendar text-muted text-xs" />
                        <span>{t('documents_ui.table.signedDate') || 'Ký ngày:'} {formatDate(doc.ngay_van_ban)}</span>
                      </div>
                    </td>

                    {/* 4. Trích yếu nội dung */}
                    <td className="px-4 py-3.5">
                      <div
                        className="line-clamp-2 text-main group-hover:text-primary dark:group-hover:text-blue-300 text-sm leading-relaxed transition-colors"
                        title={doc.trich_yeu}
                      >
                        {doc.trich_yeu}
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                        {doc.attachment_count > 0 && (
                          <button
                            type="button"
                            onClick={(e) => handleOpenAttachment(e, doc)}
                            className="inline-flex items-center gap-1.5 text-xs text-main dark:text-slate-200 bg-surface-elevated hover:bg-surface-elevated/90 px-2.5 py-0.5 rounded-md border border-border-subtle hover:border-border transition-colors cursor-pointer"
                            title={t('documents_ui.table.openAttachmentTitle') || 'Bấm để mở xem tệp đính kèm trong tab mới'}
                          >
                            <i className="fa-solid fa-paperclip text-xs text-secondary" />
                            <span>{t('documents_ui.table.attachmentsCount', { count: String(doc.attachment_count) }) || `${doc.attachment_count} tệp đính kèm`}</span>
                            <i className="fa-solid fa-arrow-up-right-from-square text-[0.65rem] text-secondary" />
                          </button>
                        )}
                        {(() => {
                          const hasDirectionalData = Boolean(
                            (doc.thay_the_cho && doc.thay_the_cho.length > 0) ||
                            (doc.bi_thay_boi && doc.bi_thay_boi.length > 0)
                          );

                          if (hasDirectionalData) {
                            return (
                              <>
                                {/* 1. Các văn bản mà tài liệu này đi thay thế */}
                                {renderReplacementBadgeGroup(doc.thay_the_cho || [], 'thay_the', doc.hieu_luc, false, t)}

                                {/* 2. Các văn bản mới đã đến thay thế tài liệu này */}
                                {renderReplacementBadgeGroup(doc.bi_thay_boi || [], 'bi_thay', undefined, false, t)}
                              </>
                            );
                          }

                          // Fallback khi chưa có dữ liệu 2 chiều
                          const repList: string[] = (doc.danh_sach_thay_the && doc.danh_sach_thay_the.length > 0)
                            ? doc.danh_sach_thay_the
                            : (doc.link_thay_the ? doc.link_thay_the.split(',').map((s) => s.trim()).filter(Boolean) : []);

                          if (repList.length === 0) return null;

                          return renderReplacementBadgeGroup(repList, 'thay_the', doc.hieu_luc, true, t);
                        })()}
                      </div>
                    </td>

                    {/* 5. Nơi ban hành / Người ký (Nâng lên 14px) */}
                    <td className="px-4 py-3.5 text-sm text-secondary whitespace-nowrap">
                      {loai === 'DI' || loai === 'MAT' ? (
                        <div>
                          <div className="flex items-center gap-1.5 font-medium text-main text-sm" title={doc.nguoi_ky || ''}>
                            <i className="fa-solid fa-pen-nib text-primary/70 text-xs" />
                            <span>{doc.nguoi_ky || '—'}</span>
                          </div>
                          {doc.chuc_vu && (
                            <div className="text-sm text-muted mt-0.5 pl-4 truncate max-w-[180px]" title={doc.chuc_vu}>
                              {doc.chuc_vu}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-sm" title={doc.noi_ban_hanh || ''}>
                          <i className="fa-solid fa-building-columns text-muted text-xs" />
                          <span className="truncate max-w-[180px]">{doc.noi_ban_hanh || '—'}</span>
                        </div>
                      )}
                    </td>

                    {/* 6. Trạng thái Hiệu lực (Badge nâng lên 14px) */}
                    <td className="px-4 py-3.5 text-center whitespace-nowrap">
                      {doc.hieu_luc === 'CON_HIEU_LUC' && (
                        <div>
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 shadow-2xs">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                            {t('documents_ui.table.statusActive') || 'Còn hiệu lực'}
                          </span>
                          {doc.ngay_het_hieu_luc && (
                            <div className="text-sm text-muted mt-0.5" title={`${t('documents_ui.table.expiresOn') || 'Hết hạn:'} ${formatDate(doc.ngay_het_hieu_luc)}`}>
                              {t('documents_ui.table.expiresOn') || 'Hết hạn:'} {formatDate(doc.ngay_het_hieu_luc)}
                            </div>
                          )}
                        </div>
                      )}
                      {doc.hieu_luc === 'CON_HIEU_LUC_1_PHAN' && (
                        <div>
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-purple-500/10 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400 border border-purple-500/30 shadow-2xs">
                            <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                            {t('documents_ui.table.statusPartiallyActive') || 'Còn hiệu lực 1 phần'}
                          </span>
                          {doc.ngay_het_hieu_luc && (
                            <div className="text-sm text-muted mt-0.5" title={`${t('documents_ui.table.expiresOn') || 'Hết hạn:'} ${formatDate(doc.ngay_het_hieu_luc)}`}>
                              {t('documents_ui.table.expiresOn') || 'Hết hạn:'} {formatDate(doc.ngay_het_hieu_luc)}
                            </div>
                          )}
                        </div>
                      )}
                      {(doc.hieu_luc === 'HET_HIEU_LUC' || doc.hieu_luc === 'HET_VA_THAY_THE') && (
                        <div>
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold bg-rose-500/10 dark:bg-rose-500/20 text-rose-700 dark:text-rose-400 border border-rose-500/30 shadow-2xs">
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                            {t('documents_ui.table.statusExpired') || 'Hết hiệu lực'}
                          </span>
                          {doc.ngay_het_hieu_luc && (
                            <div className="text-sm text-danger/80 font-medium mt-0.5" title={`${t('documents_ui.table.expiredSince') || 'Đã hết hạn từ:'} ${formatDate(doc.ngay_het_hieu_luc)}`}>
                              {t('documents_ui.table.expiresOn') || 'Hết hạn:'} {formatDate(doc.ngay_het_hieu_luc)}
                            </div>
                          )}
                        </div>
                      )}
                    </td>

                    {/* 7. Tác vụ: Menu 3 chấm ⋮ */}
                    <td
                      className={`px-4 py-3.5 text-center relative ${isActiveRow ? 'z-50' : ''}`}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="inline-block text-left" ref={activeMenuId === doc.id ? menuRef : null}>
                        <button
                          type="button"
                          onClick={() => setActiveMenuId(activeMenuId === doc.id ? null : doc.id)}
                          className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface-elevated transition-colors"
                          title={t('documents_ui.table.colActions') || 'Tác vụ'}
                        >
                          <i className="fa-solid fa-ellipsis-vertical text-base" />
                        </button>

                        {/* Dropdown Menu Popup */}
                        {activeMenuId === doc.id && (
                          <div
                            className={`absolute right-3 ${isNearBottom ? 'bottom-full mb-1' : 'top-full mt-1'
                              } w-52 bg-surface-elevated border border-border-subtle rounded-xl shadow-2xl z-50 py-1.5 animate-in fade-in zoom-in-95 duration-100 select-none`}
                          >
                            {/* 1. Nút Xem chi tiết */}
                            <button
                              type="button"
                              onClick={() => {
                                setActiveMenuId(null);
                                onViewDetail(doc.id);
                              }}
                              className="w-full text-left px-3.5 py-2 text-sm text-main hover:bg-primary-subtle hover:text-primary flex items-center gap-2.5 transition-colors cursor-pointer"
                            >
                              <i className="fa-solid fa-eye text-primary w-4 text-xs" />
                              <span>{t('documents_ui.table.viewDetail') || 'Xem chi tiết'}</span>
                            </button>

                            {/* 2. Nút Lịch sử xem */}
                            <button
                              type="button"
                              onClick={() => {
                                setActiveMenuId(null);
                                onViewHistory(doc.id);
                              }}
                              className="w-full text-left px-3.5 py-2 text-sm text-main hover:bg-info-subtle hover:text-info flex items-center gap-2.5 transition-colors cursor-pointer"
                            >
                              <i className="fa-solid fa-clock-rotate-left text-info w-4 text-xs" />
                              <span>{t('documents_ui.table.viewHistory') || 'Lịch sử xem'}</span>
                            </button>

                            {/* 3. Nút Chỉnh sửa */}
                            {canEdit && (
                              <button
                                type="button"
                                onClick={() => {
                                  setActiveMenuId(null);
                                  onEdit!(doc);
                                }}
                                className="w-full text-left px-3.5 py-2 text-sm text-main hover:bg-warning-subtle hover:text-warning-text flex items-center gap-2.5 transition-colors cursor-pointer"
                              >
                                <i className="fa-solid fa-pen-to-square text-warning-text w-4 text-xs" />
                                <span>{t('documents_ui.table.edit') || 'Chỉnh sửa'}</span>
                              </button>
                            )}

                            {/* 5. Nút Xóa văn bản */}
                            {canDelete && (
                              <>
                                <div className="border-t border-border-subtle/50 my-1" />
                                <button
                                  type="button"
                                  onClick={() => {
                                    setActiveMenuId(null);
                                    onDelete!(doc.id, doc.so_hieu);
                                  }}
                                  className="w-full text-left px-3.5 py-2 text-sm text-danger hover:bg-danger-subtle flex items-center gap-2.5 transition-colors cursor-pointer"
                                >
                                  <i className="fa-solid fa-trash-can w-4 text-xs" />
                                  <span>{t('documents_ui.table.delete') || 'Xóa văn bản'}</span>
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
        </div>
      ) : (
        /* Mobile Card View (Hiển thị riêng cho thiết bị di động < md theo Giải pháp 1) */
        <div className="p-3 space-y-3 pb-8">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, idx) => (
            <div key={idx} className="bg-surface-elevated/50 border border-border-subtle rounded-xl p-4 space-y-3 animate-pulse">
              <div className="flex items-center justify-between">
                <div className="h-4 bg-muted/20 rounded w-24" />
                <div className="h-5 bg-muted/20 rounded-full w-20" />
              </div>
              <div className="h-4 bg-muted/20 rounded w-full" />
              <div className="h-3 bg-muted/15 rounded w-3/4" />
              <div className="flex justify-between pt-2 border-t border-border-subtle/40">
                <div className="h-3 bg-muted/15 rounded w-28" />
                <div className="h-6 bg-muted/20 rounded w-16" />
              </div>
            </div>
          ))
        ) : documents.length === 0 ? (
          <div className="py-10 text-center">
            <div className="w-12 h-12 rounded-full bg-surface-elevated flex items-center justify-center text-muted text-xl mx-auto mb-2 border border-border-subtle">
              <i className="fa-solid fa-folder-open text-muted" />
            </div>
            <p className="text-sm font-semibold text-secondary">
              {loai === 'MAT'
                ? (t('documents_ui.table.emptyConfidentialTitle') || 'Không tìm thấy văn bản mật nào')
                : loai === 'DI'
                ? (t('documents_ui.table.emptyOutboundTitle') || 'Không tìm thấy văn bản đi nào')
                : (t('documents_ui.table.emptyInboundTitle') || 'Không tìm thấy văn bản đến nào')}
            </p>
            <p className="text-xs text-muted mt-1 px-4">
              {t('documents_ui.table.emptyDesc') || 'Không có văn bản nào phù hợp với điều kiện tìm kiếm. Hãy thử chọn năm khác hoặc đặt lại bộ lọc.'}
            </p>
          </div>
        ) : (
          documents.map((doc, index) => {
            const isExpired = doc.hieu_luc === 'HET_HIEU_LUC';
            const { canEdit, canDelete } = getDocPermissions(doc);

            return (
              <div
                key={`mobile-${doc.id}`}
                onClick={() => onViewDetail(doc.id)}
                className={`border rounded-xl p-3.5 shadow-sm transition-all cursor-pointer ${
                  isExpired
                    ? 'bg-slate-50/90 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700/60'
                    : 'bg-white dark:bg-surface border-border-subtle hover:border-primary/50'
                }`}
                title={t('documents_ui.table.clickToView') || 'Bấm vào thẻ để xem chi tiết văn bản'}
              >
                {/* Header thẻ: STT + Số hiệu + Badge Hạn chế + Trạng thái */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5 min-w-0">
                    {(() => {
                      const stt = (page - 1) * pageSize + index + 1;
                      const subLabel = loai === 'DI'
                        ? (t('documents_ui.table.outboundNumSub', { num: String(doc.so_thu_tu) }) || `Số đi: #${doc.so_thu_tu}`)
                        : (t('documents_ui.table.inboundNumSub', { num: String(doc.so_thu_tu) }) || `Số đến: #${doc.so_thu_tu}`);

                      return (
                        <>
                          <span className="text-xs font-bold text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                            #{stt}
                          </span>
                          {doc.so_thu_tu ? (
                            <span className="text-[11px] font-medium text-muted bg-surface-elevated border border-border-subtle px-1.5 py-0.5 rounded">
                              {subLabel}
                            </span>
                          ) : null}
                        </>
                      );
                    })()}
                    <span className="text-sm font-semibold text-main truncate hover:text-primary">
                      {doc.so_hieu}
                    </span>
                    {doc.pham_vi === 'HAN_CHE' && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.2 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/25">
                        <i className="fa-solid fa-shield-halved text-[9px]" />
                        {t('documents_ui.table.restrictedBadge') || 'Hạn chế'}
                      </span>
                    )}
                  </div>

                  {/* Trạng thái hiệu lực */}
                  <div className="shrink-0 text-right">
                    {doc.hieu_luc === 'CON_HIEU_LUC' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        {t('documents_ui.table.statusActive') || 'Còn hiệu lực'}
                      </span>
                    )}
                    {doc.hieu_luc === 'CON_HIEU_LUC_1_PHAN' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/30">
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                        {t('documents_ui.table.statusPartiallyActive') || 'Hiệu lực 1 phần'}
                      </span>
                    )}
                    {(doc.hieu_luc === 'HET_HIEU_LUC' || doc.hieu_luc === 'HET_VA_THAY_THE') && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/30">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                        {t('documents_ui.table.statusExpired') || 'Hết hiệu lực'}
                      </span>
                    )}
                  </div>
                </div>

                {/* Trích yếu */}
                <p className="text-xs text-main font-medium line-clamp-3 leading-relaxed mt-2" title={doc.trich_yeu}>
                  {doc.trich_yeu}
                </p>

                {/* Tệp đính kèm và badge thay thế (nếu có) */}
                <div className="flex flex-wrap items-center gap-1.5 mt-2">
                  {doc.attachment_count > 0 && (
                    <button
                      type="button"
                      onClick={(e) => handleOpenAttachment(e, doc)}
                      className="inline-flex items-center gap-1 text-[11px] text-main bg-surface-elevated hover:bg-surface-elevated/90 px-2 py-0.5 rounded border border-border-subtle"
                    >
                      <i className="fa-solid fa-paperclip text-[10px] text-secondary" />
                      <span>{t('documents_ui.table.attachmentsCount', { count: String(doc.attachment_count) }) || `${doc.attachment_count} tệp`}</span>
                      <i className="fa-solid fa-arrow-up-right-from-square text-[9px] text-secondary" />
                    </button>
                  )}
                  {(() => {
                    const hasDirectionalData = Boolean(
                      (doc.thay_the_cho && doc.thay_the_cho.length > 0) ||
                      (doc.bi_thay_boi && doc.bi_thay_boi.length > 0)
                    );
                    if (hasDirectionalData) {
                      return (
                        <>
                          {renderReplacementBadgeGroup(doc.thay_the_cho || [], 'thay_the', doc.hieu_luc, false, t)}
                          {renderReplacementBadgeGroup(doc.bi_thay_boi || [], 'bi_thay', undefined, false, t)}
                        </>
                      );
                    }
                    const repList = (doc.danh_sach_thay_the && doc.danh_sach_thay_the.length > 0)
                      ? doc.danh_sach_thay_the
                      : (doc.link_thay_the ? doc.link_thay_the.split(',').map((s) => s.trim()).filter(Boolean) : []);
                    if (repList.length === 0) return null;
                    return renderReplacementBadgeGroup(repList, 'thay_the', doc.hieu_luc, true, t);
                  })()}
                </div>

                {/* Thông tin phụ: Ngày & Nơi ban hành/Người ký */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-[11px] text-muted pt-2.5 mt-2.5 border-t border-border-subtle/60">
                  <div className="flex items-center gap-1.5">
                    <i className="fa-regular fa-clock text-primary text-[10px]" />
                    <span>
                      {loai === 'DI' ? (t('documents_ui.table.timeOutbound') || 'Đi: ') : loai === 'MAT' ? (t('documents_ui.table.timeSaved') || 'Lưu: ') : (t('documents_ui.table.timeInbound') || 'Đến: ')}
                      {formatDocumentEventTime(doc.ngay_den || doc.ngay_ban_hanh, doc.created_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <i className="fa-regular fa-calendar text-muted text-[10px]" />
                    <span>{t('documents_ui.table.signedDate') || 'Ký:'} {formatDate(doc.ngay_van_ban)}</span>
                  </div>
                  <div className="flex items-center gap-1.5 truncate sm:col-span-2">
                    {loai === 'DI' || loai === 'MAT' ? (
                      <>
                        <i className="fa-solid fa-pen-nib text-primary/70 text-[10px]" />
                        <span className="truncate">{doc.nguoi_ky || '—'}{doc.chuc_vu ? ` (${doc.chuc_vu})` : ''}</span>
                      </>
                    ) : (
                      <>
                        <i className="fa-solid fa-building-columns text-muted text-[10px]" />
                        <span className="truncate">{doc.noi_ban_hanh || '—'}</span>
                      </>
                    )}
                  </div>
                  {doc.ngay_het_hieu_luc && (
                    <div className="text-[10px] text-muted sm:col-span-2">
                      {isExpired ? (t('documents_ui.table.expiredSince') || 'Đã hết hạn:') : (t('documents_ui.table.expiresOn') || 'Hết hạn:')} {formatDate(doc.ngay_het_hieu_luc)}
                    </div>
                  )}
                </div>

                {/* Action buttons footer */}
                <div
                  className="flex items-center justify-end gap-1.5 pt-2 mt-2 border-t border-border-subtle/50"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    icon="fa-eye"
                    onClick={() => onViewDetail(doc.id)}
                    className="!px-2.5 !py-1 text-xs"
                  >
                    {t('documents_ui.table.viewDetail') || 'Xem'}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    icon="fa-clock-rotate-left"
                    onClick={() => onViewHistory(doc.id)}
                    className="!px-2 !py-1 text-xs"
                    title={t('documents_ui.table.viewHistory') || 'Lịch sử xem'}
                  />
                  {canEdit && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      icon="fa-pen-to-square"
                      onClick={() => onEdit!(doc)}
                      className="!px-2 !py-1 text-xs text-warning-text hover:bg-warning-subtle"
                      title={t('documents_ui.table.edit') || 'Chỉnh sửa'}
                    />
                  )}
                  {canDelete && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      icon="fa-trash-can"
                      onClick={() => onDelete!(doc.id, doc.so_hieu)}
                      className="!px-2 !py-1 text-xs text-danger hover:bg-danger-subtle"
                      title={t('documents_ui.table.delete') || 'Xóa'}
                    />
                  )}
                </div>
              </div>
            );
          })
        )}
        </div>
      )}

      {/* Thanh Phân Trang (Pagination Footer) */}
      <div className="px-4 py-3 border-t border-border-subtle bg-surface-elevated/40 flex flex-wrap items-center justify-between gap-3 text-sm">
        <div className="text-muted flex items-center gap-2">
          <span>
            {t('documents_ui.table.showing') || 'Hiển thị'}{' '}
            <span className="font-semibold text-main">{startIdx}</span>{' '}
            {t('documents_ui.table.to') || '-'}{' '}
            <span className="font-semibold text-main">{endIdx}</span>{' '}
            {t('documents_ui.table.of') || 'trên tổng số'}{' '}
            <span className="font-semibold text-main">{totalCount}</span>{' '}
            {t('documents_ui.table.documents') || 'văn bản'}
          </span>
        </div>

        {/* Nút chuyển trang */}
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1 || isLoading}
            className="!px-2 !py-1"
            title={t('documents_ui.table.prevPage') || 'Trang trước'}
          >
            <i className="fa-solid fa-chevron-left text-[0.7rem]" />
          </Button>

          {getPageNumbers().map((p, i) =>
            typeof p === 'number' ? (
              <button
                key={i}
                type="button"
                onClick={() => onPageChange(p)}
                disabled={isLoading}
                className={`min-w-[28px] h-7 px-2 rounded-lg text-xs font-semibold transition-all ${page === p
                  ? 'bg-primary text-white shadow-sm'
                  : 'text-secondary hover:text-main hover:bg-surface-elevated'
                  }`}
              >
                {p}
              </button>
            ) : (
              <span key={i} className="px-1 text-muted">
                {p}
              </span>
            )
          )}

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || isLoading}
            className="!px-2 !py-1"
            title={t('documents_ui.table.nextPage') || 'Trang kế tiếp'}
          >
            <i className="fa-solid fa-chevron-right text-[0.7rem]" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default DocumentTable;

