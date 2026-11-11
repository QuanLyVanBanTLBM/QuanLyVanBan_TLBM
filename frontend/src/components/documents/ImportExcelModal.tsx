import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@components/common';
import AlertModal, { AlertVariant } from '@components/common/AlertModal';

interface Props {
  open: boolean;
  onClose: () => void;
  onImported?: () => void;
  loai?: 'DEN' | 'DI' | 'MAT';
  phamVi?: 'NOI_BO' | 'HAN_CHE';
}

interface ImportErrorItem {
  row?: number;
  message: string;
}

/** Chuẩn hóa thông báo lỗi từng dòng, tránh lặp tiền tố "Dòng X:" nếu backend đã ghi sẵn. */
function formatImportErrorMessage(err: ImportErrorItem): string {
  const msg = (err.message || '').trim();
  if (!msg) return err.row ? `Dòng ${err.row}: Dữ liệu không hợp lệ.` : 'Dữ liệu không hợp lệ.';
  if (err.row && !/^Dòng\s+\d+\b/i.test(msg)) {
    return `Dòng ${err.row}: ${msg}`;
  }
  return msg;
}

function getFileIcon(fileName: string) {
  const ext = fileName.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return 'fa-solid fa-file-pdf text-rose-500';
    case 'doc':
    case 'docx':
      return 'fa-solid fa-file-word text-blue-500';
    case 'xls':
    case 'xlsx':
      return 'fa-solid fa-file-excel text-emerald-500';
    case 'png':
    case 'jpg':
    case 'jpeg':
      return 'fa-solid fa-file-image text-amber-500';
    default:
      return 'fa-solid fa-file text-secondary';
  }
}

function formatFileSize(bytes: number) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export default function ImportExcelModal({ open, onClose, onImported, loai = 'DEN', phamVi = 'NOI_BO' }: Props) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const attachmentInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [attachmentFiles, setAttachmentFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertTitle, setAlertTitle] = useState('Thông báo hệ thống');
  const [alertMsg, setAlertMsg] = useState('');
  const [alertDetails, setAlertDetails] = useState<string[]>([]);
  const [alertVariant, setAlertVariant] = useState<AlertVariant>('info');
  const [importErrors, setImportErrors] = useState<string[]>([]);
  const [fileWarning, setFileWarning] = useState<string | null>(null);

  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (open) {
      setSelectedFile(null);
      setAttachmentFiles([]);
      setFileWarning(null);
      setImportErrors([]);
      setAlertOpen(false);
      setAlertDetails([]);
    }
  }

  function showAlert(
    message: string,
    options?: {
      title?: string;
      details?: string[];
      variant?: AlertVariant;
    }
  ) {
    setAlertTitle(options?.title ?? 'Thông báo hệ thống');
    setAlertMsg(message);
    setAlertDetails(options?.details ?? []);
    setAlertVariant(options?.variant ?? 'info');
    setAlertOpen(true);
  }

  function checkFileMismatch(file: File): string | null {
    const name = file.name.toLowerCase();

    // 1. Kiểm tra lệch phạm vi (Nội bộ vs Hạn chế)
    const isHanChe =
      name.includes('han_che') ||
      name.includes('hanche') ||
      name.includes('hạn_chế') ||
      name.includes('hạn chế') ||
      name.includes('mat') ||
      name.includes('mật');

    const isNoiBo =
      name.includes('noi_bo') ||
      name.includes('noibo') ||
      name.includes('nội_bộ') ||
      name.includes('nội bộ');

    if (phamVi === 'NOI_BO' && isHanChe) {
      return 'File bạn chọn là biểu mẫu hoặc dữ liệu Văn bản Hạn chế. Bạn đang ở phân hệ Văn bản Nội bộ, không thể nạp file này để tránh làm lộ lọt thông tin. Vui lòng chuyển sang tab "Văn bản Hạn chế" để import.';
    }

    if (phamVi === 'HAN_CHE' && isNoiBo && !isHanChe) {
      return 'File bạn chọn là biểu mẫu hoặc dữ liệu Văn bản Nội bộ. Bạn đang ở phân hệ Văn bản Hạn chế, không thể nạp file này vì thiếu thông tin phân quyền cán bộ nhận. Vui lòng chuyển sang tab "Văn bản Nội bộ" để import.';
    }

    // 2. Kiểm tra lệch hệ (Đến vs Đi)
    const isDen =
      name.includes('_den') ||
      name.includes('van_ban_den') ||
      name.includes('văn_bản_đến') ||
      name.includes('văn bản đến');

    const isDi =
      name.includes('_di') ||
      name.includes('van_ban_di') ||
      name.includes('văn_bản_đi') ||
      name.includes('văn bản đi');

    if (loai === 'DI' && isDen && !isDi) {
      return 'File bạn chọn là biểu mẫu Văn bản Đến. Bạn đang ở phân hệ Văn bản Đi, vui lòng chọn đúng file mẫu Văn bản Đi.';
    }

    if (loai === 'DEN' && isDi && !isDen) {
      return 'File bạn chọn là biểu mẫu Văn bản Đi. Bạn đang ở phân hệ Văn bản Đến, vui lòng chọn đúng file mẫu Văn bản Đến.';
    }

    return null;
  }

  function handleFileChange(files: FileList | null) {
    if (!files || files.length === 0) return;
    const file = files[0];
    const isExcel = /\.(xlsx|xls)$/i.test(file.name);
    if (!isExcel) {
      showAlert('Chỉ chấp nhận file định dạng Excel (.xlsx hoặc .xls). Vui lòng chọn lại!', {
        title: 'Định dạng file không hợp lệ',
        variant: 'warning',
      });
      return;
    }
    const warning = checkFileMismatch(file);
    setFileWarning(warning);
    setImportErrors([]);
    setSelectedFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer && e.dataTransfer.files) {
      handleFileChange(e.dataTransfer.files);
    }
  }

  function handleAddAttachments(files: FileList | null) {
    if (!files || files.length === 0) return;
    const newFiles = Array.from(files);
    setAttachmentFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.name.toLowerCase()));
      const filtered = newFiles.filter((f) => !existingNames.has(f.name.toLowerCase()));
      return [...prev, ...filtered];
    });
  }

  function handleRemoveAttachment(index: number) {
    setAttachmentFiles((prev) => prev.filter((_, idx) => idx !== index));
  }

  async function downloadTemplate() {
    try {
      const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token') || '';
      if (import.meta.env.DEV && !token) {
        showAlert(
          'Tính năng tải dữ liệu mẫu cần kết nối máy chủ Backend. Hiện tại hệ thống đang chạy ở chế độ offline.',
          { title: 'Chưa thể tải file mẫu', variant: 'warning' }
        );
        return;
      }
      const res = await fetch(`/api/documents/template/?loai=${loai}&pham_vi=${phamVi}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Không thể tải file mẫu từ máy chủ. Vui lòng kiểm tra lại kết nối!');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const effectiveLoai = loai === 'DI' ? 'Di' : 'Den';
      const effectivePhamVi = (phamVi === 'HAN_CHE' || loai === 'MAT') ? '_Han_Che' : '_Noi_Bo';
      const a = document.createElement('a');
      a.href = url;
      a.download = `Mau_Nhap_Van_Ban_${effectiveLoai}${effectivePhamVi}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error: unknown) {
      showAlert(error instanceof Error ? error.message : String(error), {
        title: 'Không thể tải file mẫu',
        variant: 'error',
      });
    }
  }

  function openErrorAlert(errors: string[]) {
    showAlert(
      errors.length > 1
        ? `Chưa có văn bản nào được lưu. Vui lòng kiểm tra và sửa đủ ${errors.length} lỗi bên dưới rồi nhập lại:`
        : 'Chưa có văn bản nào được lưu. Vui lòng kiểm tra lỗi bên dưới rồi nhập lại:',
      {
        title: errors.length > 1 ? `Không thể nhập file Excel (${errors.length} lỗi)` : 'Không thể nhập file Excel',
        details: errors,
        variant: 'error',
      }
    );
  }

  async function handleImport() {
    if (!selectedFile) {
      showAlert('Vui lòng chọn hoặc kéo thả file Excel trước khi bấm Nhập dữ liệu!', {
        title: 'Chưa chọn file Excel',
        variant: 'warning',
      });
      return;
    }
    if (fileWarning) {
      showAlert(fileWarning, {
        title: 'Cảnh báo không đúng phân hệ',
        variant: 'warning',
      });
      return;
    }
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('loai', loai);
      fd.append('pham_vi', phamVi);
      attachmentFiles.forEach((file) => {
        fd.append('attachments', file);
      });

      const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token') || '';
      const res = await fetch('/api/documents/import/', {
        method: 'POST',
        body: fd,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json() as {
        message?: string;
        error?: string;
        errors?: ImportErrorItem[];
      };
      if (res.ok) {
        const msg = data.message || 'Nhập danh sách văn bản thành công!';
        const warnings = (data.errors ?? []).map(formatImportErrorMessage).filter(Boolean);
        setImportErrors([]);
        showAlert(msg, {
          title: 'Nhập dữ liệu thành công',
          details: warnings,
          variant: warnings.length > 0 ? 'warning' : 'success',
        });
        setSelectedFile(null);
        setAttachmentFiles([]);
        setFileWarning(null);
        onImported?.();
        onClose();
      } else {
        const detailList = Array.isArray(data.errors)
          ? data.errors.map(formatImportErrorMessage).filter(Boolean)
          : [];
        const fallbackMsg = data.error || data.message || 'Lỗi nhập dữ liệu từ máy chủ.';

        if (detailList.length > 0) {
          setImportErrors(detailList);
          openErrorAlert(detailList);
        } else {
          setImportErrors([fallbackMsg]);
          showAlert(fallbackMsg, {
            title: 'Không thể nhập file Excel',
            variant: 'error',
          });
        }
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      showAlert('Lỗi kết nối máy chủ: ' + message, {
        title: 'Lỗi kết nối',
        variant: 'error',
      });
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  const content = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-2.5 sm:p-4">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity" onClick={onClose} />

      {/* Modal Dialog */}
      <div className="bg-surface border border-border-subtle rounded-2xl shadow-2xl z-10 w-full max-w-[580px] max-h-[92vh] supports-[max-height:92dvh]:max-h-[92dvh] flex flex-col p-4 sm:p-6 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-start sm:items-center justify-between gap-2 pb-3 sm:pb-4 mb-3 sm:mb-4 border-b border-border-subtle shrink-0 min-w-0">
          <div className="flex items-start sm:items-center gap-2.5 min-w-0 flex-1">
            <span className="w-9 h-9 rounded-xl bg-surface-elevated text-secondary flex items-center justify-center text-base sm:text-lg border border-border-subtle shrink-0">
              <i className="fa-solid fa-file-excel" />
            </span>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm sm:text-base font-bold text-main m-0 flex flex-wrap items-center gap-1.5 sm:gap-2 leading-snug">
                <span>
                  {loai === 'MAT'
                    ? 'Nhập Văn Bản Mật Từ File Excel'
                    : loai === 'DI'
                    ? phamVi === 'HAN_CHE'
                      ? 'Nhập Văn Bản Đi Hạn Chế Từ File Excel'
                      : 'Nhập Văn Bản Đi Từ File Excel'
                    : phamVi === 'HAN_CHE'
                    ? 'Nhập Văn Bản Đến Hạn Chế Từ File Excel'
                    : 'Nhập Văn Bản Đến Từ File Excel'}
                </span>
                {loai !== 'MAT' && (
                  phamVi === 'HAN_CHE' ? (
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 inline-flex items-center gap-1 shrink-0">
                      <i className="fa-solid fa-shield-halved text-[10px]" /> Hạn chế
                    </span>
                  ) : (
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-blue-500/15 text-blue-700 dark:text-blue-400 border border-blue-500/30 inline-flex items-center gap-1 shrink-0">
                      <i className="fa-solid fa-users text-[10px]" /> Nội bộ
                    </span>
                  )
                )}
              </h3>
              <p className="text-xs text-muted m-0 mt-0.5 break-words">
                {loai === 'MAT'
                  ? 'Nạp hàng loạt văn bản mật vào cơ sở dữ liệu bảo mật'
                  : phamVi === 'HAN_CHE'
                  ? 'Nạp danh sách văn bản hạn chế kèm phân quyền cán bộ nhận'
                  : loai === 'DI'
                  ? 'Nạp hàng loạt công văn, văn bản đi vào cơ sở dữ liệu'
                  : 'Nạp hàng loạt công văn, văn bản đến vào cơ sở dữ liệu'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-muted hover:text-main hover:bg-hover flex items-center justify-center transition-fast shrink-0"
            title="Đóng"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Scrollable Body Content */}
        <div className="flex-1 min-h-0 overflow-y-auto pr-0.5 sm:pr-1 space-y-3 sm:space-y-4">
          {/* Step 1: Banner tải file mẫu */}
          <div className={`border rounded-xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-3 ${
            phamVi === 'HAN_CHE'
              ? 'bg-amber-500/10 border-amber-500/20'
              : 'bg-primary-subtle border-primary/20'
          }`}>
            <div className="flex items-start sm:items-center gap-2.5 min-w-0">
              <i className={`fa-solid ${phamVi === 'HAN_CHE' ? 'fa-shield-halved text-amber-600' : 'fa-circle-info text-primary'} text-sm shrink-0 mt-0.5 sm:mt-0`} />
              <span className="text-xs text-main leading-relaxed break-words">
                {phamVi === 'HAN_CHE'
                  ? 'Tải biểu mẫu Excel hạn chế (đầy đủ cột Danh mục hồ sơ, Loại văn bản và gán quyền cán bộ nhận).'
                  : 'Chưa có file mẫu? Tải file mẫu chuẩn (đã bổ sung cột Danh mục hồ sơ & Loại văn bản).'}
              </span>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              icon="fa-download"
              onClick={downloadTemplate}
              className="w-full sm:w-auto shrink-0 text-xs font-medium"
            >
              Tải file mẫu
            </Button>
          </div>

          {/* Quy tắc nghiệp vụ kiểm tra dữ liệu */}
          <div className="px-3 py-2 rounded-xl bg-surface-subtle border border-border-subtle text-[11px] text-muted flex items-start gap-2 min-w-0">
            <i className="fa-solid fa-shield-check text-primary mt-0.5 shrink-0" />
            <span className="leading-relaxed min-w-0 break-words">
              <strong className="text-main font-semibold">Quy tắc dữ liệu:</strong>{' '}
              {(phamVi === 'HAN_CHE' || loai === 'MAT') ? (
                <>
                  Cột <span className="font-semibold text-main">Danh mục hồ sơ</span> (Số ký hiệu),{' '}
                  <span className="font-semibold text-main">Loại văn bản</span>,{' '}
                  <span className="font-semibold text-main">Đơn vị nhận</span>,{' '}
                  <span className="font-semibold text-main">Cán bộ xử lý</span> và{' '}
                  <span className="font-semibold text-main">Tệp đính kèm</span> là bắt buộc (nhiều đơn vị/cán bộ ngăn cách bằng dấu <span className="font-medium text-main">,</span> hoặc <span className="font-medium text-main">;</span>). Cột <span className="text-main font-medium">Năm</span>,{' '}
                  <span className="text-main font-medium">Ngày hết hiệu lực</span>,{' '}
                  <span className="text-main font-medium">Link thay thế</span>,{' '}
                  <span className="text-main font-medium">Ghi chú</span> được phép để trống (bỏ trống <span className="text-main font-medium">Năm</span> sẽ tự lấy năm hiện tại).
                </>
              ) : (
                <>
                  Cột <span className="font-semibold text-main">Danh mục hồ sơ</span> (Số ký hiệu),{' '}
                  <span className="font-semibold text-main">Loại văn bản</span> và{' '}
                  <span className="font-semibold text-main">Tệp đính kèm</span> là bắt buộc. Cột{' '}
                  <span className="text-main font-medium">Năm</span>,{' '}
                  <span className="text-main font-medium">Đơn vị nhận</span>,{' '}
                  <span className="text-main font-medium">Cán bộ xử lý</span> (nhiều giá trị ngăn cách bằng <span className="font-medium text-main">,</span> hoặc <span className="font-medium text-main">;</span>; nếu nhập Cán bộ xử lý thì phải nhập Đơn vị nhận),{' '}
                  <span className="text-main font-medium">Ngày hết hiệu lực</span>,{' '}
                  <span className="text-main font-medium">Link thay thế</span> và{' '}
                  <span className="text-main font-medium">Ghi chú</span> được phép để trống.
                </>
              )}
            </span>
          </div>

          {/* Step 2: Vùng chọn hoặc kéo thả file Excel */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-4 sm:p-5 text-center cursor-pointer transition-fast ${isDragging
                ? 'border-primary bg-primary-subtle/40 scale-[1.01]'
                : selectedFile
                  ? fileWarning
                    ? 'border-amber-500/50 bg-amber-500/5'
                    : 'border-emerald-500/50 bg-emerald-500/5'
                  : 'border-border-subtle hover:border-primary/50 hover:bg-hover'
              }`}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files)}
            />

            {selectedFile ? (
              <div className="flex items-center gap-3 min-w-0 text-left">
                <span className={`w-10 h-10 sm:w-11 sm:h-11 rounded-xl flex items-center justify-center text-lg sm:text-xl shrink-0 ${
                  fileWarning ? 'bg-amber-500/10 text-amber-600' : 'bg-emerald-500/10 text-emerald-600'
                }`}>
                  <i className={`fa-solid ${fileWarning ? 'fa-triangle-exclamation' : 'fa-file-excel'}`} />
                </span>
                <div className="overflow-hidden min-w-0 flex-1">
                  <div className="text-xs sm:text-sm font-semibold text-main truncate" title={selectedFile.name}>
                    {selectedFile.name}
                  </div>
                  <div className="text-[11px] sm:text-xs text-muted">
                    Dung lượng: {(selectedFile.size / 1024).toFixed(1)} KB • Bấm để đổi file khác
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-1.5 py-1">
                <span className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-surface-subtle text-muted flex items-center justify-center text-base sm:text-lg">
                  <i className="fa-solid fa-cloud-arrow-up" />
                </span>
                <div className="text-xs sm:text-sm font-medium text-main">
                  Kéo thả file Excel vào đây, hoặc <span className="text-primary underline">chọn từ máy tính</span>
                </div>
                <div className="text-[11px] sm:text-xs text-muted">
                  Hỗ trợ định dạng: .xlsx, .xls (Tối đa 10MB)
                </div>
              </div>
            )}
          </div>

          {/* Warning mismatch banner */}
          {fileWarning && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-2.5 min-w-0 animate-in fade-in duration-150">
              <i className="fa-solid fa-triangle-exclamation text-sm shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
              <div className="flex-1 min-w-0 break-words">
                <span className="font-semibold block mb-0.5">Cảnh báo không đúng phân hệ:</span>
                <p className="m-0 leading-relaxed text-[11px]">{fileWarning}</p>
              </div>
            </div>
          )}

          {/* Danh sách lỗi lưu giữ sau khi đóng popup để dễ đối chiếu và sửa file */}
          {importErrors.length > 0 && !alertOpen && (
            <div
              role="region"
              aria-label="Danh sách lỗi dữ liệu file Excel"
              className="p-3 rounded-xl bg-danger-subtle border border-danger-border space-y-2 min-w-0 animate-in fade-in duration-150"
            >
              <div className="flex items-center justify-between gap-2 min-w-0">
                <div className="flex items-center gap-2 min-w-0">
                  <i className="fa-solid fa-circle-exclamation text-danger text-sm shrink-0" />
                  <span className="text-xs font-semibold text-danger truncate">
                    Phát hiện {importErrors.length} lỗi trong file (chưa lưu văn bản nào)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => openErrorAlert(importErrors)}
                  className="text-[11px] font-medium text-primary hover:underline shrink-0 cursor-pointer"
                >
                  Mở rộng
                </button>
              </div>
              <ul className="space-y-1.5 max-h-40 sm:max-h-48 overflow-y-auto pr-1 m-0 p-0 list-none">
                {importErrors.map((errMsg, idx) => (
                  <li
                    key={idx}
                    className="text-[11px] sm:text-xs leading-relaxed text-main bg-surface border border-border-subtle rounded-lg px-2.5 py-1.5 flex items-start gap-2 min-w-0"
                  >
                    <span className="shrink-0 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded bg-danger-subtle text-danger font-semibold text-[10px] tabular-nums mt-0.5">
                      {idx + 1}
                    </span>
                    <span className="min-w-0 flex-1 break-words whitespace-pre-line">{errMsg}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Step 3: Vùng chọn tệp đính kèm đi kèm (Tùy chọn) */}
          <div className="pt-3 border-t border-border-subtle">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
              <div className="min-w-0">
                <label className="text-xs font-semibold text-main block">
                  Tệp đính kèm đi kèm <span className="text-muted font-normal">(Tùy chọn)</span>
                </label>
                <p className="text-[11px] text-muted m-0">
                  Tự động so khớp tên file tải lên với cột &quot;Tệp đính kèm&quot; trong Excel.
                </p>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                icon="fa-paperclip"
                onClick={() => attachmentInputRef.current?.click()}
                className="w-full sm:w-auto text-xs shrink-0"
              >
                Chọn tệp PDF, Word...
              </Button>
              <input
                ref={attachmentInputRef}
                type="file"
                multiple
                accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.xls,.xlsx"
                className="hidden"
                onChange={(e) => handleAddAttachments(e.target.files)}
              />
            </div>

            {attachmentFiles.length > 0 && (
              <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1">
                <div className="text-[11px] font-semibold text-secondary">
                  {attachmentFiles.length} tệp đính kèm đã chọn sẵn sàng nạp:
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {attachmentFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 px-2.5 bg-surface-subtle border border-border-subtle rounded-xl text-xs overflow-hidden min-w-0"
                    >
                      <div className="flex items-center gap-2 min-w-0 flex-1 overflow-hidden">
                        <i className={`${getFileIcon(file.name)} text-sm shrink-0`} />
                        <span className="truncate text-main font-medium min-w-0 flex-1" title={file.name}>
                          {file.name}
                        </span>
                        <span className="text-[10px] text-muted shrink-0 whitespace-nowrap">
                          ({formatFileSize(file.size)})
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveAttachment(idx)}
                        className="w-5 h-5 rounded hover:bg-danger-subtle hover:text-danger text-muted flex items-center justify-center transition-fast ml-1.5 shrink-0 cursor-pointer"
                        title="Xóa tệp này"
                      >
                        <i className="fa-solid fa-xmark text-xs" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end items-stretch sm:items-center gap-2 sm:gap-2.5 mt-3 sm:mt-4 pt-3 border-t border-border-subtle shrink-0">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onClose}
            className="w-full sm:w-auto"
          >
            Đóng
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            icon="fa-file-import"
            onClick={handleImport}
            disabled={!selectedFile || loading || Boolean(fileWarning)}
            isLoading={loading}
            className="w-full sm:w-auto"
          >
            {loading ? 'Đang nạp dữ liệu...' : 'Bắt đầu Nhập'}
          </Button>
        </div>
      </div>

      <AlertModal
        open={alertOpen}
        onClose={() => setAlertOpen(false)}
        title={alertTitle}
        message={alertMsg}
        details={alertDetails}
        variant={alertVariant}
      />
    </div>
  );

  return typeof window !== 'undefined' ? createPortal(content, window.document.body) : content;
}
