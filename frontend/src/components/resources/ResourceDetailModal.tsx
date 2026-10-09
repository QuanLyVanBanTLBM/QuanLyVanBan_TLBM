import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ResourceItem, ResourceAttachment, HieuLucType } from '@app-types/resource';
import { Badge } from '@components/common/Badge';
import { Button } from '@components/common/Button';
import { useTranslation } from '@i18n/translate';

export interface ResourceDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: ResourceItem | null;
  onEdit?: (item: ResourceItem) => void;
  onDelete?: (item: ResourceItem) => void;
  onDownloadFile?: (item: ResourceItem, fileName?: string, filePath?: string) => void;
}

export const ResourceDetailModal: React.FC<ResourceDetailModalProps> = ({
  isOpen,
  onClose,
  item,
  onEdit,
  onDelete,
  onDownloadFile,
}) => {
  const { t } = useTranslation();
  // Lắng nghe phím ESC để đóng Modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !item) return null;
  if (typeof document === 'undefined') return null;

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

  // Format dung lượng tệp
  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes <= 0) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1).replace('.', ',')} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`;
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

  // Icon theo loại tệp
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

  // Render Badge trạng thái hiệu lực
  const renderStatusBadge = (hieuLuc: HieuLucType) => {
    switch (hieuLuc) {
      case 'CON_HIEU_LUC':
        return (
          <Badge variant="success" size="md" withDot>
            {t('resourceManagement.statusActive')}
          </Badge>
        );
      case 'CON_HIEU_LUC_1_PHAN':
        return (
          <Badge variant="warning" size="md" withDot>
            {t('resourceManagement.statusPartial')}
          </Badge>
        );
      case 'HET_HIEU_LUC':
        return (
          <Badge variant="danger" size="md" withDot>
            {t('resourceManagement.statusExpired')}
          </Badge>
        );
      case 'HET_VA_THAY_THE':
        return (
          <Badge variant="warning" size="md" withDot>
            {t('resourceManagement.statusExpired')}
          </Badge>
        );
      default:
        return <Badge variant="secondary" size="md">{hieuLuc}</Badge>;
    }
  };

  // Danh sách tệp cần hiển thị (ưu tiên attachments mảng, nếu không fallback về file_dinh_kem)
  const filesList = item.attachments && item.attachments.length > 0
    ? item.attachments
    : item.file_dinh_kem
      ? [{
          name: (item.file_dinh_kem.startsWith('blob:')
            ? `${item.tieu_de || 'Tệp đính kèm'}.pdf`
            : item.file_dinh_kem.split('?')[0].split('/').pop()) || 'Tệp đính kèm',
          path: item.file_dinh_kem,
        }]
      : [];

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-xs animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full max-w-3xl max-h-[90vh] bg-surface rounded-2xl border border-border-subtle shadow-2xl flex flex-col overflow-hidden animate-slide-in-bottom"
        onClick={(e) => e.stopPropagation()}
      >
        {/* KHỐI 1: Đầu Popup (Tiêu đề, Ký hiệu, badge Hiệu lực, nút đóng) */}
        <div className="flex items-start justify-between px-6 py-5 border-b border-border-subtle bg-surface-elevated shrink-0 gap-4">
          <div className="min-w-0 space-y-1.5 flex-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              {item.ky_hieu && (
                <span className="font-mono text-xs font-semibold text-secondary">
                  {item.ky_hieu}
                </span>
              )}
              {renderStatusBadge(item.hieu_luc)}
            </div>
            <h2 className="text-base sm:text-lg font-bold text-main leading-snug">
              {item.tieu_de}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface transition-colors cursor-pointer shrink-0"
            aria-label="Đóng popup"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Nội dung cuộn dọc */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5 min-h-0">
          {/* KHỐI 2: Banner theo hiệu lực ngay đầu nội dung */}
          {item.hieu_luc === 'HET_VA_THAY_THE' && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-400 text-xs sm:text-sm flex items-start gap-2.5">
              <i className="fa-solid fa-triangle-exclamation text-base shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold block">{t('resourceManagement.expiredBannerReplaced')}</span>
                {item.link_thay_the ? (
                  <a
                    href={item.link_thay_the}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 font-bold underline hover:opacity-80"
                  >
                    <span>{t('resourceManagement.viewReplacement')}</span>
                    <i className="fa-solid fa-arrow-up-right-from-square text-[10px]" />
                  </a>
                ) : (
                  <span className="italic">Chưa có liên kết văn bản thay thế</span>
                )}
              </div>
            </div>
          )}

          {item.hieu_luc === 'HET_HIEU_LUC' && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-400 text-xs sm:text-sm flex items-center gap-2.5">
              <i className="fa-solid fa-circle-xmark text-base shrink-0" />
              <span>{t('resourceManagement.expiredBannerNormal')}</span>
            </div>
          )}

          {item.hieu_luc === 'CON_HIEU_LUC_1_PHAN' && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-400 text-xs sm:text-sm flex items-center gap-2.5">
              <i className="fa-solid fa-circle-info text-base shrink-0" />
              <span>{t('resourceManagement.partialBanner')}</span>
            </div>
          )}

          {/* KHỐI 3: Thông tin chung */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-muted uppercase tracking-wider border-b border-border-subtle pb-1.5">
              Thông tin chung
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-3.5 gap-x-6 text-xs sm:text-sm">
              {/* Thư mục */}
              <div>
                <span className="text-xs text-muted block mb-0.5">{t('resourceManagement.fieldFolder')}</span>
                <span className="font-semibold text-main">
                  {item.dm_tai_lieu_name || `Thư mục #${item.dm_tai_lieu}`}
                </span>
              </div>

              {/* Loại tài liệu (tag) */}
              <div>
                <span className="text-xs text-muted block mb-1">{t('resourceManagement.fieldType')}</span>
                <div className="flex flex-wrap gap-1.5">
                  {item.loai_tai_lieu_names && item.loai_tai_lieu_names.length > 0 ? (
                    item.loai_tai_lieu_names.map((name, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 text-xs rounded-md bg-surface-elevated border border-border-subtle text-secondary font-medium"
                      >
                        {name}
                      </span>
                    ))
                  ) : (
                    <span className="text-muted italic text-xs">Chưa phân loại</span>
                  )}
                </div>
              </div>

              {/* Nơi ban hành */}
              <div>
                <span className="text-xs text-muted block mb-0.5">{t('resourceManagement.fieldIssuingAuthority')}</span>
                <span className="text-main font-medium">{item.noi_ban_hanh || '-'}</span>
              </div>

              {/* Ngày đăng */}
              <div>
                <span className="text-xs text-muted block mb-0.5">{t('resourceManagement.fieldPostedDate')}</span>
                <span className="font-mono text-main">{formatDate(item.ngay_dang)}</span>
              </div>

              {/* Ngày hết hiệu lực (nếu có) */}
              {item.ngay_het_hieu_luc && (
                <div>
                  <span className="text-xs text-muted block mb-0.5">{t('resourceManagement.fieldExpirationDate')}</span>
                  <span className="font-mono text-danger font-medium">
                    {formatDate(item.ngay_het_hieu_luc)}
                  </span>
                </div>
              )}

              {/* Phạm vi hiển thị */}
              <div>
                <span className="text-xs text-muted block mb-0.5">Phạm vi hiển thị</span>
                <span className="text-main">
                  {item.hien_thi === 'TAT_CA' ? 'Tất cả đơn vị' : 'Nội bộ phòng ban'}
                </span>
              </div>

              {/* Đơn vị sở hữu */}
              <div>
                <span className="text-xs text-muted block mb-0.5">Đơn vị sở hữu</span>
                <span className="text-main">{item.don_vi_id ? `Đơn vị #${item.don_vi_id}` : 'Tổng công ty'}</span>
              </div>

              {/* Người tạo */}
              <div>
                <span className="text-xs text-muted block mb-0.5">Người tạo</span>
                <span className="text-main">{item.nguoi_tao_name || 'Hệ thống'}</span>
              </div>
            </div>

            {/* Ghi chú nếu có */}
            {item.ghi_chu && (
              <div className="pt-2">
                <span className="text-xs text-muted block mb-0.5">Ghi chú</span>
                <p className="text-xs text-secondary bg-surface-elevated p-2.5 rounded-lg border border-border-subtle/60 leading-relaxed">
                  {item.ghi_chu}
                </p>
              </div>
            )}
          </div>

          {/* KHỐI 4: Tệp đính kèm */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-muted uppercase tracking-wider border-b border-border-subtle pb-1.5 flex items-center justify-between">
              <span>Tệp đính kèm</span>
              <span className="text-[11px] text-secondary font-medium font-mono">
                {filesList.length} tệp
              </span>
            </h3>

            {filesList.length > 0 ? (
              <div className="space-y-2">
                {filesList.map((file, idx) => {
                  const ext = getFileExt(file.name || file.path, item.attachments);
                  return (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-surface-elevated border border-border-subtle flex items-center justify-between gap-3 text-xs sm:text-sm hover:border-primary/40 transition-colors"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <i className={`fa-solid ${getFileIcon(ext)} text-lg shrink-0`} />
                        <div className="min-w-0">
                          <p className="font-semibold text-main truncate" title={file.name}>
                            {file.name}
                          </p>
                          <p className="text-[11px] text-muted font-mono">
                            {ext}
                            {file.file_size ? ` · ${formatFileSize(file.file_size)}` : ''}
                          </p>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => onDownloadFile?.(item, file.name, file.path)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary-subtle text-primary hover:bg-primary/20 transition-colors cursor-pointer shrink-0"
                        title="Tải tệp này về máy"
                        aria-label={`Tải về ${file.name}`}
                      >
                        <i className="fa-solid fa-download text-xs" />
                        <span>Tải về</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-muted italic">Không có tệp đính kèm</p>
            )}
          </div>
        </div>

        {/* KHỐI 5: Chân Popup ([Tải về] chính, [Sửa], [Xóa], [Đóng]) */}
        <div className="px-6 py-4 border-t border-border-subtle bg-surface-elevated flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2">
            {onEdit && (
              <Button
                variant="outline"
                size="sm"
                icon="fa-pen-to-square"
                onClick={() => {
                  onClose();
                  onEdit(item);
                }}
                className="text-xs"
              >
                {t('resourceManagement.edit')}
              </Button>
            )}

            {onDelete && (
              <Button
                variant="outline"
                size="sm"
                icon="fa-trash-can"
                onClick={() => {
                  onClose();
                  onDelete(item);
                }}
                className="text-xs text-danger border-danger/30 hover:bg-danger-subtle"
              >
                {t('resourceManagement.delete')}
              </Button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {filesList.length > 0 && (
              <Button
                variant="primary"
                size="sm"
                icon="fa-download"
                onClick={() => onDownloadFile?.(item)}
                className="text-xs shadow-xs"
              >
                {t('resourceManagement.download')}
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              className="text-xs"
            >
              {t('resourceManagement.close')}
            </Button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};
