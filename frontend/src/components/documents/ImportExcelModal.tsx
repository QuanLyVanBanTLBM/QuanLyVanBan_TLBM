import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@components/common';
import AlertModal from '@components/common/AlertModal';

interface Props {
  open: boolean;
  onClose: () => void;
  onImported?: () => void;
  loai?: 'DEN' | 'DI' | 'MAT';
  phamVi?: 'NOI_BO' | 'HAN_CHE';
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
  const [alertMsg, setAlertMsg] = useState('');
  const [fileWarning, setFileWarning] = useState<string | null>(null);

  const [prevOpen, setPrevOpen] = useState(open);
  if (open !== prevOpen) {
    setPrevOpen(open);
    if (open) {
      setSelectedFile(null);
      setAttachmentFiles([]);
      setFileWarning(null);
    }
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
      setAlertMsg('Chỉ chấp nhận file định dạng Excel (.xlsx hoặc .xls). Vui lòng chọn lại!');
      setAlertOpen(true);
      return;
    }
    const warning = checkFileMismatch(file);
    setFileWarning(warning);
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
        setAlertMsg('Tính năng tải dữ liệu mẫu cần kết nối máy chủ Backend. Hiện tại hệ thống đang chạy ở chế độ offline.');
        setAlertOpen(true);
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
      setAlertMsg(error instanceof Error ? error.message : String(error));
      setAlertOpen(true);
    }
  }

  async function handleImport() {
    if (!selectedFile) {
      setAlertMsg('Vui lòng chọn hoặc kéo thả file Excel trước khi bấm Nhập dữ liệu!');
      setAlertOpen(true);
      return;
    }
    if (fileWarning) {
      setAlertMsg(fileWarning);
      setAlertOpen(true);
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
        errors?: Array<{ row?: number; message: string }>;
      };
      if (res.ok) {
        let msg = data.message || 'Nhập danh sách văn bản thành công!';
        if (data.errors && data.errors.length > 0) {
          const warnings = data.errors
            .slice(0, 5)
            .map((e) => (e.row ? `Dòng ${e.row}: ${e.message}` : e.message))
            .join('\n');
          msg = `${msg}\n\nLưu ý đính kèm:\n${warnings}`;
        }
        setAlertMsg(msg);
        setAlertOpen(true);
        setSelectedFile(null);
        setAttachmentFiles([]);
        setFileWarning(null);
        onImported?.();
        onClose();
      } else {
        let msg = data.error || data.message || 'Lỗi nhập dữ liệu từ máy chủ.';
        if (data.errors && data.errors.length > 0 && !data.error) {
          const detail = data.errors
            .slice(0, 3)
            .map((e) => (e.row ? `Dòng ${e.row}: ${e.message}` : e.message))
            .join('\n');
          msg = `${msg}\n\n${detail}`;
        }
        setAlertMsg(msg);
        setAlertOpen(true);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      setAlertMsg('Lỗi kết nối máy chủ: ' + message);
      setAlertOpen(true);
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  const content = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity" onClick={onClose} />

      {/* Modal Dialog */}
      <div className="bg-surface border border-border-subtle rounded-2xl shadow-2xl z-10 w-[580px] max-w-full max-h-[92vh] flex flex-col p-6 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-border-subtle shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-xl bg-surface-elevated text-secondary flex items-center justify-center text-lg border border-border-subtle">
              <i className="fa-solid fa-file-excel" />
            </span>
            <div>
              <h3 className="text-base font-bold text-main m-0 flex items-center gap-2">
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
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 inline-flex items-center gap-1">
                      <i className="fa-solid fa-shield-halved text-[10px]" /> Hạn chế
                    </span>
                  ) : (
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-blue-500/15 text-blue-700 dark:text-blue-400 border border-blue-500/30 inline-flex items-center gap-1">
                      <i className="fa-solid fa-users text-[10px]" /> Nội bộ
                    </span>
                  )
                )}
              </h3>
              <p className="text-xs text-muted m-0">
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
            className="w-8 h-8 rounded-lg text-muted hover:text-main hover:bg-hover flex items-center justify-center transition-fast"
            title="Đóng"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Scrollable Body Content */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-4">
          {/* Step 1: Banner tải file mẫu */}
          <div className={`border rounded-xl p-3 flex items-center justify-between gap-3 ${
            phamVi === 'HAN_CHE'
              ? 'bg-amber-500/10 border-amber-500/20'
              : 'bg-primary-subtle border-primary/20'
          }`}>
            <div className="flex items-center gap-2.5">
              <i className={`fa-solid ${phamVi === 'HAN_CHE' ? 'fa-shield-halved text-amber-600' : 'fa-circle-info text-primary'} text-sm shrink-0`} />
              <span className="text-xs text-main">
                {phamVi === 'HAN_CHE'
                  ? 'Tải biểu mẫu Excel hạn chế (có cột gán quyền xem cho CBNV nhận).'
                  : 'Chưa có file mẫu? Tải file mẫu chuẩn để nhập dữ liệu đúng định dạng.'}
              </span>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              icon="fa-download"
              onClick={downloadTemplate}
              className="shrink-0 text-xs font-medium"
            >
              Tải file mẫu
            </Button>
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
            className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-fast ${isDragging
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
              <div className="flex items-center justify-center gap-3">
                <span className={`w-11 h-11 rounded-xl flex items-center justify-center text-xl shrink-0 ${
                  fileWarning ? 'bg-amber-500/10 text-amber-600' : 'bg-emerald-500/10 text-emerald-600'
                }`}>
                  <i className={`fa-solid ${fileWarning ? 'fa-triangle-exclamation' : 'fa-file-excel'}`} />
                </span>
                <div className="text-left overflow-hidden min-w-0">
                  <div className="text-sm font-semibold text-main truncate max-w-[320px]" title={selectedFile.name}>
                    {selectedFile.name}
                  </div>
                  <div className="text-xs text-muted">
                    Dung lượng: {(selectedFile.size / 1024).toFixed(1)} KB • Bấm để đổi file khác
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-1.5 py-1">
                <span className="w-11 h-11 rounded-xl bg-surface-subtle text-muted flex items-center justify-center text-lg">
                  <i className="fa-solid fa-cloud-arrow-up" />
                </span>
                <div className="text-sm font-medium text-main">
                  Kéo thả file Excel vào đây, hoặc <span className="text-primary underline">chọn từ máy tính</span>
                </div>
                <div className="text-xs text-muted">
                  Hỗ trợ định dạng: .xlsx, .xls (Tối đa 10MB)
                </div>
              </div>
            )}
          </div>

          {/* Warning mismatch banner */}
          {fileWarning && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-2.5 animate-in fade-in duration-150">
              <i className="fa-solid fa-triangle-exclamation text-sm shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
              <div className="flex-1">
                <span className="font-semibold block mb-0.5">Cảnh báo không đúng phân hệ:</span>
                <p className="m-0 leading-relaxed text-[11px]">{fileWarning}</p>
              </div>
            </div>
          )}

          {/* Step 3: Vùng chọn tệp đính kèm đi kèm (Tùy chọn) */}
          <div className="pt-3 border-t border-border-subtle">
            <div className="flex items-center justify-between mb-2">
              <div>
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
                className="text-xs shrink-0"
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
        <div className="flex justify-end items-center gap-2.5 mt-4 pt-3 border-t border-border-subtle shrink-0">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onClose}
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
          >
            {loading ? 'Đang nạp dữ liệu...' : 'Bắt đầu Nhập'}
          </Button>
        </div>
      </div>

      <AlertModal open={alertOpen} onClose={() => setAlertOpen(false)} message={alertMsg} />
    </div>
  );

  return typeof window !== 'undefined' ? createPortal(content, window.document.body) : content;
}
