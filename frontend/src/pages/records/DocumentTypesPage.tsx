import React from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '@lib/apiClient';
import { recordsService } from '@lib/recordsService';
import { Badge, Button, Card, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@components/common';
import ConfirmDialog from '@components/records/ConfirmDialog';
import Pagination from '@components/records/Pagination';
import RecordModal from '@components/records/RecordModal';
import type { Dossier, DocumentType, DocumentTypePayload } from '@app-types/records';

const PAGE_SIZE = 10;
const controlClass =
  'rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-main outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-subtle';

function messageFromError(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) return fallback;
  if (error.status === 403) return 'Bạn không có quyền thực hiện thao tác này.';
  return String(error.data?.error || error.data?.message || error.data?.detail || fallback);
}

function displayDate(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('vi-VN').format(date);
}

export default function DocumentTypesPage() {
  const { dossierId = '' } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const stateDossier = (location.state as { dossier?: Dossier } | null)?.dossier;
  const [dossier, setDossier] = React.useState<Dossier | null>(stateDossier ?? null);
  const [items, setItems] = React.useState<DocumentType[]>([]);
  const [count, setCount] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [searchInput, setSearchInput] = React.useState('');
  const [search, setSearch] = React.useState('');
  const [year, setYear] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [reloadKey, setReloadKey] = React.useState(0);
  const [editing, setEditing] = React.useState<DocumentType | null | undefined>(undefined);
  const [deleting, setDeleting] = React.useState<DocumentType | null>(null);
  const [isSaving, setIsSaving] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!dossierId || dossier) return;
    recordsService.getDossier(dossierId).then(setDossier).catch(() => undefined);
  }, [dossierId, dossier]);

  React.useEffect(() => {
    if (!dossierId) {
      queueMicrotask(() => {
        setError('Không xác định được hồ sơ cần xem.');
        setIsLoading(false);
      });
      return undefined;
    }
    let active = true;
    recordsService
      .listDocumentTypes(dossierId, { search, year, page, pageSize: PAGE_SIZE })
      .then((result) => {
        if (!active) return;
        setItems(result.items);
        setCount(result.count);
      })
      .catch((err) => {
        if (active) setError(messageFromError(err, 'Không thể tải danh sách loại văn bản.'));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [dossierId, search, year, page, reloadKey]);

  const beginReload = () => {
    setIsLoading(true);
    setError(null);
  };

  const years = React.useMemo(() => {
    const current = new Date().getFullYear();
    return Array.from({ length: 12 }, (_, index) => current - index);
  }, []);

  const handleSave = async (payload: DocumentTypePayload) => {
    setIsSaving(true);
    setSaveError(null);
    try {
      if (editing) {
        await recordsService.updateDocumentType(editing.id, payload);
        setNotice('Đã cập nhật loại văn bản thành công.');
      } else {
        await recordsService.createDocumentType(dossierId, payload);
        setNotice('Đã thêm loại văn bản thành công.');
      }
      setEditing(undefined);
      beginReload();
      setReloadKey((value) => value + 1);
    } catch (err) {
      setSaveError(messageFromError(err, 'Không thể lưu loại văn bản. Vui lòng kiểm tra lại dữ liệu.'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    setIsSaving(true);
    try {
      await recordsService.deleteDocumentType(deleting.id);
      setDeleting(null);
      setNotice('Đã xóa loại văn bản thành công.');
      beginReload();
      if (items.length === 1 && page > 1) setPage((value) => value - 1);
      else setReloadKey((value) => value + 1);
    } catch (err) {
      setDeleting(null);
      setError(messageFromError(err, 'Không thể xóa loại văn bản. Dữ liệu có thể đang được sử dụng.'));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <section className="space-y-5" aria-labelledby="document-types-title">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <button type="button" className="mb-2 cursor-pointer text-sm font-semibold text-primary hover:underline" onClick={() => navigate('/records')}>
            <i className="fa-solid fa-arrow-left mr-2" />Quay lại danh mục hồ sơ
          </button>
          <h1 id="document-types-title" className="m-0 text-2xl font-bold text-main">Loại văn bản</h1>
          <p className="m-0 mt-1 text-sm text-secondary">
            Hồ sơ: <strong className="text-main">{dossier?.ten_ho_so ?? `#${dossierId}`}</strong>
            {dossier?.so_ky_hieu && <Badge variant="secondary" className="ml-2">{dossier.so_ky_hieu}</Badge>}
          </p>
        </div>
        <Button type="button" icon="fa-plus" onClick={() => { setSaveError(null); setEditing(null); }}>
          Thêm loại văn bản
        </Button>
      </div>

      {notice && (
        <div className="flex items-center justify-between rounded-lg border border-success-border bg-success-subtle px-4 py-3 text-sm text-success" role="status">
          <span><i className="fa-solid fa-circle-check mr-2" />{notice}</span>
          <button type="button" className="cursor-pointer" onClick={() => setNotice(null)} aria-label="Đóng thông báo"><i className="fa-solid fa-xmark" /></button>
        </div>
      )}

      <Card>
        <form className="flex flex-col gap-3 border-b border-border-subtle p-4 md:flex-row" onSubmit={(event) => { event.preventDefault(); beginReload(); setPage(1); setSearch(searchInput.trim()); }}>
          <label className="relative flex-1">
            <span className="sr-only">Tìm loại văn bản</span>
            <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input className={`${controlClass} w-full pl-9`} placeholder="Tìm theo tên loại văn bản..." value={searchInput} onChange={(event) => setSearchInput(event.target.value)} />
          </label>
          <select className={`${controlClass} w-full md:w-40`} value={year} onChange={(event) => { beginReload(); setYear(event.target.value); setPage(1); }} aria-label="Lọc theo năm">
            <option value="">Tất cả năm</option>
            {years.map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
          <Button type="submit" variant="secondary" icon="fa-filter">Lọc dữ liệu</Button>
          {(search || year) && <Button type="button" variant="ghost" onClick={() => { beginReload(); setSearchInput(''); setSearch(''); setYear(''); setPage(1); }}>Đặt lại</Button>}
        </form>

        {error ? (
          <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center" role="alert">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-subtle text-xl text-danger"><i className="fa-solid fa-triangle-exclamation" /></span>
            <div><h2 className="m-0 text-base font-bold text-main">Không thể tải dữ liệu</h2><p className="mt-1 text-sm text-secondary">{error}</p></div>
            <Button type="button" variant="secondary" icon="fa-rotate-right" onClick={() => { beginReload(); setReloadKey((value) => value + 1); }}>Thử lại</Button>
          </div>
        ) : isLoading ? (
          <div className="space-y-3 p-5" aria-label="Đang tải danh sách loại văn bản">
            {Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-12 animate-pulse rounded-lg bg-surface-elevated" />)}
          </div>
        ) : items.length === 0 ? (
          <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-subtle text-2xl text-primary"><i className="fa-solid fa-file-circle-plus" /></span>
            <div><h2 className="m-0 text-base font-bold text-main">Chưa có loại văn bản phù hợp</h2><p className="mt-1 text-sm text-secondary">Thay đổi bộ lọc hoặc thêm loại văn bản mới cho hồ sơ này.</p></div>
          </div>
        ) : (
          <>
            <div className="p-4">
              <Table>
                <TableHeader><TableRow>
                  <TableHead className="w-20">STT</TableHead>
                  <TableHead>Tên loại văn bản</TableHead>
                  <TableHead>Ngày lập</TableHead>
                  <TableHead>Ghi chú</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {items.map((item, index) => (
                    <TableRow key={item.id}>
                      <TableCell>{(page - 1) * PAGE_SIZE + index + 1}</TableCell>
                      <TableCell><span className="font-semibold text-main">{item.ten_loai}</span></TableCell>
                      <TableCell className="whitespace-nowrap">{displayDate(item.ngay_lap)}</TableCell>
                      <TableCell><span className="block max-w-md truncate text-secondary">{item.ghi_chu || '—'}</span></TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button type="button" size="sm" variant="ghost" icon="fa-pen" onClick={() => { setSaveError(null); setEditing(item); }} aria-label={`Sửa ${item.ten_loai}`} />
                          <Button type="button" size="sm" variant="ghost" icon="fa-trash" className="text-danger hover:text-danger" onClick={() => setDeleting(item)} aria-label={`Xóa ${item.ten_loai}`} />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <Pagination page={page} pageSize={PAGE_SIZE} count={count} onChange={(value) => { beginReload(); setPage(value); }} />
          </>
        )}
      </Card>

      <RecordModal
        open={editing !== undefined}
        mode="documentType"
        value={editing}
        isLoading={isSaving}
        error={saveError}
        onClose={() => { if (!isSaving) setEditing(undefined); }}
        onSubmit={handleSave}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Xóa loại văn bản?"
        message={`Loại văn bản “${deleting?.ten_loai ?? ''}” sẽ bị xóa. Thao tác có thể bị từ chối nếu đang có văn bản sử dụng.`}
        isLoading={isSaving}
        onCancel={() => setDeleting(null)}
        onConfirm={handleDelete}
      />
    </section>
  );
}
