import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from '@i18n/translate';
import { Button } from '@components/common/Button';
import { apiClient, downloadBlob } from '@lib/apiClient';
import { ExcelImportError, ExcelImportJob } from '@app-types/employee';

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
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [submissionKey, setSubmissionKey] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState<ExcelImportJob | null>(null);

  const resetState = useCallback(() => {
    setSelectedFile(null);
    setIsDragging(false);
    setIsUploading(false);
    setIsDownloadingTemplate(false);
    setGeneralError(null);
    setErrorList([]);
    setActiveJobId(null);
    setSubmissionKey(null);
    setJobProgress(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  const handleClose = useCallback(() => {
    if (isUploading) return;
    resetState();
    onClose();
  }, [isUploading, resetState, onClose]);

  const handleClearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isUploading) return;
    setSelectedFile(null);
    setGeneralError(null);
    setErrorList([]);
    setActiveJobId(null);
    setSubmissionKey(null);
    setJobProgress(null);
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
    if (isUploading) return;
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
      setActiveJobId(null);
      setSubmissionKey(null);
      setJobProgress(null);
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
    if (isUploading) return;
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
      setActiveJobId(null);
      setSubmissionKey(null);
      setJobProgress(null);
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
    if (!activeJobId && !selectedFile) {
      setGeneralError(t('employees.import.noFileSelected'));
      return;
    }

    let submittedJobId = activeJobId;
    try {
      setIsUploading(true);
      setGeneralError(null);
      if (!submittedJobId) {
        setErrorList([]);
        if (!selectedFile) return;

        const idempotencyKey = submissionKey || (
          typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(36).slice(2)}`
        );
        setSubmissionKey(idempotencyKey);
        const formData = new FormData();
        formData.append('file', selectedFile);

        const accepted = await apiClient<{ job_id: string }>(
          '/api/accounts/employees/import-async/',
          {
            method: 'POST',
            body: formData,
            headers: { 'Idempotency-Key': idempotencyKey },
          }
        );
        submittedJobId = accepted.job_id;
        setActiveJobId(submittedJobId);
      }

      while (submittedJobId) {
        const job = await apiClient<ExcelImportJob>(
          `/api/accounts/employees/import-jobs/${submittedJobId}/`
        );
        setJobProgress(job);

        if (job.status === 'done') {
          onSuccess(job.created_count || 0);
          resetState();
          onClose();
          return;
        }

        if (job.status === 'failed') {
          setErrorList(job.errors || []);
          setGeneralError(t(job.message || 'employees.import.uploadError'));
          setActiveJobId(null);
          setSubmissionKey(null);
          return;
        }

        await new Promise((resolve) => window.setTimeout(resolve, 250));
      }
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'data' in err) {
        const errorData = (err as { data: { errors?: ExcelImportError[]; message?: string; detail?: string } }).data;
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
      setGeneralError(
        t(submittedJobId ? 'employees.import.jobPollFailed' : 'employees.import.jobSubmissionUncertain')
      );
    } finally {
      setIsUploading(false);
    }
  };

  const importProgressPercent = jobProgress?.total
    ? Math.min(100, Math.floor((jobProgress.processed / jobProgress.total) * 100))
    : 0;

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
            disabled={isUploading}
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
            onClick={() => !isUploading && fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${isUploading ? 'cursor-not-allowed opacity-70' : 'cursor-pointer'} ${
              isDragging
                ? 'border-primary bg-primary-subtle'
                : 'border-border hover:border-primary bg-surface-elevated'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              disabled={isUploading}
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
                    disabled={isUploading}
                    className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-danger hover:text-white bg-danger-subtle hover:bg-danger border border-danger-border rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
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

          {isUploading && !jobProgress && (
            <div className="space-y-2 rounded-xl border border-primary/20 bg-primary-subtle p-4" role="status" aria-live="polite">
              <div className="flex items-center gap-2 text-sm font-semibold text-main">
                <i className="fa-solid fa-spinner fa-spin text-primary" aria-hidden="true" />
                <span>{t('employees.import.uploadingFile')}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-surface">
                <div className="h-full w-1/3 rounded-full bg-primary motion-safe:animate-pulse" />
              </div>
            </div>
          )}

          {jobProgress && (jobProgress.status === 'queued' || jobProgress.status === 'processing') && (
            <div className="space-y-2 rounded-xl border border-primary/20 bg-primary-subtle p-4" role="status" aria-live="polite">
              <div className="flex items-center justify-between gap-3 text-sm font-semibold text-main">
                <span>{t(jobProgress.message)}</span>
                {jobProgress.total > 0 && <span>{importProgressPercent}%</span>}
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-surface">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-300"
                  style={{ width: `${importProgressPercent}%` }}
                />
              </div>
              {jobProgress.total > 0 && (
                <p className="text-xs text-secondary">
                  {t('employees.import.jobProgress', {
                    processed: jobProgress.processed,
                    total: jobProgress.total,
                  })}
                </p>
              )}
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
            disabled={!selectedFile && !activeJobId}
            icon="fa-upload"
          >
            {t(activeJobId ? 'employees.import.resumeImport' : 'employees.import.startImport')}
          </Button>
        </div>
      </div>
    </div>
  );
};
