import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DocumentItem, DocumentFilterParams, DocumentStatus, PaginatedResponse } from '@app-types/document';
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
import { useTranslation } from '@i18n/translate';

const extractDocType = (doc: DocumentItem): string | null => {
  const soHieu = (doc.so_hieu || '').toUpperCase();
  const trichYeu = (doc.trich_yeu || '').trim();

  if (/\bQĐ\b|\/QĐ|\/QD/i.test(soHieu) || /^(quyết định|quy định)/i.test(trichYeu)) return 'Quyết định';
  if (/\bTB\b|\/TB/i.test(soHieu) || /^thông báo/i.test(trichYeu)) return 'Thông báo';
  if (/\bHĐ\b|\bHD\b|\/HD|\/HĐ/i.test(soHieu) || /^hướng dẫn/i.test(trichYeu)) return 'Hướng dẫn';
  if (/\bKH\b|\/KH/i.test(soHieu) || /^kế hoạch/i.test(trichYeu)) return 'Kế hoạch';
  if (/\bCV\b|\/CV/i.test(soHieu) || /^(công văn|v\/v)/i.test(trichYeu)) return 'Công văn';
  if (/\bCT\b|\/CT/i.test(soHieu) || /^chỉ thị/i.test(trichYeu)) return 'Chỉ thị';
  if (/\bTTR\b|\/TTR/i.test(soHieu) || /^tờ trình/i.test(trichYeu)) return 'Tờ trình';
  if (/\bBC\b|\/BC/i.test(soHieu) || /^báo cáo/i.test(trichYeu)) return 'Báo cáo';
  if (/\bNQ\b|\/NQ/i.test(soHieu) || /^nghị quyết/i.test(trichYeu)) return 'Nghị quyết';

  return null;
};

export const InboundDocumentPage: React.FC = () => {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [availableDocTypes, setAvailableDocTypes] = useState<string[]>([]);

  // Khởi tạo bộ lọc đồng bộ 2 chiều với URL SearchParams
  const [filters, setFilters] = useState<DocumentFilterParams>(() => ({
    q: searchParams.get('q') || '',
    nam: searchParams.get('nam') || '',
    tu_ngay: searchParams.get('tu_ngay') || '',
    den_ngay: searchParams.get('den_ngay') || '',
    hieu_luc: (searchParams.get('hieu_luc') as DocumentStatus | 'HIEU_LUC' | '') || '',
    page: searchParams.get('page') ? Number(searchParams.get('page')) : 1,
    page_size: searchParams.get('page_size') ? Number(searchParams.get('page_size')) : 10,
    loai: 'DEN',
    loai_van_ban: searchParams.get('loai_van_ban') || undefined,
    ho_so: searchParams.get('ho_so') || undefined,
    pham_vi: (searchParams.get('pham_vi') as 'NOI_BO' | 'HAN_CHE' | 'ALL') || 'NOI_BO',
  }));

  // Hàm đồng bộ trạng thái bộ lọc lên URL query parameters
  const syncFiltersToUrl = useCallback((currentFilters: DocumentFilterParams) => {
    const nextParams = new URLSearchParams();
    if (currentFilters.q) nextParams.set('q', currentFilters.q.trim());
    if (currentFilters.nam) nextParams.set('nam', String(currentFilters.nam));
    if (currentFilters.tu_ngay) nextParams.set('tu_ngay', currentFilters.tu_ngay);
    if (currentFilters.den_ngay) nextParams.set('den_ngay', currentFilters.den_ngay);
    if (currentFilters.hieu_luc) nextParams.set('hieu_luc', currentFilters.hieu_luc);
    if (currentFilters.loai_van_ban) nextParams.set('loai_van_ban', String(currentFilters.loai_van_ban));
    if (currentFilters.ho_so) {
      nextParams.set('ho_so', currentFilters.ho_so);
      const dossierName = searchParams.get('ten_ho_so');
      if (currentFilters.ho_so === searchParams.get('ho_so') && dossierName) {
        nextParams.set('ten_ho_so', dossierName);
      }
    }
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
        setFilters((prev) => {
          const nextLoaiVanBan = searchParams.get('loai_van_ban') || undefined;
          const rawPhamVi = searchParams.get('pham_vi');
          const nextPhamVi: 'NOI_BO' | 'HAN_CHE' | 'ALL' =
            rawPhamVi === 'HAN_CHE' || rawPhamVi === 'ALL' || rawPhamVi === 'NOI_BO'
              ? rawPhamVi
              : 'NOI_BO';
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
    const next: DocumentFilterParams = { ...filters, pham_vi: 'NOI_BO', page: 1 };
    setFilters(next);
    syncFiltersToUrl(next);
  };

  // Quản lý modal xem chi tiết & modal danh sách người đọc
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState<boolean>(false);
  const [isViewersOpen, setIsViewersOpen] = useState<boolean>(false);

  // Quản lý modal Thêm/Sửa & Import Excel (từ PR #34 của Tân)
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [editingDoc, setEditingDoc] = useState<DocumentItem | null>(null);
  const [isImportOpen, setIsImportOpen] = useState<boolean>(false);
  const [importMenuOpen, setImportMenuOpen] = useState<boolean>(false);
  const [exportMenuOpen, setExportMenuOpen] = useState<boolean>(false);
  const [importPhamVi, setImportPhamVi] = useState<'NOI_BO' | 'HAN_CHE'>('NOI_BO');
  const importMenuRef = useRef<HTMLDivElement>(null);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (importMenuRef.current && !importMenuRef.current.contains(e.target as Node)) {
        setImportMenuOpen(false);
      }
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setExportMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const [pendingDelete, setPendingDelete] = useState<{ id: number; soHieu: string } | null>(null);
  const [alertMsg, setAlertMsg] = useState<string>('');
  const [isAlertOpen, setIsAlertOpen] = useState<boolean>(false);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [availableFolders, setAvailableFolders] = useState<string[]>([]);
  const [folderDocTypesMap, setFolderDocTypesMap] = useState<Record<string, string[]>>({});
  const [recordDossiers, setRecordDossiers] = useState<Array<{ id: number | string; ten_ho_so: string; so_ky_hieu?: string }>>([]);
  const [recordDocTypes, setRecordDocTypes] = useState<Array<{ id: number | string; ten_loai: string; ho_so?: number | string; ten_ho_so?: string }>>([]);
  const [allStatsItems, setAllStatsItems] = useState<DocumentItem[]>([]);

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

  // Lấy thống kê số lượng văn bản theo trạng thái (loại bỏ các văn bản hết hiệu lực) và nạp danh sách Loại văn bản toàn hệ thống
  const fetchStats = useCallback(async () => {
    try {
      // Luôn tải từ toàn bộ văn bản để danh mục Loại văn bản không bị co cụm khi người dùng lọc
      const res = await apiClient.get<PaginatedResponse<DocumentItem>>('/api/documents/?loai=DEN&page_size=1000');
      const items = res && Array.isArray(res.results) ? res.results : (Array.isArray(res) ? (res as DocumentItem[]) : []);
      setAllStatsItems(items);

      // 2. Lấy danh mục hồ sơ và loại văn bản từ Nhóm 3 (app records) để đồng bộ danh mục hệ thống
      const recordsFolders: string[] = [];
      const recordsFolderTypeMap: Record<string, Set<string>> = {};

      try {
        const dossiersRes = await apiClient.get<unknown>('/api/records/dossiers/?page_size=100');
        const rawDossiers = Array.isArray(dossiersRes)
          ? dossiersRes
          : (dossiersRes as { results?: Array<{ ten_ho_so?: string }>; items?: Array<{ ten_ho_so?: string }> })?.results
          || (dossiersRes as { results?: Array<{ ten_ho_so?: string }>; items?: Array<{ ten_ho_so?: string }> })?.items
          || [];

        if (Array.isArray(rawDossiers) && rawDossiers.length > 0) {
          const parsedDossiers: Array<{ id: number | string; ten_ho_so: string; so_ky_hieu?: string }> = [];
          rawDossiers.forEach((d) => {
            const rawD = d as { id?: number | string; ten_ho_so?: string; so_ky_hieu?: string };
            const name = rawD?.ten_ho_so?.trim();
            if (name) {
              recordsFolders.push(name);
              parsedDossiers.push({
                id: rawD.id ?? '',
                ten_ho_so: name,
                so_ky_hieu: rawD.so_ky_hieu,
              });
            }
          });
          setRecordDossiers(parsedDossiers);
        }
      } catch {
        // Fallback an toàn nếu API records chưa sẵn sàng
      }

      try {
        const docTypesRes = await apiClient.get<unknown>('/api/records/document-types/?page_size=100');
        const rawDocTypes = Array.isArray(docTypesRes)
          ? docTypesRes
          : (docTypesRes as { results?: Array<{ ten_ho_so?: string; ten_loai?: string }>; items?: Array<{ ten_ho_so?: string; ten_loai?: string }> })?.results
          || (docTypesRes as { results?: Array<{ ten_ho_so?: string; ten_loai?: string }>; items?: Array<{ ten_ho_so?: string; ten_loai?: string }> })?.items
          || [];

        if (Array.isArray(rawDocTypes) && rawDocTypes.length > 0) {
          const parsedDocTypes: Array<{ id: number | string; ten_loai: string; ho_so?: number | string; ten_ho_so?: string }> = [];
          rawDocTypes.forEach((dt) => {
            const rawDt = dt as { id?: number | string; ten_ho_so?: string; ten_loai?: string; ho_so?: number | string | { id?: number | string } };
            const folderName = rawDt?.ten_ho_so?.trim();
            const typeName = rawDt?.ten_loai?.trim();
            const rawHoSo = rawDt?.ho_so;
            let hoSoId: number | string | undefined = undefined;
            if (typeof rawHoSo === 'string' || typeof rawHoSo === 'number') {
              hoSoId = rawHoSo;
            } else if (rawHoSo && typeof rawHoSo === 'object' && 'id' in rawHoSo) {
              hoSoId = rawHoSo.id;
            }
            if (typeName) {
              parsedDocTypes.push({
                id: rawDt.id ?? '',
                ten_loai: typeName,
                ho_so: hoSoId,
                ten_ho_so: folderName,
              });
            }
            if (folderName && typeName) {
              if (!recordsFolderTypeMap[folderName]) {
                recordsFolderTypeMap[folderName] = new Set<string>();
              }
              recordsFolderTypeMap[folderName].add(typeName);
            }
          });
          setRecordDocTypes(parsedDocTypes);
        }
      } catch {
        // Fallback an toàn
      }

      // Trích xuất các Loại văn bản và ánh xạ Danh mục hồ sơ -> Loại văn bản thực tế từ các văn bản trong hệ thống
      const extractedTypes = new Set<string>();
      const extractedFolders = new Set<string>();
      const folderTypeMapping: Record<string, Set<string>> = {};

      const typeMapping: Record<string, string> = {
        'QĐ': 'Quyết định',
        'QD': 'Quyết định',
        'TB': 'Thông báo',
        'CV': 'Công văn',
        'HD': 'Hướng dẫn',
        'KH': 'Kế hoạch',
        'CT': 'Chỉ thị',
        'BC': 'Báo cáo',
        'TTR': 'Tờ trình',
        'NQ': 'Nghị quyết',
      };

      items.forEach((d) => {
        const rawItem = d as unknown as Record<string, unknown>;
        const rawDocType = rawItem.ten_loai_van_ban || rawItem.loai_van_ban;
        let detectedType = typeof rawDocType === 'string' && rawDocType.trim() ? rawDocType.trim() : '';

        if (!detectedType) {
          const match = d.so_hieu ? d.so_hieu.match(/\/([A-ZĐ]+)(?:-|$)/i) : null;
          if (match && typeMapping[match[1].toUpperCase()]) {
            detectedType = typeMapping[match[1].toUpperCase()];
          } else if (d.trich_yeu) {
            const trichYeuUpper = d.trich_yeu.trim().toUpperCase();
            for (const name of Object.values(typeMapping)) {
              if (trichYeuUpper.startsWith(name.toUpperCase())) {
                detectedType = name;
                break;
              }
            }
          }
        }

        if (detectedType) {
          extractedTypes.add(detectedType);
        }

        const rawFolder = rawItem.danh_muc_ho_so || rawItem.ho_so;
        if (typeof rawFolder === 'string' && rawFolder.trim()) {
          const folderName = rawFolder.trim();
          extractedFolders.add(folderName);
          if (!folderTypeMapping[folderName]) {
            folderTypeMapping[folderName] = new Set<string>();
          }
          if (detectedType) {
            folderTypeMapping[folderName].add(detectedType);
          }
        }
      });

      // Gộp danh mục hồ sơ: kết hợp hồ sơ từ Nhóm 3 (app records) và hồ sơ thực tế trong văn bản
      const combinedFoldersSet = new Set<string>([...recordsFolders, ...extractedFolders]);
      const serializableFolderMap: Record<string, string[]> = {};

      // Xây dựng bản đồ ánh xạ Hồ sơ -> Loại văn bản kết hợp
      combinedFoldersSet.forEach((folder) => {
        const fromRecords = recordsFolderTypeMap[folder] ? Array.from(recordsFolderTypeMap[folder]) : [];
        const fromDocuments = folderTypeMapping[folder] ? Array.from(folderTypeMapping[folder]) : [];
        const combinedTypes = Array.from(new Set([...fromRecords, ...fromDocuments])).sort((a, b) => a.localeCompare(b, 'vi'));
        if (combinedTypes.length > 0) {
          serializableFolderMap[folder] = combinedTypes;
        }
      });

      // Nếu có hồ sơ trong folderTypeMapping chưa có trong combinedFoldersSet
      Object.entries(folderTypeMapping).forEach(([folder, typeSet]) => {
        if (!serializableFolderMap[folder]) {
          serializableFolderMap[folder] = Array.from(typeSet).sort((a, b) => a.localeCompare(b, 'vi'));
        }
      });

      setAvailableDocTypes(Array.from(extractedTypes).sort((a, b) => a.localeCompare(b, 'vi')));
      setAvailableFolders(Array.from(combinedFoldersSet).sort((a, b) => a.localeCompare(b, 'vi')));
      setFolderDocTypesMap(serializableFolderMap);
    } catch {
      // Giữ nguyên trạng thái hiện tại nếu lỗi
    }
  }, []);

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
      if (filters.page) params.append('page', String(filters.page));
      if (filters.page_size) params.append('page_size', String(filters.page_size));
      if (filters.q) params.append('q', filters.q.trim());
      if (filters.nam) params.append('nam', String(filters.nam));
      if (filters.tu_ngay) params.append('tu_ngay', filters.tu_ngay);
      if (filters.den_ngay) params.append('den_ngay', filters.den_ngay);
      if (filters.hieu_luc) params.append('hieu_luc', filters.hieu_luc);
      if (filters.loai_van_ban) params.append('loai_van_ban', String(filters.loai_van_ban));
      if (filters.ho_so) params.append('ho_so', filters.ho_so.trim());
      const targetPhamVi = filters.pham_vi || 'NOI_BO';
      if (targetPhamVi !== 'ALL') params.append('pham_vi', targetPhamVi);

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

          // Trích xuất các loại văn bản thực tế có sẵn
          const detectedTypes = new Set<string>();
          response.results.forEach((doc) => {
            const t = extractDocType(doc);
            if (t) detectedTypes.add(t);
          });
          setAvailableDocTypes(prev => {
            const merged = Array.from(new Set([...prev, ...Array.from(detectedTypes)])).sort();
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
    const next = { ...filters, page: newPage };
    setFilters(next);
    syncFiltersToUrl(next);
  };

  // Xử lý đổi số dòng / trang
  const handlePageSizeChange = (newPageSize: number) => {
    const next = { ...filters, page_size: newPageSize, page: 1 };
    setFilters(next);
    syncFiltersToUrl(next);
  };

  // Đặt lại bộ lọc
  const handleResetFilters = () => {
    const defaultFilters: DocumentFilterParams = {
      q: '',
      nam: '',
      tu_ngay: '',
      den_ngay: '',
      hieu_luc: '',
      page: 1,
      page_size: 10,
      loai: 'DEN',
      loai_van_ban: undefined,
      ho_so: undefined,
      pham_vi: filters.pham_vi || 'NOI_BO',
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
      if (cancelled) return;
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
        }
      } else if (!actionParam && !editParam) {
        setIsFormOpen(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [searchParams, documents]);

  // Thực hiện xóa sau khi xác nhận ConfirmModal
  const doDelete = async () => {
    if (!pendingDelete) return;
    try {
      await apiClient.delete(`/api/documents/${pendingDelete.id}/?loai=DEN`);
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

  // Xuất file Excel văn bản đến (theo phạm vi: Nội bộ, Hạn chế hoặc Tất cả)
  const handleExportExcel = async (exportPhamVi: 'NOI_BO' | 'HAN_CHE' | 'ALL' = 'NOI_BO') => {
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
      if (exportPhamVi !== 'ALL') {
        params.append('pham_vi', exportPhamVi);
      }

      const res = await fetch(`/api/documents/export/?${params.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Quá trình xuất Excel thất bại. Vui lòng kiểm tra lại kết nối!');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const phamViSuffix = exportPhamVi === 'HAN_CHE' ? 'Han_Che' : exportPhamVi === 'ALL' ? 'Tat_Ca' : 'Noi_Bo';
      a.download = `Danh_Sach_Van_Ban_Den_${phamViSuffix}_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error: unknown) {
      setAlertMsg(error instanceof Error ? error.message : String(error));
      setIsAlertOpen(true);
    }
  };


  const currentPhamVi = filters.pham_vi || 'NOI_BO';

  // Tra cứu Tên hồ sơ và Tên loại văn bản thân thiện từ danh mục Nhóm 3 khi URL truyền mã ID tham chiếu
  const resolvedRecordLabels = useMemo(() => {
    let resolvedDocType = '';
    let resolvedFolder = '';

    if (filters.loai_van_ban) {
      const lvStr = String(filters.loai_van_ban).trim();
      const matchedType = recordDocTypes.find((dt) => String(dt.id) === lvStr);
      if (matchedType) {
        resolvedDocType = matchedType.ten_loai;
        if (matchedType.ten_ho_so) {
          resolvedFolder = matchedType.ten_ho_so;
        } else if (matchedType.ho_so) {
          const matchedDossier = recordDossiers.find((d) => String(d.id) === String(matchedType.ho_so));
          if (matchedDossier) {
            resolvedFolder = matchedDossier.ten_ho_so;
          }
        }
      } else if (!/^\d+$/.test(lvStr)) {
        resolvedDocType = lvStr;
      }
    }

    if (!resolvedFolder && filters.ho_so) {
      const hsStr = String(filters.ho_so).trim();
      const matchedDossier = recordDossiers.find((d) => String(d.id) === hsStr);
      if (matchedDossier) {
        resolvedFolder = matchedDossier.ten_ho_so;
      } else {
        const urlTenHoSo = searchParams.get('ten_ho_so');
        if (urlTenHoSo && urlTenHoSo.trim()) {
          resolvedFolder = urlTenHoSo.trim();
        } else if (!/^\d+$/.test(hsStr)) {
          resolvedFolder = hsStr;
        }
      }
    } else if (!resolvedFolder && searchParams.get('ten_ho_so')) {
      resolvedFolder = searchParams.get('ten_ho_so')!.trim();
    }

    return {
      docTypeName: resolvedDocType,
      dossierName: resolvedFolder,
    };
  }, [filters.loai_van_ban, filters.ho_so, recordDocTypes, recordDossiers, searchParams]);

  // Thống kê số lượng: Mục tổng văn bản đến và top card gộp cả Còn hiệu lực và Còn hiệu lực 1 phần theo đúng phạm vi (Nội bộ / Hạn chế / Tất cả)
  const countActive = useMemo(() => {
    // Khi đang tham chiếu từ phân hệ Hồ sơ (có lọc theo loai_van_ban hoặc ho_so):
    // Đếm theo số lượng văn bản thực tế của tập kết quả tham chiếu theo đúng phạm vi hiện tại
    if (filters.loai_van_ban || filters.ho_so) {
      if (totalCount === 0) return 0;
      if (filters.hieu_luc === 'HIEU_LUC') return totalCount;
      const activeInCurrent = documents.filter(
        (d) => d.hieu_luc === 'CON_HIEU_LUC' || d.hieu_luc === 'CON_HIEU_LUC_1_PHAN'
      ).length;
      if (totalCount <= documents.length) {
        return activeInCurrent;
      }
      const ratio = documents.length > 0 ? activeInCurrent / documents.length : 1;
      return Math.round(ratio * totalCount);
    }

    const sourceList = allStatsItems.length > 0 ? allStatsItems : documents;
    return sourceList.filter((d) => {
      const isActive = d.hieu_luc === 'CON_HIEU_LUC' || d.hieu_luc === 'CON_HIEU_LUC_1_PHAN';
      if (!isActive) return false;
      if (currentPhamVi === 'ALL') return true;
      const docPhamVi = d.pham_vi || 'NOI_BO';
      return docPhamVi === currentPhamVi;
    }).length;
  }, [allStatsItems, documents, currentPhamVi, filters.loai_van_ban, filters.ho_so, filters.hieu_luc, totalCount]);

  return (
    <div className="w-full p-2 sm:p-4 md:p-6 animate-in fade-in duration-150">
      {/* 1. Header Trang & Thao tác */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <span className="w-8 h-8 rounded-lg bg-primary-subtle text-primary flex items-center justify-center font-bold text-sm">
              <i className="fa-solid fa-inbox text-base" />
            </span>
            <h1 className="text-xl md:text-2xl font-bold text-main m-0">{t('pages.documents_incoming.title') || 'Quản Lý Văn Bản Đến'}</h1>
          </div>
          <p className="text-xs md:text-sm text-secondary m-0">
            {t('pages.documents_incoming.desc') || 'Theo dõi, tra cứu, quản lý và ghi nhận lịch sử xử lý công văn, văn bản đến từ cơ quan bên ngoài.'}
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
            title={t('documents_incoming_page.addBtn') || 'Thêm mới'}
          >
            {t('documents_incoming_page.addBtn') || 'Thêm mới'}
          </Button>

          {/* Dropdown Import Excel */}
          <div className="relative" ref={importMenuRef}>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              icon="fa-file-excel"
              onClick={() => {
                setImportMenuOpen((prev) => !prev);
                setExportMenuOpen(false);
              }}
              className={`transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 ${importMenuOpen ? 'border-primary/50 shadow-xs bg-surface-elevated' : ''}`}
              title={t('documents_ui.actions.importExcelTitle') || 'Nhập danh sách từ tệp Excel'}
            >
              <span>{t('documents_ui.actions.importExcel') || 'Import Excel'}</span>
              <i className={`fa-solid fa-chevron-down text-[10px] ml-1 text-secondary transition-transform duration-200 ${importMenuOpen ? 'rotate-180' : ''}`} />
            </Button>

            {importMenuOpen && (
              <div className="absolute left-0 sm:right-0 sm:left-auto top-full mt-2 w-56 p-1.5 bg-surface/95 backdrop-blur-md border border-border-subtle rounded-2xl shadow-xl z-50 animate-in fade-in zoom-in-95 duration-150 space-y-1">
                <button
                  type="button"
                  onClick={() => {
                    setImportMenuOpen(false);
                    setImportPhamVi('NOI_BO');
                    setIsImportOpen(true);
                  }}
                  className="group w-full text-left px-3 py-2.5 text-xs font-semibold text-main hover:text-primary rounded-xl transition-all duration-150 hover:-translate-y-[1px] hover:shadow-md hover:bg-white dark:hover:bg-slate-800 border border-transparent hover:border-slate-200/80 dark:hover:border-slate-700/80 flex items-center gap-2.5 cursor-pointer"
                >
                  <span className="w-6 h-6 rounded-lg bg-surface-elevated group-hover:bg-primary/10 flex items-center justify-center transition-colors">
                    <i className="fa-regular fa-file-lines text-secondary group-hover:text-primary text-xs transition-colors" />
                  </span>
                  <span>{t('documents_ui.actions.importInternal') || 'Nhập văn bản thường'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setImportMenuOpen(false);
                    setImportPhamVi('HAN_CHE');
                    setIsImportOpen(true);
                  }}
                  className="group w-full text-left px-3 py-2.5 text-xs font-semibold text-main hover:text-primary rounded-xl transition-all duration-150 hover:-translate-y-[1px] hover:shadow-md hover:bg-white dark:hover:bg-slate-800 border border-transparent hover:border-slate-200/80 dark:hover:border-slate-700/80 flex items-center gap-2.5 cursor-pointer"
                >
                  <span className="w-6 h-6 rounded-lg bg-surface-elevated group-hover:bg-primary/10 flex items-center justify-center transition-colors">
                    <i className="fa-solid fa-shield-halved text-secondary group-hover:text-primary text-xs transition-colors" />
                  </span>
                  <span>{t('documents_ui.actions.importRestricted') || 'Nhập văn bản hạn chế'}</span>
                </button>
              </div>
            )}
          </div>

          {/* Dropdown Xuất Excel */}
          <div className="relative" ref={exportMenuRef}>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              icon="fa-file-export"
              onClick={() => {
                setExportMenuOpen((prev) => !prev);
                setImportMenuOpen(false);
              }}
              className={`transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 ${exportMenuOpen ? 'border-primary/50 shadow-xs bg-surface-elevated' : ''}`}
              title={t('documents_ui.actions.exportExcelTitle') || 'Xuất dữ liệu ra file Excel'}
            >
              <span>{t('documents_ui.actions.exportExcel') || 'Xuất Excel'}</span>
              <i className={`fa-solid fa-chevron-down text-[10px] ml-1 text-secondary transition-transform duration-200 ${exportMenuOpen ? 'rotate-180' : ''}`} />
            </Button>

            {exportMenuOpen && (
              <div className="absolute left-0 sm:right-0 sm:left-auto top-full mt-2 w-56 p-1.5 bg-surface/95 backdrop-blur-md border border-border-subtle rounded-2xl shadow-xl z-50 animate-in fade-in zoom-in-95 duration-150 space-y-1">
                <button
                  type="button"
                  onClick={() => {
                    setExportMenuOpen(false);
                    handleExportExcel('NOI_BO');
                  }}
                  className="group w-full text-left px-3 py-2.5 text-xs font-semibold text-main hover:text-primary rounded-xl transition-all duration-150 hover:-translate-y-[1px] hover:shadow-md hover:bg-white dark:hover:bg-slate-800 border border-transparent hover:border-slate-200/80 dark:hover:border-slate-700/80 flex items-center gap-2.5 cursor-pointer"
                >
                  <span className="w-6 h-6 rounded-lg bg-surface-elevated group-hover:bg-primary/10 flex items-center justify-center transition-colors">
                    <i className="fa-regular fa-file-lines text-secondary group-hover:text-primary text-xs transition-colors" />
                  </span>
                  <span>{t('documents_ui.actions.exportInternal') || 'Xuất văn bản thường'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setExportMenuOpen(false);
                    handleExportExcel('HAN_CHE');
                  }}
                  className="group w-full text-left px-3 py-2.5 text-xs font-semibold text-main hover:text-primary rounded-xl transition-all duration-150 hover:-translate-y-[1px] hover:shadow-md hover:bg-white dark:hover:bg-slate-800 border border-transparent hover:border-slate-200/80 dark:hover:border-slate-700/80 flex items-center gap-2.5 cursor-pointer"
                >
                  <span className="w-6 h-6 rounded-lg bg-surface-elevated group-hover:bg-primary/10 flex items-center justify-center transition-colors">
                    <i className="fa-solid fa-shield-halved text-secondary group-hover:text-primary text-xs transition-colors" />
                  </span>
                  <span>{t('documents_ui.actions.exportRestricted') || 'Xuất văn bản hạn chế'}</span>
                </button>
                <div className="h-px bg-border-subtle my-1 mx-2" />
                <button
                  type="button"
                  onClick={() => {
                    setExportMenuOpen(false);
                    handleExportExcel('ALL');
                  }}
                  className="group w-full text-left px-3 py-2.5 text-xs font-semibold text-main hover:text-primary rounded-xl transition-all duration-150 hover:-translate-y-[1px] hover:shadow-md hover:bg-white dark:hover:bg-slate-800 border border-transparent hover:border-slate-200/80 dark:hover:border-slate-700/80 flex items-center gap-2.5 cursor-pointer"
                >
                  <span className="w-6 h-6 rounded-lg bg-surface-elevated group-hover:bg-primary/10 flex items-center justify-center transition-colors">
                    <i className="fa-solid fa-layer-group text-secondary group-hover:text-primary text-xs transition-colors" />
                  </span>
                  <span>{t('documents_ui.actions.exportAll') || 'Xuất tất cả văn bản'}</span>
                </button>
              </div>
            )}
          </div>

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

      {/* 2. Thẻ Thống Kê Tổng Hợp (Hiển thị trạng thái Còn hiệu lực gộp cả hiệu lực 1 phần) */}
      <div className="bg-surface border border-border-subtle rounded-2xl p-4 sm:p-5 mb-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          {/* Cột Trái: Mục Tổng số văn bản đến hiển thị số lượng văn bản còn hiệu lực */}
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-primary-subtle text-primary flex items-center justify-center text-xl shrink-0 shadow-2xs">
              <i className="fa-solid fa-file-circle-check" />
            </div>
            <div>
              <span className="text-sm text-muted block mb-0.5 font-medium">
                <span>{t('documents_ui.topCard.totalInbound') || 'Tổng số văn bản đến'}</span>
                {currentPhamVi === 'HAN_CHE' && <span className="ml-1 text-rose-500 font-semibold">{t('documents_ui.topCard.scopeRestricted') || '(Hạn chế)'}</span>}
                {currentPhamVi === 'ALL' && <span className="ml-1 text-primary font-semibold">{t('documents_ui.topCard.scopeAll') || '(Tất cả)'}</span>}
                {currentPhamVi === 'NOI_BO' && <span className="ml-1 text-secondary font-medium">{t('documents_ui.topCard.scopeInternal') || '(Nội bộ)'}</span>}
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-bold text-main">{countActive}</span>
                <span className="text-sm text-muted font-medium">{t('documents_ui.topCard.activeDocs') || 'văn bản còn hiệu lực'}</span>
              </div>
            </div>
          </div>

          {/* Cột Phải: Nút lọc trạng thái Còn hiệu lực với hiệu ứng màu xanh lá */}
          <div className="flex items-center">
            <button
              type="button"
              onClick={() => {
                const nextStatus: DocumentFilterParams['hieu_luc'] =
                  filters.hieu_luc === 'HIEU_LUC' ? '' : 'HIEU_LUC';
                const next: DocumentFilterParams = { ...filters, hieu_luc: nextStatus, page: 1 };
                setFilters(next);
                syncFiltersToUrl(next);
              }}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
                filters.hieu_luc === 'HIEU_LUC'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-500/25 ring-2 ring-emerald-500/40'
                  : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/25 hover:bg-emerald-500/20'
              }`}
              title={t('documents_ui.topCard.activeFilterTitle') || 'Lọc danh sách theo văn bản còn hiệu lực (bao gồm cả hiệu lực 1 phần)'}
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

      {/* 3. Chỉ báo lọc Loại văn bản từ URL (Nhóm 3 liên kết) */}
      {filters.loai_van_ban && (
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 mb-4 bg-primary/10 border border-primary/20 rounded-xl text-xs text-primary shadow-2xs">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-filter text-primary" />
            <span>
              {t('documents_ui.scopeTabs.loaiVanBanFilterNotice') || 'Đang lọc danh sách theo Loại văn bản (từ phân hệ Hồ sơ):'}{' '}
              {resolvedRecordLabels.docTypeName ? (
                <>
                  <strong className="text-primary font-bold">{resolvedRecordLabels.docTypeName}</strong>{' '}
                  <strong className="text-primary/70 font-semibold">#{filters.loai_van_ban}</strong>
                </>
              ) : (
                <strong className="text-primary font-bold">#{filters.loai_van_ban}</strong>
              )}
              {resolvedRecordLabels.dossierName && (
                <span className="ml-1 text-secondary font-medium">
                  (thuộc Danh mục: <strong>{resolvedRecordLabels.dossierName}</strong>)
                </span>
              )}
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

      {/* 3.1. Thanh Chuyển Tab Chuyên Biệt: Nội bộ vs Hạn chế vs Tất cả (Giải pháp 1) */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="inline-flex p-1 bg-surface border border-border-subtle rounded-xl shadow-2xs">
          <button
            type="button"
            onClick={() => {
              const next: DocumentFilterParams = { ...filters, pham_vi: 'NOI_BO', page: 1 };
              setFilters(next);
              syncFiltersToUrl(next);
            }}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
              filters.pham_vi === 'NOI_BO' || !filters.pham_vi
                ? 'bg-primary text-white shadow-xs'
                : 'text-secondary hover:text-main hover:bg-canvas/60'
            }`}
          >
            <i className="fa-solid fa-folder-open text-xs" />
            <span>{t('documents_ui.scopeTabs.internal') || 'Văn bản Nội bộ'}</span>
          </button>

          <button
            type="button"
            onClick={() => {
              const next: DocumentFilterParams = { ...filters, pham_vi: 'HAN_CHE', page: 1 };
              setFilters(next);
              syncFiltersToUrl(next);
            }}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
              filters.pham_vi === 'HAN_CHE'
                ? 'bg-rose-600 text-white shadow-xs'
                : 'text-secondary hover:text-main hover:bg-canvas/60'
            }`}
          >
            <i className={`fa-solid fa-shield-halved text-xs ${filters.pham_vi === 'HAN_CHE' ? 'text-white' : 'text-rose-500'}`} />
            <span>{t('documents_ui.scopeTabs.restricted') || 'Văn bản Hạn chế'}</span>
          </button>

          <button
            type="button"
            onClick={() => {
              const next: DocumentFilterParams = { ...filters, pham_vi: 'ALL', page: 1 };
              setFilters(next);
              syncFiltersToUrl(next);
            }}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all cursor-pointer ${
              filters.pham_vi === 'ALL'
                ? 'bg-canvas-subtle text-main font-semibold border border-border-subtle'
                : 'text-muted hover:text-secondary hover:bg-canvas/60'
            }`}
          >
            <span>{t('documents_ui.scopeTabs.all') || 'Tất cả'}</span>
          </button>
        </div>

        {filters.pham_vi === 'HAN_CHE' && (
          <div className="flex items-center justify-between gap-3 px-4 py-2.5 my-1 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-800 dark:text-amber-300 shadow-2xs w-full">
            <div className="flex items-center gap-2">
              <i className="fa-solid fa-shield-halved text-amber-600 dark:text-amber-400" />
              <span>
                {t('documents_ui.scopeTabs.restrictedNotice') || 'Đang lọc danh sách theo phạm vi: Văn bản hạn chế (Mật) — Chỉ hiển thị văn bản bạn có thẩm quyền tiếp cận.'}
              </span>
            </div>
            <button
              type="button"
              onClick={handleClearPhamVi}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface hover:bg-surface-elevated text-secondary hover:text-main text-xs border border-border-subtle transition-all cursor-pointer shadow-2xs"
              title={t('documents_ui.scopeTabs.clearFilterTitle') || 'Xóa bộ lọc phạm vi'}
            >
              <i className="fa-solid fa-xmark text-danger" />
              <span>{t('documents_ui.scopeTabs.clearFilter') || 'Bỏ lọc'}</span>
            </button>
          </div>
        )}
      </div>

      {/* 4. Thanh Tìm Kiếm & Bộ Lọc Đa Tiêu Chí */}
      <FilterBar
        filters={filters}
        onFilterChange={handleFilterChange}
        onSearch={fetchDocuments}
        onReset={handleResetFilters}
        isLoading={isLoading}
        availableYears={availableYears}
        availableFolders={availableFolders}
        availableDocTypes={availableDocTypes}
        folderDocTypesMap={folderDocTypesMap}
        recordDossiers={recordDossiers}
        recordDocTypes={recordDocTypes}
        documentType="DEN"
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
        onEdit={handleOpenEdit}
        onDelete={(id, soHieu) => {
          setPendingDelete({ id, soHieu });
        }}
      />

      {/* 5. Modals Nghiệp Vụ */}
      <DocumentDetailModal
        isOpen={isDetailOpen}
        onClose={handleCloseDetail}
        documentId={selectedDocId}
        loai="DEN"
      />

      <DocumentViewersModal
        isOpen={isViewersOpen}
        onClose={handleCloseHistory}
        documentId={selectedDocId}
        loai="DEN"
      />

      <DocumentFormModal
        open={isFormOpen}
        initial={editingDoc}
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
        loai="DEN"
        phamVi={importPhamVi}
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
