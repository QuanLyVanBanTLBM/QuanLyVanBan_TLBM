import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ResourceItem, ResourceAttachment } from '@app-types/resource';
import { Badge } from '@components/common/Badge';
import { Button } from '@components/common/Button';
import { useTranslation } from '@i18n/translate';
import { computeEffectiveStatus } from '@lib/resourceValidity';
import { apiClientBlob, downloadBlob } from '@lib/apiClient';
import { FilePreviewModal } from './FilePreviewModal';

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
  const [previewAttachment, setPreviewAttachment] = useState<ResourceAttachment | null>(null);
  const [loadingFileId, setLoadingFileId] = useState<number | string | null>(null);

  // Kiểm tra tệp có thể mở xem trực tiếp trong tab mới (PDF, Ảnh)
  const isDirectPreviewable = (fileName?: string) => {
    if (!fileName) return false;
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    return ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'bmp'].includes(ext);
  };

  // Tải tệp đính kèm về máy (ZIP, DOCX, EXCEL hoặc khi bấm Tải về)
  const handleDownloadAttachment = async (file: { id?: number; name: string; path?: string }) => {
    const downloadUrl = file.id
      ? `/api/resources/attachments/${file.id}/download/`
      : (file.path || item?.file_dinh_kem || '');

    if (!downloadUrl) return;

    try {
      setLoadingFileId(file.id ?? file.name);
      await downloadBlob(downloadUrl, file.name);
    } catch (err) {
      console.warn('Lỗi downloadBlob, chuyển sang fallback tải file:', err);
      if (item && onDownloadFile) {
        onDownloadFile(item, file.name, file.path);
      } else {
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = file.name;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }
    } finally {
      setLoadingFileId(null);
    }
  };

  // Xem trước tệp: PDF/Ảnh -> mở tab mới; ZIP/DOCX/EXCEL -> tải về máy
  const handlePreviewAttachment = async (file: { id?: number; name: string; path?: string; file_size?: number; mime_type?: string }) => {
    const isPreviewable = isDirectPreviewable(file.name);
    const targetUrl = file.id
      ? `/api/resources/attachments/${file.id}/view/`
      : (file.path || item?.file_dinh_kem);

    if (!targetUrl) return;

    // Đối với zip, docx, excel hoặc tệp không xem trực tiếp được -> Tải về máy
    if (!isPreviewable) {
      await handleDownloadAttachment(file);
      return;
    }

    // Đối với PDF hoặc Ảnh -> Mở tab mới xem luôn
    try {
      setLoadingFileId(file.id ?? file.name);
      const rawBlob = await apiClientBlob(targetUrl);
      const lower = file.name.toLowerCase();
      let mimeType = rawBlob.type;
      if (lower.endsWith('.pdf')) {
        mimeType = 'application/pdf';
      } else if (lower.endsWith('.png')) {
        mimeType = 'image/png';
      } else if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) {
        mimeType = 'image/jpeg';
      } else if (lower.endsWith('.webp')) {
        mimeType = 'image/webp';
      } else if (lower.endsWith('.gif')) {
        mimeType = 'image/gif';
      } else if (lower.endsWith('.svg')) {
        mimeType = 'image/svg+xml';
      } else if (lower.endsWith('.bmp')) {
        mimeType = 'image/bmp';
      }
      const viewBlob = mimeType ? new Blob([rawBlob], { type: mimeType }) : rawBlob;
      const blobUrl = window.URL.createObjectURL(viewBlob);
      window.open(blobUrl, '_blank');
    } catch (err) {
      console.error('Lỗi khi mở xem trước tệp trong tab mới:', err);
      window.open(targetUrl, '_blank');
    } finally {
      setLoadingFileId(null);
    }
  };

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

  // Format dung lượng tệp
  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes <= 0) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1).replace('.', ',')} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`;
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
      case 'CSV':
        return 'fa-file-excel text-[#107C41] dark:text-emerald-400';
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

  const validity = computeEffectiveStatus(item.hieu_luc, item.ngay_het_hieu_luc, item.link_thay_the);

  // Render Badge trạng thái hiệu lực
  const renderStatusBadge = () => {
    if (validity.isScheduled && validity.expirationDate) {
      return (
        <Badge variant="success" size="md" withDot>
          {t('resourceManagement.statusActive')} ({t('resourceManagement.expiresOnDate', { date: formatDate(validity.expirationDate) })})
        </Badge>
      );
    }
    switch (validity.status) {
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
        return <Badge variant="secondary" size="md">{validity.status}</Badge>;
    }
  };

  // Danh sách tệp cần hiển thị (ưu tiên attachments mảng, nếu không fallback về file_dinh_kem)
  const activeAttachments = (item.attachments || []).filter((att) => !att.is_deleted);
  const filesList = activeAttachments.length > 0
    ? activeAttachments
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
      className="fixed inset-0 z-[9999] flex items-center justify-center p-2 sm:p-6 bg-black/60 backdrop-blur-xs animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full max-w-3xl max-h-[90vh] bg-surface rounded-2xl border border-border-subtle shadow-2xl flex flex-col overflow-hidden animate-slide-in-bottom"
        onClick={(e) => e.stopPropagation()}
      >
        {/* KHỐI 1: Đầu Popup (Tiêu đề, Ký hiệu, badge Hiệu lực, nút đóng) */}
        <div className="flex items-start justify-between px-4 sm:px-6 py-4 sm:py-5 border-b border-border-subtle bg-surface-elevated shrink-0 gap-3 sm:gap-4">
          <div className="min-w-0 space-y-1.5 flex-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              {item.ky_hieu && (
                <span className="text-xs font-semibold text-secondary">
                  {item.ky_hieu}
                </span>
              )}
              {renderStatusBadge()}
            </div>
            <h2 className="text-base sm:text-lg font-bold text-main leading-snug">
              {item.tieu_de}
            </h2>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface transition-colors cursor-pointer shrink-0"
            aria-label={t('resourceManagement.close')}
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Nội dung cuộn dọc */}
        <div className="flex-1 overflow-y-auto p-3.5 sm:p-6 space-y-4 sm:space-y-5 min-h-0">
          {/* KHỐI 2: Banner theo hiệu lực ngay đầu nội dung */}
          {validity.isScheduled && (
            <div className="p-3.5 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-700 dark:text-blue-300 text-xs sm:text-sm flex items-center gap-2.5">
              <i className="fa-solid fa-calendar-check text-base shrink-0" />
              <span>
                {t('resourceManagement.scheduledExpiryNotice', {
                  date: formatDate(validity.expirationDate),
                })}
              </span>
            </div>
          )}

          {validity.status === 'HET_VA_THAY_THE' && (
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
                  <span className="italic">{t('resourceManagement.noReplacementLink')}</span>
                )}
              </div>
            </div>
          )}

          {validity.status === 'HET_HIEU_LUC' && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-400 text-xs sm:text-sm flex items-center gap-2.5">
              <i className="fa-solid fa-circle-xmark text-base shrink-0" />
              <span>{t('resourceManagement.expiredBannerNormal')}</span>
            </div>
          )}

          {validity.status === 'CON_HIEU_LUC_1_PHAN' && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-400 text-xs sm:text-sm flex items-center gap-2.5">
              <i className="fa-solid fa-circle-info text-base shrink-0" />
              <span>{t('resourceManagement.partialBanner')}</span>
            </div>
          )}

          {/* KHỐI 3: Thông tin chung */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-muted uppercase tracking-wider border-b border-border-subtle pb-1.5">
              {t('resourceManagement.generalInfo')}
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
                    <span className="text-muted italic text-xs">{t('resourceManagement.unclassified')}</span>
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
                <span className="text-main font-medium">{formatDate(item.ngay_dang)}</span>
              </div>

              {/* Ngày hết hiệu lực */}
              {item.ngay_het_hieu_luc && (
                <div>
                  <span className="text-xs text-muted block mb-0.5">{t('resourceManagement.fieldExpirationDate')}</span>
                  <span className={`font-medium ${validity.isExpired ? 'text-danger' : 'text-blue-600 dark:text-blue-400'}`}>
                    {formatDate(item.ngay_het_hieu_luc)}
                  </span>
                </div>
              )}

              {/* Phạm vi hiển thị */}
              <div>
                <span className="text-xs text-muted block mb-0.5">{t('resourceManagement.fieldDisplayScope')}</span>
                <span className="text-main">
                  {item.hien_thi === 'TAT_CA' ? t('resourceManagement.scopeAll') : t('resourceManagement.scopeInternalOnly')}
                </span>
              </div>

              {/* Đơn vị sở hữu */}
              <div>
                <span className="text-xs text-muted block mb-0.5">{t('resourceManagement.fieldScope')}</span>
                <span className="text-main">{item.don_vi_id ? `Đơn vị #${item.don_vi_id}` : t('resourceManagement.headquarters')}</span>
              </div>

              {/* Người tạo */}
              <div>
                <span className="text-xs text-muted block mb-0.5">{t('resourceManagement.fieldAuthor')}</span>
                <span className="text-main">{item.nguoi_tao_name || t('resourceManagement.systemUser')}</span>
              </div>
            </div>

            {/* Ghi chú nếu có */}
            {item.ghi_chu && (
              <div className="pt-2">
                <span className="text-xs text-muted block mb-0.5">{t('resourceManagement.fieldNotes')}</span>
                <p className="text-xs text-secondary bg-surface-elevated p-2.5 rounded-lg border border-border-subtle/60 leading-relaxed">
                  {item.ghi_chu}
                </p>
              </div>
            )}
          </div>

          {/* KHỐI 4: Tệp đính kèm */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-muted uppercase tracking-wider border-b border-border-subtle pb-1.5 flex items-center justify-between">
              <span>{t('resourceManagement.fieldAttachments')}</span>
              <span className="text-[11px] text-secondary font-medium">
                {filesList.length} {t('resourceManagement.attachment')}
              </span>
            </h3>

            {filesList.length > 0 ? (
              <div className="space-y-2">
                {filesList.map((file, idx) => {
                  const ext = getFileExt(file.name || file.path, file.mime_type);
                  const isCurrentLoading = loadingFileId === (file.id ?? file.name);

                  return (
                    <div
                      key={idx}
                      onClick={() => handlePreviewAttachment(file)}
                      className="p-3 rounded-xl bg-surface-elevated border border-border-subtle flex items-center justify-between gap-3 text-xs sm:text-sm hover:border-primary/50 hover:bg-primary-subtle/10 transition-all cursor-pointer group"
                      title={t('resourceManagement.previewAttachment')}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <i className={`fa-solid ${getFileIcon(ext)} text-lg shrink-0 group-hover:scale-110 transition-transform`} />
                        <div className="min-w-0">
                          <p className="font-semibold text-main truncate group-hover:text-primary transition-colors" title={file.name}>
                            {file.name}
                          </p>
                          <p className="text-[11px] text-muted">
                            {ext}
                            {file.file_size ? ` · ${formatFileSize(file.file_size)}` : ''}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePreviewAttachment(file);
                          }}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold rounded-lg bg-surface border border-border-subtle text-secondary hover:text-primary hover:border-primary/40 hover:bg-surface-elevated transition-colors cursor-pointer"
                          title={t('resourceManagement.previewAttachment')}
                          aria-label={t('resourceManagement.previewAttachment')}
                        >
                          <i className={`fa-solid ${isCurrentLoading ? 'fa-spinner fa-spin' : 'fa-eye'} text-xs`} />
                          <span className="hidden sm:inline">{t('resourceManagement.previewAttachment')}</span>
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownloadAttachment(file);
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-surface border border-border-subtle text-secondary hover:text-primary hover:border-primary/40 hover:bg-surface-elevated transition-colors cursor-pointer"
                          title={t('resourceManagement.download')}
                          aria-label={`Tải về ${file.name}`}
                        >
                          <i className="fa-solid fa-download text-xs" />
                          <span>{t('resourceManagement.download')}</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-muted italic">{t('resourceManagement.noAttachments')}</p>
            )}
          </div>
        </div>

        {/* KHỐI 5: Chân Popup ([Tải về] chính, [Sửa], [Xóa], [Đóng]) */}
        <div className="px-4 sm:px-6 py-3.5 sm:py-4 border-t border-border-subtle bg-surface-elevated flex items-center justify-between flex-wrap sm:flex-nowrap gap-2 sm:gap-3 shrink-0">
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

      {/* Modal xem trước tệp đính kèm */}
      {previewAttachment && (
        <FilePreviewModal
          isOpen={Boolean(previewAttachment)}
          onClose={() => setPreviewAttachment(null)}
          file={previewAttachment}
          documentTitle={item.tieu_de}
          onDownload={() => onDownloadFile?.(item, previewAttachment.name, previewAttachment.path)}
        />
      )}
    </div>,
    document.body
  );
};
