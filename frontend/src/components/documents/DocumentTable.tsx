import React, { useState, useEffect, useRef } from 'react';
import { DocumentItem } from '@app-types/document';
import { Badge } from '@components/common/Badge';
import { Button } from '@components/common/Button';
import { formatDate } from '@lib/dateUtils';

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
}

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
}) => {
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

  return (
    <div className="bg-surface border border-border-subtle rounded-xl shadow-sm overflow-hidden transition-all duration-normal">
      {/* Bảng Dữ Liệu */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse min-w-[950px]">
          <thead>
            <tr className="bg-surface-elevated/70 text-xs font-bold text-muted uppercase tracking-wider border-b border-border-subtle">
              <th className="px-4 py-3 text-center w-16">Số đến</th>
              <th className="px-4 py-3 w-40">Số, ký hiệu</th>
              <th className="px-4 py-3 w-40">Ngày văn bản</th>
              <th className="px-4 py-3 min-w-[280px]">Trích yếu nội dung</th>
              <th className="px-4 py-3 w-48">Nơi ban hành</th>
              <th className="px-4 py-3 w-40 text-center">Hiệu lực</th>
              <th className="px-4 py-3 w-20 text-center">Tác vụ</th>
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
                      Không tìm thấy văn bản đến nào
                    </span>
                    <span className="text-xs text-muted max-w-sm">
                      Không có văn bản nào phù hợp với điều kiện tìm kiếm. Hãy thử chọn năm khác hoặc đặt lại bộ lọc.
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              /* Danh sách văn bản */
              documents.map((doc, index) => {
                const isExpired = doc.hieu_luc === 'HET_HIEU_LUC';
                const isReplaced = doc.hieu_luc === 'HET_VA_THAY_THE';
                const isPartial = doc.hieu_luc === 'CON_HIEU_LUC_1_PHAN';
                const isActive = doc.hieu_luc === 'CON_HIEU_LUC';
                const isActiveRow = activeMenuId === doc.id;
                const isNearBottom = index >= documents.length - 2 && documents.length > 2;

                // Quyền sửa & xóa: Cán bộ có thể thao tác khi có hàm xử lý
                const canEdit = !isConfidential && Boolean(onEdit);
                const canDelete = !isConfidential && Boolean(onDelete);

                // Tông màu hàng theo trạng thái hiệu lực:
                // - Văn bản có hiệu lực: tông xanh lá nhẹ + viền trái xanh lá
                // - Văn bản còn hiệu lực 1 phần: tông tím nhẹ + viền trái tím
                // - Văn bản đã thay thế: tông cam/hổ phách nhẹ + viền trái cam
                // - Văn bản hết hiệu lực: tông tối/đỏ nhẹ + viền trái đỏ
                const rowHighlightClass = isExpired
                  ? 'bg-slate-500/10 dark:bg-black/40 border-l-4 border-l-danger hover:bg-slate-500/15'
                  : isReplaced
                    ? 'bg-amber-500/5 dark:bg-amber-950/20 border-l-4 border-l-warning hover:bg-amber-500/10'
                    : isPartial
                      ? 'bg-purple-500/5 dark:bg-purple-950/20 border-l-4 border-l-purple-500 hover:bg-purple-500/10'
                      : isActive
                        ? 'bg-emerald-500/5 dark:bg-emerald-950/20 border-l-4 border-l-emerald-500 hover:bg-emerald-500/10'
                        : 'hover:bg-surface-hover/80 transition-colors border-l-4 border-l-transparent';

                return (
                  <tr
                    key={doc.id}
                    className={`${rowHighlightClass} transition-colors group ${isActiveRow ? 'relative z-30' : ''
                      }`}
                  >
                    {/* 1. Số đến */}
                    <td className="px-4 py-3.5 text-center font-bold text-primary whitespace-nowrap text-sm">
                      {doc.so_thu_tu ? `#${doc.so_thu_tu}` : '—'}
                    </td>

                    {/* 2. Số, ký hiệu */}
                    <td className="px-4 py-3.5 font-semibold text-main whitespace-nowrap text-sm">
                      <button
                        type="button"
                        onClick={() => onViewDetail(doc.id)}
                        className="text-left font-semibold text-main hover:text-primary hover:underline transition-colors flex items-center gap-1.5"
                        title="Bấm để xem chi tiết văn bản"
                      >
                        <i className="fa-solid fa-file-contract text-primary/70 text-xs shrink-0" />
                        <span>{doc.so_hieu}</span>
                      </button>
                    </td>

                    {/* 3. Ngày văn bản (đồng bộ với VB Đi và VB Mật, kèm ngày tiếp nhận đến) */}
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      <div className="text-sm font-semibold text-main flex items-center gap-1.5">
                        <i className="fa-regular fa-calendar text-primary text-xs" />
                        <span>{formatDate(doc.ngay_van_ban || doc.ngay_ban_hanh)}</span>
                      </div>
                      {doc.ngay_den && (
                        <div className="text-xs text-muted flex items-center gap-1.5 mt-0.5" title={`Ngày tiếp nhận đến: ${formatDate(doc.ngay_den)}`}>
                          <i className="fa-regular fa-calendar-check text-muted text-xs" />
                          <span>Đến: {formatDate(doc.ngay_den)}</span>
                        </div>
                      )}
                    </td>

                    {/* 4. Trích yếu nội dung */}
                    <td className="px-4 py-3.5">
                      <div
                        className="line-clamp-2 text-main text-sm leading-relaxed cursor-pointer hover:text-primary transition-colors"
                        title={doc.trich_yeu}
                        onClick={() => onViewDetail(doc.id)}
                      >
                        {doc.trich_yeu}
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                        {doc.attachment_count > 0 && (
                          <div className="inline-flex items-center gap-1 text-xs text-secondary bg-surface-elevated px-2 py-0.5 rounded-md border border-border-subtle">
                            <i className="fa-solid fa-paperclip text-primary text-xs" />
                            <span>{doc.attachment_count} tệp đính kèm</span>
                          </div>
                        )}
                        {(() => {
                          const repList: string[] = (doc.danh_sach_thay_the && doc.danh_sach_thay_the.length > 0)
                            ? doc.danh_sach_thay_the
                            : (doc.link_thay_the ? doc.link_thay_the.split(',').map((s) => s.trim()).filter(Boolean) : []);

                          if (repList.length === 0) return null;

                          return repList.map((targetSoHieu, idx) => {
                            if (doc.hieu_luc === 'CON_HIEU_LUC') {
                              return (
                                <div
                                  key={idx}
                                  className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20"
                                  title={`Thay thế cho văn bản: ${targetSoHieu}`}
                                >
                                  <i className="fa-solid fa-repeat text-emerald-600 dark:text-emerald-400 text-xs" />
                                  <span>Thay thế: <strong className="font-mono">{targetSoHieu}</strong></span>
                                </div>
                              );
                            }
                            if (doc.hieu_luc === 'CON_HIEU_LUC_1_PHAN') {
                              return (
                                <div
                                  key={idx}
                                  className="inline-flex items-center gap-1 text-xs font-medium text-purple-700 dark:text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-md border border-purple-500/20"
                                  title={`Thay thế cho văn bản: ${targetSoHieu}`}
                                >
                                  <i className="fa-solid fa-repeat text-purple-600 dark:text-purple-400 text-xs" />
                                  <span>Thay thế: <strong className="font-mono">{targetSoHieu}</strong></span>
                                </div>
                              );
                            }
                            if (doc.hieu_luc === 'HET_VA_THAY_THE') {
                              return (
                                <div
                                  key={idx}
                                  className="inline-flex items-center gap-1 text-xs font-medium text-warning-text bg-warning/10 px-2 py-0.5 rounded-md border border-warning/30"
                                  title={`Bị thay thế bởi văn bản: ${targetSoHieu}`}
                                >
                                  <i className="fa-solid fa-triangle-exclamation text-warning text-xs" />
                                  <span>Bị thay bởi: <strong className="font-mono">{targetSoHieu}</strong></span>
                                </div>
                              );
                            }
                            // Khi văn bản đã hết hiệu lực theo ngày nhưng vẫn lưu giữ lịch sử thay thế
                            return (
                              <div
                                key={idx}
                                className="inline-flex items-center gap-1 text-xs font-medium text-secondary bg-surface-elevated px-2 py-0.5 rounded-md border border-border-subtle"
                                title={`Văn bản liên quan: ${targetSoHieu}`}
                              >
                                <i className="fa-solid fa-repeat text-muted text-xs" />
                                <span>Thay thế: <strong className="font-mono">{targetSoHieu}</strong></span>
                              </div>
                            );
                          });
                        })()}
                      </div>
                    </td>

                    {/* 5. Nơi ban hành */}
                    <td className="px-4 py-3.5 text-sm text-secondary whitespace-nowrap">
                      <div className="flex items-center gap-1.5" title={doc.noi_ban_hanh || ''}>
                        <i className="fa-solid fa-building-columns text-muted text-xs" />
                        <span className="truncate max-w-[180px]">{doc.noi_ban_hanh || '—'}</span>
                      </div>
                    </td>

                    {/* 6. Trạng thái Hiệu lực (Badge) */}
                    <td className="px-4 py-3.5 text-center whitespace-nowrap">
                      {doc.hieu_luc === 'CON_HIEU_LUC' && (
                        <div>
                          <Badge variant="success" size="sm" withDot>
                            Còn hiệu lực
                          </Badge>
                          {doc.ngay_het_hieu_luc && (
                            <div className="text-xs text-muted mt-0.5" title={`Hết hạn vào: ${formatDate(doc.ngay_het_hieu_luc)}`}>
                              Hết hạn: {formatDate(doc.ngay_het_hieu_luc)}
                            </div>
                          )}
                        </div>
                      )}
                      {doc.hieu_luc === 'CON_HIEU_LUC_1_PHAN' && (
                        <div>
                          <Badge variant="purple" size="sm" withDot>
                            Hiệu lực 1 phần
                          </Badge>
                          {doc.ngay_het_hieu_luc && (
                            <div className="text-xs text-muted mt-0.5" title={`Hết hạn vào: ${formatDate(doc.ngay_het_hieu_luc)}`}>
                              Hết hạn: {formatDate(doc.ngay_het_hieu_luc)}
                            </div>
                          )}
                        </div>
                      )}
                      {doc.hieu_luc === 'HET_HIEU_LUC' && (
                        <div>
                          <Badge variant="danger" size="sm" withDot>
                            Hết hiệu lực
                          </Badge>
                          {doc.ngay_het_hieu_luc && (
                            <div className="text-xs text-danger/80 font-medium mt-0.5" title={`Đã hết hạn từ: ${formatDate(doc.ngay_het_hieu_luc)}`}>
                              Hết hạn: {formatDate(doc.ngay_het_hieu_luc)}
                            </div>
                          )}
                        </div>
                      )}
                      {doc.hieu_luc === 'HET_VA_THAY_THE' && (
                        <Badge variant="warning" size="sm" withDot>
                          Đã thay thế
                        </Badge>
                      )}
                    </td>

                    {/* 7. Tác vụ: Menu 3 chấm ⋮ */}
                    <td className={`px-4 py-3.5 text-center relative ${isActiveRow ? 'z-50' : ''}`}>
                      <div className="inline-block text-left" ref={activeMenuId === doc.id ? menuRef : null}>
                        <button
                          type="button"
                          onClick={() => setActiveMenuId(activeMenuId === doc.id ? null : doc.id)}
                          className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface-elevated transition-colors"
                          title="Tác vụ"
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
                              <span>Xem chi tiết</span>
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
                              <span>Lịch sử xem</span>
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
                                <span>Chỉnh sửa</span>
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
                                  <span>Xóa văn bản</span>
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

      {/* Thanh Phân Trang (Pagination Footer) */}
      <div className="px-4 py-3 border-t border-border-subtle bg-surface-elevated/40 flex flex-wrap items-center justify-between gap-3 text-sm">
        <div className="text-muted flex items-center gap-2">
          <span>
            Hiển thị <span className="font-semibold text-main">{startIdx}</span> -{' '}
            <span className="font-semibold text-main">{endIdx}</span> trên tổng số{' '}
            <span className="font-semibold text-main">{totalCount}</span> văn bản
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
            title="Trang trước"
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
            title="Trang kế tiếp"
          >
            <i className="fa-solid fa-chevron-right text-[0.7rem]" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default DocumentTable;
