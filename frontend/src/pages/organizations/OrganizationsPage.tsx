/**
 * Trang Quản lý Cơ cấu Tổ chức & Đơn vị (Module 7.3 - Nhóm 7).
 * Tác giả: Lê Duy Khánh.
 */
import React, { useState, useEffect } from 'react';
import { useTranslation } from '@i18n/translate';
import { apiClient, ApiError } from '@lib/apiClient';
import { authService } from '@lib/authService';
import { Card, Button, Badge } from '@components/common';
import {
  KhoiKhuVuc,
  DonVi,
  DonViPaginationResponse,
  CreateKhoiPayload,
  CreateDonViPayload,
} from '../../types/organizations';

export default function OrganizationsPage() {
  const { t } = useTranslation();

  // ── Tab State ────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<'units' | 'regions'>('units');

  // ── Data States ──────────────────────────────────────────────────────
  const [regions, setRegions] = useState<KhoiKhuVuc[]>([]);
  const [units, setUnits] = useState<DonVi[]>([]);
  const [totalUnitsCount, setTotalUnitsCount] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  // ── Filter States ────────────────────────────────────────────────────
  const [unitSearch, setUnitSearch] = useState<string>('');
  const [selectedRegionId, setSelectedRegionId] = useState<string>('');
  const [selectedPublicFilter, setSelectedPublicFilter] = useState<string>('');
  const [regionSearch, setRegionSearch] = useState<string>('');

  // ── Loading & Status States ──────────────────────────────────────────
  const [loading, setLoading] = useState<boolean>(true);
  const [exporting, setExporting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // ── Modal States ─────────────────────────────────────────────────────
  // Modal Khối
  const [isRegionModalOpen, setIsRegionModalOpen] = useState<boolean>(false);
  const [editingRegion, setEditingRegion] = useState<KhoiKhuVuc | null>(null);
  const [regionForm, setRegionForm] = useState<CreateKhoiPayload>({ ten: '', thu_tu_hien_thi: 0 });
  const [regionSubmitting, setRegionSubmitting] = useState<boolean>(false);
  const [regionFormError, setRegionFormError] = useState<string>('');

  // Modal Đơn vị
  const [isUnitModalOpen, setIsUnitModalOpen] = useState<boolean>(false);
  const [editingUnit, setEditingUnit] = useState<DonVi | null>(null);
  const [unitForm, setUnitForm] = useState<CreateDonViPayload>({
    khoi_id: 0,
    ten: '',
    stt_uu_tien: null,
    dia_chi: '',
    dien_thoai: '',
    email: '',
    is_public: true,
    ghi_chu: '',
  });
  const [unitSubmitting, setUnitSubmitting] = useState<boolean>(false);
  const [unitFormError, setUnitFormError] = useState<string>('');

  // Modal Xác nhận Xóa
  const [deleteConfirm, setDeleteConfirm] = useState<{
    isOpen: boolean;
    type: 'region' | 'unit';
    id: number;
    name: string;
  }>({ isOpen: false, type: 'unit', id: 0, name: '' });
  const [deleting, setDeleting] = useState<boolean>(false);

  // ── Reload Triggers ──────────────────────────────────────────────────
  const [reloadRegions, setReloadRegions] = useState<number>(0);
  const [reloadUnits, setReloadUnits] = useState<number>(0);

  // ── Auto-hide Toast ──────────────────────────────────────────────────
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => setToastMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  // ── Fetch Khối / Khu vực ─────────────────────────────────────────────
  useEffect(() => {
    let isMounted = true;
    apiClient
      .get<KhoiKhuVuc[] | { results: KhoiKhuVuc[] }>('/api/organizations/regions/')
      .then((res) => {
        if (!isMounted) return;
        const list = Array.isArray(res) ? res : res?.results || [];
        setRegions(list);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Error fetching regions:', err);
      });

    return () => {
      isMounted = false;
    };
  }, [reloadRegions]);

  // ── Fetch Đơn vị / Phòng ban ─────────────────────────────────────────
  useEffect(() => {
    let isMounted = true;
    const params = new URLSearchParams();
    params.append('page', currentPage.toString());
    if (unitSearch.trim()) params.append('search', unitSearch.trim());
    if (selectedRegionId) params.append('region_id', selectedRegionId);
    if (selectedPublicFilter) params.append('is_public', selectedPublicFilter);

    apiClient
      .get<DonViPaginationResponse>(`/api/organizations/units/?${params.toString()}`)
      .then((res) => {
        if (!isMounted) return;
        if (res && Array.isArray(res.results)) {
          setUnits(res.results);
          setTotalUnitsCount(res.count || 0);
        } else {
          setUnits([]);
          setTotalUnitsCount(0);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Error fetching units:', err);
        setToastMessage({ type: 'error', text: t('organizations.loadError') });
        setUnits([]);
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [currentPage, unitSearch, selectedRegionId, selectedPublicFilter, reloadUnits, t]);

  // ── Handlers: Xuất Excel ─────────────────────────────────────────────
  const handleExportExcel = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (unitSearch.trim()) params.append('search', unitSearch.trim());
      if (selectedRegionId) params.append('region_id', selectedRegionId);
      if (selectedPublicFilter) params.append('is_public', selectedPublicFilter);

      const token = authService.getAccessToken();

      const url = `/api/organizations/units/export/${params.toString() ? `?${params.toString()}` : ''}`;
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!res.ok) {
        throw new Error('Export failed');
      }

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = 'Danh_sach_don_vi_phong_ban.xlsx';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

      setToastMessage({ type: 'success', text: 'Xuất file Excel danh sách đơn vị thành công!' });
    } catch (err) {
      console.error('Error exporting excel:', err);
      setToastMessage({ type: 'error', text: 'Xuất file Excel thất bại. Vui lòng thử lại!' });
    } finally {
      setExporting(false);
    }
  };

  // ── Handlers: Khối / Khu vực Modal & CRUD ────────────────────────────
  const openAddRegionModal = () => {
    setEditingRegion(null);
    setRegionForm({ ten: '', thu_tu_hien_thi: regions.length + 1 });
    setRegionFormError('');
    setIsRegionModalOpen(true);
  };

  const openEditRegionModal = (item: KhoiKhuVuc) => {
    setEditingRegion(item);
    setRegionForm({ ten: item.ten, thu_tu_hien_thi: item.thu_tu_hien_thi });
    setRegionFormError('');
    setIsRegionModalOpen(true);
  };

  const handleSaveRegion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regionForm.ten.trim()) {
      setRegionFormError('Vui lòng nhập tên Khối / Khu vực.');
      return;
    }

    setRegionSubmitting(true);
    setRegionFormError('');
    try {
      if (editingRegion) {
        await apiClient.put(`/api/organizations/regions/${editingRegion.id}/`, regionForm);
      } else {
        await apiClient.post('/api/organizations/regions/', regionForm);
      }
      setIsRegionModalOpen(false);
      setToastMessage({ type: 'success', text: t('organizations.saveSuccess') });
      setReloadRegions((v) => v + 1);
    } catch (err) {
      const error = err as ApiError;
      setRegionFormError(error?.message || error?.data?.detail || 'Lưu thông tin khối thất bại.');
    } finally {
      setRegionSubmitting(false);
    }
  };

  // ── Handlers: Đơn vị / Phòng ban Modal & CRUD ────────────────────────
  const openAddUnitModal = () => {
    setEditingUnit(null);
    setUnitForm({
      khoi_id: regions.length > 0 ? regions[0].id : 0,
      ten: '',
      stt_uu_tien: null,
      dia_chi: '',
      dien_thoai: '',
      email: '',
      is_public: true,
      ghi_chu: '',
    });
    setUnitFormError('');
    setIsUnitModalOpen(true);
  };

  const openEditUnitModal = (item: DonVi) => {
    setEditingUnit(item);
    setUnitForm({
      khoi_id: item.khoi_id,
      ten: item.ten,
      stt_uu_tien: item.stt_uu_tien,
      dia_chi: item.dia_chi || '',
      dien_thoai: item.dien_thoai || '',
      email: item.email || '',
      is_public: item.is_public,
      ghi_chu: item.ghi_chu || '',
    });
    setUnitFormError('');
    setIsUnitModalOpen(true);
  };

  const handleSaveUnit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!unitForm.ten.trim()) {
      setUnitFormError('Vui lòng nhập tên Đơn vị / Phòng ban.');
      return;
    }
    if (!unitForm.khoi_id) {
      setUnitFormError('Vui lòng chọn Khối / Khu vực trực thuộc.');
      return;
    }

    setUnitSubmitting(true);
    setUnitFormError('');
    try {
      const payload: Record<string, unknown> = {
        khoi_id: Number(unitForm.khoi_id),
        ten: unitForm.ten.trim(),
        dia_chi: unitForm.dia_chi?.trim() || '',
        dien_thoai: unitForm.dien_thoai?.trim() || '',
        email: unitForm.email?.trim() || '',
        is_public: unitForm.is_public ?? true,
        ghi_chu: unitForm.ghi_chu?.trim() || '',
      };
      if (unitForm.stt_uu_tien !== null && unitForm.stt_uu_tien !== undefined && unitForm.stt_uu_tien !== ('' as unknown)) {
        payload.stt_uu_tien = Number(unitForm.stt_uu_tien);
      }

      if (editingUnit) {
        await apiClient.put(`/api/organizations/units/${editingUnit.id}/`, payload);
      } else {
        await apiClient.post('/api/organizations/units/', payload);
      }
      setIsUnitModalOpen(false);
      setToastMessage({ type: 'success', text: t('organizations.saveSuccess') });
      setReloadUnits((v) => v + 1);
      setReloadRegions((v) => v + 1);
    } catch (err) {
      const error = err as ApiError;
      const detail = error?.data?.stt_uu_tien || error?.data?.detail || error?.message || 'Lưu thông tin thất bại.';
      setUnitFormError(Array.isArray(detail) ? detail.join(', ') : String(detail));
    } finally {
      setUnitSubmitting(false);
    }
  };

  // ── Handlers: Xóa Bản Ghi ────────────────────────────────────────────
  const confirmDelete = (type: 'region' | 'unit', id: number, name: string) => {
    setDeleteConfirm({ isOpen: true, type, id, name });
  };

  const handleExecuteDelete = async () => {
    if (!deleteConfirm.id) return;
    setDeleting(true);
    try {
      if (deleteConfirm.type === 'region') {
        await apiClient.delete(`/api/organizations/regions/${deleteConfirm.id}/`);
        setReloadRegions((v) => v + 1);
      } else {
        await apiClient.delete(`/api/organizations/units/${deleteConfirm.id}/`);
        setReloadUnits((v) => v + 1);
        setReloadRegions((v) => v + 1);
      }
      setToastMessage({ type: 'success', text: t('organizations.deleteSuccess') });
      setDeleteConfirm({ isOpen: false, type: 'unit', id: 0, name: '' });
    } catch (err) {
      const error = err as ApiError;
      const errMsg = error?.data?.detail || error?.message || 'Không thể xóa bản ghi.';
      setToastMessage({ type: 'error', text: String(errMsg) });
    } finally {
      setDeleting(false);
    }
  };

  // Filtered regions for tab 2
  const filteredRegions = regions.filter((r) =>
    r.ten.toLowerCase().includes(regionSearch.toLowerCase())
  );

  const totalPages = Math.ceil(totalUnitsCount / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* ── Toast Notification ────────────────────────────────────────── */}
      {toastMessage && (
        <div
          role="alert"
          aria-live="assertive"
          className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-xl border text-sm font-medium transition-all animate-in fade-in slide-in-from-top-4 ${
            toastMessage.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400 backdrop-blur-md'
              : 'bg-rose-500/10 border-rose-500/20 text-rose-600 dark:text-rose-400 backdrop-blur-md'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-current" />
          <span>{toastMessage.text}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-2 hover:opacity-75 focus:outline-none"
            aria-label="Close notification"
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Page Header ──────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            {t('organizations.pageTitle')}
          </h1>
          <p className="text-sm text-text-muted mt-1">
            {t('organizations.pageSubtitle')}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          {activeTab === 'units' ? (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleExportExcel}
                disabled={exporting || units.length === 0}
                className="flex items-center gap-2"
              >
                <span>📊</span>
                <span>{exporting ? t('organizations.exporting') : t('organizations.exportExcel')}</span>
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={openAddUnitModal}
                className="flex items-center gap-2"
              >
                <span>➕</span>
                <span>{t('organizations.addUnit')}</span>
              </Button>
            </>
          ) : (
            <Button
              variant="primary"
              size="sm"
              onClick={openAddRegionModal}
              className="flex items-center gap-2"
            >
              <span>➕</span>
              <span>{t('organizations.addRegion')}</span>
            </Button>
          )}
        </div>
      </div>

      {/* ── Tabs Navigation ──────────────────────────────────────────── */}
      <div className="flex items-center gap-2 border-b border-border">
        <button
          onClick={() => setActiveTab('units')}
          className={`pb-3 px-2 text-sm font-semibold transition-all relative ${
            activeTab === 'units'
              ? 'text-primary'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          <span className="flex items-center gap-2">
            <span>🏢</span>
            <span>{t('organizations.unitsTab')}</span>
            <Badge variant="primary" size="sm">
              {totalUnitsCount}
            </Badge>
          </span>
          {activeTab === 'units' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
          )}
        </button>

        <button
          onClick={() => setActiveTab('regions')}
          className={`pb-3 px-2 text-sm font-semibold transition-all relative ${
            activeTab === 'regions'
              ? 'text-primary'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          <span className="flex items-center gap-2">
            <span>🌐</span>
            <span>{t('organizations.regionsTab')}</span>
            <Badge variant="secondary" size="sm">
              {regions.length}
            </Badge>
          </span>
          {activeTab === 'regions' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
          )}
        </button>
      </div>

      {/* ── TAB 1: ĐƠN VỊ / PHÒNG BAN ─────────────────────────────────── */}
      {activeTab === 'units' && (
        <Card className="p-0 overflow-hidden border border-border shadow-sm">
          {/* Toolbar: Search & Filters */}
          <div className="p-4 border-b border-border bg-surface-elevated/30 flex flex-col md:flex-row gap-3">
            {/* Search Input */}
            <div className="relative flex-1">
              <span className="absolute inset-y-0 left-3 flex items-center text-text-muted text-sm pointer-events-none">
                🔍
              </span>
              <input
                type="text"
                value={unitSearch}
                onChange={(e) => {
                  setUnitSearch(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder={t('organizations.searchUnit')}
                className="w-full pl-9 pr-4 py-2 text-sm rounded-lg bg-surface border border-border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary placeholder:text-text-muted"
              />
            </div>

            {/* Filter by Region */}
            <div className="w-full md:w-64">
              <select
                value={selectedRegionId}
                onChange={(e) => {
                  setSelectedRegionId(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
              >
                <option value="">{t('organizations.allRegions')}</option>
                {regions.map((reg) => (
                  <option key={reg.id} value={reg.id}>
                    {reg.ten}
                  </option>
                ))}
              </select>
            </div>

            {/* Filter by Public Status */}
            <div className="w-full md:w-48">
              <select
                value={selectedPublicFilter}
                onChange={(e) => {
                  setSelectedPublicFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
              >
                <option value="">— {t('organizations.status')} —</option>
                <option value="true">{t('organizations.publicStatus')}</option>
                <option value="false">{t('organizations.privateStatus')}</option>
              </select>
            </div>

            {/* Reset Filter Button */}
            {(unitSearch || selectedRegionId || selectedPublicFilter) && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setUnitSearch('');
                  setSelectedRegionId('');
                  setSelectedPublicFilter('');
                  setCurrentPage(1);
                }}
                className="whitespace-nowrap"
              >
                Xóa bộ lọc
              </Button>
            )}
          </div>

          {/* Units Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-elevated/60 text-text-muted font-medium border-b border-border">
                <tr>
                  <th className="py-3 px-4 w-16 text-center">{t('organizations.priorityOrder')}</th>
                  <th className="py-3 px-4">{t('organizations.unitName')}</th>
                  <th className="py-3 px-4">{t('organizations.parentRegion')}</th>
                  <th className="py-3 px-4">{t('organizations.phone')}</th>
                  <th className="py-3 px-4">{t('organizations.email')}</th>
                  <th className="py-3 px-4 text-center">{t('organizations.status')}</th>
                  <th className="py-3 px-4 text-right">{t('organizations.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-text-muted">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                        <span>Đang tải danh sách đơn vị...</span>
                      </div>
                    </td>
                  </tr>
                ) : units.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-text-muted">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <span className="text-3xl">🏢</span>
                        <p className="font-medium text-text-primary">{t('organizations.emptyUnits')}</p>
                        <p className="text-xs text-text-muted">Thử thay đổi từ khóa hoặc bộ lọc để tìm lại.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  units.map((unit) => (
                    <tr
                      key={unit.id}
                      className={`hover:bg-surface-elevated/40 transition-colors ${
                        !unit.is_public ? 'bg-amber-500/5' : ''
                      }`}
                    >
                      <td className="py-3 px-4 text-center font-semibold text-text-muted">
                        #{unit.stt_uu_tien}
                      </td>
                      <td className="py-3 px-4 font-medium text-text-primary">
                        <div>
                          <span>{unit.ten}</span>
                          {unit.dia_chi && (
                            <p className="text-xs text-text-muted font-normal mt-0.5 line-clamp-1">
                              📍 {unit.dia_chi}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-text-secondary">
                        <Badge variant="secondary" size="sm">
                          {unit.khoi_ten}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-text-secondary">
                        {unit.dien_thoai || '—'}
                      </td>
                      <td className="py-3 px-4 text-text-secondary">
                        {unit.email ? (
                          <a
                            href={`mailto:${unit.email}`}
                            className="text-primary hover:underline"
                          >
                            {unit.email}
                          </a>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {unit.is_public ? (
                          <Badge variant="success" size="sm">
                            {t('organizations.publicStatus')}
                          </Badge>
                        ) : (
                          <Badge variant="warning" size="sm">
                            {t('organizations.privateStatus')}
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => openEditUnitModal(unit)}
                            className="p-1.5 rounded-md hover:bg-surface-elevated text-text-muted hover:text-primary transition-colors"
                            title={t('organizations.editUnit')}
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => confirmDelete('unit', unit.id, unit.ten)}
                            className="p-1.5 rounded-md hover:bg-rose-500/10 text-text-muted hover:text-rose-500 transition-colors"
                            title={t('organizations.deleteUnit')}
                          >
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          {!loading && units.length > 0 && (
            <div className="p-4 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-text-muted">
              <div>
                <span>
                  {t('organizations.recordsCount', { count: String(totalUnitsCount) })} •{' '}
                  {t('organizations.page', { current: String(currentPage), total: String(totalPages) })}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                >
                  ◀ Trước
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => p + 1)}
                >
                  Sau ▶
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* ── TAB 2: KHỐI / KHU VỰC ────────────────────────────────────── */}
      {activeTab === 'regions' && (
        <Card className="p-0 overflow-hidden border border-border shadow-sm">
          {/* Toolbar */}
          <div className="p-4 border-b border-border bg-surface-elevated/30 flex items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <span className="absolute inset-y-0 left-3 flex items-center text-text-muted text-sm pointer-events-none">
                🔍
              </span>
              <input
                type="text"
                value={regionSearch}
                onChange={(e) => setRegionSearch(e.target.value)}
                placeholder={t('organizations.searchRegion')}
                className="w-full pl-9 pr-4 py-2 text-sm rounded-lg bg-surface border border-border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
              />
            </div>
            <span className="text-xs text-text-muted">
              Tổng số: {regions.length} khối / khu vực
            </span>
          </div>

          {/* Regions Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-elevated/60 text-text-muted font-medium border-b border-border">
                <tr>
                  <th className="py-3 px-4 w-20 text-center">ID</th>
                  <th className="py-3 px-4">{t('organizations.regionName')}</th>
                  <th className="py-3 px-4 text-center">{t('organizations.displayOrder')}</th>
                  <th className="py-3 px-4 text-center">{t('organizations.childUnitsCount')}</th>
                  <th className="py-3 px-4 text-right">{t('organizations.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredRegions.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-text-muted">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <span className="text-3xl">🌐</span>
                        <p className="font-medium text-text-primary">{t('organizations.emptyRegions')}</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredRegions.map((reg) => (
                    <tr key={reg.id} className="hover:bg-surface-elevated/40 transition-colors">
                      <td className="py-3 px-4 text-center font-mono text-text-muted">
                        #{reg.id}
                      </td>
                      <td className="py-3 px-4 font-semibold text-text-primary">
                        {reg.ten}
                      </td>
                      <td className="py-3 px-4 text-center text-text-secondary">
                        {reg.thu_tu_hien_thi}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge variant={(reg.don_vi_count || 0) > 0 ? 'info' : 'secondary'} size="sm">
                          {reg.don_vi_count || 0} đơn vị
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => openEditRegionModal(reg)}
                            className="p-1.5 rounded-md hover:bg-surface-elevated text-text-muted hover:text-primary transition-colors"
                            title={t('organizations.editRegion')}
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => confirmDelete('region', reg.id, reg.ten)}
                            className="p-1.5 rounded-md hover:bg-rose-500/10 text-text-muted hover:text-rose-500 transition-colors"
                            title={t('organizations.deleteRegion')}
                          >
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── MODAL: THÊM / SỬA KHỐI / KHU VỰC ──────────────────────────── */}
      {isRegionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface rounded-2xl shadow-2xl border border-border w-full max-w-md overflow-hidden">
            <div className="p-5 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold text-text-primary">
                {editingRegion ? t('organizations.editRegion') : t('organizations.addRegion')}
              </h2>
              <button
                onClick={() => setIsRegionModalOpen(false)}
                className="text-text-muted hover:text-text-primary"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveRegion} className="p-5 space-y-4">
              {regionFormError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs">
                  {regionFormError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                  {t('organizations.regionName')} <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={regionForm.ten}
                  onChange={(e) => setRegionForm({ ...regionForm, ten: e.target.value })}
                  placeholder="Ví dụ: KHU VỰC MIỀN NAM"
                  className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                  {t('organizations.displayOrder')}
                </label>
                <input
                  type="number"
                  min="0"
                  value={regionForm.thu_tu_hien_thi}
                  onChange={(e) => setRegionForm({ ...regionForm, thu_tu_hien_thi: Number(e.target.value) })}
                  className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
                />
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-border">
                <Button
                  variant="outline"
                  type="button"
                  onClick={() => setIsRegionModalOpen(false)}
                >
                  {t('organizations.cancel')}
                </Button>
                <Button
                  variant="primary"
                  type="submit"
                  disabled={regionSubmitting}
                >
                  {regionSubmitting ? t('organizations.saving') : t('organizations.save')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: THÊM / SỬA ĐƠN VỊ / PHÒNG BAN ───────────────────────── */}
      {isUnitModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface rounded-2xl shadow-2xl border border-border w-full max-w-xl max-h-[90vh] overflow-y-auto">
            <div className="p-5 border-b border-border flex items-center justify-between sticky top-0 bg-surface z-10">
              <h2 className="text-lg font-bold text-text-primary">
                {editingUnit ? t('organizations.editUnit') : t('organizations.addUnit')}
              </h2>
              <button
                onClick={() => setIsUnitModalOpen(false)}
                className="text-text-muted hover:text-text-primary"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveUnit} className="p-5 space-y-4">
              {unitFormError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500 text-xs">
                  {unitFormError}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Khối trực thuộc */}
                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                    {t('organizations.parentRegion')} <span className="text-rose-500">*</span>
                  </label>
                  <select
                    required
                    value={unitForm.khoi_id}
                    onChange={(e) => setUnitForm({ ...unitForm, khoi_id: Number(e.target.value) })}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
                  >
                    <option value="">— Chọn Khối / Khu vực —</option>
                    {regions.map((reg) => (
                      <option key={reg.id} value={reg.id}>
                        {reg.ten}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Tên đơn vị */}
                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                    {t('organizations.unitName')} <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={unitForm.ten}
                    onChange={(e) => setUnitForm({ ...unitForm, ten: e.target.value })}
                    placeholder="Ví dụ: Phòng Hành chính Tổng hợp"
                    className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
                  />
                </div>

                {/* STT ưu tiên */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                    {t('organizations.priorityOrder')}
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={unitForm.stt_uu_tien ?? ''}
                    onChange={(e) =>
                      setUnitForm({
                        ...unitForm,
                        stt_uu_tien: e.target.value ? Number(e.target.value) : null,
                      })
                    }
                    placeholder="Tự động (Max + 1)"
                    className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary placeholder:text-text-muted"
                  />
                  <p className="text-[11px] text-text-muted mt-1">
                    {t('organizations.priorityOrderHelp')}
                  </p>
                </div>

                {/* Điện thoại */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                    {t('organizations.phone')}
                  </label>
                  <input
                    type="text"
                    value={unitForm.dien_thoai}
                    onChange={(e) => setUnitForm({ ...unitForm, dien_thoai: e.target.value })}
                    placeholder="Ví dụ: 0912345678"
                    className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
                  />
                </div>

                {/* Email */}
                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                    {t('organizations.email')}
                  </label>
                  <input
                    type="email"
                    value={unitForm.email}
                    onChange={(e) => setUnitForm({ ...unitForm, email: e.target.value })}
                    placeholder="donvi@baolong.vn"
                    className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
                  />
                </div>

                {/* Địa chỉ */}
                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                    {t('organizations.address')}
                  </label>
                  <input
                    type="text"
                    value={unitForm.dia_chi}
                    onChange={(e) => setUnitForm({ ...unitForm, dia_chi: e.target.value })}
                    placeholder="Số nhà, đường, quận/huyện, tỉnh/thành..."
                    className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
                  />
                </div>

                {/* Ghi chú */}
                <div className="md:col-span-2">
                  <label className="block text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">
                    {t('organizations.notes')}
                  </label>
                  <textarea
                    rows={2}
                    value={unitForm.ghi_chu}
                    onChange={(e) => setUnitForm({ ...unitForm, ghi_chu: e.target.value })}
                    placeholder="Ghi chú thêm về đơn vị..."
                    className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border focus:ring-2 focus:ring-primary/20 focus:border-primary text-text-primary"
                  />
                </div>

                {/* Checkbox isPublic */}
                <div className="md:col-span-2 flex items-start gap-3 p-3 rounded-lg bg-surface-elevated/40 border border-border">
                  <input
                    type="checkbox"
                    id="is_public_cb"
                    checked={unitForm.is_public}
                    onChange={(e) => setUnitForm({ ...unitForm, is_public: e.target.checked })}
                    className="mt-1 w-4 h-4 rounded text-primary focus:ring-primary border-border"
                  />
                  <label htmlFor="is_public_cb" className="text-sm cursor-pointer select-none">
                    <span className="font-semibold text-text-primary">{t('organizations.isPublic')}</span>
                    <p className="text-xs text-text-muted mt-0.5">{t('organizations.isPublicDesc')}</p>
                  </label>
                </div>
              </div>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-border">
                <Button
                  variant="outline"
                  type="button"
                  onClick={() => setIsUnitModalOpen(false)}
                >
                  {t('organizations.cancel')}
                </Button>
                <Button
                  variant="primary"
                  type="submit"
                  disabled={unitSubmitting}
                >
                  {unitSubmitting ? t('organizations.saving') : t('organizations.save')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: XÁC NHẬN XÓA ────────────────────────────────────────── */}
      {deleteConfirm.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in">
          <div className="bg-surface rounded-2xl shadow-2xl border border-border w-full max-w-md overflow-hidden">
            <div className="p-5 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-bold text-rose-500 flex items-center gap-2">
                <span>⚠️</span>
                <span>{t('organizations.deleteConfirmTitle')}</span>
              </h2>
              <button
                onClick={() => setDeleteConfirm({ ...deleteConfirm, isOpen: false })}
                className="text-text-muted hover:text-text-primary"
              >
                ✕
              </button>
            </div>

            <div className="p-5 space-y-3">
              <p className="text-sm text-text-primary">
                {deleteConfirm.type === 'region'
                  ? t('organizations.deleteRegionConfirm', { name: deleteConfirm.name })
                  : t('organizations.deleteUnitConfirm', { name: deleteConfirm.name })}
              </p>
              <p className="text-xs text-text-muted">
                {t('organizations.deleteWarning')}
              </p>

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-border">
                <Button
                  variant="outline"
                  type="button"
                  onClick={() => setDeleteConfirm({ ...deleteConfirm, isOpen: false })}
                >
                  {t('organizations.cancel')}
                </Button>
                <Button
                  variant="danger"
                  onClick={handleExecuteDelete}
                  disabled={deleting}
                >
                  {deleting ? t('organizations.deleting') : t('organizations.deleteBtn')}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
