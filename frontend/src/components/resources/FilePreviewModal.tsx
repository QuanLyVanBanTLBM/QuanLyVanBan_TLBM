import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ResourceAttachment } from '@app-types/resource';

export interface FilePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  file: ResourceAttachment | null;
  documentTitle?: string;
  onDownload?: () => void;
}

interface ExcelSheet {
  name: string;
  rows: (string | number | null)[][];
}

interface PreviewApiResponse {
  id?: number;
  name: string;
  file_type: string;
  file_size?: number;
  file_url: string;
  sheets?: ExcelSheet[];
  note?: string;
}

export const FilePreviewModal: React.FC<FilePreviewModalProps> = ({
  isOpen,
  onClose,
  file,
  documentTitle,
  onDownload,
}) => {
  const [activeSheetIndex, setActiveSheetIndex] = useState(0);
  const [excelData, setExcelData] = useState<ExcelSheet[] | null>(null);
  const [isLoadingExcel, setIsLoadingExcel] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Trích xuất đuôi tệp
  const getFileExt = (fileNameOrPath?: string) => {
    if (!fileNameOrPath) return 'FILE';
    const clean = fileNameOrPath.split('?')[0].split('#')[0];
    const nameOnly = clean.split('/').pop() || '';
    const parts = nameOnly.split('.');
    if (parts.length > 1) {
      return parts.pop()?.toUpperCase() || 'FILE';
    }
    return 'FILE';
  };

  const ext = getFileExt(file?.name || file?.path);
  const isPdf = ext === 'PDF';
  const isExcel = ['XLS', 'XLSX', 'CSV'].includes(ext);
  const isImage = ['JPG', 'JPEG', 'PNG', 'WEBP', 'GIF', 'SVG'].includes(ext);
  const isDocx = ['DOC', 'DOCX'].includes(ext);

  // Đóng bằng phím Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Nếu là file Excel, gọi API backend để lấy cấu trúc dữ liệu các sheet
  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    if (!isOpen || !file || !isExcel) {
      setExcelData(null);
      setIsLoadingExcel(false);
      setLoadError(null);
      return;
    }

    if (file.id) {
      setIsLoadingExcel(true);
      setLoadError(null);
      fetch(`/api/resources/attachments/${file.id}/preview/`)
        .then((res) => {
          if (!res.ok) throw new Error('Không thể tải cấu trúc bảng tính');
          return res.json() as Promise<PreviewApiResponse>;
        })
        .then((data) => {
          if (data.sheets && data.sheets.length > 0) {
            setExcelData(data.sheets);
            setActiveSheetIndex(0);
          } else {
            setLoadError(data.note || 'Không có dữ liệu trong tệp bảng tính.');
          }
        })
        .catch((err) => {
          console.warn('Lỗi đọc dữ liệu Excel:', err);
          setLoadError('Không thể nạp dữ liệu chi tiết bảng tính. Bạn có thể mở hoặc tải về file gốc.');
        })
        .finally(() => {
          setIsLoadingExcel(false);
        });
    } else {
      setExcelData(null);
    }
  }, [isOpen, file, isExcel]);

  if (!isOpen || !file) return null;
  if (typeof document === 'undefined') return null;

  const fileUrl = file.path || '';

  const getBadgeStyle = (extension: string) => {
    switch (extension) {
      case 'PDF':
        return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20';
      case 'XLS':
      case 'XLSX':
      case 'CSV':
        return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
      case 'DOC':
      case 'DOCX':
        return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
      case 'JPG':
      case 'JPEG':
      case 'PNG':
      case 'WEBP':
        return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';
      default:
        return 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20';
    }
  };

  const getFileIcon = (extension: string) => {
    switch (extension) {
      case 'PDF':
        return 'fa-file-pdf text-rose-500';
      case 'XLS':
      case 'XLSX':
      case 'CSV':
        return 'fa-file-excel text-emerald-500';
      case 'DOC':
      case 'DOCX':
        return 'fa-file-word text-blue-500';
      case 'JPG':
      case 'JPEG':
      case 'PNG':
      case 'WEBP':
        return 'fa-file-image text-purple-500';
      default:
        return 'fa-file-lines text-secondary';
    }
  };

  const getColumnLetter = (colIndex: number): string => {
    let letter = '';
    let temp = colIndex;
    while (temp >= 0) {
      letter = String.fromCharCode((temp % 26) + 65) + letter;
      temp = Math.floor(temp / 26) - 1;
    }
    return letter;
  };

  return createPortal(
    <div
      className="fixed inset-0 z-[10005] flex items-center justify-center p-2 sm:p-4 bg-black/70 backdrop-blur-xs animate-fade-in"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="w-full max-w-5xl h-[92vh] bg-surface rounded-2xl border border-border-subtle shadow-2xl flex flex-col overflow-hidden animate-slide-in-bottom"
        onClick={(e) => e.stopPropagation()}
      >
        {/* HEADER */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border-subtle bg-surface-elevated shrink-0 gap-3">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className="w-9 h-9 rounded-xl bg-surface border border-border-subtle flex items-center justify-center shrink-0 shadow-2xs">
              <i className={`fa-solid ${getFileIcon(ext)} text-lg`} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase ${getBadgeStyle(ext)}`}>
                  {ext}
                </span>
                <h3 className="text-sm sm:text-base font-bold text-main truncate leading-tight" title={file.name}>
                  {file.name}
                </h3>
              </div>
              {documentTitle && (
                <p className="text-[11px] text-muted truncate mt-0.5">
                  Tài liệu: {documentTitle}
                </p>
              )}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            {fileUrl && (
              <a
                href={fileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-surface hover:bg-surface-elevated text-secondary hover:text-main border border-border-subtle transition-colors cursor-pointer"
                title="Mở trong tab trình duyệt mới"
              >
                <i className="fa-solid fa-arrow-up-right-from-square text-[11px]" />
                <span className="hidden sm:inline">Mở tab mới</span>
              </a>
            )}

            {onDownload ? (
              <button
                type="button"
                onClick={onDownload}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-white hover:bg-primary-hover shadow-2xs transition-colors cursor-pointer"
                title="Tải tệp này về máy"
              >
                <i className="fa-solid fa-download text-[11px]" />
                <span className="hidden sm:inline">Tải về</span>
              </button>
            ) : fileUrl ? (
              <a
                href={fileUrl}
                download={file.name}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-primary text-white hover:bg-primary-hover shadow-2xs transition-colors cursor-pointer"
                title="Tải tệp này về máy"
              >
                <i className="fa-solid fa-download text-[11px]" />
                <span className="hidden sm:inline">Tải về</span>
              </a>
            ) : null}

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
          {/* TRƯỜNG HỢP 1: Tệp PDF */}
          {isPdf && (
            <div className="w-full h-full flex flex-col">
              {fileUrl ? (
                <iframe
                  src={`${fileUrl}#toolbar=1&navpanes=1`}
                  className="w-full h-full border-0 bg-white"
                  title={file.name}
                />
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-muted">
                  <i className="fa-solid fa-file-pdf text-4xl text-rose-500 mb-2 opacity-50" />
                  <p className="text-sm font-medium">Không tìm thấy đường dẫn tệp PDF</p>
                </div>
              )}
            </div>
          )}

          {/* TRƯỜNG HỢP 2: Tệp Excel (Bảng tính trang tính) */}
          {isExcel && (
            <div className="w-full h-full flex flex-col">
              {isLoadingExcel ? (
                <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                  <i className="fa-solid fa-circle-notch fa-spin text-3xl text-emerald-500 mb-3" />
                  <p className="text-sm font-semibold text-main">Đang nạp dữ liệu bảng tính Excel...</p>
                  <p className="text-xs text-muted mt-1">Đang phân tích cấu trúc các cột và dòng dữ liệu</p>
                </div>
              ) : excelData && excelData.length > 0 ? (
                <div className="flex-1 flex flex-col overflow-hidden">
                  {/* Sheet tabs selector */}
                  {excelData.length > 1 && (
                    <div className="flex items-center gap-1 px-4 py-2 bg-surface border-b border-border-subtle shrink-0 overflow-x-auto">
                      <span className="text-[11px] font-bold text-muted uppercase mr-1 shrink-0">Trang tính:</span>
                      {excelData.map((sheet, sIdx) => (
                        <button
                          key={sIdx}
                          type="button"
                          onClick={() => setActiveSheetIndex(sIdx)}
                          className={`px-3 py-1 text-xs font-semibold rounded-lg transition-colors cursor-pointer shrink-0 ${
                            activeSheetIndex === sIdx
                              ? 'bg-emerald-600 text-white shadow-2xs'
                              : 'bg-surface-elevated text-secondary hover:text-main hover:bg-border-subtle/50'
                          }`}
                        >
                          <i className="fa-solid fa-table mr-1.5 text-[10px]" />
                          <span>{sheet.name}</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Spreadsheet Grid */}
                  <div className="flex-1 overflow-auto bg-surface p-2">
                    {excelData[activeSheetIndex] && excelData[activeSheetIndex].rows.length > 0 ? (
                      <div className="inline-block min-w-full align-middle border border-border-subtle rounded-lg overflow-hidden shadow-2xs">
                        <table className="min-w-full border-collapse text-xs">
                          {/* Column Headers (A, B, C...) */}
                          <thead>
                            <tr className="bg-slate-100 dark:bg-slate-800 text-secondary border-b border-border-subtle font-mono text-[11px]">
                              <th className="w-12 px-2 py-1.5 text-center font-bold border-r border-border-subtle bg-slate-200/70 dark:bg-slate-700/70 text-muted">
                                #
                              </th>
                              {Array.from({
                                length: Math.max(...excelData[activeSheetIndex].rows.map((r) => r.length), 1),
                              }).map((_, colIdx) => (
                                <th
                                  key={colIdx}
                                  className="px-3 py-1.5 text-center font-bold border-r border-border-subtle min-w-[100px]"
                                >
                                  {getColumnLetter(colIdx)}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {excelData[activeSheetIndex].rows.map((row, rIdx) => {
                              const isHeaderRow = rIdx === 0;
                              return (
                                <tr
                                  key={rIdx}
                                  className={`border-b border-border-subtle/60 hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors ${
                                    isHeaderRow ? 'bg-slate-50 dark:bg-slate-800/60 font-semibold text-main' : 'text-main'
                                  }`}
                                >
                                  {/* Row index (1, 2, 3...) */}
                                  <td className="px-2 py-1.5 text-center font-mono text-[11px] font-bold border-r border-border-subtle bg-slate-100/60 dark:bg-slate-800/40 text-muted select-none">
                                    {rIdx + 1}
                                  </td>
                                  {row.map((cell, cIdx) => (
                                    <td
                                      key={cIdx}
                                      className="px-3 py-1.5 border-r border-border-subtle/60 truncate max-w-[280px]"
                                      title={String(cell ?? '')}
                                    >
                                      {String(cell ?? '')}
                                    </td>
                                  ))}
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="h-64 flex flex-col items-center justify-center text-muted">
                        <i className="fa-solid fa-table text-3xl mb-2 opacity-40" />
                        <p className="text-xs">Trang tính này trống, không có dữ liệu dòng nào.</p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-surface">
                  <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center mx-auto mb-3 text-3xl">
                    <i className="fa-solid fa-file-excel" />
                  </div>
                  <h4 className="text-base font-bold text-main mb-1">Tệp bảng tính Excel</h4>
                  <p className="text-xs text-muted max-w-md mb-4 leading-relaxed">
                    {loadError || 'Định dạng bảng tính cần được tải về hoặc mở trực tiếp bằng phần mềm chuyên dụng (Microsoft Excel, Google Trang tính) để trải nghiệm tốt nhất.'}
                  </p>
                  <div className="flex items-center gap-2">
                    {fileUrl && (
                      <a
                        href={fileUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-surface-elevated hover:bg-border-subtle/50 text-main border border-border-subtle transition-colors cursor-pointer"
                      >
                        <i className="fa-solid fa-arrow-up-right-from-square text-xs" />
                        <span>Mở tệp trực tiếp</span>
                      </a>
                    )}
                    {onDownload ? (
                      <button
                        type="button"
                        onClick={onDownload}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-2xs transition-colors cursor-pointer"
                      >
                        <i className="fa-solid fa-download text-xs" />
                        <span>Tải về máy</span>
                      </button>
                    ) : fileUrl ? (
                      <a
                        href={fileUrl}
                        download={file.name}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white shadow-2xs transition-colors cursor-pointer"
                      >
                        <i className="fa-solid fa-download text-xs" />
                        <span>Tải về máy</span>
                      </a>
                    ) : null}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TRƯỜNG HỢP 3: Tệp Hình ảnh */}
          {isImage && (
            <div className="w-full h-full flex items-center justify-center p-4 overflow-auto bg-black/10">
              {fileUrl ? (
                <img
                  src={fileUrl}
                  alt={file.name}
                  className="max-w-full max-h-full object-contain rounded-xl shadow-lg border border-border-subtle bg-surface"
                />
              ) : (
                <p className="text-xs text-muted">Không có đường dẫn ảnh</p>
              )}
            </div>
          )}

          {/* TRƯỜNG HỢP 4: Tệp Word (DOC / DOCX) hoặc tệp khác */}
          {!isPdf && !isExcel && !isImage && (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-surface">
              <div className="w-16 h-16 rounded-2xl bg-blue-500/10 text-blue-600 flex items-center justify-center mx-auto mb-3 text-3xl">
                <i className={`fa-solid ${getFileIcon(ext)}`} />
              </div>
              <h4 className="text-base font-bold text-main mb-1">
                {isDocx ? 'Tài liệu Microsoft Word' : `Tệp định dạng ${ext}`}
              </h4>
              <p className="text-xs text-secondary mb-1 font-medium">{file.name}</p>
              <p className="text-xs text-muted max-w-md mb-5 leading-relaxed">
                Định dạng tệp này có thể mở trực tiếp hoặc tải về máy để mở bằng ứng dụng tương thích.
              </p>

              <div className="flex items-center gap-2.5">
                {fileUrl && (
                  <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-surface-elevated hover:bg-border-subtle/50 text-main border border-border-subtle transition-colors cursor-pointer"
                  >
                    <i className="fa-solid fa-arrow-up-right-from-square text-xs" />
                    <span>Mở tệp trực tiếp</span>
                  </a>
                )}
                {onDownload ? (
                  <button
                    type="button"
                    onClick={onDownload}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-primary hover:bg-primary-hover text-white shadow-2xs transition-colors cursor-pointer"
                  >
                    <i className="fa-solid fa-download text-xs" />
                    <span>Tải về máy</span>
                  </button>
                ) : fileUrl ? (
                  <a
                    href={fileUrl}
                    download={file.name}
                    className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-primary hover:bg-primary-hover text-white shadow-2xs transition-colors cursor-pointer"
                  >
                    <i className="fa-solid fa-download text-xs" />
                    <span>Tải về máy</span>
                  </a>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};
