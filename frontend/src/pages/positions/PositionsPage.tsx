import { useEffect, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { ApiError, apiClient } from '@lib/apiClient';
import { usePermissions } from '@lib/permissions';
import { PaginatedResponse, Position, PositionFormData } from '@app-types/position';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';
import { PositionModal } from './components/PositionModal';
import { DeleteConfirmModal } from './components/DeleteConfirmModal';
import { ImportModal } from './components/ImportModal';

const PAGE_SIZE = 10;

function errorKeyFrom(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const detail = err.data.detail;
    if (typeof detail === 'string' && detail.startsWith('positions.')) return detail;
  }
  return fallback;
}

export default function PositionsPage() {
  const { t } = useTranslation();
  const { can } = usePermissions();

  const [positions, setPositions] = useState<Position[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  const [isLoading, setIsLoading] = useState(true);
  const [loadErrorKey, setLoadErrorKey] = useState<string | null>(null);
  const [toast, setToast] = useState<{ textKey: string; isError?: boolean } | null>(null);

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editing, setEditing] = useState<Position | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deleting, setDeleting] = useState<Position | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteErrorKey, setDeleteErrorKey] = useState<string | null>(null);
  const [isImportOpen, setIsImportOpen] = useState(false);

  const showToast = (textKey: string, isError = false) => {
    setToast({ textKey, isError });
    setTimeout(() => setToast(null), 3500);
  };

  const reload = () => setReloadKey((key) => key + 1);

  useEffect(() => {
    let ignore = false;
    const params = new URLSearchParams({ page: String(page) });
    if (searchQuery.trim()) params.append('search', searchQuery.trim());

    apiClient<PaginatedResponse<Position>>(`/api/positions/?${params.toString()}`)
      .then((res) => {
        if (ignore) return;
        setPositions(res.results || []);
        setTotal(res.count || 0);
        setLoadErrorKey(null);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (ignore) return;
        setLoadErrorKey(errorKeyFrom(err, 'positions.messages.fetchError'));
        setIsLoading(false);
      });

    return () => {
      ignore = true;
    };
  }, [page, searchQuery, reloadKey]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const from = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(page * PAGE_SIZE, total);

  const handleSave = async (formData: PositionFormData) => {
    setIsSubmitting(true);
    try {
      if (editing) {
        await apiClient.put(`/api/positions/${editing.id}/`, formData);
        showToast('positions.messages.updateSuccess');
      } else {
        await apiClient.post('/api/positions/', formData);
        showToast('positions.messages.createSuccess');
      }
      reload();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleting) return;
    setIsDeleting(true);
    try {
      await apiClient.delete(`/api/positions/${deleting.id}/`);
      setDeleting(null);
      setDeleteErrorKey(null);
      if (positions.length === 1 && page > 1) setPage(page - 1);
      showToast('positions.messages.deleteSuccess');
      reload();
    } catch (err: unknown) {
      setDeleteErrorKey(errorKeyFrom(err, 'positions.messages.saveError'));
    } finally {
      setIsDeleting(false);
    }
  };

  // Người chỉ có quyền xem: không có nút sửa/xóa nên ẩn luôn cột Thao tác (tránh cột trống).
  const showActions = can('change_chucvu') || can('delete_chucvu');
  const columnCount = showActions ? 5 : 4;

  return (
    <div className="space-y-6">
      {toast && (
        <div
          role="status"
          className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center gap-2.5 text-sm font-semibold animate-fade-in ${
            toast.isError ? 'bg-danger text-white border border-danger-border' : 'bg-success text-white border border-success-border'
          }`}
        >
          <i className={`fa-solid ${toast.isError ? 'fa-circle-xmark' : 'fa-circle-check'}`} />
          {t(toast.textKey)}
        </div>
      )}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface p-6 rounded-2xl border border-border">
        <div>
          <h1 className="text-2xl font-bold text-main flex items-center gap-2.5">
            <i className="fa-solid fa-id-badge text-primary" />
            {t('positions.title')}
          </h1>
          <p className="text-secondary text-sm mt-1">{t('positions.desc')}</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {can('import_chucvu') && (
            <Button variant="outline" icon="fa-file-excel" onClick={() => setIsImportOpen(true)}>
              {t('positions.import.openBtn')}
            </Button>
          )}
          {can('add_chucvu') && (
            <Button
              variant="primary"
              icon="fa-plus"
              onClick={() => {
                setEditing(null);
                setIsFormOpen(true);
              }}
            >
              {t('positions.addBtn')}
            </Button>
          )}
        </div>
      </div>

      <div className="relative">
        <i className="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-muted text-sm" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setPage(1);
          }}
          placeholder={t('positions.actions.searchPlaceholder')}
          aria-label={t('positions.actions.searchPlaceholder')}
          className="w-full pl-10 pr-3.5 py-2 text-sm bg-surface border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary"
        />
      </div>

      <div className="bg-surface border border-border rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead className="bg-surface-elevated text-secondary text-xs uppercase font-bold border-b border-border">
              <tr>
                <th className="px-4 py-3 text-center w-20">{t('positions.table.stt')}</th>
                <th className="px-4 py-3">{t('positions.table.name')}</th>
                <th className="px-4 py-3 text-center">{t('positions.table.status')}</th>
                <th className="px-4 py-3">{t('positions.table.notes')}</th>
                {showActions && <th className="px-4 py-3 text-center w-28">{t('positions.table.actions')}</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                <tr>
                  <td colSpan={columnCount} className="text-center py-12 text-secondary">
                    <i className="fa-solid fa-spinner fa-spin text-2xl text-primary mb-2 block" />
                    {t('positions.table.loading')}
                  </td>
                </tr>
              ) : loadErrorKey ? (
                <tr>
                  <td colSpan={columnCount} className="text-center py-12 text-danger" role="alert">
                    <i className="fa-solid fa-circle-exclamation text-3xl mb-2 block" />
                    {t(loadErrorKey)}
                    {loadErrorKey !== 'positions.messages.permissionDenied' && (
                    <div className="mt-3">
                      <Button
                        variant="outline"
                        icon="fa-rotate-right"
                        onClick={() => {
                          setIsLoading(true);
                          reload();
                        }}
                      >
                        {t('positions.actions.retry')}
                      </Button>
                    </div>
                    )}
                  </td>
                </tr>
              ) : positions.length === 0 ? (
                <tr>
                  <td colSpan={columnCount} className="text-center py-12 text-secondary">
                    <i className="fa-solid fa-folder-open text-3xl text-muted mb-2 block" />
                    {searchQuery.trim() ? t('positions.table.emptySearch') : t('positions.table.empty')}
                  </td>
                </tr>
              ) : (
                positions.map((position) => (
                  <tr
                    key={position.id}
                    data-testid={`position-row-${position.id}`}
                    className={`transition-colors hover:bg-surface-hover ${
                      position.is_public ? '' : 'bg-warning-subtle border-l-4 border-l-warning'
                    }`}
                  >
                    <td className="px-4 py-3 text-center font-bold text-main">{position.display_order}</td>
                    <td className="px-4 py-3 font-semibold text-main">{position.name}</td>
                    <td className="px-4 py-3 text-center">
                      {position.is_public ? (
                        <Badge variant="success" size="sm">
                          {t('positions.table.public')}
                        </Badge>
                      ) : (
                        <Badge variant="warning" size="sm">
                          {t('positions.table.internal')}
                        </Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-secondary">{position.note || t('positions.table.emptyValue')}</td>
                    {showActions && (
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-1">
                        {can('change_chucvu') && (
                          <button
                            type="button"
                            title={t('positions.actions.edit')}
                            aria-label={`${t('positions.actions.edit')} ${position.name}`}
                            onClick={() => {
                              setEditing(position);
                              setIsFormOpen(true);
                            }}
                            className="p-2 text-secondary hover:text-primary hover:bg-primary-subtle rounded-lg transition-colors cursor-pointer"
                          >
                            <i className="fa-solid fa-pen-to-square" />
                          </button>
                        )}
                        {can('delete_chucvu') && (
                          <button
                            type="button"
                            title={t('positions.actions.delete')}
                            aria-label={`${t('positions.actions.delete')} ${position.name}`}
                            onClick={() => {
                              setDeleteErrorKey(null);
                              setDeleting(position);
                            }}
                            className="p-2 text-secondary hover:text-danger hover:bg-danger-subtle rounded-lg transition-colors cursor-pointer"
                          >
                            <i className="fa-solid fa-trash-can" />
                          </button>
                        )}
                      </div>
                    </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {!isLoading && !loadErrorKey && total > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 border-t border-border bg-surface-elevated">
            <span className="text-xs text-secondary">
              {t('positions.table.paginationInfo', { from: String(from), to: String(to), total: String(total) })}
            </span>
            <div className="flex items-center gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                {t('positions.table.prevPage')}
              </Button>
              <span className="text-sm font-semibold text-main">
                {page} / {totalPages}
              </span>
              <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                {t('positions.table.nextPage')}
              </Button>
            </div>
          </div>
        )}
      </div>

      {isFormOpen && (
        <PositionModal
          key={editing?.id ?? 'new'}
          initialData={editing}
          isLoading={isSubmitting}
          onClose={() => setIsFormOpen(false)}
          onSubmit={handleSave}
        />
      )}

      {deleting && (
        <DeleteConfirmModal
          name={deleting.name}
          isLoading={isDeleting}
          errorKey={deleteErrorKey}
          onClose={() => {
            setDeleting(null);
            setDeleteErrorKey(null);
          }}
          onConfirm={handleConfirmDelete}
        />
      )}

      {isImportOpen && <ImportModal onClose={() => setIsImportOpen(false)} onImported={reload} />}
    </div>
  );
}
