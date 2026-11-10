import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiClientBlob } from '@lib/apiClient';
import { formatFileSize } from '@lib/fileUtils';
import { extractDocxParagraphs } from '@lib/filePreview';

export interface AttachmentPreviewTarget {
  name: string;
  size?: number;
  url?: string;
  file?: File;
}

export interface AttachmentPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  target: AttachmentPreviewTarget | null;
}

export const AttachmentPreviewModal: React.FC<AttachmentPreviewModalProps> = ({
  isOpen,
  onClose,
  target,
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [docxParagraphs, setDocxParagraphs] = useState<string[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const ext = (target?.name.split('.').pop() || '').toLowerCase();
  const isPdf = ext === 'pdf';
  const isImage = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'bmp'].includes(ext);
  const isDocx = ext === 'docx';
  const isDoc = ext === 'doc';

  // Lắng nghe phím ESC để đóng modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Nạp dữ liệu xem trước khi mở modal
  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    let active = true;
    let createdUrl: string | null = null;

    if (!isOpen || !target) {
      setBlobUrl(null);
      setDocxParagraphs(null);
      setIsLoading(false);
      setErrorMsg(null);
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    setDocxParagraphs(null);

    const loadContent = async () => {
      try {
        if (target.file) {
          // Tệp mới tải lên từ máy client
          if (isPdf || isImage) {
            createdUrl = URL.createObjectURL(target.file);
            if (active) setBlobUrl(createdUrl);
          } else if (isDocx) {
            const arrayBuffer = await target.file.arrayBuffer();
            const lines = await extractDocxParagraphs(arrayBuffer);
            if (active) setDocxParagraphs(lines);
          }
        } else if (target.url) {
          // Tệp hiện có từ máy chủ
          if (isPdf || isImage) {
            try {
              const rawBlob = await apiClientBlob(target.url);
              let mimeType = rawBlob.type;
              if (isPdf) mimeType = 'application/pdf';
              else if (ext === 'png') mimeType = 'image/png';
              else if (ext === 'jpg' || ext === 'jpeg') mimeType = 'image/jpeg';
              else if (ext === 'webp') mimeType = 'image/webp';
              else if (ext === 'gif') mimeType = 'image/gif';
              else if (ext === 'svg') mimeType = 'image/svg+xml';
              const typedBlob = mimeType ? new Blob([rawBlob], { type: mimeType }) : rawBlob;
              createdUrl = URL.createObjectURL(typedBlob);
              if (active) setBlobUrl(createdUrl);
            } catch {
              // Fallback dùng trực tiếp url
              if (active) setBlobUrl(target.url);
            }
          } else if (isDocx) {
            const rawBlob = await apiClientBlob(target.url);
            const arrayBuffer = await rawBlob.arrayBuffer();
            const lines = await extractDocxParagraphs(arrayBuffer);
            if (active) setDocxParagraphs(lines);
          }
        }
      } catch (err) {
        if (active) {
          console.error('Lỗi khi nạp nội dung tệp xem trước:', err);
          setErrorMsg('Không thể nạp nội dung xem trước của tệp này.');
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };

    void loadContent();

    return () => {
      active = false;
      if (createdUrl) {
        URL.revokeObjectURL(createdUrl);
      }
    };
  }, [isOpen, target, isPdf, isImage, isDocx, ext]);

  const handleDownload = () => {
    if (!target) return;
    if (blobUrl) {
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = target.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      return;
    }
    if (target.file) {
      const tempUrl = URL.createObjectURL(target.file);
      const a = document.createElement('a');
      a.href = tempUrl;
      a.download = target.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(tempUrl), 1000);
      return;
    }
    if (target.url) {
      const a = document.createElement('a');
      a.href = target.url;
      a.download = target.name;
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
  };

  const handleOpenNewTab = () => {
    if (blobUrl) {
      window.open(blobUrl, '_blank');
      return;
    }
    if (target?.url) {
      window.open(target.url, '_blank');
    }
  };

  if (!isOpen || !target) return null;
  if (typeof document === 'undefined') return null;

  const getHeaderIcon = () => {
    if (isPdf) return 'fa-file-pdf text-rose-500';
    if (isImage) return 'fa-file-image text-purple-500';
    if (isDocx || isDoc) return 'fa-file-word text-blue-500';
    return 'fa-file-lines text-secondary';
  };

  const getBadgeStyle = () => {
    if (isPdf) return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20';
    if (isImage) return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';
    if (isDocx || isDoc) return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
    return 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20';
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[10010] flex items-center justify-center p-2 sm:p-4 bg-black/75 backdrop-blur-xs animate-fadeIn"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="w-full max-w-5xl h-[90vh] bg-surface rounded-2xl border border-border-subtle shadow-2xl flex flex-col overflow-hidden animate-slideUp"
        onClick={(e) => e.stopPropagation()}
      >
        {/* HEADER */}
        <div className="flex items-center justify-between px-4 sm:px-5 py-3 border-b border-border-subtle bg-surface-elevated shrink-0 gap-3">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className="w-9 h-9 rounded-xl bg-surface border border-border-subtle flex items-center justify-center shrink-0 shadow-2xs">
              <i className={`fa-solid ${getHeaderIcon()} text-lg`} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase ${getBadgeStyle()}`}>
                  {ext.toUpperCase() || 'FILE'}
                </span>
                <h3 className="text-sm sm:text-base font-bold text-main truncate leading-tight" title={target.name}>
                  {target.name}
                </h3>
              </div>
              {target.size && (
                <p className="text-[11px] text-muted truncate mt-0.5">
                  Dung lượng: {formatFileSize(target.size)}
                </p>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            {(isPdf || isImage) && (blobUrl || target.url) && (
              <button
                type="button"
                onClick={handleOpenNewTab}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-surface hover:bg-surface-elevated text-secondary hover:text-main border border-border-subtle transition-colors cursor-pointer"
                title="Mở trong tab trình duyệt mới"
              >
                <i className="fa-solid fa-arrow-up-right-from-square text-[11px]" />
                <span className="hidden sm:inline">Mở tab mới</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-white hover:bg-primary-hover shadow-2xs transition-colors cursor-pointer"
              title="Tải tệp này về máy"
            >
              <i className="fa-solid fa-download text-[11px]" />
              <span className="hidden sm:inline">Tải về</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-main hover:bg-surface transition-colors cursor-pointer shrink-0"
              aria-label="Đóng popup xem trước"
            >
              <i className="fa-solid fa-xmark text-base" />
            </button>
          </div>
        </div>

        {/* BODY */}
        <div className="flex-1 overflow-hidden bg-slate-900/5 dark:bg-slate-950/40 relative flex flex-col">
          {isLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
              <i className="fa-solid fa-circle-notch fa-spin text-3xl text-primary mb-3" />
              <p className="text-sm font-semibold text-main">Đang nạp xem trước tệp...</p>
              <p className="text-xs text-muted mt-1">{target.name}</p>
            </div>
          ) : errorMsg ? (
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-muted">
              <i className="fa-solid fa-triangle-exclamation text-3xl text-amber-500 mb-2" />
              <p className="text-sm font-medium text-main">{errorMsg}</p>
              <button
                type="button"
                onClick={handleDownload}
                className="mt-3 px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-semibold hover:bg-primary-hover transition-colors"
              >
                Tải tệp về máy để xem
              </button>
            </div>
          ) : isPdf ? (
            <div className="w-full h-full flex flex-col">
              {blobUrl ? (
                <iframe
                  src={`${blobUrl}#view=Fit&navpanes=0&toolbar=1`}
                  className="w-full h-full border-0 bg-white"
                  title={target.name}
                />
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-muted">
                  <i className="fa-solid fa-file-pdf text-4xl text-rose-500 mb-2 opacity-50" />
                  <p className="text-sm font-medium">Không thể tạo đường dẫn xem trước PDF</p>
                </div>
              )}
            </div>
          ) : isImage ? (
            <div className="w-full h-full flex items-center justify-center p-4 overflow-auto bg-black/20">
              {blobUrl ? (
                <img
                  src={blobUrl}
                  alt={target.name}
                  className="max-w-full max-h-full object-contain rounded-xl shadow-lg border border-border-subtle bg-surface"
                />
              ) : (
                <p className="text-xs text-muted">Không có đường dẫn ảnh</p>
              )}
            </div>
          ) : isDocx ? (
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 bg-slate-900/5 dark:bg-slate-950/40 custom-scrollbar">
              <div className="max-w-3xl mx-auto bg-surface border border-border-subtle rounded-xl p-6 sm:p-10 shadow-lg min-h-[500px]">
                <div className="pb-4 mb-6 border-b border-border-subtle/80 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-7 h-7 rounded-lg bg-blue-500/10 text-blue-600 flex items-center justify-center text-sm font-bold">
                      <i className="fa-solid fa-file-word" />
                    </span>
                    <span className="text-xs font-bold text-main uppercase tracking-wider">
                      Nội dung tài liệu Word số hóa
                    </span>
                  </div>
                  {docxParagraphs && (
                    <span className="text-[11px] text-muted font-mono">{docxParagraphs.length} đoạn văn bản</span>
                  )}
                </div>

                {docxParagraphs && docxParagraphs.length > 0 ? (
                  <div className="space-y-3.5 text-main text-sm leading-relaxed font-sans">
                    {docxParagraphs.map((para, idx) => (
                      <p key={idx} className="text-justify leading-relaxed whitespace-pre-wrap">
                        {para}
                      </p>
                    ))}
                  </div>
                ) : (
                  <div className="py-12 text-center text-muted">
                    <i className="fa-solid fa-file-lines text-3xl mb-2 opacity-40 block" />
                    <p className="text-xs">Tài liệu không có nội dung chữ hoặc chứa bảng tính/hình ảnh phức tạp.</p>
                    <button
                      type="button"
                      onClick={handleDownload}
                      className="mt-3 px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-semibold hover:bg-primary-hover transition-colors"
                    >
                      Tải tệp về máy
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-surface">
              <div className="w-16 h-16 rounded-2xl bg-blue-500/10 text-blue-600 flex items-center justify-center mx-auto mb-3 text-3xl">
                <i className={`fa-solid ${getHeaderIcon()}`} />
              </div>
              <h4 className="text-base font-bold text-main mb-1">
                {isDoc ? 'Tài liệu Microsoft Word (.doc)' : `Tệp định dạng .${ext.toUpperCase()}`}
              </h4>
              <p className="text-xs text-secondary mb-1 font-medium">{target.name}</p>
              <p className="text-xs text-muted max-w-md mb-5 leading-relaxed">
                Định dạng tệp này không hỗ trợ trình chiếu trực tiếp trên nền web. Bạn có thể tải tệp về máy tính để mở bằng ứng dụng tương thích.
              </p>
              <button
                type="button"
                onClick={handleDownload}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-primary text-white hover:bg-primary-hover shadow-2xs transition-colors cursor-pointer"
              >
                <i className="fa-solid fa-download text-xs" />
                <span>Tải tệp về máy</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default AttachmentPreviewModal;
