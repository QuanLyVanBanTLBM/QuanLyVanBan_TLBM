import React, { useState, useEffect } from 'react';
import { useTranslation } from '@i18n/translate';
import { ApiError, apiClient, downloadBlob } from '@lib/apiClient';
import { usePermissions } from '@lib/permissions';
import { Region, Unit, PaginatedResponse, RegionFormData, UnitFormData } from '@app-types/organization';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';
import { Select } from '@components/common/Select';
import { RegionModal } from './components/RegionModal';
import { UnitModal } from './components/UnitModal';
import { DeleteConfirmModal } from './components/DeleteConfirmModal';

export default function OrganizationsPage() {
  const { t, currentLang } = useTranslation();
  const { can } = usePermissions();
  // Khối và Đơn vị dùng chung bộ quyền *_donvi của DDL; backend vẫn kiểm quyền thật ở mọi API.
  const showRowActions = can('change_donvi') || can('delete_donvi');

  // Tab chuyển đổi: 'units' (Đơn vị) hoặc 'regions' (Khối)
  const [activeTab, setActiveTab] = useState<'units' | 'regions'>('units');

  // Dữ liệu Khối & Đơn vị
  const [dropdownRegions, setDropdownRegions] = useState<Region[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionsTotal, setRegionsTotal] = useState<number>(0);
  const [units, setUnits] = useState<Unit[]>([]);
  const [unitsTotal, setUnitsTotal] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  // Bộ lọc & Tìm kiếm
  const [selectedRegionId, setSelectedRegionId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [regionSearchQuery, setRegionSearchQuery] = useState<string>('');

  // Trạng thái tải & thông báo
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<{ textKey: string; isError?: boolean } | null>(null);

  // Quản lý Modal Khối
  const [isRegionModalOpen, setIsRegionModalOpen] = useState<boolean>(false);
  const [editingRegion, setEditingRegion] = useState<Region | null>(null);
  const [deletingRegion, setDeletingRegion] = useState<Region | null>(null);
  const [regionDeleteErrorKey, setRegionDeleteErrorKey] = useState<string | null>(null);
  const [isSubmittingRegion, setIsSubmittingRegion] = useState<boolean>(false);
  const [isDeletingRegion, setIsDeletingRegion] = useState<boolean>(false);

  // Quản lý Modal Đơn vị
  const [isUnitModalOpen, setIsUnitModalOpen] = useState<boolean>(false);
  const [editingUnit, setEditingUnit] = useState<Unit | null>(null);
  const [deletingUnit, setDeletingUnit] = useState<Unit | null>(null);
  const [unitDeleteErrorKey, setUnitDeleteErrorKey] = useState<string | null>(null);
  const [isSubmittingUnit, setIsSubmittingUnit] = useState<boolean>(false);
  const [isDeletingUnit, setIsDeletingUnit] = useState<boolean>(false);

  // Hiển thị thông báo tạm thời
  const showToast = (textKey: string, isError = false) => {
    setToastMessage({ textKey, isError });
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Phân trang cho Tab Khối
  const [regionPage, setRegionPage] = useState<number>(1);
  const regionPageSize = 10;

  // 1. Tải danh sách toàn bộ Khối cho các Dropdown/Select
  const refreshDropdownRegions = async () => {
    try {
      const data = await apiClient<Region[]>('/api/organizations/regions/?all=true');
      setDropdownRegions(data || []);
    } catch {
      // Lỗi được xử lý ngầm
    }
  };

  useEffect(() => {
    let ignore = false;
    apiClient<Region[]>('/api/organizations/regions/?all=true')
      .then((data) => {
        if (!ignore) setDropdownRegions(data || []);
      })
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, []);

  // 2. Tải danh sách Bảng Khối có phân trang và tìm kiếm phía Server
  useEffect(() => {
    let ignore = false;
    const params = new URLSearchParams();
    params.append('page', regionPage.toString());
    if (regionSearchQuery.trim()) params.append('search', regionSearchQuery.trim());

    apiClient<PaginatedResponse<Region> | Region[]>(`/api/organizations/regions/?${params.toString()}`)
      .then((res) => {
        if (!ignore) {
          if (Array.isArray(res)) {
            setRegions(res);
            setRegionsTotal(res.length);
          } else {
            setRegions(res.results || []);
            setRegionsTotal(res.count || 0);
          }
        }
      })
      .catch(() => {
        if (!ignore) {
          setToastMessage({ textKey: 'organizations.messages.fetchError', isError: true });
        }
      });

    return () => {
      ignore = true;
    };
  }, [regionPage, regionSearchQuery]);

  // Tải danh sách Đơn vị khi thay đổi trang, khối hoặc từ khóa tìm kiếm
  useEffect(() => {
    let ignore = false;
    const params = new URLSearchParams();
    params.append('page', currentPage.toString());
    if (selectedRegionId) params.append('region_id', selectedRegionId);
    if (searchQuery.trim()) params.append('search', searchQuery.trim());

    apiClient<PaginatedResponse<Unit>>(`/api/organizations/units/?${params.toString()}`)
      .then((res) => {
        if (!ignore) {
          setUnits(res.results || []);
          setUnitsTotal(res.count || 0);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (!ignore) {
          setToastMessage({ textKey: 'organizations.messages.fetchError', isError: true });
          setIsLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [currentPage, selectedRegionId, searchQuery]);

  // Làm mới danh sách Khối sau khi thêm/sửa/xóa
  const refreshRegions = async () => {
    await refreshDropdownRegions();
    try {
      const params = new URLSearchParams();
      params.append('page', regionPage.toString());
      if (regionSearchQuery.trim()) params.append('search', regionSearchQuery.trim());
      const res = await apiClient<PaginatedResponse<Region> | Region[]>(`/api/organizations/regions/?${params.toString()}`);
      if (Array.isArray(res)) {
        setRegions(res);
        setRegionsTotal(res.length);
      } else {
        setRegions(res.results || []);
        setRegionsTotal(res.count || 0);
      }
    } catch {
      showToast('organizations.messages.fetchError', true);
    }
  };

  // Làm mới danh sách Đơn vị sau khi thêm/sửa/xóa
  const refreshUnits = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('page', currentPage.toString());
      if (selectedRegionId) params.append('region_id', selectedRegionId);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());

      const res = await apiClient<PaginatedResponse<Unit>>(`/api/organizations/units/?${params.toString()}`);
      setUnits(res.results || []);
      setUnitsTotal(res.count || 0);
    } catch {
      showToast('organizations.messages.fetchError', true);
    } finally {
      setIsLoading(false);
    }
  };

  const totalRegionPages = Math.ceil(regionsTotal / regionPageSize) || 1;

  // Xử lý Khối/Khu vực (Thêm / Sửa / Xóa)
  const handleSaveRegion = async (formData: RegionFormData) => {
    setIsSubmittingRegion(true);
    try {
      if (editingRegion) {
        await apiClient.put(`/api/organizations/regions/${editingRegion.id}/`, formData);
        showToast('organizations.messages.updateSuccess');
      } else {
        await apiClient.post('/api/organizations/regions/', formData);
        showToast('organizations.messages.createSuccess');
      }
      await refreshRegions();
    } finally {
      setIsSubmittingRegion(false);
    }
  };

  const handleConfirmDeleteRegion = async () => {
    if (!deletingRegion) return;
    setIsDeletingRegion(true);
    try {
      await apiClient.delete(`/api/organizations/regions/${deletingRegion.id}/`);
      setDeletingRegion(null);
      setRegionDeleteErrorKey(null);
      showToast('organizations.messages.deleteSuccess');
      await refreshRegions();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'data' in err) {
        const apiErr = (err as { data?: { detail?: string; key?: string } }).data;
        setRegionDeleteErrorKey(apiErr?.key || apiErr?.detail || 'organizations.messages.regionHasUnits');
      } else {
        setRegionDeleteErrorKey('organizations.messages.regionHasUnits');
      }
    } finally {
      setIsDeletingRegion(false);
    }
  };

  // Xử lý Đơn vị/Phòng ban (Thêm / Sửa / Xóa)
  const handleSaveUnit = async (formData: UnitFormData) => {
    setIsSubmittingUnit(true);
    try {
      if (editingUnit) {
        await apiClient.put(`/api/organizations/units/${editingUnit.id}/`, formData);
        showToast('organizations.messages.updateSuccess');
      } else {
        await apiClient.post('/api/organizations/units/', formData);
        showToast('organizations.messages.createSuccess');
      }
      await refreshUnits();
    } finally {
      setIsSubmittingUnit(false);
    }
  };

  const handleConfirmDeleteUnit = async () => {
    if (!deletingUnit) return;
    setIsDeletingUnit(true);
    try {
      await apiClient.delete(`/api/organizations/units/${deletingUnit.id}/`);
      setDeletingUnit(null);
      setUnitDeleteErrorKey(null);
      showToast('organizations.messages.deleteSuccess');
      await refreshUnits();
    } catch (err: unknown) {
      // Giữ hộp thoại mở và nêu đúng lý do server trả về (đơn vị còn CBNV, đang được dùng, thiếu quyền...).
      const candidate = err instanceof ApiError ? err.data.key ?? err.data.detail : null;
      setUnitDeleteErrorKey(
        typeof candidate === 'string' && candidate.includes('.') ? candidate : 'organizations.messages.deleteError',
      );
    } finally {
      setIsDeletingUnit(false);
    }
  };

  // Xử lý Xuất file Excel
  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      const params = new URLSearchParams();
      params.append('lang', currentLang);
      if (selectedRegionId) params.append('region_id', selectedRegionId);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());

      await downloadBlob(
        `/api/organizations/units/export/?${params.toString()}`,
        t('organizations.exportFilename')
      );
      showToast('organizations.messages.exportSuccess');
    } catch (err: unknown) {
      const candidate = err instanceof ApiError ? err.data.key ?? err.data.detail : null;
      const errorKey = typeof candidate === 'string' && candidate.includes('.')
        ? candidate
        : 'organizations.messages.exportError';
      showToast(errorKey, true);
    } finally {
      setIsExporting(false);
    }
  };

  const totalPages = Math.ceil(unitsTotal / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center gap-2.5 text-sm font-semibold animate-fade-in ${
            toastMessage.isError
              ? 'bg-danger text-white border border-danger-border'
              : 'bg-success text-white border border-success-border'
          }`}
        >
          <i className={`fa-solid ${toastMessage.isError ? 'fa-circle-xmark' : 'fa-circle-check'}`} />
          {t(toastMessage.textKey)}
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-surface p-6 rounded-2xl border border-border">
        <div>
          <h1 className="text-2xl font-bold text-main flex items-center gap-2.5">
            <i className="fa-solid fa-sitemap text-primary" />
            {t('organizations.title')}
          </h1>
          <p className="text-secondary text-sm mt-1">{t('organizations.desc')}</p>
        </div>

        {/* Nút hành động thêm mới theo Tab */}
        <div className="flex items-center gap-3">
          {activeTab === 'units' ? (
            <>
              {can('export_donvi') && (
                <Button
                  variant="outline"
                  icon="fa-file-excel"
                  onClick={handleExportExcel}
                  isLoading={isExporting}
                >
                  {isExporting ? t('organizations.actions.exporting') : t('organizations.actions.exportExcel')}
                </Button>
              )}
              {can('add_donvi') && (
                <Button
                  variant="primary"
                  icon="fa-plus"
                  onClick={() => {
                    setEditingUnit(null);
                    setIsUnitModalOpen(true);
                  }}
                >
                  {t('organizations.unit.addBtn')}
                </Button>
              )}
            </>
          ) : (
            can('add_donvi') && (
              <Button
                variant="primary"
                icon="fa-plus"
                onClick={() => {
                  setEditingRegion(null);
                  setIsRegionModalOpen(true);
                }}
              >
                {t('organizations.region.addBtn')}
              </Button>
            )
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-border gap-2">
        <button
          type="button"
          onClick={() => setActiveTab('units')}
          className={`px-5 py-3 font-bold text-sm border-b-2 transition-all cursor-pointer flex items-center gap-2 select-none ${
            activeTab === 'units'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-main'
          }`}
        >
          <i className="fa-solid fa-building" />
          {t('organizations.tabs.units')}
          <span className="text-xs px-2 py-0.5 rounded-full bg-surface-elevated text-secondary border border-border">
            {unitsTotal}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('regions')}
          className={`px-5 py-3 font-bold text-sm border-b-2 transition-all cursor-pointer flex items-center gap-2 select-none ${
            activeTab === 'regions'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-main'
          }`}
        >
          <i className="fa-solid fa-layer-group" />
          {t('organizations.tabs.regions')}
          <span className="text-xs px-2 py-0.5 rounded-full bg-surface-elevated text-secondary border border-border">
            {regionsTotal}
          </span>
        </button>
      </div>

      {/* ── NỘI DUNG TAB 1: ĐƠN VỊ / PHÒNG BAN ── */}
      {activeTab === 'units' && (
        <div className="space-y-4">
          {/* Thanh công cụ lọc & tìm kiếm */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Lọc theo Khối */}
            <div>
              <Select
                value={selectedRegionId}
                onChange={(val) => {
                  setSelectedRegionId(val);
                  setCurrentPage(1);
                }}
                placeholder={t('organizations.actions.filterRegionAll')}
                leftIcon="fa-layer-group"
                clearable
                searchable={dropdownRegions.length > 7}
                options={[
                  { value: '', label: t('organizations.actions.filterRegionAll') },
                  ...dropdownRegions.map((reg) => ({
                    value: String(reg.id),
                    label: reg.ten,
                  })),
                ]}
              />
            </div>

            {/* Tìm kiếm */}
            <div className="md:col-span-2 relative">
              <i className="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-muted text-sm" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder={t('organizations.actions.searchPlaceholder')}
                className="w-full pl-10 pr-3.5 py-2 text-sm bg-surface border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          {/* Bảng danh sách Đơn vị */}
          <div className="bg-surface border border-border rounded-xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead className="bg-surface-elevated text-secondary text-xs uppercase font-bold border-b border-border">
                  <tr>
                    <th className="px-4 py-3 text-center w-16">{t('organizations.table.priority')}</th>
                    <th className="px-4 py-3">{t('organizations.table.unitName')}</th>
                    <th className="px-4 py-3">{t('organizations.table.parentRegion')}</th>
                    <th className="px-4 py-3">{t('organizations.table.phone')}</th>
                    <th className="px-4 py-3">{t('organizations.table.email')}</th>
                    <th className="px-4 py-3 text-center">{t('organizations.table.status')}</th>
                    {showRowActions && (
                      <th className="px-4 py-3 text-center w-28">{t('organizations.table.actions')}</th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {isLoading ? (
                    <tr>
                      <td colSpan={showRowActions ? 7 : 6} className="text-center py-12 text-secondary">
                        <i className="fa-solid fa-spinner fa-spin text-2xl text-primary mb-2 block" />
                        {t('organizations.table.loading')}
                      </td>
                    </tr>
                  ) : units.length === 0 ? (
                    <tr>
                      <td colSpan={showRowActions ? 7 : 6} className="text-center py-12 text-secondary">
                        <i className="fa-solid fa-folder-open text-3xl text-muted mb-2 block" />
                        {t('organizations.table.empty')}
                      </td>
                    </tr>
                  ) : (
                    units.map((unit) => {
                      // Quy tắc spec: nếu is_public = false -> đổi màu hiển thị cho admin
                      const isInternal = !unit.is_public;
                      return (
                        <tr
                          key={unit.id}
                          className={`transition-colors hover:bg-surface-hover ${
                            isInternal ? 'bg-warning-subtle/20 border-l-4 border-l-warning' : ''
                          }`}
                        >
                          <td className="px-4 py-3 text-center font-bold text-main">{unit.stt_uu_tien}</td>
                          <td className="px-4 py-3 font-semibold text-main">
                            <div>{unit.ten}</div>
                            {unit.dia_chi && (
                              <div className="text-xs text-secondary font-normal flex items-center gap-1 mt-0.5">
                                <i className="fa-solid fa-location-dot text-muted text-[0.65rem]" />
                                {unit.dia_chi}
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3 text-secondary">{unit.khoi_ten || t('organizations.table.emptyValue')}</td>
                          <td className="px-4 py-3 text-secondary font-mono text-xs">
                            {unit.dien_thoai || t('organizations.table.emptyValue')}
                          </td>
                          <td className="px-4 py-3 text-secondary text-xs">
                            {unit.email || t('organizations.table.emptyValue')}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {unit.is_public ? (
                              <Badge variant="success" size="sm">
                                {t('organizations.table.public')}
                              </Badge>
                            ) : (
                              <Badge variant="warning" size="sm">
                                {t('organizations.table.internal')}
                              </Badge>
                            )}
                          </td>
                          {showRowActions && (
                            <td className="px-4 py-3 text-center">
                              <div className="flex items-center justify-center gap-1">
                                {can('change_donvi') && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setEditingUnit(unit);
                                      setIsUnitModalOpen(true);
                                    }}
                                    title={t('organizations.actions.edit')}
                                    className="p-1.5 text-secondary hover:text-primary rounded-lg transition-colors cursor-pointer"
                                  >
                                    <i className="fa-solid fa-pen-to-square" />
                                  </button>
                                )}
                                {can('delete_donvi') && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setDeletingUnit(unit);
                                      setUnitDeleteErrorKey(null);
                                    }}
                                    title={t('organizations.actions.delete')}
                                    className="p-1.5 text-secondary hover:text-danger rounded-lg transition-colors cursor-pointer"
                                  >
                                    <i className="fa-solid fa-trash-can" />
                                  </button>
                                )}
                              </div>
                            </td>
                          )}
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Phân trang */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-6 py-3 border-t border-border bg-surface-elevated text-sm">
                <span className="text-secondary text-xs">
                  {t('organizations.table.paginationInfo', {
                    from: String((currentPage - 1) * pageSize + 1),
                    to: String(Math.min(currentPage * pageSize, unitsTotal)),
                    total: String(unitsTotal),
                  })}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={currentPage <= 1}
                    onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                  >
                    <i className="fa-solid fa-chevron-left" />
                  </Button>
                  <span className="px-3 py-1 font-bold text-xs text-main">
                    {currentPage} / {totalPages}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={currentPage >= totalPages}
                    onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  >
                    <i className="fa-solid fa-chevron-right" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── NỘI DUNG TAB 2: KHỐI / KHU VỰC ── */}
      {activeTab === 'regions' && (
        <div className="space-y-4">
          {/* Tìm kiếm Khối */}
          <div className="relative max-w-md">
            <i className="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-muted text-sm" />
            <input
              type="text"
              value={regionSearchQuery}
              onChange={(e) => {
                setRegionSearchQuery(e.target.value);
                setRegionPage(1);
              }}
              placeholder={t('organizations.region.namePlaceholder')}
              className="w-full pl-10 pr-3.5 py-2 text-sm bg-surface border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary"
            />
          </div>

          {/* Bảng danh sách Khối */}
          <div className="bg-surface border border-border rounded-xl shadow-sm overflow-hidden">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="bg-surface-elevated text-secondary text-xs uppercase font-bold border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-center w-16">{t('organizations.table.id')}</th>
                  <th className="px-4 py-3">{t('organizations.table.regionName')}</th>
                  <th className="px-4 py-3 text-center">{t('organizations.table.unitsCount')}</th>
                  {showRowActions && (
                    <th className="px-4 py-3 text-center w-28">{t('organizations.table.actions')}</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {regions.length === 0 ? (
                  <tr>
                    <td colSpan={showRowActions ? 4 : 3} className="text-center py-12 text-secondary">
                      <i className="fa-solid fa-folder-open text-3xl text-muted mb-2 block" />
                      {t('organizations.table.empty')}
                    </td>
                  </tr>
                ) : (
                  regions.map((region) => (
                    <tr key={region.id} className="transition-colors hover:bg-surface-hover">
                      <td className="px-4 py-3 text-center font-mono text-xs text-muted">{region.id}</td>
                      <td className="px-4 py-3 font-bold text-main">{region.ten}</td>
                      <td className="px-4 py-3 text-center">
                        <Badge variant="info" size="sm">
                          {t('organizations.table.unitCountLabel', { count: String(region.don_vi_count ?? 0) })}
                        </Badge>
                      </td>
                      {showRowActions && (
                        <td className="px-4 py-3 text-center">
                          <div className="flex items-center justify-center gap-1">
                            {can('change_donvi') && (
                              <button
                                type="button"
                                onClick={() => {
                                  setEditingRegion(region);
                                  setIsRegionModalOpen(true);
                                }}
                                title={t('organizations.actions.edit')}
                                className="p-1.5 text-secondary hover:text-primary rounded-lg transition-colors cursor-pointer"
                              >
                                <i className="fa-solid fa-pen-to-square" />
                              </button>
                            )}
                            {can('delete_donvi') && (
                              <button
                                type="button"
                                onClick={() => {
                                  setDeletingRegion(region);
                                  setRegionDeleteErrorKey(null);
                                }}
                                title={t('organizations.actions.delete')}
                                className="p-1.5 text-secondary hover:text-danger rounded-lg transition-colors cursor-pointer"
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

            {/* Phân trang Khối */}
            {totalRegionPages > 1 && (
              <div className="flex items-center justify-between px-6 py-3 border-t border-border bg-surface-elevated text-sm">
                <span className="text-secondary text-xs">
                  {t('organizations.table.paginationInfo', {
                    from: String(regionsTotal === 0 ? 0 : (regionPage - 1) * regionPageSize + 1),
                    to: String(Math.min(regionPage * regionPageSize, regionsTotal)),
                    total: String(regionsTotal),
                  })}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={regionPage <= 1}
                    onClick={() => setRegionPage((p) => Math.max(p - 1, 1))}
                  >
                    <i className="fa-solid fa-chevron-left" />
                  </Button>
                  <span className="px-3 py-1 font-bold text-xs text-main">
                    {regionPage} / {totalRegionPages}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={regionPage >= totalRegionPages}
                    onClick={() => setRegionPage((p) => Math.min(p + 1, totalRegionPages))}
                  >
                    <i className="fa-solid fa-chevron-right" />
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── CÁC MODALS ── */}
      {/* Modal Khối */}
      <RegionModal
        key={editingRegion?.id ?? (isRegionModalOpen ? 'open-new-region' : 'closed-region')}
        isOpen={isRegionModalOpen}
        onClose={() => setIsRegionModalOpen(false)}
        onSubmit={handleSaveRegion}
        initialData={editingRegion}
        isLoading={isSubmittingRegion}
      />

      {/* Modal Đơn vị */}
      <UnitModal
        key={editingUnit?.id ?? (isUnitModalOpen ? 'open-new-unit' : 'closed-unit')}
        isOpen={isUnitModalOpen}
        onClose={() => setIsUnitModalOpen(false)}
        onSubmit={handleSaveUnit}
        initialData={editingUnit}
        regions={dropdownRegions}
        isLoading={isSubmittingUnit}
      />

      {/* Xác nhận xóa Khối */}
      <DeleteConfirmModal
        isOpen={!!deletingRegion}
        onClose={() => {
          setDeletingRegion(null);
          setRegionDeleteErrorKey(null);
        }}
        onConfirm={handleConfirmDeleteRegion}
        titleKey="organizations.region.deleteConfirmTitle"
        descKey="organizations.region.deleteConfirmDesc"
        name={deletingRegion?.ten}
        errorKey={regionDeleteErrorKey}
        isLoading={isDeletingRegion}
      />

      {/* Xác nhận xóa Đơn vị */}
      <DeleteConfirmModal
        isOpen={!!deletingUnit}
        onClose={() => {
          setDeletingUnit(null);
          setUnitDeleteErrorKey(null);
        }}
        onConfirm={handleConfirmDeleteUnit}
        titleKey="organizations.unit.deleteConfirmTitle"
        descKey="organizations.unit.deleteConfirmDesc"
        name={deletingUnit?.ten}
        errorKey={unitDeleteErrorKey}
        isLoading={isDeletingUnit}
      />
    </div>
  );
}
