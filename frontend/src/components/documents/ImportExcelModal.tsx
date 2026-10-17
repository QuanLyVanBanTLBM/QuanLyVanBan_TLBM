import React, { useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@components/common';
import AlertModal from '@components/common/AlertModal';

interface Props {
  open: boolean;
  onClose: () => void;
  onImported?: () => void;
}

export default function ImportExcelModal({ open, onClose, onImported }: Props) {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMsg, setAlertMsg] = useState('');

  if (!open) return null;

  function handleFileChange(files: FileList | null) {
    if (!files || files.length === 0) return;
    const file = files[0];
    const isExcel = /\.(xlsx|xls)$/i.test(file.name);
    if (!isExcel) {
      setAlertMsg('Chỉ chấp nhận file định dạng Excel (.xlsx hoặc .xls). Vui lòng chọn lại!');
      setAlertOpen(true);
      return;
    }
    setSelectedFile(file);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer && e.dataTransfer.files) {
      handleFileChange(e.dataTransfer.files);
    }
  }

  async function downloadTemplate() {
    try {
      const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token') || '';
      if (import.meta.env.DEV && !token) {
        setAlertMsg('Tính năng tải dữ liệu mẫu cần kết nối máy chủ Backend. Hiện tại hệ thống đang chạy ở chế độ offline.');
        setAlertOpen(true);
        return;
      }
      const res = await fetch('/api/documents/template/?loai=DEN', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Không thể tải file mẫu từ máy chủ. Vui lòng kiểm tra lại kết nối!');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'Mau_Nhap_Van_Ban_Den.xlsx';
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
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('loai', 'DEN');
      const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token') || '';
      const res = await fetch('/api/documents/import/', {
        method: 'POST',
        body: fd,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const data = await res.json() as { message?: string; error?: string };
      if (res.ok) {
        setAlertMsg(data.message || 'Nhập danh sách văn bản thành công!');
        setAlertOpen(true);
        setSelectedFile(null);
        onImported?.();
        onClose();
      } else {
        setAlertMsg('Lỗi nhập dữ liệu: ' + (data.error || data.message || JSON.stringify(data)));
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

  const content = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity" onClick={onClose} />

      {/* Modal Dialog */}
      <div className="bg-surface border border-border-subtle rounded-2xl shadow-2xl z-10 w-[540px] max-w-full p-6 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-border-subtle">
          <div className="flex items-center gap-2.5">
            <span className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center text-lg">
              <i className="fa-solid fa-file-excel" />
            </span>
            <div>
              <h3 className="text-base font-bold text-main m-0">Nhập Văn Bản Từ File Excel</h3>
              <p className="text-xs text-muted m-0">Nạp hàng loạt công văn, văn bản đến vào cơ sở dữ liệu</p>
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

        {/* Step 1: Banner tải file mẫu */}
        <div className="bg-primary-subtle border border-primary/20 rounded-xl p-3 mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <i className="fa-solid fa-circle-info text-primary text-sm shrink-0" />
            <span className="text-xs text-main">
              Chưa có file mẫu? Tải file mẫu chuẩn để nhập dữ liệu đúng định dạng.
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

        {/* Step 2: Vùng chọn hoặc kéo thả file */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-fast ${isDragging
              ? 'border-primary bg-primary-subtle/40 scale-[1.01]'
              : selectedFile
                ? 'border-emerald-500/50 bg-emerald-500/5'
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
              <span className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center text-2xl shrink-0">
                <i className="fa-solid fa-file-excel" />
              </span>
              <div className="text-left overflow-hidden">
                <div className="text-sm font-semibold text-main truncate max-w-[280px]">
                  {selectedFile.name}
                </div>
                <div className="text-xs text-muted">
                  Dung lượng: {(selectedFile.size / 1024).toFixed(1)} KB • Bấm để đổi file khác
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <span className="w-12 h-12 rounded-xl bg-surface-subtle text-muted flex items-center justify-center text-xl">
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

        {/* Footer Actions */}
        <div className="flex justify-end items-center gap-2.5 mt-5 pt-3 border-t border-border-subtle">
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
            disabled={!selectedFile || loading}
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
