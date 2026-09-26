import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '@lib/apiClient';
import { recordsService } from '@lib/recordsService';
import { Badge, Button, Card, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@components/common';
import ConfirmDialog from '@components/records/ConfirmDialog';
import Pagination from '@components/records/Pagination';
import RecordModal from '@components/records/RecordModal';
import type { Dossier, DossierPayload } from '@app-types/records';

const PAGE_SIZE = 10;
const controlClass =
  'rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-main outline-none transition focus:border-primary focus:ring-2 focus:ring-primary-subtle';

function apiErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) return fallback;
  if (error.status === 403) return 'Bạn không có quyền thực hiện thao tác này.';
  return String(error.data?.error || error.data?.message || error.data?.detail || fallback);
}

function displayDate(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('vi-VN').format(date);
}

function creatorName(value: Dossier['nguoi_lap']): string {
  if (!value) return '—';
  if (typeof value === 'string') return value;
  return value.full_name || value.ho_ten || value.username || '—';
}

function sortedDossiers(items: Dossier[]): Dossier[] {
  return [...items].sort((a, b) => {
    const aCommon = a.ten_ho_so.trim().toLocaleLowerCase('vi') === 'hồ sơ chung' ? 0 : 1;
    const bCommon = b.ten_ho_so.trim().toLocaleLowerCase('vi') === 'hồ sơ chung' ? 0 : 1;
    if (aCommon !== bCommon) return aCommon - bCommon;
    return (a.stt_uu_tien ?? Number.MAX_SAFE_INTEGER) - (b.stt_uu_tien ?? Number.MAX_SAFE_INTEGER);
  });
}

export default function DossiersPage() {
  const navigate = useNavigate();
  const [items, setItems] = React.useState<Dossier[]>([]);
  const [count, setCount] = React.useState(0);
  const [page, setPage] = React.useState(1);
  const [searchInput, setSearchInput] = React.useState('');
  const [search, setSearch] = React.useState('');
  const [year, setYear] = React.useState('');
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [reloadKey, setReloadKey] = React.useState(0);
  const [editing, setEditing] = React.useState<Dossier | null | undefined>(undefined);
  const [deleting, setDeleting] = React.useState<Dossier | null>(null);
  const [isSaving, setIsSaving] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;
    recordsService
      .listDossiers({ search, year, page, pageSize: PAGE_SIZE })
      .then((result) => {
        if (!active) return;
        setItems(sortedDossiers(result.items));
        setCount(result.count);
      })
      .catch((err) => {
        if (active) setError(apiErrorMessage(err, 'Không thể tải danh sách hồ sơ.'));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [search, year, page, reloadKey]);

  const beginReload = () => {
    setIsLoading(true);
    setError(null);
  };

  const years = React.useMemo(() => {
    const current = new Date().getFullYear();
    return Array.from({ length: 12 }, (_, index) => current - index);
  }, []);

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    beginReload();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const handleSave = async (payload: DossierPayload) => {
    setIsSaving(true);
    setSaveError(null);
    try {
      if (editing) {
        await recordsService.updateDossier(editing.id, payload);
        setNotice('Đã cập nhật hồ sơ thành công.');
      } else {
        await recordsService.createDossier(payload);
        setNotice('Đã thêm hồ sơ thành công.');
      }
      setEditing(undefined);
      beginReload();
      setReloadKey((value) => value + 1);
    } catch (err) {
      setSaveError(apiErrorMessage(err, 'Không thể lưu hồ sơ. Vui lòng kiểm tra lại dữ liệu.'));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleting) return;
    setIsSaving(true);
    try {
      await recordsService.deleteDossier(deleting.id);
      setDeleting(null);
      setNotice('Đã xóa hồ sơ thành công.');
      beginReload();
      if (items.length === 1 && page > 1) setPage((value) => value - 1);
      else setReloadKey((value) => value + 1);
    } catch (err) {
      setDeleting(null);
      setError(apiErrorMessage(err, 'Không thể xóa hồ sơ. Hồ sơ có thể đang chứa dữ liệu liên quan.'));
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
            Nhóm 3 · Hồ sơ và tài liệu
          </div>
          <h1 id="dossiers-title" className="m-0 text-2xl font-bold text-main">Danh mục hồ sơ</h1>
          <p className="m-0 mt-1 text-sm text-secondary">Quản lý hồ sơ cấp 1 và truy cập các loại văn bản thuộc từng hồ sơ.</p>
        </div>
        <Button type="button" icon="fa-plus" onClick={() => { setSaveError(null); setEditing(null); }}>
          Thêm hồ sơ
        </Button>
      </div>

      {notice && (
        <div className="flex items-center justify-between rounded-lg border border-success-border bg-success-subtle px-4 py-3 text-sm text-success" role="status">
          <span><i className="fa-solid fa-circle-check mr-2" />{notice}</span>
          <button type="button" className="cursor-pointer" onClick={() => setNotice(null)} aria-label="Đóng thông báo"><i className="fa-solid fa-xmark" /></button>
        </div>
      )}

      <Card>
        <form className="flex flex-col gap-3 border-b border-border-subtle p-4 md:flex-row" onSubmit={submitSearch}>
          <label className="relative flex-1">
            <span className="sr-only">Tìm kiếm hồ sơ</span>
            <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input
              className={`${controlClass} w-full pl-9`}
              placeholder="Tìm theo tên hoặc số/ký hiệu hồ sơ..."
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </label>
          <label>
            <span className="sr-only">Lọc theo năm</span>
            <select className={`${controlClass} w-full md:w-40`} value={year} onChange={(event) => { beginReload(); setYear(event.target.value); setPage(1); }}>
              <option value="">Tất cả năm</option>
              {years.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <Button type="submit" variant="secondary" icon="fa-filter">Lọc dữ liệu</Button>
          {(search || year) && (
            <Button type="button" variant="ghost" onClick={() => { beginReload(); setSearchInput(''); setSearch(''); setYear(''); setPage(1); }}>Đặt lại</Button>
          )}
        </form>

        {error ? (
          <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center" role="alert">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-danger-subtle text-xl text-danger"><i className="fa-solid fa-triangle-exclamation" /></span>
            <div><h2 className="m-0 text-base font-bold text-main">Không thể tải dữ liệu</h2><p className="mt-1 text-sm text-secondary">{error}</p></div>
            <Button type="button" variant="secondary" icon="fa-rotate-right" onClick={() => { beginReload(); setReloadKey((value) => value + 1); }}>Thử lại</Button>
          </div>
        ) : isLoading ? (
          <div className="space-y-3 p-5" aria-label="Đang tải danh sách hồ sơ">
            {Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-12 animate-pulse rounded-lg bg-surface-elevated" />)}
          </div>
        ) : items.length === 0 ? (
          <div className="flex min-h-72 flex-col items-center justify-center gap-3 p-8 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary-subtle text-2xl text-primary"><i className="fa-solid fa-folder-open" /></span>
            <div><h2 className="m-0 text-base font-bold text-main">Chưa có hồ sơ phù hợp</h2><p className="mt-1 text-sm text-secondary">Thay đổi bộ lọc hoặc thêm hồ sơ mới để bắt đầu.</p></div>
          </div>
        ) : (
          <>
            <div className="p-4">
              <Table>
                <TableHeader><TableRow>
                  <TableHead className="w-20">STT</TableHead>
                  <TableHead>Số/ký hiệu</TableHead>
                  <TableHead>Tên hồ sơ</TableHead>
                  <TableHead>Người lập</TableHead>
                  <TableHead>Ngày lập</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow></TableHeader>
                <TableBody>
                  {items.map((item, index) => (
                    <TableRow key={item.id} className="cursor-pointer" onClick={() => navigate(`/records/${item.id}/document-types`, { state: { dossier: item } })}>
                      <TableCell>{item.stt_uu_tien ?? (page - 1) * PAGE_SIZE + index + 1}</TableCell>
                      <TableCell><Badge variant="secondary">{item.so_ky_hieu || '—'}</Badge></TableCell>
                      <TableCell><div className="font-semibold text-main">{item.ten_ho_so}</div>{item.ghi_chu && <div className="mt-1 max-w-sm truncate text-xs text-muted">{item.ghi_chu}</div>}</TableCell>
                      <TableCell>{creatorName(item.nguoi_lap)}</TableCell>
                      <TableCell className="whitespace-nowrap">{displayDate(item.ngay_lap)}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-1">
                          <Button type="button" size="sm" variant="ghost" icon="fa-folder-open" onClick={(event) => { event.stopPropagation(); navigate(`/records/${item.id}/document-types`, { state: { dossier: item } }); }} aria-label={`Xem loại văn bản của ${item.ten_ho_so}`}>Xem</Button>
                          <Button type="button" size="sm" variant="ghost" icon="fa-pen" onClick={(event) => { event.stopPropagation(); setSaveError(null); setEditing(item); }} aria-label={`Sửa ${item.ten_ho_so}`} />
                          <Button type="button" size="sm" variant="ghost" icon="fa-trash" className="text-danger hover:text-danger" onClick={(event) => { event.stopPropagation(); setDeleting(item); }} aria-label={`Xóa ${item.ten_ho_so}`} />
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
        mode="dossier"
        value={editing}
        isLoading={isSaving}
        error={saveError}
        onClose={() => { if (!isSaving) setEditing(undefined); }}
        onSubmit={handleSave}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Xóa hồ sơ?"
        message={`Hồ sơ “${deleting?.ten_ho_so ?? ''}” sẽ bị xóa. Thao tác có thể bị từ chối nếu hồ sơ còn dữ liệu liên quan.`}
        isLoading={isSaving}
        onCancel={() => setDeleting(null)}
        onConfirm={handleDelete}
      />
    </section>
  );
}
