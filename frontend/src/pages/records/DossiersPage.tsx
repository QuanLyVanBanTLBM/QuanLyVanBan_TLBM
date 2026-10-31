import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '@lib/apiClient';
import { recordsService } from '@lib/recordsService';
import { dossierDocumentTypesDestination } from '@lib/recordsDocumentNavigation';
import { Badge, Button, Card, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@components/common';
import ConfirmDialog from '@components/records/ConfirmDialog';
import Pagination from '@components/records/Pagination';
import RecordModal from '@components/records/RecordModal';
import { useTranslation } from '@i18n/translate';
import type { Dossier, DossierPayload } from '@app-types/records';

const PAGE_SIZE = 10;
const controlClass =
  'rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-main outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-subtle';

function apiErrorMessage(error: unknown, fallback: string, forbidden: string): string {
  if (!(error instanceof ApiError)) return fallback;
  if (error.status === 403) return forbidden;
  const direct = error.data?.error || error.data?.message || error.data?.detail;
  if (direct) return String(direct);

  for (const value of Object.values(error.data ?? {})) {
    if (typeof value === 'string' && value.trim()) return value;
    if (Array.isArray(value) && value.length > 0) return String(value[0]);
  }
  return fallback;
}

function displayDate(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(locale).format(date);
}

function creatorName(value: Dossier['nguoi_lap']): string {
  if (!value) return '—';
  if (typeof value === 'string') return value;
  return value.full_name || value.ho_ten || value.username || '—';
}

function sortedDossiers(items: Dossier[]): Dossier[] {
  return [...items].sort((a, b) => {
    const aCommon = a.is_he_thong ? 0 : 1;
    const bCommon = b.is_he_thong ? 0 : 1;
    if (aCommon !== bCommon) return aCommon - bCommon;
    return (a.stt_uu_tien ?? Number.MAX_SAFE_INTEGER) - (b.stt_uu_tien ?? Number.MAX_SAFE_INTEGER);
  });
}

export default function DossiersPage() {
  const navigate = useNavigate();
  const { currentLang, t } = useTranslation();
  const [items, setItems] = React.useState<Dossier[]>([]);
  const [count, setCount] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [searchInput, setSearchInput] = React.useState('');
  const [search, setSearch] = React.useState('');
  const [year, setYear] = React.useState('');
  const [appliedYear, setAppliedYear] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [reloadKey, setReloadKey] = React.useState(0);
  const [editing, setEditing] = React.useState<Dossier | null | undefined>(undefined);
  const [deleting, setDeleting] = React.useState<Dossier | null>(null);
  const [isSaving, setIsSaving] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);
  const [saveError, setSaveError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => {
        if (!active) return null;
        setIsLoading(true);
        setError(null);
        return recordsService.listDossiers({ search, year: appliedYear, page, pageSize: PAGE_SIZE });
      })
      .then((result) => {
        if (!active || !result) return;
        setItems(sortedDossiers(result.items));
        setCount(result.count);
      })
      .catch((err) => {
        if (active) {
          setError(
            apiErrorMessage(
              err,
              t('records.errors.loadDossiers'),
              t('records.errors.forbidden')
            )
          );
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [search, appliedYear, page, reloadKey, t]);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      const trimmed = searchInput.trim();
      if (trimmed !== search) {
        setPage(1);
        setSearch(trimmed);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchInput, search]);

  const years = React.useMemo(() => {
    const current = new Date().getFullYear();
    return Array.from({ length: 12 }, (_, index) => current - index);
  }, []);

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
    setAppliedYear(year);
    setReloadKey((value) => value + 1);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    if (search !== '') {
      setPage(1);
      setSearch('');
    }
  };

  const handleSave = async (payload: DossierPayload) => {
    setIsSaving(true);
    setSaveError(null);
    try {
      if (editing) {
        await recordsService.updateDossier(editing.id, payload);
        setNotice(t('records.dossiers.notices.updated'));
      } else {
        await recordsService.createDossier(payload);
        setNotice(t('records.dossiers.notices.created'));
      }
      setEditing(undefined);
      setReloadKey((value) => value + 1);
    } catch (err) {
      setSaveError(
        apiErrorMessage(
          err,
          t('records.errors.saveDossier'),
          t('records.errors.forbidden')
        )
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleting || isSaving) return;
    setDeleteError(null);
    setIsSaving(true);
    try {
      await recordsService.deleteDossier(deleting.id);
      setDeleting(null);
      setNotice(t('records.dossiers.notices.deleted'));
      if (items.length === 1 && page > 1) setPage((value) => value - 1);
      else setReloadKey((value) => value + 1);
    } catch (err) {
      setDeleteError(
        apiErrorMessage(
          err,
          t('records.errors.deleteDossier'),
          t('records.errors.forbidden')
        )
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="space-y-5" aria-labelledby="dossiers-title">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary">
            <i className="fa-solid fa-folder-tree" />
            {t('records.dossiers.moduleLabel')}
          </div>
          <h1 id="dossiers-title" className="m-0 text-2xl font-bold text-main">
            {t('records.dossiers.title')}
          </h1>
          <p className="m-0 mt-1 text-sm text-secondary">
            {t('records.dossiers.description')}
          </p>
        </div>
        <Button type="button" icon="fa-plus" onClick={() => { setSaveError(null); setEditing(null); }}>
          {t('records.dossiers.add')}
        </Button>
      </div>

      {notice && (
        <div className="flex items-center justify-between rounded-lg border border-success-border bg-success-subtle px-4 py-3 text-sm text-success" role="status">
          <span><i className="fa-solid fa-circle-check mr-2" />{notice}</span>
          <button type="button" className="cursor-pointer" onClick={() => setNotice(null)} aria-label={t('records.dossiers.closeNotice')}><i className="fa-solid fa-xmark" /></button>
        </div>
      )}

      <Card>
        <form className="flex flex-col gap-3 border-b border-border-subtle p-4 md:flex-row" onSubmit={submitSearch}>
          <label className="relative flex-1">
            <span className="sr-only">{t('records.dossiers.searchLabel')}</span>
            <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              className={`${controlClass} w-full pl-9 ${searchInput ? 'pr-8' : ''}`}
              placeholder={t('records.dossiers.searchPlaceholder')}
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
            {searchInput && (
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer border-none bg-transparent p-0 text-muted transition hover:text-main"
                onClick={handleClearSearch}
                aria-label={t('records.actions.reset')}
              >
                <i className="fa-solid fa-xmark text-sm" />
              </button>
            )}
          </label>
          <label>
            <span className="sr-only">{t('records.filters.year')}</span>
            <select
              className={`${controlClass} w-full md:w-40`}
              value={year}
              onChange={(event) => setYear(event.target.value)}
            >
              <option value="">{t('records.filters.allYears')}</option>
              {years.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <Button type="submit" variant="secondary" icon="fa-filter">{t('records.actions.filter')}</Button>
          {(search || year || appliedYear) && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setSearchInput('');
                setSearch('');
                setYear('');
                setAppliedYear('');
                setPage(1);
              }}
            >
              {t('records.actions.reset')}
            </Button>
          )}
        </form>

        {error ? (
          <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center" role="alert">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-subtle text-xl text-danger"><i className="fa-solid fa-triangle-exclamation" /></span>
            <div><h2 className="m-0 text-base font-bold text-main">{t('records.errors.title')}</h2><p className="mt-1 text-sm text-secondary">{error}</p></div>
            <Button type="button" variant="secondary" icon="fa-rotate-right" onClick={() => setReloadKey((value) => value + 1)}>{t('records.actions.retry')}</Button>
          </div>
        ) : isLoading ? (
          <div className="space-y-3 p-5" aria-label={t('records.dossiers.loading')}>
            {Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-12 animate-pulse rounded-lg bg-surface-elevated" />)}
          </div>
        ) : items.length === 0 ? (
          <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-subtle text-2xl text-primary"><i className="fa-solid fa-folder-open" /></span>
            <div><h2 className="m-0 text-base font-bold text-main">{t('records.dossiers.emptyTitle')}</h2><p className="mt-1 text-sm text-secondary">{t('records.dossiers.emptyDescription')}</p></div>
          </div>
        ) : (
          <>
            <div className="p-4">
              <Table>
                <TableHeader><TableRow>
                  <TableHead className="w-20">{t('records.table.index')}</TableHead>
                  <TableHead>{t('records.dossiers.reference')}</TableHead>
                  <TableHead>{t('records.dossiers.name')}</TableHead>
                  <TableHead>{t('records.dossiers.creator')}</TableHead>
                  <TableHead>{t('records.table.createdDate')}</TableHead>
                  <TableHead className="text-right">{t('records.table.action')}</TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {items.map((item, index) => (
                    <TableRow key={item.id} className="cursor-pointer" onClick={() => navigate(dossierDocumentTypesDestination(item))}>
                      <TableCell>{item.stt_uu_tien ?? (page - 1) * PAGE_SIZE + index + 1}</TableCell>
                      <TableCell><Badge variant="secondary">{item.so_ky_hieu || '—'}</Badge></TableCell>
                      <TableCell><div className="font-semibold text-main">{item.ten_ho_so}</div>{item.ghi_chu && <div className="mt-1 max-w-sm truncate text-xs text-muted">{item.ghi_chu}</div>}</TableCell>
                      <TableCell>{creatorName(item.nguoi_lap)}</TableCell>
                      <TableCell className="whitespace-nowrap">{displayDate(item.ngay_lap, currentLang === 'vi' ? 'vi-VN' : 'en-US')}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button type="button" size="sm" variant="ghost" icon="fa-folder-open" onClick={(event) => { event.stopPropagation(); navigate(dossierDocumentTypesDestination(item)); }} aria-label={t('records.dossiers.viewDocumentTypesLabel', { name: item.ten_ho_so })}>{t('records.actions.view')}</Button>
                          <Button type="button" size="sm" variant="ghost" icon="fa-pen" onClick={(event) => { event.stopPropagation(); setSaveError(null); setEditing(item); }} aria-label={t('records.dossiers.editLabel', { name: item.ten_ho_so })} />
                          {!item.is_he_thong && (
                            <Button type="button" size="sm" variant="ghost" icon="fa-trash" className="text-danger hover:text-danger" onClick={(event) => { event.stopPropagation(); setDeleteError(null); setDeleting(item); }} aria-label={t('records.dossiers.deleteLabel', { name: item.ten_ho_so })} />
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={count} onChange={(value) => setPage(value)} />
          </>
        )}
      </Card>

      <RecordModal
        open={editing !== undefined}
        mode="dossier"
        value={editing}
        isLoading={isSaving}
        error={saveError}
        onClose={() => { if (!isSaving) setEditing(undefined); }}
        onSubmit={handleSave}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        title={t('records.dossiers.confirmDeleteTitle')}
        message={t('records.dossiers.confirmDeleteMessage', { name: deleting?.ten_ho_so ?? '' })}
        isLoading={isSaving}
        error={deleteError}
        onCancel={() => { if (!isSaving) setDeleting(null); }}
        onConfirm={handleDelete}
      />
    </section>
  );
}
