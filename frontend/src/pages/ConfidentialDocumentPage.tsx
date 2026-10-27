import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DocumentItem, DocumentFilterParams, PaginatedResponse } from '@app-types/document';
import FilterBar from '@components/documents/FilterBar';
import DocumentTable from '@components/documents/DocumentTable';
import DocumentDetailModal from '@components/documents/DocumentDetailModal';
import DocumentViewersModal from '@components/documents/DocumentViewersModal';
import DocumentFormModal from '@components/documents/DocumentFormModal';
import ImportExcelModal from '@components/documents/ImportExcelModal';
import AlertModal from '@components/common/AlertModal';
import ConfirmModal from '@components/common/ConfirmModal';
import { Button } from '@components/common/Button';
import apiClient from '@lib/apiClient';
import { useTranslation } from '@i18n/translate';

export const ConfidentialDocumentPage: React.FC = () => {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const loaiVanBanParam = searchParams.get('loai_van_ban');
  const phamViParam = searchParams.get('pham_vi');

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Bộ lọc cho Văn bản Mật (mặc định pham_vi=HAN_CHE)
  const [filters, setFilters] = useState<DocumentFilterParams>({
    q: '',
    nam: '',
    tu_ngay: '',
    den_ngay: '',
    hieu_luc: '',
    page: 1,
    page_size: 10,
    loai: 'MAT',
    loai_van_ban: loaiVanBanParam || undefined,
    pham_vi: phamViParam || undefined,
  });

  // Hàm đồng bộ trạng thái bộ lọc lên URL query parameters
  const syncFiltersToUrl = useCallback((currentFilters: DocumentFilterParams) => {
    const nextParams = new URLSearchParams();
    if (currentFilters.q) nextParams.set('q', currentFilters.q.trim());
    if (currentFilters.nam) nextParams.set('nam', String(currentFilters.nam));
    if (currentFilters.tu_ngay) nextParams.set('tu_ngay', currentFilters.tu_ngay);
    if (currentFilters.den_ngay) nextParams.set('den_ngay', currentFilters.den_ngay);
    if (currentFilters.hieu_luc) nextParams.set('hieu_luc', currentFilters.hieu_luc);
    if (currentFilters.loai_van_ban) nextParams.set('loai_van_ban', String(currentFilters.loai_van_ban));
    if (currentFilters.ho_so) nextParams.set('ho_so', currentFilters.ho_so);
    if (currentFilters.pham_vi) nextParams.set('pham_vi', String(currentFilters.pham_vi));
    if (currentFilters.page && currentFilters.page > 1) nextParams.set('page', String(currentFilters.page));

    // Bảo toàn các params trạng thái modal (detail, viewers, action, edit)
    ['detail', 'viewers', 'action', 'edit'].forEach((key) => {
      const val = searchParams.get(key);
      if (val) nextParams.set(key, val);
    });

    setSearchParams(nextParams, { replace: true });
  }, [searchParams, setSearchParams]);

  // Helper đồng bộ query params của Modal lên URL mà không làm mất các filter
  const updateModalParam = useCallback((paramsToUpdate: Record<string, string | null>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      Object.entries(paramsToUpdate).forEach(([key, val]) => {
        if (val) {
          next.set(key, val);
        } else {
          next.delete(key);
        }
      });
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const handleFilterChange = (newFilters: DocumentFilterParams) => {
    setFilters(newFilters);
    syncFiltersToUrl(newFilters);
  };

  useEffect(() => {
    let cancelled = false;
    Promise.resolve().then(() => {
      if (!cancelled) {
        setFilters(prev => {
          const nextLoaiVanBan = searchParams.get('loai_van_ban') || undefined;
          const nextPhamVi = searchParams.get('pham_vi') || undefined;
          const nextHoSo = searchParams.get('ho_so') || undefined;
          if (prev.loai_van_ban === nextLoaiVanBan && prev.pham_vi === nextPhamVi && prev.ho_so === nextHoSo) {
            return prev;
          }
          return {
            ...prev,
            loai_van_ban: nextLoaiVanBan,
            pham_vi: nextPhamVi,
            ho_so: nextHoSo,
            page: 1,
          };
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  const handleClearLoaiVanBan = () => {
    const next = { ...filters, loai_van_ban: undefined, page: 1 };
    setFilters(next);
    syncFiltersToUrl(next);
  };

  const handleClearPhamVi = () => {
    const next = { ...filters, pham_vi: undefined, page: 1 };
    setFilters(next);
    syncFiltersToUrl(next);
  };

  // Quản lý modal xem chi tiết & modal danh sách người đọc (Audit Log)
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState<boolean>(false);
  const [isViewersOpen, setIsViewersOpen] = useState<boolean>(false);

  // Quản lý modal Thêm/Sửa & Import Excel
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [editingDoc, setEditingDoc] = useState<DocumentItem | null>(null);
  const [isImportOpen, setIsImportOpen] = useState<boolean>(false);
  const [alertMsg, setAlertMsg] = useState<string>('');
  const [isAlertOpen, setIsAlertOpen] = useState<boolean>(false);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [stats, setStats] = useState<{
    total: number;
    active: number;
    partial: number;
    replaced: number;
  }>({
    total: 0,
    active: 0,
    partial: 0,
    replaced: 0,
  });

  // Lấy danh sách các năm thực tế có văn bản mật trong CSDL
  const fetchYears = useCallback(async () => {
    try {
      const res = await apiClient.get<number[]>('/api/documents/years/?loai=MAT');
      if (Array.isArray(res) && res.length > 0) {
        setAvailableYears(res);
      }
    } catch {
      // Giữ nguyên danh sách hiện tại nếu lỗi
    }
  }, []);

  // Lấy thống kê số lượng văn bản mật theo trạng thái
  const fetchStats = useCallback(async () => {
    try {
      const extraQuery = `${filters.loai_van_ban ? `&loai_van_ban=${encodeURIComponent(String(filters.loai_van_ban))}` : ''}${filters.pham_vi ? `&pham_vi=${encodeURIComponent(String(filters.pham_vi))}` : ''}`;
      const res = await apiClient.get<PaginatedResponse<DocumentItem>>(`/api/documents/?loai=MAT&page_size=1000${extraQuery}`);
      const items = res && Array.isArray(res.results) ? res.results : (Array.isArray(res) ? (res as DocumentItem[]) : []);
      const active = items.filter((d) => d.hieu_luc === 'CON_HIEU_LUC').length;
      const partial = items.filter((d) => d.hieu_luc === 'CON_HIEU_LUC_1_PHAN').length;
      const replaced = items.filter((d) => d.hieu_luc === 'HET_VA_THAY_THE').length;
      setStats({
        total: items.length,
        active,
        partial,
        replaced,
      });
    } catch {
      // Bỏ qua lỗi thống kê khi chạy offline
    }
  }, [filters.loai_van_ban, filters.pham_vi]);

  useEffect(() => {
    let ignore = false;
    (async () => {
      await Promise.resolve();
      if (ignore) return;
      fetchYears();
      fetchStats();
    })();
    return () => {
      ignore = true;
    };
  }, [fetchYears, fetchStats]);

  // Lấy danh sách văn bản mật từ API Backend
  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('loai', 'MAT');
      if (filters.page) params.append('page', String(filters.page));
      if (filters.page_size) params.append('page_size', String(filters.page_size));
      if (filters.q) params.append('q', filters.q.trim());
      if (filters.nam) params.append('nam', String(filters.nam));
      if (filters.tu_ngay) params.append('tu_ngay', filters.tu_ngay);
      if (filters.den_ngay) params.append('den_ngay', filters.den_ngay);
      if (filters.hieu_luc) params.append('hieu_luc', filters.hieu_luc);
      if (filters.loai_van_ban) params.append('loai_van_ban', String(filters.loai_van_ban));
      if (filters.ho_so) params.append('ho_so', filters.ho_so.trim());
      if (filters.pham_vi) params.append('pham_vi', String(filters.pham_vi));

      const endpoint = `/api/documents/?${params.toString()}`;
      const response = await apiClient.get<PaginatedResponse<DocumentItem>>(endpoint);

      if (response && Array.isArray(response.results)) {
        setDocuments(response.results);
        setTotalCount(response.count || 0);
        if (response.results.length > 0) {
          const docYears = Array.from(new Set(response.results.map((document) => document.nam).filter(Boolean))) as number[];
          setAvailableYears(prev => {
            const merged = Array.from(new Set([...prev, ...docYears])).sort((a, b) => b - a);
            return merged;
          });
        }
      } else if (Array.isArray(response)) {
        setDocuments(response as unknown as DocumentItem[]);
        setTotalCount((response as unknown as DocumentItem[]).length);
      } else {
        setDocuments([]);
        setTotalCount(0);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Không thể tải danh sách văn bản mật.';
      setError(errMsg);
      setDocuments([]);
      setTotalCount(0);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    let cancelled = false;
    Promise.resolve().then(() => {
      if (!cancelled) void fetchDocuments();
    });
    return () => {
      cancelled = true;
    };
  }, [fetchDocuments]);

  const handlePageChange = (newPage: number) => {
    const next = { ...filters, page: newPage };
    setFilters(next);
    syncFiltersToUrl(next);
  };

  const handlePageSizeChange = (newPageSize: number) => {
    const next = { ...filters, page_size: newPageSize, page: 1 };
    setFilters(next);
    syncFiltersToUrl(next);
  };

  const handleResetFilters = () => {
    const defaultFilters: DocumentFilterParams = {
      q: '',
      nam: '',
      tu_ngay: '',
      den_ngay: '',
      hieu_luc: '',
      page: 1,
      page_size: 10,
      loai: 'MAT',
      loai_van_ban: undefined,
      ho_so: undefined,
      pham_vi: undefined,
    };
    setFilters(defaultFilters);
    syncFiltersToUrl(defaultFilters);
  };

  // Mở modal xem chi tiết và đồng bộ URL query param `detail`
  const handleViewDetail = (id: number) => {
    setSelectedDocId(id);
    setIsDetailOpen(true);
    updateModalParam({ detail: String(id), viewers: null, action: null, edit: null });
  };

  const handleCloseDetail = () => {
    setIsDetailOpen(false);
    setSelectedDocId(null);
    updateModalParam({ detail: null });
  };

  // Mở modal xem danh sách người đã đọc và đồng bộ URL query param `viewers`
  const handleViewHistory = (id: number) => {
    setSelectedDocId(id);
    setIsViewersOpen(true);
    updateModalParam({ viewers: String(id), detail: null, action: null, edit: null });
  };

  const handleCloseHistory = () => {
    setIsViewersOpen(false);
    setSelectedDocId(null);
    updateModalParam({ viewers: null });
  };

  // Mở modal thêm mới và đồng bộ URL query param `action=create`
  const handleOpenCreate = () => {
    setEditingDoc(null);
    setIsFormOpen(true);
    updateModalParam({ action: 'create', detail: null, viewers: null, edit: null });
  };

  // Mở modal sửa và đồng bộ URL query param `edit=id`
  const handleOpenEdit = (doc: DocumentItem) => {
    setEditingDoc(doc);
    setIsFormOpen(true);
    updateModalParam({ edit: String(doc.id), detail: null, viewers: null, action: null });
  };

  const handleCloseForm = () => {
    setIsFormOpen(false);
    setEditingDoc(null);
    updateModalParam({ action: null, edit: null });
  };

  // Lắng nghe URL query params để tự động mở modal tương ứng khi truy cập link trực tiếp
  useEffect(() => {
    let cancelled = false;
    Promise.resolve().then(() => {
      if (!cancelled) {
        const detailParam = searchParams.get('detail');
        const viewersParam = searchParams.get('viewers');
        const actionParam = searchParams.get('action');
        const editParam = searchParams.get('edit');

        if (detailParam && !isNaN(Number(detailParam))) {
          setSelectedDocId(Number(detailParam));
          setIsDetailOpen(true);
        } else {
          setIsDetailOpen(false);
        }

        if (viewersParam && !isNaN(Number(viewersParam))) {
          setSelectedDocId(Number(viewersParam));
          setIsViewersOpen(true);
        } else {
          setIsViewersOpen(false);
        }

        if (actionParam === 'create') {
          setEditingDoc(null);
          setIsFormOpen(true);
        } else if (editParam && !isNaN(Number(editParam))) {
          const editId = Number(editParam);
          const found = documents.find((d) => d.id === editId);
          if (found) {
            setEditingDoc(found);
            setIsFormOpen(true);
          } else {
            apiClient.get<DocumentItem>(`/api/documents/${editId}/?loai=MAT`)
              .then(res => {
                if (!cancelled && res) {
                  setEditingDoc(res);
                  setIsFormOpen(true);
                }
              })
              .catch(() => undefined);
          }
        } else if (!actionParam && !editParam) {
          setIsFormOpen(false);
        }
      }
    });
    return () => {
      cancelled = true;
    };
  }, [searchParams, documents]);

  // Xóa văn bản mật (Quản trị viên)
  const [pendingDelete, setPendingDelete] = useState<{ id: number; soHieu: string } | null>(null);

  const doDelete = async () => {
    if (!pendingDelete) return;
    try {
      await apiClient.delete(`/api/documents/${pendingDelete.id}/?loai=MAT`);
      setPendingDelete(null);
      setAlertMsg(`Đã xóa văn bản mật "${pendingDelete.soHieu}" thành công.`);
      setIsAlertOpen(true);
      fetchDocuments();
      fetchYears();
      fetchStats();
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Xóa văn bản mật thất bại.';
      setPendingDelete(null);
      setAlertMsg(`Lỗi xóa văn bản mật: ${errMsg}`);
      setIsAlertOpen(true);
    }
  };

  // Xuất file Excel văn bản mật
  const handleExportExcel = async () => {
    try {
      const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token') || '';
      const params = new URLSearchParams();
      params.append('loai', 'MAT');
      if (filters.q) params.append('q', filters.q.trim());
      if (filters.nam) params.append('nam', String(filters.nam));
      if (filters.tu_ngay) params.append('tu_ngay', filters.tu_ngay);
      if (filters.den_ngay) params.append('den_ngay', filters.den_ngay);
      if (filters.hieu_luc) params.append('hieu_luc', filters.hieu_luc);
      if (filters.loai_van_ban) params.append('loai_van_ban', String(filters.loai_van_ban));
      if (filters.pham_vi) params.append('pham_vi', String(filters.pham_vi));

      const res = await fetch(`/api/documents/export/?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Quá trình xuất Excel văn bản mật thất bại. Vui lòng kiểm tra lại kết nối!');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Danh_Sach_Van_Ban_Mat_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error: unknown) {
      setAlertMsg(error instanceof Error ? error.message : String(error));
      setIsAlertOpen(true);
    }
  };

  const countActive = stats.active + stats.partial;

  return (
    <div className="w-full p-2 sm:p-4 md:p-6 animate-in fade-in duration-150">
      {/* 1. Header Trang & Thao tác */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <span className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center font-bold text-sm">
              <i className="fa-solid fa-shield-halved text-base" />
            </span>
            <h1 className="text-xl md:text-2xl font-bold text-main m-0">{t('pages.documents_confidential.title') || 'Quản Lý Văn Bản Mật'}</h1>
            <span className="px-2 py-0.5 rounded-md text-xs font-bold uppercase bg-rose-500/15 text-rose-600 border border-rose-500/25">
              {t('documents_ui.table.restrictedBadge') || 'Bảo mật'}
            </span>
          </div>
          <p className="text-xs md:text-sm text-secondary m-0">
            {t('pages.documents_confidential.desc') || 'Lưu trữ, tra cứu và phân quyền văn bản mật theo các quy định an toàn thông tin & kiểm toán truy cập.'}
          </p>
        </div>

        {/* Các nút hành động chính (Thêm mới, Nhập Excel, Xuất Excel, Làm mới) */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            type="button"
            variant="primary"
            size="sm"
            icon="fa-plus"
            onClick={handleOpenCreate}
            title={t('documents_incoming_page.addBtn') || 'Thêm văn bản mật mới'}
          >
            {t('documents_incoming_page.addBtn') || 'Thêm mới'}
          </Button>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon="fa-file-excel"
            onClick={() => setIsImportOpen(true)}
            title={t('documents_ui.actions.importExcelTitle') || 'Nhập danh sách văn bản mật từ tệp Excel'}
          >
            {t('documents_ui.actions.importExcel') || 'Import Excel'}
          </Button>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon="fa-file-export"
            onClick={handleExportExcel}
            title={t('documents_ui.actions.exportExcelTitle') || 'Xuất dữ liệu văn bản mật ra file Excel'}
          >
            {t('documents_ui.actions.exportExcel') || 'Xuất Excel'}
          </Button>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon="fa-rotate"
            onClick={() => {
              fetchDocuments();
              fetchStats();
            }}
            isLoading={isLoading}
            title={t('documents_ui.actions.refreshTitle') || 'Làm mới danh sách'}
          >
            {t('documents_ui.actions.refresh') || 'Làm mới'}
          </Button>
        </div>
      </div>

      {/* 2. Thẻ Cảnh Báo An Toàn & Bảo Mật */}
      <div className="bg-rose-500/5 border border-rose-500/20 rounded-2xl p-4 sm:p-4.5 mb-5 shadow-2xs flex items-start gap-3.5">
        <div className="w-10 h-10 rounded-xl bg-rose-500/15 text-rose-600 dark:text-rose-400 flex items-center justify-center text-lg shrink-0 mt-0.5">
          <i className="fa-solid fa-lock" />
        </div>
        <div className="flex-1 text-xs">
          <h4 className="font-bold text-rose-700 dark:text-rose-300 text-sm mb-1 m-0">
            Nguyên tắc bảo mật văn bản nội bộ
          </h4>
          <p className="text-secondary m-0 leading-relaxed">
            Văn bản mật thuộc phạm vi lưu hành <strong>Hạn chế</strong>. Chỉ người tạo, lãnh đạo có thẩm quyền và cán bộ nhận được chỉ định mới có quyền xem thông tin và tệp đính kèm. Tuyệt đối không xóa văn bản mật khỏi hệ thống; mọi thao tác đọc/tải tệp đều được ghi vào nhật ký kiểm toán.
          </p>
        </div>
      </div>

      {/* 3. Thẻ Thống Kê Tổng Hợp */}
      <div className="bg-surface border border-border-subtle rounded-2xl p-4 sm:p-5 mb-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-rose-500/10 text-rose-600 flex items-center justify-center text-xl shrink-0 shadow-2xs">
              <i className="fa-solid fa-shield-halved" />
            </div>
            <div>
              <span className="text-sm text-muted block mb-0.5 font-medium">{t('documents_ui.topCard.totalConfidential') || 'Tổng số văn bản mật'}</span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-bold text-main">{countActive}</span>
                <span className="text-sm text-muted font-medium">{t('documents_ui.topCard.activeConfidentialDocs') || 'văn bản mật còn hiệu lực'}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center">
            <button
              type="button"
              onClick={() => {
                const next: DocumentFilterParams = {
                  ...filters,
                  hieu_luc: filters.hieu_luc === 'HIEU_LUC' ? '' : 'HIEU_LUC',
                  page: 1,
                };
                setFilters(next);
                syncFiltersToUrl(next);
              }}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                filters.hieu_luc === 'HIEU_LUC'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-500/25 ring-2 ring-emerald-500/40'
                  : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/25 hover:bg-emerald-500/20'
              }`}
              title={t('documents_ui.topCard.activeFilterTitle') || 'Lọc danh sách theo văn bản còn hiệu lực'}
            >
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shadow-sm shadow-emerald-500/50" />
              <span>{t('documents_ui.topCard.activeBtn') || 'Còn hiệu lực'}</span>
              <span
                className={`ml-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  filters.hieu_luc === 'HIEU_LUC'
                    ? 'bg-white/20 text-white'
                    : 'bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 font-mono'
                }`}
              >
                {countActive}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* 4. Chỉ báo lọc Loại văn bản từ URL */}
      {filters.loai_van_ban && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 mb-4 bg-primary/10 border border-primary/20 rounded-xl text-xs text-primary shadow-2xs">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-filter text-primary" />
            <span>
              {t('documents_ui.scopeTabs.loaiVanBanFilterNotice') || 'Đang lọc danh sách theo Loại văn bản (từ phân hệ Hồ sơ):'} <strong>#{filters.loai_van_ban}</strong>
            </span>
          </div>
          <button
            type="button"
            onClick={handleClearLoaiVanBan}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface hover:bg-surface-elevated text-secondary hover:text-main text-xs border border-border-subtle transition-all cursor-pointer shadow-2xs"
            title={t('documents_ui.scopeTabs.clearLoaiVanBanTitle') || 'Xóa bộ lọc loại văn bản'}
          >
            <i className="fa-solid fa-xmark text-danger" />
            <span>{t('documents_ui.scopeTabs.clearFilter') || 'Bỏ lọc'}</span>
          </button>
        </div>
      )}

      {/* 4.1. Chỉ báo lọc Phạm vi */}
      {filters.pham_vi && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 mb-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-800 dark:text-amber-300 shadow-2xs">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-shield-halved text-amber-600 dark:text-amber-400" />
            <span>
              Đang lọc danh sách theo phạm vi: <strong>{filters.pham_vi === 'HAN_CHE' ? 'Văn bản hạn chế (Mật)' : filters.pham_vi}</strong>
            </span>
          </div>
          <button
            type="button"
            onClick={handleClearPhamVi}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface hover:bg-surface-elevated text-secondary hover:text-main text-xs border border-border-subtle transition-all cursor-pointer shadow-2xs"
            title="Xóa bộ lọc phạm vi"
          >
            <i className="fa-solid fa-xmark text-danger" />
            <span>Bỏ lọc</span>
          </button>
        </div>
      )}

      {/* 5. Bộ Lọc Đa Tiêu Chí */}
      <FilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onSearch={fetchDocuments}
        onReset={handleResetFilters}
        isLoading={isLoading}
        availableYears={availableYears}
        documentType="MAT"
      />

      {/* Thông báo lỗi nếu có */}
      {error && (
        <div className="bg-danger-subtle text-danger border border-danger-border rounded-xl p-3.5 text-xs mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-circle-exclamation text-base" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={fetchDocuments}
            className="underline font-semibold hover:text-danger-hover"
          >
            Thử lại
          </button>
        </div>
      )}

      {/* 6. Bảng Danh Sách Văn Bản Mật */}
      <DocumentTable
        documents={documents}
        totalCount={totalCount}
        page={Number(filters.page) || 1}
        pageSize={Number(filters.page_size) || 10}
        onPageChange={handlePageChange}
        onPageSizeChange={handlePageSizeChange}
        isLoading={isLoading}
        onViewDetail={handleViewDetail}
        onViewHistory={handleViewHistory}
        isConfidential={true}
        loai="MAT"
        onEdit={handleOpenEdit}
        onDelete={(id, soHieu) => {
          setPendingDelete({ id, soHieu });
        }}
      />

      {/* 7. Modals Nghiệp Vụ */}
      <DocumentDetailModal
        isOpen={isDetailOpen}
        onClose={handleCloseDetail}
        documentId={selectedDocId}
        loai="MAT"
      />

      <DocumentViewersModal
        isOpen={isViewersOpen}
        onClose={handleCloseHistory}
        documentId={selectedDocId}
        loai="MAT"
      />

      <DocumentFormModal
        open={isFormOpen}
        initial={editingDoc}
        defaultLoai="MAT"
        onClose={handleCloseForm}
        onSaved={() => {
          handleCloseForm();
          fetchDocuments();
          fetchYears();
          fetchStats();
        }}
      />

      <ImportExcelModal
        open={isImportOpen}
        loai="MAT"
        onClose={() => setIsImportOpen(false)}
        onImported={() => {
          setIsImportOpen(false);
          fetchDocuments();
          fetchYears();
          fetchStats();
        }}
      />

      <ConfirmModal
        open={!!pendingDelete}
        title="Xác nhận xóa văn bản mật"
        message={`Bạn có chắc chắn muốn xóa văn bản mật "${pendingDelete?.soHieu}" không? Hành động này sẽ xóa văn bản khỏi hệ thống.`}
        confirmText="Xóa văn bản"
        cancelText="Hủy bỏ"
        onConfirm={doDelete}
        onCancel={() => setPendingDelete(null)}
      />

      <AlertModal
        open={isAlertOpen}
        onClose={() => setIsAlertOpen(false)}
        message={alertMsg}
      />
    </div>
  );
};

export default ConfidentialDocumentPage;
