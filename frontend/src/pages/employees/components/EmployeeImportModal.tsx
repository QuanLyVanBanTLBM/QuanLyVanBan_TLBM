import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from '@i18n/translate';
import { Button } from '@components/common/Button';
import { apiClient, downloadBlob } from '@lib/apiClient';
import { ExcelImportError, ExcelImportResponse } from '@app-types/employee';

interface EmployeeImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (count: number) => void;
}

export const EmployeeImportModal: React.FC<EmployeeImportModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isDownloadingTemplate, setIsDownloadingTemplate] = useState<boolean>(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [errorList, setErrorList] = useState<ExcelImportError[]>([]);

  const resetState = useCallback(() => {
    setSelectedFile(null);
    setIsDragging(false);
    setIsUploading(false);
    setIsDownloadingTemplate(false);
    setGeneralError(null);
    setErrorList([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onClose();
  }, [resetState, onClose]);

  const handleClearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    setGeneralError(null);
    setErrorList([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };


  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isUploading) {
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isUploading, handleClose]);

  if (!isOpen) return null;

  const isExcelFile = (fileName: string) => {
    const lower = fileName.toLowerCase();
    return lower.endsWith('.xlsx');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (!isExcelFile(file.name)) {
        setGeneralError(t('employees.import.invalidFileType'));
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setGeneralError(null);
      setErrorList([]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (!isExcelFile(file.name)) {
        setGeneralError(t('employees.import.invalidFileType'));
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setGeneralError(null);
      setErrorList([]);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      setIsDownloadingTemplate(true);
      await downloadBlob('/api/accounts/employees/template/', 'mau_danh_sach_cbnv.xlsx');
    } catch {
      setGeneralError(t('employees.import.downloadTemplateError'));
    } finally {
      setIsDownloadingTemplate(false);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setGeneralError(t('employees.import.noFileSelected'));
      return;
    }

    try {
      setIsUploading(true);
      setGeneralError(null);
      setErrorList([]);

      const formData = new FormData();
      formData.append('file', selectedFile);

      const res = await apiClient<ExcelImportResponse>(
        '/api/accounts/employees/import/',
        {
          method: 'POST',
          body: formData,
        }
      );

      if (res.success) {
        onSuccess(res.created_count || 0);
        handleClose();
      }
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'data' in err) {
        const errorData = (err as { data: ExcelImportResponse & { detail?: string } }).data;
        if (errorData?.errors && Array.isArray(errorData.errors)) {
          setErrorList(errorData.errors);
          const rawMsg = errorData.message || 'employees.import.hasErrors';
          setGeneralError(t(rawMsg));
          return;
        }
        const singleMsg = errorData?.message || errorData?.detail;
        if (singleMsg) {
          setGeneralError(t(singleMsg));
          return;
        }
      }
      if (err instanceof Error) {
        setGeneralError(t(err.message));
      } else {
        setGeneralError(t('employees.import.uploadError'));
      }
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fade-in"
      onClick={handleClose}
    >
      <div
        className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-scale-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-success-subtle text-success flex items-center justify-center text-lg">
              <i className="fa-solid fa-file-excel" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-main">
                {t('employees.import.title')}
              </h2>
              <p className="text-xs text-muted">
                {t('employees.import.subtitle')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="text-secondary hover:text-main p-2 rounded-lg hover:bg-surface-hover transition-colors"
            title={t('employees.actions.close')}
          >
            <i className="fa-solid fa-xmark text-lg" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Download Template Box */}
          <div className="flex items-center justify-between p-4 bg-surface-elevated border border-border rounded-xl">
            <div className="flex items-center gap-3">
              <i className="fa-solid fa-circle-info text-primary text-lg" />
              <div>
                <p className="text-sm font-semibold text-main">
                  {t('employees.import.templateGuide')}
                </p>
                <p className="text-xs text-secondary">
                  {t('employees.import.templateDesc')}
                </p>
              </div>
            </div>
            <Button
              type="button"
              variant="secondary"
              onClick={handleDownloadTemplate}
              isLoading={isDownloadingTemplate}
              icon="fa-download"
            >
              {t('employees.import.downloadTemplate')}
            </Button>
          </div>

          {/* Drag & Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              isDragging
                ? 'border-primary bg-primary-subtle'
                : 'border-border hover:border-primary bg-surface-elevated'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="w-14 h-14 rounded-full bg-primary-subtle text-primary flex items-center justify-center mx-auto text-2xl mb-3">
              <i className="fa-solid fa-cloud-arrow-up" />
            </div>
            {selectedFile ? (
              <div className="space-y-1">
                <p className="text-sm font-semibold text-main break-all">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-muted">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={handleClearFile}
                    className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-danger hover:text-white bg-danger-subtle hover:bg-danger border border-danger-border rounded-lg transition-colors cursor-pointer"
                    title={t('employees.import.removeFile')}
                  >
                    <i className="fa-solid fa-xmark text-xs" />
                    <span>{t('employees.import.removeFile')}</span>
                  </button>
                </div>
              </div>
            ) : (
              <>
                <p className="text-sm font-semibold text-main">
                  {t('employees.import.dragDropPrompt')}
                </p>
                <p className="text-xs text-muted mt-1">
                  {t('employees.import.formatNotice')}
                </p>
              </>
            )}
          </div>

          {/* General Error Message */}
          {generalError && (
            <div className="p-3 text-sm text-danger bg-danger-subtle border border-danger-border rounded-lg flex items-center gap-2">
              <i className="fa-solid fa-circle-exclamation shrink-0" />
              <span>{generalError}</span>
            </div>
          )}

          {/* Error Table */}
          {errorList.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-danger uppercase tracking-wider">
                  {t('employees.import.errorListHeader', { count: errorList.length })}
                </span>
              </div>
              <div className="border border-danger-border rounded-lg overflow-hidden max-h-48 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-danger-subtle text-danger font-semibold border-b border-danger-border">
                    <tr>
                      <th className="py-2 px-3 w-16 text-center">{t('employees.import.row')}</th>
                      <th className="py-2 px-3">{t('employees.import.errorDetail')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-danger-border bg-surface">
                    {errorList.map((err, idx) => {
                      const fieldLabel = err.field
                        ? t(`employees.import.fields.${err.field}`)
                        : null;
                      const hasFieldLabel = fieldLabel && !fieldLabel.startsWith('employees.import.fields.');
                      const errorDetail = err.code
                        ? t(err.code, { value: err.value || '', field: err.field || '' })
                        : err.message;

                      return (
                        <tr key={idx} className="hover:bg-danger-subtle">
                          <td className="py-2 px-3 text-center font-mono font-semibold text-danger">
                            {err.row > 0 ? `#${err.row}` : '-'}
                          </td>
                          <td className="py-2 px-3 text-secondary">
                            {hasFieldLabel && (
                              <span className="font-semibold text-main mr-1.5">
                                [{fieldLabel}]:
                              </span>
                            )}
                            <span>{errorDetail}</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-surface-elevated">
          <Button type="button" variant="secondary" onClick={handleClose} disabled={isUploading}>
            {t('employees.actions.cancel')}
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={handleUpload}
            isLoading={isUploading}
            disabled={!selectedFile}
            icon="fa-upload"
          >
            {t('employees.import.startImport')}
          </Button>
        </div>
      </div>
    </div>
  );
};
