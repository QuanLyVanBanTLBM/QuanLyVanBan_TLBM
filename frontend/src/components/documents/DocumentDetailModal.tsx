import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { DocumentDetail } from '@app-types/document';
import { Button } from '@components/common/Button';
import { formatDateTime, formatDate, formatFileSize } from '@lib/dateUtils';
import { getAbsoluteFileUrl } from '@lib/fileUtils';
import apiClient, { apiClientBlob, downloadBlob } from '@lib/apiClient';
import { resolveDocumentApiUrl } from '@lib/routes';
import { useTranslation } from '@i18n/translate';

export interface DocumentDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: number | null;
  loai?: 'DEN' | 'DI' | 'MAT';
}

export const DocumentDetailModal: React.FC<DocumentDetailModalProps> = ({
  isOpen,
  onClose,
  documentId,
  loai,
}) => {
  const { t } = useTranslation();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState<number>(0);
  const [loadingFileId, setLoadingFileId] = useState<number | null>(null);
  const [loadingAction, setLoadingAction] = useState<'preview' | 'download' | null>(null);

  useEffect(() => {
    if (!isOpen || !documentId) {
      return;
    }
    let ignore = false;
    (async () => {
      await Promise.resolve();
      if (ignore) return;
      setIsLoading(true);
      setError(null);
      try {
        const apiUrl = resolveDocumentApiUrl(documentId, loai);
        const data = await apiClient.get<DocumentDetail>(apiUrl);
        if (!ignore) {
          setDocument(data);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const errMsg = err instanceof Error ? err.message : 'Không thể tải chi tiết văn bản.';
          setError(errMsg);
          setDocument(null);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      ignore = true;
    };
  }, [isOpen, documentId, reloadKey, loai]);

  // Đóng bằng phím ESC
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Lấy icon tương ứng loại file
  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return 'fa-solid fa-file-pdf text-danger';
    if (ext === 'doc' || ext === 'docx') return 'fa-solid fa-file-word text-primary';
    if (ext === 'jpg' || ext === 'jpeg' || ext === 'png') return 'fa-solid fa-file-image text-warning-text';
    return 'fa-solid fa-file text-secondary';
  };

  const isBrowserPreviewable = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    return ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'txt'].includes(ext);
  };

  const handlePreviewAttachment = async (fileUrl: string | null | undefined, fileName: string, fileId: number) => {
    if (!fileUrl) return;
    // Đối với tệp tin không hỗ trợ hiển thị trực tiếp trong tab trình duyệt (Word .doc, .docx, Excel .xls, .xlsx...):
    // Tự động tải về máy với đúng tên gốc và đuôi mở rộng để mở bằng ứng dụng trên máy tính
    if (!isBrowserPreviewable(fileName)) {
      await handleDownloadAttachment(fileUrl, fileName, fileId);
      return;
    }

    try {
      setLoadingFileId(fileId);
      setLoadingAction('preview');
      const rawBlob = await apiClientBlob(fileUrl);
      const lower = (fileName || '').toLowerCase();
      let mimeType = rawBlob.type;
      if (lower.endsWith('.pdf')) {
        mimeType = 'application/pdf';
      } else if (lower.endsWith('.png')) {
        mimeType = 'image/png';
      } else if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) {
        mimeType = 'image/jpeg';
      } else if (lower.endsWith('.gif')) {
        mimeType = 'image/gif';
      } else if (lower.endsWith('.webp')) {
        mimeType = 'image/webp';
      } else if (lower.endsWith('.svg')) {
        mimeType = 'image/svg+xml';
      } else if (lower.endsWith('.txt')) {
        mimeType = 'text/plain';
      }
      const viewBlob = mimeType ? new Blob([rawBlob], { type: mimeType }) : rawBlob;
      const blobUrl = window.URL.createObjectURL(viewBlob);
      window.open(blobUrl, '_blank');
    } catch (err: unknown) {
      console.error('Lỗi khi mở xem tệp tin:', err);
      const directUrl = getAbsoluteFileUrl(fileUrl);
      if (directUrl) {
        window.open(directUrl, '_blank');
      }
    } finally {
      setLoadingFileId(null);
      setLoadingAction(null);
    }
  };

  const handleDownloadAttachment = async (fileUrl: string | null | undefined, fileName: string, fileId: number) => {
    if (!fileUrl) return;

    try {
      setLoadingFileId(fileId);
      setLoadingAction('download');
      await downloadBlob(fileUrl, fileName);
    } catch (err: unknown) {
      console.error('Lỗi khi tải tệp tin:', err);
      const directUrl = getAbsoluteFileUrl(fileUrl);
      if (directUrl) {
        window.open(directUrl, '_blank');
      }
    } finally {
      setLoadingFileId(null);
      setLoadingAction(null);
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 md:p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border-subtle rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-xl overflow-hidden animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Modal */}
        <div className="px-5 py-4 border-b border-border-subtle flex items-center justify-between gap-3 bg-surface-subtle">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm shrink-0 ${document?.loai === 'MAT' ? 'bg-rose-500/10 text-rose-600' : 'bg-primary-subtle text-primary'
              }`}>
              <i className={document?.loai === 'MAT' ? 'fa-solid fa-shield-halved' : 'fa-solid fa-file-lines'} />
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-base md:text-lg font-bold text-main m-0 truncate">
                  {document?.loai === 'MAT'
                    ? (t('documents_ui.detailModal.titleConfidential') || 'Chi Tiết Văn Bản Mật')
                    : document?.loai === 'DI'
                    ? (t('documents_ui.detailModal.titleOutbound') || 'Chi Tiết Văn Bản Đi')
                    : (t('documents_ui.detailModal.titleInbound') || 'Chi Tiết Văn Bản Đến')}
                </h2>
                {document?.loai === 'MAT' && (
                  <span className="px-2 py-0.5 rounded-md text-xs font-bold bg-rose-500/15 text-rose-600 border border-rose-500/25">
                    {t('documents_ui.topCard.confidential') || 'MẬT'}
                  </span>
                )}
                {document?.pham_vi === 'HAN_CHE' && document?.loai !== 'MAT' && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/25">
                    <i className="fa-solid fa-shield-halved text-[10px]" /> {t('documents_ui.detailModal.scopeRestricted') || 'HẠN CHẾ'}
                  </span>
                )}
                {document?.so_hieu && (
                  <span className="px-2 py-0.5 rounded-md text-xs font-semibold bg-primary-subtle text-primary">
                    {document.so_hieu}
                  </span>
                )}
              </div>
              <p className="text-xs text-secondary m-0 truncate">
                {document?.loai === 'MAT'
                  ? 'Văn bản bảo mật nội bộ — Chỉ cán bộ có thẩm quyền mới có quyền tiếp cận.'
                  : 'Xem toàn bộ thông tin chi tiết và danh sách tệp đính kèm.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-secondary hover:text-main hover:bg-surface-elevated transition-colors shrink-0"
            title={t('documents_ui.detailModal.closeEsc') || 'Đóng (ESC)'}
          >
            <i className="fa-solid fa-xmark text-lg" />
          </button>
        </div>

        {/* Nội dung chi tiết (Scrollable) */}
        <div className="p-5 overflow-y-auto flex-1 space-y-5">
          {isLoading && (
            <div className="py-16 text-center text-secondary">
              <i className="fa-solid fa-circle-notch fa-spin text-2xl text-primary mb-2 block" />
              <span className="text-xs">{t('documents_ui.detailModal.loading') || 'Đang tải thông tin văn bản...'}</span>
            </div>
          )}

          {error && !isLoading && (
            <div className="bg-danger-subtle text-danger border border-danger-border rounded-xl p-4 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <i className="fa-solid fa-circle-exclamation text-base" />
                <span>{error}</span>
              </div>
              {documentId && (
                <button
                  type="button"
                  onClick={() => setReloadKey(k => k + 1)}
                  className="underline font-semibold hover:text-danger-hover"
                >
                  {t('documents_ui.detailModal.retry') || 'Thử lại'}
                </button>
              )}
            </div>
          )}

          {document && !isLoading && (
            <>
              {/* Banner liên kết thay thế 2 chiều */}
              {(((document.thay_the_cho && document.thay_the_cho.length > 0) || document.link_thay_the) && (document.hieu_luc === 'CON_HIEU_LUC' || document.hieu_luc === 'CON_HIEU_LUC_1_PHAN')) && (
                <div className="bg-primary/10 border border-primary/20 rounded-xl p-3.5 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/20 text-primary flex items-center justify-center text-sm shrink-0 mt-0.5">
                    <i className="fa-solid fa-repeat" />
                  </div>
                  <div className="text-xs">
                    <div className="font-bold text-primary mb-0.5">{t('documents_ui.detailModal.replacementBannerTitle') || 'VĂN BẢN THAY THẾ'}</div>
                    <p className="text-main m-0 leading-relaxed">
                      {t('documents_ui.detailModal.replacementBannerText') || 'Văn bản này được ban hành để thay thế cho:'}{' '}
                      <strong className="font-mono text-primary">
                        {(document.thay_the_cho && document.thay_the_cho.length > 0)
                          ? document.thay_the_cho.join(', ')
                          : document.link_thay_the}
                      </strong>.
                    </p>
                  </div>
                </div>
              )}

              {document.hieu_luc === 'CON_HIEU_LUC_1_PHAN' && Boolean(document.bi_thay_boi && document.bi_thay_boi.length > 0) && (
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-3.5 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-700 dark:text-purple-300 flex items-center justify-center text-sm shrink-0 mt-0.5">
                    <i className="fa-solid fa-circle-half-stroke" />
                  </div>
                  <div className="text-xs">
                    <div className="font-bold text-purple-700 dark:text-purple-300 mb-0.5">{t('documents_ui.detailModal.partialActiveBannerTitle') || 'VĂN BẢN CÒN HIỆU LỰC MỘT PHẦN'}</div>
                    <p className="text-main m-0 leading-relaxed">
                      {t('documents_ui.detailModal.partialActiveBannerText') || 'Văn bản này đã được sửa đổi / thay thế một phần bởi văn bản:'}{' '}
                      <strong className="font-mono text-purple-700 dark:text-purple-300">
                        {document.bi_thay_boi.join(', ')}
                      </strong>. {t('documents_ui.detailModal.partialActiveBannerNote') || 'Các điều khoản còn lại vẫn có giá trị thi hành.'}
                    </p>
                  </div>
                </div>
              )}

              {(document.hieu_luc === 'HET_HIEU_LUC' || document.hieu_luc === 'HET_VA_THAY_THE') && (
                <div className="bg-danger/10 border border-danger/30 rounded-xl p-3.5 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-danger/20 text-danger flex items-center justify-center text-sm shrink-0 mt-0.5">
                    <i className="fa-solid fa-calendar-xmark" />
                  </div>
                  <div className="text-xs">
                    <div className="font-bold text-danger mb-0.5">
                      {(document.bi_thay_boi && document.bi_thay_boi.length > 0) || document.link_thay_the
                        ? (t('documents_ui.detailModal.expiredReplacedBannerTitle') || 'VĂN BẢN ĐÃ HẾT HIỆU LỰC (ĐÃ ĐƯỢC THAY THẾ)')
                        : (t('documents_ui.detailModal.expiredBannerTitle') || 'VĂN BẢN ĐÃ HẾT HIỆU LỰC')}
                    </div>
                    <p className="text-main m-0 leading-relaxed">
                      {(document.bi_thay_boi && document.bi_thay_boi.length > 0) || document.link_thay_the ? (
                        <>{t('documents_ui.detailModal.expiredReplacedText') || 'Văn bản này không còn giá trị thi hành do đã được thay thế bởi văn bản:'}{' '}
                          <strong className="font-mono text-danger">
                            {(document.bi_thay_boi && document.bi_thay_boi.length > 0)
                              ? document.bi_thay_boi.join(', ')
                              : document.link_thay_the}
                          </strong>.
                        </>
                      ) : document.ngay_het_hieu_luc ? (
                        <>{t('documents_ui.detailModal.expiredDateText', { date: formatDate(document.ngay_het_hieu_luc) }) || `Văn bản này đã hết hiệu lực thi hành từ ngày ${formatDate(document.ngay_het_hieu_luc)}.`}</>
                      ) : (
                        <>{t('documents_ui.detailModal.expiredGeneralText') || 'Văn bản này đã hết hiệu lực thi hành.'}</>
                      )}
                    </p>
                  </div>
                </div>
              )}

              {/* Trích yếu nội dung */}
              <div className="bg-surface-subtle border border-border-subtle rounded-xl p-4">
                <span className="text-xs font-semibold text-secondary uppercase tracking-wider block mb-1.5">
                  {t('documents_ui.detailModal.summaryLabel') || 'Trích yếu nội dung'}
                </span>
                <p className="text-sm md:text-base font-medium text-main leading-relaxed m-0 whitespace-pre-wrap">
                  {document.trich_yeu}
                </p>
              </div>

              {/* Lưới thông tin văn bản */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Cột trái */}
                <div className="space-y-3 bg-surface border border-border-subtle rounded-xl p-4">
                  <h3 className="text-xs font-bold text-main uppercase tracking-wider pb-2 border-b border-border-subtle m-0 flex items-center gap-2">
                    <i className={document.loai === 'MAT' ? 'fa-solid fa-shield-halved text-rose-500' : 'fa-solid fa-hashtag text-primary'} />
                    {document.loai === 'MAT' ? (t('documents_ui.detailModal.specsConfidential') || 'Thông số văn bản mật') : document.loai === 'DI' ? (t('documents_ui.detailModal.specsOutbound') || 'Thông số đi') : (t('documents_ui.detailModal.specsInbound') || 'Thông số đến')}
                  </h3>

                  {document.loai !== 'MAT' && (
                    <div className="flex justify-between items-center text-xs py-1 border-b border-border-subtle/50">
                      <span className="text-secondary">{document.loai === 'DI' ? (t('documents_ui.detailModal.outboundNo') || 'Số đi (STT năm):') : (t('documents_ui.detailModal.inboundNo') || 'Số đến (STT năm):')}</span>
                      <span className="font-bold text-main font-mono">
                        {document.so_thu_tu !== null && document.so_thu_tu !== undefined
                          ? `#${document.so_thu_tu}`
                          : '—'}
                      </span>
                    </div>
                  )}

                  <div className="flex justify-between items-center text-xs py-1 border-b border-border-subtle/50">
                    <span className="text-secondary">{t('documents_ui.detailModal.recordYear') || 'Năm sổ sách:'}</span>
                    <span className="font-semibold text-main">{document.nam}</span>
                  </div>

                  <div className="flex justify-between items-center text-xs py-1 border-b border-border-subtle/50">
                    <span className="text-secondary">{t('documents_ui.detailModal.scope') || 'Phạm vi văn bản:'}</span>
                    <span className="font-semibold text-main">
                      {document.pham_vi === 'HAN_CHE' ? (
                        <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 font-semibold">
                          <i className="fa-solid fa-shield-halved text-[11px]" /> {t('documents_ui.detailModal.scopeRestricted') || 'Hạn chế'}
                        </span>
                      ) : (
                        t('documents_ui.detailModal.scopeInternal') || 'Nội bộ'
                      )}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-xs py-1 border-b border-border-subtle/50">
                    <span className="text-secondary">{document.loai === 'MAT' ? (t('documents_ui.detailModal.savedDate') || 'Ngày lưu văn bản:') : document.loai === 'DI' ? (t('documents_ui.detailModal.issuedDate') || 'Ngày ban hành:') : (t('documents_ui.detailModal.receivedDate') || 'Ngày đến:')}</span>
                    <span className="font-semibold text-main font-mono">
                      {(document.ngay_den || document.ngay_ban_hanh) ? formatDate(document.ngay_den || document.ngay_ban_hanh) : '—'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-xs py-1">
                    <span className="text-secondary">{t('documents_ui.detailModal.documentDate') || 'Ngày văn bản:'}</span>
                    <span className="font-semibold text-main">
                      {document.ngay_van_ban ? formatDate(document.ngay_van_ban) : '—'}
                    </span>
                  </div>
                </div>

                {/* Cột phải */}
                <div className="space-y-3 bg-surface border border-border-subtle rounded-xl p-4">
                  <h3 className="text-xs font-bold text-main uppercase tracking-wider pb-2 border-b border-border-subtle m-0 flex items-center gap-2">
                    <i className="fa-solid fa-building text-primary" /> {t('documents_ui.detailModal.authorityAndStatus') || 'Cơ quan ban hành & Hiệu lực'}
                  </h3>

                  <div className="flex justify-between items-center text-xs py-1 border-b border-border-subtle/50">
                    <span className="text-secondary">{t('documents_ui.detailModal.issuer') || 'Nơi ban hành:'}</span>
                    <span className="font-semibold text-main text-right">
                      {document.noi_ban_hanh || '—'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-xs py-1 border-b border-border-subtle/50">
                    <span className="text-secondary">{t('documents_ui.detailModal.signerPosition') || 'Người ký / Chức vụ:'}</span>
                    <span className="font-semibold text-main text-right">
                      {document.nguoi_ky ? `${document.nguoi_ky}${document.chuc_vu ? ` (${document.chuc_vu})` : ''}` : '—'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center text-xs py-1 border-b border-border-subtle/50">
                    <span className="text-secondary">{t('documents_ui.detailModal.validityStatus') || 'Trạng thái hiệu lực:'}</span>
                    {document.hieu_luc === 'CON_HIEU_LUC' ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-white dark:bg-surface-elevated text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 shadow-2xs">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        {t('documents_ui.detailModal.statusActive') || 'Còn hiệu lực'}
                      </span>
                    ) : document.hieu_luc === 'CON_HIEU_LUC_1_PHAN' ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-white dark:bg-surface-elevated text-purple-600 dark:text-purple-400 border border-purple-500/30 shadow-2xs">
                        <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                        {t('documents_ui.detailModal.statusPartiallyActive') || 'Còn hiệu lực 1 phần'}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-white dark:bg-surface-elevated text-rose-600 dark:text-rose-400 border border-rose-500/30 shadow-2xs">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                        {t('documents_ui.detailModal.statusExpired') || 'Hết hiệu lực'}
                      </span>
                    )}
                  </div>

                  {document.ngay_het_hieu_luc && (
                    <div className="flex justify-between items-center text-xs py-1">
                      <span className="text-secondary">{t('documents_ui.detailModal.expirationDate') || 'Ngày hết hiệu lực:'}</span>
                      <span className="font-semibold text-warning-text font-mono">
                        {formatDate(document.ngay_het_hieu_luc)}
                      </span>
                    </div>
                  )}

                  {/* Hiển thị chi tiết thay thế 2 chiều phân định rõ ràng */}
                  {(document.thay_the_cho && document.thay_the_cho.length > 0) ||
                    (document.bi_thay_boi && document.bi_thay_boi.length > 0) ? (
                    <>
                      {document.thay_the_cho && document.thay_the_cho.length > 0 && (
                        <div className="flex justify-between items-start text-xs py-1">
                          <span className="text-secondary shrink-0 pt-0.5">{t('documents_ui.detailModal.replaces') || 'Thay thế cho:'}</span>
                          <div className="flex flex-wrap justify-end gap-1.5 max-w-[320px]">
                            {document.thay_the_cho.map((s: string, idx: number) => (
                              <span key={`ttc-${idx}`} className="font-semibold font-mono text-[0.7rem] px-2 py-0.5 rounded-md bg-primary-subtle text-primary border border-primary/20">
                                {s.trim()}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {document.bi_thay_boi && document.bi_thay_boi.length > 0 && (
                        <div className="flex justify-between items-start text-xs py-1">
                          <span className="text-secondary shrink-0 pt-0.5">{t('documents_ui.detailModal.replacedBy') || 'Bị thay bởi:'}</span>
                          <div className="flex flex-wrap justify-end gap-1.5 max-w-[320px]">
                            {document.bi_thay_boi.map((s: string, idx: number) => (
                              <span key={`btb-${idx}`} className="font-semibold font-mono text-[0.7rem] px-2 py-0.5 rounded-md bg-warning/10 text-warning-text border border-warning/30">
                                {s.trim()}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  ) : document.link_thay_the ? (
                    <div className="flex justify-between items-start text-xs py-1">
                      <span className="text-secondary shrink-0 pt-0.5">
                        {document.hieu_luc === 'CON_HIEU_LUC' || document.hieu_luc === 'CON_HIEU_LUC_1_PHAN' ? (t('documents_ui.detailModal.replaces') || 'Thay thế cho:') : (t('documents_ui.detailModal.replacedBy') || 'Bị thay bởi:')}
                      </span>
                      <div className="flex flex-wrap justify-end gap-1.5 max-w-[320px]">
                        {document.link_thay_the.split(',').map((s: string, idx: number) => (
                          <span key={idx} className="font-semibold font-mono text-[0.7rem] px-2 py-0.5 rounded-md bg-primary-subtle text-primary border border-primary/20">
                            {s.trim()}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>

              {/* Ghi chú nếu có */}
              {document.ghi_chu && (
                <div className="bg-surface border border-border-subtle rounded-xl p-3.5 text-xs">
                  <span className="font-semibold text-secondary block mb-1">Ghi chú:</span>
                  <p className="text-main m-0 leading-relaxed">{document.ghi_chu}</p>
                </div>
              )}

              {/* Danh sách tệp đính kèm */}
              <div className="bg-surface border border-border-subtle rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
                  <h3 className="text-xs font-bold text-main uppercase tracking-wider m-0 flex items-center gap-2">
                    <i className="fa-solid fa-paperclip text-primary" /> {t('documents_ui.detailModal.attachmentsTitle') || 'Tệp đính kèm'} (
                    {document.attachments?.length || 0})
                  </h3>
                </div>

                {document.attachments && document.attachments.length > 0 ? (
                  <div className="space-y-2.5">
                    {document.attachments.map((att) => {
                      const isItemLoading = loadingFileId === att.id;
                      return (
                        <div
                          key={att.id}
                          className="flex items-center justify-between p-3 rounded-xl border border-border-subtle bg-surface-subtle hover:bg-surface-elevated transition-colors gap-3 min-w-0 overflow-hidden"
                        >
                          <div className="flex items-center gap-3 min-w-0 flex-1 overflow-hidden">
                            <i className={`${getFileIcon(att.file_name)} text-xl shrink-0`} />
                            <div className="min-w-0 flex-1 overflow-hidden">
                              <button
                                type="button"
                                disabled={isItemLoading}
                                onClick={() => void handlePreviewAttachment(att.file, att.file_name, att.id)}
                                className="text-left text-xs font-semibold text-main hover:text-primary transition-colors block truncate cursor-pointer bg-transparent border-0 p-0 w-full max-w-full disabled:opacity-50"
                                title={
                                  isBrowserPreviewable(att.file_name)
                                    ? `Xem trước: ${att.file_name} (Mở tab mới)`
                                    : `Tải về để mở xem: ${att.file_name}`
                                }
                              >
                                {att.file_name}
                              </button>
                              <span className="text-xs text-muted block mt-0.5 truncate" title={`${formatFileSize(att.file_size)} • ${formatDate(att.uploaded_at)}`}>
                                {formatFileSize(att.file_size)} • {formatDate(att.uploaded_at)}
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            <button
                              type="button"
                              disabled={isItemLoading}
                              onClick={() => void handlePreviewAttachment(att.file, att.file_name, att.id)}
                              className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-primary text-white font-medium hover:bg-primary-hover shadow-sm transition-colors cursor-pointer disabled:opacity-50 min-w-[68px]"
                              title={
                                isBrowserPreviewable(att.file_name)
                                  ? (t('documents_ui.detailModal.viewAttachmentInBrowser') || 'Xem trực tiếp nội dung tệp tin trong tab mới của trình duyệt')
                                  : (t('documents_ui.detailModal.downloadToOpenApp') || 'Tải tệp tin về máy để mở xem bằng ứng dụng tương ứng')
                              }
                            >
                              {isItemLoading && loadingAction === 'preview' ? (
                                <i className="fa-solid fa-spinner fa-spin text-[0.7rem]" />
                              ) : (
                                <i className="fa-solid fa-arrow-up-right-from-square text-[0.7rem]" />
                              )}
                              <span>{t('documents_ui.detailModal.viewAttachment') || 'Xem'}</span>
                            </button>
                            <button
                              type="button"
                              disabled={isItemLoading}
                              onClick={() => void handleDownloadAttachment(att.file, att.file_name, att.id)}
                              className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-surface-elevated border border-border-subtle text-secondary hover:text-main hover:border-primary/40 transition-colors cursor-pointer disabled:opacity-50 min-w-[75px]"
                              title="Tải tệp tin về máy"
                            >
                              {isItemLoading && loadingAction === 'download' ? (
                                <i className="fa-solid fa-spinner fa-spin text-[0.7rem]" />
                              ) : (
                                <i className="fa-solid fa-download text-[0.7rem]" />
                              )}
                              <span>{t('documents_ui.detailModal.downloadAttachment') || 'Tải về'}</span>
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-muted m-0 italic py-2">
                    {t('documents_ui.detailModal.attachmentsEmpty') || 'Không có tệp đính kèm nào cho văn bản này.'}
                  </p>
                )}
              </div>

              {/* Footer metadata */}
              <div className="text-xs text-muted flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border-subtle/50">
                <span>
                  Người tạo: <strong>{document.nguoi_tao_name || 'Hệ thống'}</strong> lúc{' '}
                  {formatDateTime(document.created_at)}
                </span>
                <span>Cập nhật gần nhất: {formatDateTime(document.updated_at)}</span>
              </div>
            </>
          )}
        </div>

        {/* Footer Modal */}
        <div className="px-5 py-3.5 border-t border-border-subtle bg-surface-subtle flex items-center justify-end">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>
            {t('documents_ui.detailModal.close') || 'Đóng'}
          </Button>
        </div>
      </div>
    </div>,
    window.document.body
  );
};

export default DocumentDetailModal;
