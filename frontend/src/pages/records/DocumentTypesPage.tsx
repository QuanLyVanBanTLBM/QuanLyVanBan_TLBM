import React from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '@lib/apiClient';
import { recordsService } from '@lib/recordsService';
import { useTranslation } from '@i18n/translate';
import {
  Badge,
  Button,
  Card,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@components/common';
import Pagination from '@components/records/Pagination';
import DocumentDestinationDialog from '@components/records/DocumentDestinationDialog';
import ConfirmDialog from '@components/records/ConfirmDialog';
import RecordModal from '@components/records/RecordModal';
import type { Dossier, DocumentType, DocumentTypePayload } from '@app-types/records';

const PAGE_SIZE = 10;
const controlClass =
  'rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-main outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-subtle';

function errorMessage(error: unknown, fallback: string, forbidden: string): string {
  if (!(error instanceof ApiError)) return fallback;
  if (error.status === 403) return forbidden;
  const direct = error.data?.detail || error.data?.message || error.data?.error;
  if (typeof direct === 'string') return direct;
  for (const value of Object.values(error.data ?? {})) {
    if (typeof value === 'string' && value.trim()) return value;
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
  }
  return fallback;
}

export default function DocumentTypesPage() {
  const { dossierId = '' } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { currentLang, t } = useTranslation();
  const [parentContext, setParentContext] = React.useState<{ routeId: string; dossier: Dossier } | null>(null);
  const dossier = parentContext?.routeId === dossierId ? parentContext.dossier : null;
  const [items, setItems] = React.useState<DocumentType[]>([]);
  const [count, setCount] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [searchInput, setSearchInput] = React.useState('');
  const [search, setSearch] = React.useState('');
  const [year, setYear] = React.useState('');
  const [appliedYear, setAppliedYear] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [reloadKey, setReloadKey] = React.useState(0);
  const [editing, setEditing] = React.useState<DocumentType | null | undefined>(undefined);
  const [deleting, setDeleting] = React.useState<DocumentType | null>(null);
  const [isSaving, setIsSaving] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [dossierOptions, setDossierOptions] = React.useState<Dossier[]>([]);
  const [createDossierId, setCreateDossierId] = React.useState(dossierId);
  const [isLoadingDossiers, setIsLoadingDossiers] = React.useState(false);
  const mutationPending = React.useRef(false);
  const createRequest = React.useRef(0);

  const [selectedCategory, setSelectedCategory] = React.useState<DocumentType | null>(null);
  const closeDestination = React.useCallback(() => setSelectedCategory(null), []);

  React.useEffect(() => {
    if (!dossierId) return;
    let active = true;
    recordsService.getDossier(dossierId).then((value) => {
      if (active && String(value.id) === dossierId) setParentContext({ routeId: dossierId, dossier: value });
    }).catch(() => undefined);
    return () => { active = false; };
  }, [dossierId]);

  React.useEffect(() => {
    if (!dossier) return;
    const query = new URLSearchParams(location.search);
    if (query.getAll('ten_ho_so').length === 1 && query.get('ten_ho_so') === dossier.ten_ho_so.trim()) return;
    query.set('ten_ho_so', dossier.ten_ho_so.trim());
    navigate({ pathname: location.pathname, search: `?${query}` }, { replace: true });
  }, [dossier, location.pathname, location.search, navigate]);

  React.useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => {
        if (!active) return null;
        setIsLoading(true);
        setError(null);
        return dossierId
          ? recordsService.listDocumentTypes(dossierId, { search, year: appliedYear, page, pageSize: PAGE_SIZE })
          : recordsService.listDocumentTypeCatalog({ search, year: appliedYear, page, pageSize: PAGE_SIZE });
      })
      .then((result) => {
        if (!active || !result) return;
        setItems(result.items);
        setCount(result.count);
      })
      .catch((requestError) => {
        if (!active) return;
        const detail =
          requestError instanceof ApiError
            ? requestError.data?.detail || requestError.data?.message || requestError.data?.error
            : null;
        setError(String(detail || t('records.errors.loadDocumentTypes')));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [dossierId, search, appliedYear, page, reloadKey, t]);

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

  const handleClearSearch = () => {
    setSearchInput('');
    if (search !== '') {
      setPage(1);
      setSearch('');
    }
  };

  const closeEditor = () => {
    if (mutationPending.current) return;
    createRequest.current += 1;
    setIsLoadingDossiers(false);
    setEditing(undefined);
  };

  const openCreate = async () => {
    const requestId = ++createRequest.current;
    setSaveError(null);
    setCreateDossierId(dossierId);
    setDossierOptions([]);
    setEditing(null);
    setIsLoadingDossiers(!dossierId);
    if (dossierId) return;
    try {
      const parents: Dossier[] = [];
      let nextPage = 1;
      let result;
      do {
        result = await recordsService.listDossiers({ page: nextPage++, pageSize: 100 });
        parents.push(...result.items);
      } while (result.next);
      if (requestId === createRequest.current) setDossierOptions(parents);
    } catch (requestError) {
      if (requestId === createRequest.current) setSaveError(errorMessage(requestError, t('records.errors.loadDossiers'), t('records.errors.forbidden')));
    } finally {
      if (requestId === createRequest.current) setIsLoadingDossiers(false);
    }
  };

  const handleSave = async (payload: DocumentTypePayload) => {
    if (mutationPending.current) return;
    const parentId = dossierId || createDossierId;
    if (!editing && !parentId) {
      setSaveError(t('records.modal.validation.dossierRequired'));
      return;
    }
    mutationPending.current = true;
    setIsSaving(true);
    setSaveError(null);
    try {
      if (editing) await recordsService.updateDocumentType(editing.id, payload);
      else await recordsService.createDocumentType(parentId, payload);
      setNotice(t(editing ? 'records.documentTypes.notices.updated' : 'records.documentTypes.notices.created'));
      setEditing(undefined);
      setReloadKey((value) => value + 1);
    } catch (requestError) {
      setSaveError(errorMessage(requestError, t('records.errors.saveDocumentType'), t('records.errors.forbidden')));
    } finally {
      mutationPending.current = false;
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleting || mutationPending.current) return;
    mutationPending.current = true;
    setIsSaving(true);
    setDeleteError(null);
    try {
      await recordsService.deleteDocumentType(deleting.id);
      setDeleting(null);
      setNotice(t('records.documentTypes.notices.deleted'));
      if (items.length === 1 && page > 1) setPage((value) => value - 1);
      else setReloadKey((value) => value + 1);
    } catch (requestError) {
      setDeleteError(errorMessage(requestError, t('records.errors.deleteDocumentType'), t('records.errors.forbidden')));
    } finally {
      mutationPending.current = false;
      setIsSaving(false);
    }
  };

  const years = React.useMemo(() => {
    const current = new Date().getFullYear();
    return Array.from({ length: 12 }, (_, index) => current - index);
  }, []);

  const displayDate = (value?: string | null) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(currentLang === 'vi' ? 'vi-VN' : 'en-US').format(date);
  };


  return (
    <section className="space-y-5" aria-labelledby="document-types-title">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <button
            type="button"
            className="mb-2 cursor-pointer text-sm font-semibold text-primary hover:underline"
            onClick={() => navigate('/records')}
          >
            <i className="fa-solid fa-arrow-left mr-2" />
            {t('records.documentTypes.back')}
          </button>
          <h1 id="document-types-title" className="m-0 text-2xl font-bold text-main">
            {t('records.documentTypes.title')}
          </h1>
          {dossierId && <p className="m-0 mt-1 text-sm text-secondary">
            {t('records.common.dossier')}: <strong>{dossier?.ten_ho_so ?? `#${dossierId}`}</strong>
            {dossier?.so_ky_hieu && <Badge variant="secondary" className="ml-2">{dossier.so_ky_hieu}</Badge>}
          </p>}
          <p className="m-0 mt-2 text-xs text-muted">
            {t('records.documentTypes.description')}
          </p>
        </div>
        <Button type="button" icon="fa-plus" onClick={() => void openCreate()}>{t('records.documentTypes.add')}</Button>
      </div>

      {notice && <div className="flex items-center justify-between rounded-lg border border-success-border bg-success-subtle px-4 py-3 text-sm text-success" role="status">
        <span>{notice}</span>
        <button type="button" onClick={() => setNotice(null)} aria-label={t('records.documentTypes.closeNotice')}><i className="fa-solid fa-xmark" aria-hidden="true" /></button>
      </div>}

      <Card>
        <form
          className="flex flex-col gap-3 border-b border-border-subtle p-4 md:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            const trimmed = searchInput.trim();
            setPage(1);
            setSearch(trimmed);
            setAppliedYear(year);
            setReloadKey((value) => value + 1);
          }}
        >
          <label className="relative flex-1">
            <span className="sr-only">{t('records.documentTypes.searchLabel')}</span>
            <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              type="text"
              className={`${controlClass} w-full pl-9 ${searchInput ? 'pr-8' : ''}`}
              placeholder={t('records.documentTypes.searchPlaceholder')}
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
          <select
            className={`${controlClass} w-full md:w-40`}
            value={year}
            onChange={(event) => setYear(event.target.value)}
            aria-label={t('records.filters.year')}
          >
            <option value="">{t('records.filters.allYears')}</option>
            {years.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <Button type="submit" variant="secondary" icon="fa-filter">
            {t('records.actions.filter')}
          </Button>
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
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-subtle text-xl text-danger">
              <i className="fa-solid fa-triangle-exclamation" />
            </span>
            <div>
              <h2 className="m-0 text-base font-bold text-main">{t('records.errors.title')}</h2>
              <p className="mt-1 text-sm text-secondary">{error}</p>
            </div>
            <Button
              type="button"
              variant="secondary"
              icon="fa-rotate-right"
              onClick={() => {
                setReloadKey((value) => value + 1);
              }}
            >
              {t('records.actions.retry')}
            </Button>
          </div>
        ) : isLoading ? (
          <div className="space-y-3 p-5" aria-label={t('records.documentTypes.loading')}>
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index} className="h-12 animate-pulse rounded-lg bg-surface-elevated" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-subtle text-2xl text-primary">
              <i className="fa-solid fa-folder-open" />
            </span>
            <div>
              <h2 className="m-0 text-base font-bold text-main">
                {t('records.documentTypes.emptyTitle')}
              </h2>
              <p className="mt-1 text-sm text-secondary">
                {t('records.documentTypes.emptyDescription')}
              </p>
            </div>

          </div>
        ) : (
          <>
            <div className="p-4">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-20">{t('records.table.index')}</TableHead>
                    <TableHead>{t('records.documentTypes.name')}</TableHead>
                    {!dossierId && <TableHead>{t('records.common.dossier')}</TableHead>}
                    <TableHead>{t('records.table.createdDate')}</TableHead>
                    <TableHead>{t('records.table.note')}</TableHead>
                    <TableHead className="text-right">{t('records.table.action')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item, index) => (
                    <TableRow key={item.id} className="cursor-pointer" onClick={() => setSelectedCategory(item)}>
                      <TableCell>{(page - 1) * PAGE_SIZE + index + 1}</TableCell>
                      <TableCell>
                        <button type="button" className="cursor-pointer text-left font-semibold text-primary hover:underline"
                          onClick={(event) => { event.stopPropagation(); setSelectedCategory(item); }}>{item.ten_loai}</button>
                      </TableCell>
                      {!dossierId && <TableCell>{item.ten_ho_so || `#${typeof item.ho_so === 'object' ? item.ho_so.id : item.ho_so}`}</TableCell>}
                      <TableCell className="whitespace-nowrap">{displayDate(item.ngay_lap)}</TableCell>
                      <TableCell>
                        <span className="block max-w-md truncate text-secondary">
                          {item.ghi_chu || '—'}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex flex-wrap justify-end gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          icon="fa-folder-open"
                          onClick={(event) => {
                            event.stopPropagation();
                            setSelectedCategory(item);
                          }}
                        >
                          {t('records.actions.viewDocuments')}
                        </Button>
                        <Button type="button" size="sm" variant="ghost" icon="fa-pen"
                          aria-label={t('records.documentTypes.editLabel', { name: item.ten_loai })}
                          onClick={(event) => { event.stopPropagation(); setSaveError(null); setEditing(item); }}>
                          {t('records.actions.edit')}
                        </Button>
                        <Button type="button" size="sm" variant="ghost" icon="fa-trash"
                          aria-label={t('records.documentTypes.deleteLabel', { name: item.ten_loai })}
                          onClick={(event) => { event.stopPropagation(); setDeleteError(null); setDeleting(item); }}>
                          {t('records.actions.delete')}
                        </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <Pagination
              page={page}
              pageSize={PAGE_SIZE}
              count={count}
              onChange={(value) => setPage(value)}
            />
          </>
        )}
      </Card>
      {editing !== undefined && <RecordModal open mode="documentType" value={editing} isLoading={isSaving}
        error={saveError} onClose={closeEditor} onSubmit={(payload) => void handleSave(payload)}
        dossierOptions={!editing && !dossierId ? dossierOptions : undefined}
        dossierId={createDossierId} isLoadingDossiers={isLoadingDossiers} onDossierChange={setCreateDossierId} />}
      <ConfirmDialog open={Boolean(deleting)} title={t('records.documentTypes.confirmDeleteTitle')}
        message={t('records.documentTypes.confirmDeleteMessage', { name: deleting?.ten_loai ?? '' })}
        isLoading={isSaving} error={deleteError} onCancel={() => { if (!mutationPending.current) setDeleting(null); }}
        onConfirm={() => void handleDelete()} />
      {selectedCategory && <DocumentDestinationDialog key={`${dossierId}:${selectedCategory.id}`} category={selectedCategory} dossierId={dossierId || undefined}
        onClose={closeDestination} onNavigate={(destination) => navigate(destination)} />}
    </section>
  );
}
