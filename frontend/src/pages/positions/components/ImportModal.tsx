import React, { useRef, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { ApiError, apiClient, downloadBlob } from '@lib/apiClient';
import { PositionImportResult } from '@app-types/position';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';

interface ImportModalProps {
  onClose: () => void;
  onImported: () => void;
}

export const ImportModal: React.FC<ImportModalProps> = ({ onClose, onImported }) => {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const [result, setResult] = useState<PositionImportResult | null>(null);

  const handleDownloadTemplate = async () => {
    setIsDownloading(true);
    setErrorKey(null);
    try {
      await downloadBlob('/api/positions/import-template/', 'mau_import_chuc_vu.xlsx');
    } catch (err: unknown) {
      const candidate = err instanceof ApiError ? err.data.detail : null;
      setErrorKey(
        typeof candidate === 'string' && candidate.startsWith('positions.') ? candidate : 'positions.messages.templateError',
      );
    } finally {
      setIsDownloading(false);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setErrorKey('positions.import.errors.fileRequired');
      return;
    }
    setIsUploading(true);
    setErrorKey(null);
    setResult(null);
    try {
      const body = new FormData();
      body.append('file', file);
      const data = await apiClient<PositionImportResult>('/api/positions/import/', { method: 'POST', body });
      setResult(data);
      if (data.imported > 0) onImported();
    } catch (err: unknown) {
      const candidate = err instanceof ApiError ? err.data.detail : null;
      setErrorKey(
        typeof candidate === 'string' && candidate.startsWith('positions.') ? candidate : 'positions.import.errors.importFailed',
      );
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-backdrop backdrop-blur-sm animate-fade-in">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('positions.import.title')}
        className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-scale-up"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated">
          <h3 className="font-bold text-lg text-main">{t('positions.import.title')}</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label={t('positions.actions.close')}
            className="text-secondary hover:text-main p-1 rounded-lg transition-colors cursor-pointer"
          >
            <i className="fa-solid fa-xmark text-lg" />
          </button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto">
          <p className="text-sm text-secondary leading-relaxed">{t('positions.import.desc')}</p>

          {errorKey && (
            <div role="alert" className="p-3 text-sm text-danger bg-danger-subtle border border-danger-border rounded-lg">
              <i className="fa-solid fa-circle-exclamation mr-2" />
              {t(errorKey)}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant="outline" icon="fa-file-arrow-down" onClick={handleDownloadTemplate} isLoading={isDownloading}>
              {t('positions.import.downloadTemplate')}
            </Button>
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              data-testid="position-import-file"
              className="hidden"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setResult(null);
                setErrorKey(null);
              }}
            />
            <Button type="button" variant="secondary" icon="fa-file-excel" onClick={() => inputRef.current?.click()}>
              {t('positions.import.chooseFile')}
            </Button>
            <span className="text-sm text-secondary truncate max-w-[16rem]">{file ? file.name : t('positions.import.noFile')}</span>
          </div>

          {result && (
            <div className="space-y-3" data-testid="position-import-result">
              <h4 className="font-bold text-main">{t('positions.import.resultTitle')}</h4>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {t('positions.import.totalRows')}: {result.total}
                </Badge>
                <Badge variant="success">
                  {t('positions.import.importedRows')}: {result.imported}
                </Badge>
                <Badge variant={result.failed > 0 ? 'danger' : 'secondary'}>
                  {t('positions.import.failedRows')}: {result.failed}
                </Badge>
              </div>

              {result.errors.length === 0 ? (
                <p className="text-sm text-success">
                  <i className="fa-solid fa-circle-check mr-2" />
                  {t('positions.import.allSuccess')}
                </p>
              ) : (
                <div>
                  <h5 className="text-sm font-semibold text-secondary mb-2">{t('positions.import.errorsTitle')}</h5>
                  <ul className="divide-y divide-border border border-border rounded-lg max-h-64 overflow-y-auto">
                    {result.errors.map((error, index) => (
                      <li key={`${error.row}-${error.field}-${index}`} className="px-3 py-2 text-sm flex flex-col gap-0.5">
                        <span className="font-semibold text-main">
                          {t('positions.import.rowLabel', { row: String(error.row) })}
                          <span className="font-normal text-secondary"> · {t(`positions.import.fields.${error.field}`)}</span>
                        </span>
                        <span className="text-danger">{t(error.code)}</span>
                        {error.value && (
                          <span className="text-xs text-muted">{t('positions.import.valueLabel', { value: error.value })}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isUploading}>
            {t('positions.actions.close')}
          </Button>
          <Button type="button" variant="primary" icon="fa-upload" onClick={handleUpload} isLoading={isUploading}>
            {isUploading ? t('positions.import.uploading') : t('positions.import.upload')}
          </Button>
        </div>
      </div>
    </div>
  );
};
