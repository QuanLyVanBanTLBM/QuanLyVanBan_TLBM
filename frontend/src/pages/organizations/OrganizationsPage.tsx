import React, { useState, useEffect } from 'react';
import { useTranslation } from '@i18n/translate';
import { ApiError, apiClient, downloadBlob } from '@lib/apiClient';
import { usePermissions } from '@lib/permissions';
import { Region, Unit, PaginatedResponse, RegionFormData, UnitFormData } from '@app-types/organization';
import { Button } from '@components/common/Button';
import { Badge } from '@components/common/Badge';
import { Select } from '@components/common/Select';
import { RegionUnitSelect } from './components/RegionUnitSelect';
import { RegionModal } from './components/RegionModal';
import { UnitModal } from './components/UnitModal';
import { DeleteConfirmModal } from './components/DeleteConfirmModal';
import './OrganizationsPage.mobile.css';

export default function OrganizationsPage() {
  const { t, currentLang } = useTranslation();
  const { can } = usePermissions();
  // Khối và Đơn vị dùng chung bộ quyền *_donvi của DDL; backend vẫn kiểm quyền thật ở mọi API.
  const showRowActions = can('change_donvi') || can('delete_donvi');
  // Bảng Khối có thêm nút xuất danh bạ theo từng Khối nên người chỉ có export_donvi cũng cần cột Thao tác
  const showRegionRowActions = showRowActions || can('export_donvi');

  // Tab chuyển đổi: 'regions' (Khối, cấp 1, mở đầu tiên) hoặc 'units' (Đơn vị, cấp 2)
  const [activeTab, setActiveTab] = useState<'units' | 'regions'>('regions');

  // Dữ liệu Khối & Đơn vị
  const [dropdownRegions, setDropdownRegions] = useState<Region[]>([]);
  const [regions, setRegions] = useState<Region[]>([]);
  const [regionsTotal, setRegionsTotal] = useState<number>(0);
  // Khối đang mở ở tab Khối (bấm vào Khối để hiện các Đơn vị trực thuộc)
  const [expandedRegionIds, setExpandedRegionIds] = useState<Set<number>>(new Set());
  const toggleInSet = (set: Set<number>, id: number) => {
    const next = new Set(set);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  };
  const [units, setUnits] = useState<Unit[]>([]);
  const [unitsTotal, setUnitsTotal] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  // Bộ lọc & Tìm kiếm
  const [selectedRegionId, setSelectedRegionId] = useState<string>('');
  const [selectedUnitId, setSelectedUnitId] = useState<string>('');
  const [allUnits, setAllUnits] = useState<Unit[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [regionSearchQuery, setRegionSearchQuery] = useState<string>('');

  // Trạng thái tải & thông báo
  const [isLoading, setIsLoading] = useState<boolean>(true);
  // Tab Khối mở đầu tiên: chờ cả danh sách Khối và danh sách Đơn vị để không hiện "Chưa có dữ liệu" hay "0 đơn vị" khi đang tải
  const [isRegionsLoading, setIsRegionsLoading] = useState<boolean>(true);
  const [isAllUnitsLoading, setIsAllUnitsLoading] = useState<boolean>(true);
  const [isExporting, setIsExporting] = useState<boolean>(false);
  // Chọn nhiều Khối và Đơn vị để xuất chung một file; giữ nguyên khi đổi tab hoặc trang
  const [pickedRegionIds, setPickedRegionIds] = useState<Set<number>>(new Set());
  const [pickedUnitIds, setPickedUnitIds] = useState<Set<number>>(new Set());
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

  // Thiếu quyền xem (403) khác lỗi mạng: báo đúng nguyên nhân một lần trong khung thay vì "kiểm tra kết nối" và số 0.
  const [accessDenied, setAccessDenied] = useState<boolean>(false);
  const handleLoadError = (err: unknown) => {
    if (err instanceof ApiError && err.status === 403) {
      setAccessDenied(true);
      return;
    }
    showToast('organizations.messages.fetchError', true);
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

  // Toàn bộ Đơn vị (cấp 2) người dùng được xem: danh sách Đơn vị trực thuộc ở tab Khối,
  // dropdown Khối hiện theo hover, dropdown Đơn vị lọc theo Khối đang chọn
  const loadAllUnits = async () => {
    try {
      const data = await apiClient<Unit[]>('/api/organizations/units/?all=true');
      const list = Array.isArray(data) ? data : [];
      setAllUnits(list);
      setSelectedUnitId((cur) => (list.some((u) => String(u.id) === cur) ? cur : ''));
    } catch {
      // Lỗi được xử lý ngầm
    }
  };

  useEffect(() => {
    let ignore = false;
    apiClient<Unit[]>('/api/organizations/units/?all=true')
      .then((data) => {
        if (!ignore) setAllUnits(Array.isArray(data) ? data : []);
      })
      .catch((err: unknown) => {
        // Tab Khối mở đầu tiên dựa vào danh sách này để đếm và liệt kê Đơn vị nên phải báo lỗi
        if (!ignore) handleLoadError(err);
      })
      .finally(() => {
        if (!ignore) setIsAllUnitsLoading(false);
      });
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
      .catch((err: unknown) => {
        if (!ignore) handleLoadError(err);
      })
      .finally(() => {
        if (!ignore) setIsRegionsLoading(false);
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
      .catch((err: unknown) => {
        if (!ignore) {
          handleLoadError(err);
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
    } catch (err: unknown) {
      handleLoadError(err);
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
      await loadAllUnits();
    } catch (err: unknown) {
      handleLoadError(err);
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

  // Xử lý Xuất file Excel: scope là phạm vi của file (Khối, Đơn vị, từ khóa), rỗng nghĩa là không lọc
  const exportDirectory = async (scope: {
    regionId: string;
    unitId: string;
    search: string;
    regionIds?: number[];
    unitIds?: number[];
  }) => {
    setIsExporting(true);
    try {
      const params = new URLSearchParams();
      params.append('lang', currentLang);
      if (scope.regionId) params.append('region_id', scope.regionId);
      // Đã chọn một Đơn vị thì file chỉ gồm Đơn vị đó, khớp với bảng đang hiển thị
      if (scope.unitId) params.append('unit_id', scope.unitId);
      if (scope.search) params.append('search', scope.search);
      // Danh sách Khối và Đơn vị đã tích: một file gồm hợp của hai danh sách
      if (scope.regionIds?.length) params.append('region_ids', scope.regionIds.join(','));
      if (scope.unitIds?.length) params.append('unit_ids', scope.unitIds.join(','));

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

  // Tab Đơn vị: xuất theo bộ lọc đang chọn trên bảng
  const handleExportExcel = () =>
    exportDirectory({ regionId: selectedRegionId, unitId: selectedUnitId, search: searchQuery.trim() });
  // Tab Khối: nút trên thanh công cụ xuất toàn bộ Khối, nút trên từng dòng xuất đúng Khối đó
  const handleExportAll = () => exportDirectory({ regionId: '', unitId: '', search: '' });
  const handleExportRegion = (regionId: number) =>
    exportDirectory({ regionId: String(regionId), unitId: '', search: '' });
  // Xuất các Khối và Đơn vị đã tích vào một file
  const pickedCount = pickedRegionIds.size + pickedUnitIds.size;
  const handleExportPicked = () =>
    exportDirectory({
      regionId: '',
      unitId: '',
      search: '',
      regionIds: Array.from(pickedRegionIds),
      unitIds: Array.from(pickedUnitIds),
    });
  const clearPicked = () => {
    setPickedRegionIds(new Set());
    setPickedUnitIds(new Set());
  };
  const canExport = can('export_donvi');
  const allRegionsPicked = regions.length > 0 && regions.every((r) => pickedRegionIds.has(r.id));
  const toggleAllRegions = () =>
    setPickedRegionIds(allRegionsPicked ? new Set() : new Set(regions.map((r) => r.id)));

  // Chọn đơn vị cấp 2 cụ thể thì bảng chỉ hiển thị đơn vị đó
  const dropdownUnits = selectedRegionId ? allUnits.filter((u) => String(u.khoi) === selectedRegionId) : [];
  const keyword = searchQuery.trim().toLowerCase();
  const pickedUnit = selectedUnitId ? dropdownUnits.find((u) => String(u.id) === selectedUnitId) : undefined;
  // Ô tìm kiếm vẫn có hiệu lực khi đã chọn đơn vị (cùng các trường với API: tên, điện thoại, email, địa chỉ)
  const pickedMatches =
    !!pickedUnit &&
    (!keyword ||
      [pickedUnit.ten, pickedUnit.dien_thoai, pickedUnit.email, pickedUnit.dia_chi].some((v) => (v ?? '').toLowerCase().includes(keyword)));
  const shownUnits = pickedUnit ? (pickedMatches ? [pickedUnit] : []) : units;
  const shownTotal = pickedUnit ? shownUnits.length : unitsTotal;
  const totalPages = Math.ceil(shownTotal / pageSize) || 1;
  const allShownUnitsPicked = shownUnits.length > 0 && shownUnits.every((u) => pickedUnitIds.has(u.id));
  const toggleAllShownUnits = () =>
    setPickedUnitIds((s) => {
      const next = new Set(s);
      shownUnits.forEach((u) => (allShownUnitsPicked ? next.delete(u.id) : next.add(u.id)));
      return next;
    });

  return (
    <div className="space-y-6 pb-24 md:pb-0">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-xl shadow-2xl flex items-center gap-2.5 text-sm font-semibold animate-fade-in ${
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
        <div className="flex flex-wrap items-center gap-3">
          {canExport && pickedCount > 0 && (
            <>
              <Button variant="primary" icon="fa-file-excel" onClick={handleExportPicked} isLoading={isExporting}>
                {t('organizations.actions.exportSelected', { count: String(pickedCount) })}
              </Button>
              <Button variant="secondary" onClick={clearPicked} disabled={isExporting}>
                {t('organizations.actions.clearSelection')}
              </Button>
            </>
          )}
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
            <>
              {can('export_donvi') && (
                <Button
                  variant="outline"
                  icon="fa-file-excel"
                  onClick={handleExportAll}
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
                    setEditingRegion(null);
                    setIsRegionModalOpen(true);
                  }}
                >
                  {t('organizations.region.addBtn')}
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-border gap-2">
        <button
          type="button"
          onClick={() => setActiveTab('regions')}
          className={`flex-1 sm:flex-none justify-center px-2 sm:px-5 py-3 font-bold text-sm text-center leading-tight border-b-2 transition-all cursor-pointer flex items-center gap-2 select-none ${
            activeTab === 'regions'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-main'
          }`}
        >
          <i className="fa-solid fa-layer-group hidden sm:inline" />
          {t('organizations.tabs.regions')}
          {!accessDenied && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-surface-elevated text-secondary border border-border">
              {regionsTotal}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('units')}
          className={`flex-1 sm:flex-none justify-center px-2 sm:px-5 py-3 font-bold text-sm text-center leading-tight border-b-2 transition-all cursor-pointer flex items-center gap-2 select-none ${
            activeTab === 'units'
              ? 'border-primary text-primary'
              : 'border-transparent text-secondary hover:text-main'
          }`}
        >
          <i className="fa-solid fa-building hidden sm:inline" />
          {t('organizations.tabs.units')}
          {!accessDenied && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-surface-elevated text-secondary border border-border">
              {unitsTotal}
            </span>
          )}
        </button>
      </div>

      {accessDenied && (
        <div role="alert" className="bg-surface border border-border rounded-xl py-12 text-center text-danger">
          <i className="fa-solid fa-circle-exclamation text-3xl mb-2 block" />
          {t('organizations.messages.permissionDenied')}
        </div>
      )}

      {/* ── NỘI DUNG TAB 2: ĐƠN VỊ / PHÒNG BAN ── */}
      {!accessDenied && activeTab === 'units' && (
        <div className="space-y-4">
          {/* Thanh công cụ lọc & tìm kiếm */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {/* Lọc theo Khối */}
            <div>
              <RegionUnitSelect
                regions={dropdownRegions}
                units={allUnits}
                regionId={selectedRegionId}
                unitId={selectedUnitId}
                placeholder={t('organizations.actions.filterRegionAll')}
                allLabel={t('organizations.actions.filterRegionAll')}
                unitsLabel={t('organizations.actions.filterUnitsOfRegion')}
                onSelectRegion={(val) => {
                  setSelectedRegionId(val);
                  setSelectedUnitId('');
                  setCurrentPage(1);
                }}
                onSelectUnit={(regionVal, unitVal) => {
                  setSelectedRegionId(regionVal);
                  setSelectedUnitId(unitVal);
                  setCurrentPage(1);
                }}
              />
            </div>

            {/* Lọc theo Đơn vị cấp 2, phụ thuộc Khối đã chọn */}
            <div>
              <Select
                value={selectedUnitId}
                onChange={(val) => {
                  setSelectedUnitId(val);
                  setCurrentPage(1);
                }}
                placeholder={
                  selectedRegionId
                    ? t('organizations.actions.filterUnitAll')
                    : t('organizations.actions.filterUnitSelectRegionFirst')
                }
                leftIcon="fa-building"
                clearable
                disabled={!selectedRegionId}
                searchable={dropdownUnits.length > 7}
                options={[
                  { value: '', label: t('organizations.actions.filterUnitAll') },
                  ...dropdownUnits.map((u) => ({ value: String(u.id), label: u.ten })),
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
              <table className="units-table w-full text-left text-sm border-collapse">
                <thead className="units-table__head bg-surface-elevated text-secondary text-xs uppercase font-bold border-b border-border">
                  <tr>
                    <th className="px-4 py-3 text-center w-16">
                      <label className="inline-flex items-center gap-1.5 cursor-pointer">
                        {canExport && (
                          <input
                            type="checkbox"
                            aria-label={t('organizations.actions.selectAllUnits')}
                            checked={allShownUnitsPicked}
                            onChange={toggleAllShownUnits}
                          />
                        )}
                        {t('organizations.table.priority')}
                      </label>
                    </th>
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
                <tbody className="units-table__body divide-y divide-border">
                  {isLoading ? (
                    <tr className="units-table__row--message">
                      <td colSpan={showRowActions ? 7 : 6} className="text-center py-12 text-secondary">
                        <i className="fa-solid fa-spinner fa-spin text-2xl text-primary mb-2 block" />
                        {t('organizations.table.loading')}
                      </td>
                    </tr>
                  ) : shownUnits.length === 0 ? (
                    <tr className="units-table__row--message">
                      <td colSpan={showRowActions ? 7 : 6} className="text-center py-12 text-secondary">
                        <i className="fa-solid fa-folder-open text-3xl text-muted mb-2 block" />
                        {t('organizations.table.empty')}
                      </td>
                    </tr>
                  ) : (
                    shownUnits.map((unit) => {
                      // Quy tắc spec: nếu is_public = false -> đổi màu hiển thị cho admin
                      const isInternal = !unit.is_public;
                      return (
                        <tr
                          key={unit.id}
                          className={`units-table__row transition-colors hover:bg-surface-hover ${
                            isInternal ? 'bg-warning-subtle/20 border-l-4 border-l-warning' : ''
                          }`}
                        >
                          <td className="units-table__cell units-table__cell--order px-4 py-3 text-center font-bold text-main">
                            <label className="inline-flex items-center gap-2 cursor-pointer">
                              {canExport && (
                                <input
                                  type="checkbox"
                                  aria-label={t('organizations.actions.selectUnit', { name: unit.ten })}
                                  checked={pickedUnitIds.has(unit.id)}
                                  onChange={() => setPickedUnitIds((s) => toggleInSet(s, unit.id))}
                                />
                              )}
                              {unit.stt_uu_tien}
                            </label>
                          </td>
                          <td className="units-table__cell units-table__cell--name px-4 py-3 font-semibold text-main min-w-[14rem]">
                            <div>{unit.ten}</div>
                            {unit.dia_chi && (
                              <div className="text-xs text-secondary font-normal flex items-center gap-1 mt-0.5">
                                <i className="fa-solid fa-location-dot text-muted text-[0.65rem]" />
                                {unit.dia_chi}
                              </div>
                            )}
                          </td>
                          <td
                            data-label={t('organizations.table.parentRegion')}
                            className="units-table__cell units-table__cell--region px-4 py-3 text-secondary min-w-[10rem]"
                          >
                            {unit.khoi_ten || t('organizations.table.emptyValue')}
                          </td>
                          <td
                            data-label={t('organizations.table.phone')}
                            className="units-table__cell units-table__cell--phone px-4 py-3 text-secondary font-mono text-xs whitespace-nowrap"
                          >
                            {unit.dien_thoai || t('organizations.table.emptyValue')}
                          </td>
                          <td
                            data-label={t('organizations.table.email')}
                            className="units-table__cell units-table__cell--email px-4 py-3 text-secondary text-xs"
                          >
                            {unit.email || t('organizations.table.emptyValue')}
                          </td>
                          <td className="units-table__cell units-table__cell--status px-4 py-3 text-center whitespace-nowrap">
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
                            <td className="units-table__cell units-table__cell--actions px-4 py-3 text-center">
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
                    to: String(Math.min(currentPage * pageSize, shownTotal)),
                    total: String(shownTotal),
                  })}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={currentPage <= 1}
                    aria-label={t('organizations.table.prevPage')}
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
                    aria-label={t('organizations.table.nextPage')}
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

      {/* ── NỘI DUNG TAB 1: KHỐI / KHU VỰC ── */}
      {!accessDenied && activeTab === 'regions' && (
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
              placeholder={t('organizations.actions.searchRegionPlaceholder')}
              className="w-full pl-10 pr-3.5 py-2 text-sm bg-surface border border-border rounded-lg text-main placeholder-muted focus:outline-none focus:border-primary"
            />
          </div>

          {/* Bảng danh sách Khối */}
          <div className="bg-surface border border-border rounded-xl shadow-sm overflow-hidden">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="bg-surface-elevated text-secondary text-xs uppercase font-bold border-b border-border">
                <tr>
                  <th className="hidden sm:table-cell px-4 py-3 text-center w-16">{t('organizations.table.id')}</th>
                  <th className="px-2 sm:px-4 py-3 text-center w-16 sm:w-32">
                    <label className="inline-flex items-center gap-1.5 cursor-pointer">
                      {canExport && (
                        <input
                          type="checkbox"
                          aria-label={t('organizations.actions.selectAllRegions')}
                          checked={allRegionsPicked}
                          onChange={toggleAllRegions}
                        />
                      )}
                      {/* Màn hình hẹp dùng nhãn ngắn để tiêu đề cột không xuống nhiều dòng */}
                      <span className="sm:hidden">{t('organizations.table.priority')}</span>
                      <span className="hidden sm:inline">{t('organizations.table.displayOrder')}</span>
                    </label>
                  </th>
                  <th className="px-3 sm:px-4 py-3">{t('organizations.table.regionName')}</th>
                  <th className="px-2 sm:px-4 py-3 text-center">{t('organizations.table.unitsCount')}</th>
                  {showRegionRowActions && (
                    <th className="px-2 sm:px-4 py-3 text-center w-20 sm:w-28">{t('organizations.table.actions')}</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {isRegionsLoading || isAllUnitsLoading ? (
                  <tr>
                    <td colSpan={showRegionRowActions ? 5 : 4} className="text-center py-12 text-secondary">
                      <i className="fa-solid fa-spinner fa-spin text-2xl text-primary mb-2 block" />
                      {t('organizations.table.loading')}
                    </td>
                  </tr>
                ) : regions.length === 0 ? (
                  <tr>
                    <td colSpan={showRegionRowActions ? 5 : 4} className="text-center py-12 text-secondary">
                      <i className="fa-solid fa-folder-open text-3xl text-muted mb-2 block" />
                      {t('organizations.table.empty')}
                    </td>
                  </tr>
                ) : (
                  regions.map((region) => {
                    // Bấm vào Khối thì hiện các Đơn vị trực thuộc. Chỉ tính những Đơn vị người dùng được xem
                    // (don_vi_count của API đếm cả Đơn vị nội bộ mà người không phải admin không thấy)
                    const children = allUnits.filter((u) => u.khoi === region.id);
                    const open = children.length > 0 && expandedRegionIds.has(region.id);
                    const toggle = () => setExpandedRegionIds((s) => toggleInSet(s, region.id));
                    return (
                      <React.Fragment key={region.id}>
                        <tr
                          onClick={children.length > 0 ? toggle : undefined}
                          className={`transition-colors hover:bg-surface-hover ${children.length > 0 ? 'cursor-pointer' : ''} ${
                            open ? 'bg-primary-subtle' : ''
                          }`}
                        >
                          <td className="hidden sm:table-cell px-4 py-3 text-center font-mono text-xs text-muted">{region.id}</td>
                          <td className="px-2 sm:px-4 py-3 text-center font-mono text-xs text-secondary" onClick={(e) => e.stopPropagation()}>
                            <label className="inline-flex items-center gap-1.5 cursor-pointer">
                              {canExport && (
                                <input
                                  type="checkbox"
                                  aria-label={t('organizations.actions.selectRegion', { name: region.ten })}
                                  checked={pickedRegionIds.has(region.id)}
                                  onChange={() => setPickedRegionIds((s) => toggleInSet(s, region.id))}
                                />
                              )}
                              {region.thu_tu_hien_thi ?? 0}
                            </label>
                          </td>
                          <td className="px-3 sm:px-4 py-3 font-bold text-main">
                            {children.length > 0 ? (
                              <button
                                type="button"
                                aria-expanded={open}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggle();
                                }}
                                className="flex items-center gap-2 text-left font-bold text-main hover:text-primary transition-colors cursor-pointer"
                              >
                                <i
                                  className={`fa-solid fa-chevron-right text-[11px] text-muted transition-transform ${
                                    open ? 'rotate-90' : ''
                                  }`}
                                />
                                {region.ten}
                              </button>
                            ) : (
                              <span className="flex items-center gap-2">
                                <i className="fa-solid fa-chevron-right text-[11px] invisible" />
                                {region.ten}
                              </span>
                            )}
                          </td>
                          <td className="px-2 sm:px-4 py-3 text-center whitespace-nowrap">
                            <Badge variant="info" size="sm">
                              {t('organizations.table.unitCountLabel', { count: String(children.length) })}
                            </Badge>
                          </td>
                          {showRegionRowActions && (
                            <td className="px-2 sm:px-4 py-3 text-center" onClick={(e) => e.stopPropagation()}>
                              <div className="flex items-center justify-center gap-1">
                                {can('export_donvi') && (
                                  <button
                                    type="button"
                                    onClick={() => handleExportRegion(region.id)}
                                    disabled={isExporting}
                                    title={t('organizations.actions.exportRegion')}
                                    aria-label={t('organizations.actions.exportRegion')}
                                    className="p-1.5 text-secondary hover:text-success rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                                  >
                                    <i className="fa-solid fa-file-excel" />
                                  </button>
                                )}
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
                        {/* Đơn vị trực thuộc: mỗi Đơn vị một dòng, thẳng cột với Khối (số thứ tự đánh lại từ 1 trong Khối, tên, trạng thái).
                            Vạch màu ở mép trái và đường kẻ nét đứt để tách nhóm Đơn vị khỏi các dòng Khối */}
                        {open &&
                          children.map((unit, index) => (
                            <tr key={`unit-${unit.id}`} data-unit-row className="bg-surface-hover border-dashed">
                              <td className="hidden sm:table-cell px-4 py-3 shadow-[inset_4px_0_0_var(--color-primary)]" />
                              <td className="px-2 sm:px-4 py-3 text-center font-mono text-xs text-secondary shadow-[inset_4px_0_0_var(--color-primary)] sm:shadow-none">
                                <label className="inline-flex items-center gap-1.5 cursor-pointer">
                                  {canExport && (
                                    <input
                                      type="checkbox"
                                      aria-label={t('organizations.actions.selectUnit', { name: unit.ten })}
                                      checked={pickedUnitIds.has(unit.id)}
                                      onChange={() => setPickedUnitIds((s) => toggleInSet(s, unit.id))}
                                    />
                                  )}
                                  {index + 1}
                                </label>
                              </td>
                              <td className="px-3 sm:px-4 py-3">
                                <div className="flex items-start gap-2">
                                  <i className="fa-solid fa-chevron-right text-[11px] invisible" />
                                  <div className="min-w-0">
                                    <div className="font-semibold text-main">{unit.ten}</div>
                                    {unit.dien_thoai && (
                                      <div className="text-secondary font-mono mt-0.5 flex items-center gap-1.5">
                                        <i className="fa-solid fa-phone text-muted text-[0.65rem]" />
                                        {unit.dien_thoai}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </td>
                              <td className="px-2 sm:px-4 py-3 text-center whitespace-nowrap">
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
                              {showRegionRowActions && <td className="px-2 sm:px-4 py-3" />}
                            </tr>
                          ))}
                      </React.Fragment>
                    );
                  })
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
                    aria-label={t('organizations.table.prevPage')}
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
                    aria-label={t('organizations.table.nextPage')}
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
        key={`${editingRegion?.id ?? 'new-region'}-${isRegionModalOpen ? 'open' : 'closed'}`}
        isOpen={isRegionModalOpen}
        onClose={() => setIsRegionModalOpen(false)}
        onSubmit={handleSaveRegion}
        initialData={editingRegion}
        isLoading={isSubmittingRegion}
      />

      {/* Modal Đơn vị */}
      <UnitModal
        key={`${editingUnit?.id ?? 'new-unit'}-${isUnitModalOpen ? 'open' : 'closed'}`}
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
