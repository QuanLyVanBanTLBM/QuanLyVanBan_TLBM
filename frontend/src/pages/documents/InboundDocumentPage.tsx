import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DocumentItem, DocumentFilterParams, PaginatedResponse } from '@app-types/document';
import FilterBar from '@components/documents/FilterBar';
import DocumentTable from '@components/documents/DocumentTable';
import DocumentDetailModal from '@components/documents/DocumentDetailModal';
import DocumentViewersModal from '@components/documents/DocumentViewersModal';
import DocumentFormModal from '@components/documents/DocumentFormModal';
import ImportExcelModal from '@components/documents/ImportExcelModal';
import ConfirmModal from '@components/common/ConfirmModal';
import AlertModal from '@components/common/AlertModal';
import { Button } from '@components/common/Button';
import apiClient from '@lib/apiClient';

export const InboundDocumentPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const loaiVanBanParam = searchParams.get('loai_van_ban');
  const phamViParam = searchParams.get('pham_vi');

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Bộ lọc hiện tại
  const [filters, setFilters] = useState<DocumentFilterParams>({
    q: '',
    nam: '',
    tu_ngay: '',
    den_ngay: '',
    hieu_luc: '',
    page: 1,
    page_size: 10,
    loai: 'DEN',
    loai_van_ban: loaiVanBanParam || undefined,
    pham_vi: phamViParam || undefined,
  });

  useEffect(() => {
    let cancelled = false;
    Promise.resolve().then(() => {
      if (!cancelled) {
        setFilters(prev => {
          const nextLoaiVanBan = loaiVanBanParam || undefined;
          const nextPhamVi = phamViParam || undefined;
          if (prev.loai_van_ban === nextLoaiVanBan && prev.pham_vi === nextPhamVi) {
            return prev;
          }
          return {
            ...prev,
            loai_van_ban: nextLoaiVanBan,
            pham_vi: nextPhamVi,
            page: 1,
          };
        });
      }
    });
    return () => {
      cancelled = true;
    };
  }, [loaiVanBanParam, phamViParam]);

  const handleClearLoaiVanBan = () => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('loai_van_ban');
    setSearchParams(nextParams);
    setFilters(prev => ({ ...prev, loai_van_ban: undefined, page: 1 }));
  };

  const handleClearPhamVi = () => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('pham_vi');
    setSearchParams(nextParams);
    setFilters(prev => ({ ...prev, pham_vi: undefined, page: 1 }));
  };

  // Quản lý modal xem chi tiết & modal danh sách người đọc
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState<boolean>(false);
  const [isViewersOpen, setIsViewersOpen] = useState<boolean>(false);

  // Quản lý modal Thêm/Sửa & Import Excel (từ PR #34 của Tân)
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [editingDoc, setEditingDoc] = useState<DocumentItem | null>(null);
  const [isImportOpen, setIsImportOpen] = useState<boolean>(false);
  const [pendingDelete, setPendingDelete] = useState<{ id: number; soHieu: string } | null>(null);
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

  // Lấy danh sách các năm thực tế có văn bản trong CSDL
  const fetchYears = useCallback(async () => {
    try {
      const res = await apiClient.get<number[]>('/api/documents/years/?loai=DEN');
      if (Array.isArray(res) && res.length > 0) {
        setAvailableYears(res);
      }
    } catch {
      // Giữ nguyên danh sách hiện tại nếu lỗi
    }
  }, []);

  // Lấy thống kê số lượng văn bản theo trạng thái (loại bỏ các văn bản hết hiệu lực)
  const fetchStats = useCallback(async () => {
    try {
      const extraQuery = `${filters.loai_van_ban ? `&loai_van_ban=${encodeURIComponent(String(filters.loai_van_ban))}` : ''}${filters.pham_vi ? `&pham_vi=${encodeURIComponent(String(filters.pham_vi))}` : ''}`;
      const res = await apiClient.get<PaginatedResponse<DocumentItem>>(`/api/documents/?loai=DEN&page_size=1000${extraQuery}`);
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
      // Giữ nguyên trạng thái hiện tại nếu lỗi
    }
  }, [filters.loai_van_ban, filters.pham_vi]);

  useEffect(() => {
    let cancelled = false;
    Promise.resolve().then(() => {
      if (!cancelled) {
        void fetchYears();
        void fetchStats();
      }
    });
    return () => {
      cancelled = true;
    };
  }, [fetchYears, fetchStats]);

  // Gọi API lấy danh sách văn bản đến
  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('loai', 'DEN');
      if (phamViParam === 'HAN_CHE') params.set('pham_vi', 'HAN_CHE');
      if (filters.page) params.append('page', String(filters.page));
      if (filters.page_size) params.append('page_size', String(filters.page_size));
      if (filters.q) params.append('q', filters.q.trim());
      if (filters.nam) params.append('nam', String(filters.nam));
      if (filters.tu_ngay) params.append('tu_ngay', filters.tu_ngay);
      if (filters.den_ngay) params.append('den_ngay', filters.den_ngay);
      if (filters.hieu_luc) params.append('hieu_luc', filters.hieu_luc);
      if (filters.loai_van_ban) params.append('loai_van_ban', String(filters.loai_van_ban));
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
        // Fallback trường hợp API trả về mảng trực tiếp
        setDocuments(response as unknown as DocumentItem[]);
        setTotalCount((response as unknown as DocumentItem[]).length);
      } else {
        setDocuments([]);
        setTotalCount(0);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Không thể tải danh sách văn bản đến.';
      setError(errMsg);
      setDocuments([]);
      setTotalCount(0);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  // Nạp dữ liệu khi bộ lọc thay đổi
  useEffect(() => {
    let cancelled = false;
    Promise.resolve().then(() => {
      if (!cancelled) void fetchDocuments();
    });
    return () => {
      cancelled = true;
    };
  }, [fetchDocuments]);

  // Xử lý đổi trang
  const handlePageChange = (newPage: number) => {
    setFilters((prev) => ({ ...prev, page: newPage }));
  };

  // Xử lý đổi số dòng / trang
  const handlePageSizeChange = (newPageSize: number) => {
    setFilters((prev) => ({ ...prev, page_size: newPageSize, page: 1 }));
  };

  // Đặt lại bộ lọc
  const handleResetFilters = () => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('loai_van_ban');
    nextParams.delete('pham_vi');
    setSearchParams(nextParams);
    setFilters({
      q: '',
      nam: '',
      tu_ngay: '',
      den_ngay: '',
      hieu_luc: '',
      page: 1,
      page_size: 10,
      loai: 'DEN',
      loai_van_ban: undefined,
      pham_vi: undefined,
    });
  };

  // Mở modal xem chi tiết
  const handleViewDetail = (id: number) => {
    setSelectedDocId(id);
    setIsDetailOpen(true);
  };

  // Mở modal xem danh sách người đã đọc
  const handleViewHistory = (id: number) => {
    setSelectedDocId(id);
    setIsViewersOpen(true);
  };

  // Thực hiện xóa sau khi xác nhận ConfirmModal
  const doDelete = async () => {
    if (!pendingDelete) return;
    try {
      await apiClient.delete(`/api/documents/${pendingDelete.id}/`);
      setPendingDelete(null);
      setAlertMsg(`Đã xóa văn bản "${pendingDelete.soHieu}" thành công.`);
      setIsAlertOpen(true);
      fetchDocuments();
      fetchYears();
      fetchStats();
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Xóa văn bản thất bại.';
      setPendingDelete(null);
      setAlertMsg(`Lỗi xóa văn bản: ${errMsg}`);
      setIsAlertOpen(true);
    }
  };

  // Xuất file Excel văn bản đến (Ẩn văn bản hết hiệu lực theo yêu cầu)
  const handleExportExcel = async () => {
    try {
      const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token') || '';
      const params = new URLSearchParams();
      params.append('loai', 'DEN');
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
      if (!res.ok) throw new Error('Quá trình xuất Excel thất bại. Vui lòng kiểm tra lại kết nối!');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${phamViParam === 'HAN_CHE' ? 'Danh_Sach_Van_Ban_Mat' : 'Danh_Sach_Van_Ban_Den'}_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error: unknown) {
      setAlertMsg(error instanceof Error ? error.message : String(error));
      setIsAlertOpen(true);
    }
  };


  // Thống kê số lượng: Mục tổng văn bản đến và top card gộp cả Còn hiệu lực và Còn hiệu lực 1 phần
  const countActive = stats.total > 0
    ? (stats.active + stats.partial)
    : documents.filter((d) => d.hieu_luc === 'CON_HIEU_LUC' || d.hieu_luc === 'CON_HIEU_LUC_1_PHAN').length;

  return (
    <div className="w-full p-2 sm:p-4 md:p-6 animate-in fade-in duration-150">
      {/* 1. Header Trang & Thao tác */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <span className="w-8 h-8 rounded-lg bg-primary-subtle text-primary flex items-center justify-center font-bold text-sm">
              <i className="fa-solid fa-inbox text-base" />
            </span>
            <h1 className="text-xl md:text-2xl font-bold text-main m-0">{phamViParam === 'HAN_CHE' ? 'Quản Lý Văn Bản Mật' : 'Quản Lý Văn Bản Đến'}</h1>
          </div>
          <p className="text-xs md:text-sm text-secondary m-0">
            {phamViParam === 'HAN_CHE' ? 'Quản lý văn bản mật, chỉ định cán bộ được phép tiếp cận và theo dõi lịch sử xử lý.' : 'Theo dõi, tra cứu, quản lý và ghi nhận lịch sử xử lý công văn, văn bản đến từ cơ quan bên ngoài.'}
          </p>
        </div>

        {/* Các nút hành động chính (Thêm mới, Nhập Excel, Xuất Excel, Làm mới) */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            type="button"
            variant="primary"
            size="sm"
            icon="fa-plus"
            onClick={() => {
              setEditingDoc(null);
              setIsFormOpen(true);
            }}
            title={phamViParam === 'HAN_CHE' ? 'Thêm văn bản mật mới' : 'Thêm văn bản đến mới'}
          >
            Thêm mới
          </Button>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon="fa-file-excel"
            onClick={() => setIsImportOpen(true)}
            title="Nhập danh sách từ tệp Excel"
          >
            Nhập Excel
          </Button>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon="fa-file-export"
            onClick={handleExportExcel}
            title="Xuất dữ liệu ra file Excel"
          >
            Xuất Excel
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
            title="Làm mới danh sách"
          >
            Làm mới
          </Button>
        </div>
      </div>

      {/* 2. Thẻ Thống Kê Tổng Hợp (Hiển thị trạng thái Còn hiệu lực gộp cả hiệu lực 1 phần) */}
      <div className="bg-surface border border-border-subtle rounded-2xl p-4 sm:p-5 mb-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          {/* Cột Trái: Mục Tổng số văn bản đến hiển thị số lượng văn bản còn hiệu lực */}
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-primary-subtle text-primary flex items-center justify-center text-xl shrink-0 shadow-2xs">
              <i className="fa-solid fa-file-circle-check" />
            </div>
            <div>
              <span className="text-sm text-muted block mb-0.5 font-medium">{phamViParam === 'HAN_CHE' ? 'Tổng số văn bản mật' : 'Tổng số văn bản đến'}</span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-bold text-main">{countActive}</span>
                <span className="text-sm text-muted font-medium">văn bản còn hiệu lực</span>
              </div>
            </div>
          </div>

          {/* Cột Phải: Nút lọc trạng thái Còn hiệu lực (gộp cả hiệu lực 1 phần) */}
          <div className="flex items-center">
            <button
              type="button"
              onClick={() =>
                setFilters((prev) => ({
                  ...prev,
                  hieu_luc: prev.hieu_luc === 'HIEU_LUC' ? '' : 'HIEU_LUC',
                  page: 1,
                }))
              }
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                filters.hieu_luc === 'HIEU_LUC'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-500/25 ring-2 ring-emerald-600/30'
                  : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20'
              }`}
              title="Lọc danh sách theo văn bản còn hiệu lực (bao gồm cả hiệu lực 1 phần)"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Còn hiệu lực</span>
              <span
                className={`ml-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  filters.hieu_luc === 'HIEU_LUC'
                    ? 'bg-white/20 text-white'
                    : 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-400'
                }`}
              >
                {countActive}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* 3. Chỉ báo lọc Loại văn bản từ URL (Nhóm 3 liên kết) */}
      {filters.loai_van_ban && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 mb-4 bg-primary/10 border border-primary/20 rounded-xl text-xs text-primary shadow-2xs">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-filter text-primary" />
            <span>
              Đang lọc danh sách theo Loại văn bản (từ phân hệ Hồ sơ): <strong>#{filters.loai_van_ban}</strong>
            </span>
          </div>
          <button
            type="button"
            onClick={handleClearLoaiVanBan}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface hover:bg-surface-elevated text-secondary hover:text-main text-xs border border-border-subtle transition-all cursor-pointer shadow-2xs"
            title="Xóa bộ lọc loại văn bản"
          >
            <i className="fa-solid fa-xmark text-danger" />
            <span>Bỏ lọc</span>
          </button>
        </div>
      )}

      {/* 3.1. Chỉ báo lọc Phạm vi văn bản từ URL (Văn bản hạn chế / Mật từ Nhóm 3) */}
      {filters.pham_vi && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 mb-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-800 dark:text-amber-300 shadow-2xs">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-shield-halved text-amber-600 dark:text-amber-400" />
            <span>
              Đang lọc danh sách theo phạm vi: <strong>{filters.pham_vi === 'HAN_CHE' ? 'Văn bản hạn chế (Mật)' : filters.pham_vi}</strong> — Chỉ hiển thị văn bản bạn có thẩm quyền tiếp cận.
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

      {/* 4. Thanh Tìm Kiếm & Bộ Lọc Đa Tiêu Chí */}
      <FilterBar
        filters={filters}
        onFilterChange={setFilters}
        onSearch={fetchDocuments}
        onReset={handleResetFilters}
        isLoading={isLoading}
        availableYears={availableYears}
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

      {/* 4. Bảng Danh Sách Văn Bản với Phân Trang & Menu Thao Tác */}
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
        onEdit={(doc) => {
          setEditingDoc(doc);
          setIsFormOpen(true);
        }}
        onDelete={(id, soHieu) => {
          setPendingDelete({ id, soHieu });
        }}
      />

      {/* 5. Modals Nghiệp Vụ */}
      <DocumentDetailModal
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        documentId={selectedDocId}
      />

      <DocumentViewersModal
        isOpen={isViewersOpen}
        onClose={() => setIsViewersOpen(false)}
        documentId={selectedDocId}
      />

      <DocumentFormModal
        open={isFormOpen}
        initial={editingDoc}
        onClose={() => {
          setIsFormOpen(false);
          setEditingDoc(null);
        }}
        confidential={phamViParam === 'HAN_CHE'}
        onSaved={() => {
          setIsFormOpen(false);
          setEditingDoc(null);
          fetchDocuments();
          fetchYears();
          fetchStats();
        }}
      />

      <ImportExcelModal
        open={isImportOpen}
        loai="DEN"
        phamVi={phamViParam === 'HAN_CHE' ? 'HAN_CHE' : undefined}
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
        title="Xác nhận xóa văn bản đến"
        message={`Bạn có chắc chắn muốn xóa văn bản "${pendingDelete?.soHieu}" không? Hành động này không thể hoàn tác.`}
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

export default InboundDocumentPage;
