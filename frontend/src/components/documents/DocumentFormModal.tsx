import React, { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import apiClient from '@lib/apiClient';
import { DocumentDetail, DocumentItem, DocumentStatus, PaginatedResponse } from '@app-types/document';
import { Button } from '@components/common';
import AlertModal from '@components/common/AlertModal';

export type InitialDocType =
  | DocumentItem
  | DocumentDetail
  | (Omit<Partial<DocumentDetail>, 'hieu_luc'> & { hieu_luc?: string; [key: string]: unknown });

interface UserOption {
  id: number;
  ho_ten?: string;
  full_name?: string;
  username: string;
  don_vi_id?: number;
  don_vi_ten?: string;
  department?: string;
  chuc_vu_id?: number;
  chuc_vu_ten?: string;
}

interface ExistingAttachment {
  id: number;
  file: string;
  file_name: string;
  file_size?: number;
}

interface SuggestedDoc {
  id: number;
  so_hieu: string;
  trich_yeu: string;
  noi_ban_hanh?: string;
  loai_display?: string;
  nam?: number;
  ngay_ban_hanh?: string;
  ngay_den?: string;
  hieu_luc?: string;
  link_thay_the?: string;
}

interface FormState {
  loai: 'DEN' | 'DI';
  nam: number;
  so_hieu: string;
  so_thu_tu?: number | null;
  ngay_den: string;
  ngay_van_ban: string;
  noi_ban_hanh: string;
  trich_yeu: string;
  danh_muc_ho_so: string;
  ten_loai_van_ban: string;
  nguoi_ky: string;
  chuc_vu: string;
  hieu_luc: 'CON_HIEU_LUC' | 'CON_HIEU_LUC_1_PHAN' | 'HET_HIEU_LUC' | 'HET_VA_THAY_THE';
  ngay_het_hieu_luc: string;
  link_thay_the: string;
  ghi_chu: string;
  pham_vi: 'NOI_BO' | 'HAN_CHE';
  hien_thi: boolean;
  gui_mail_toan_he_thong: boolean;
  nguoi_nhan: (number | string)[];
}

interface DocumentFormInput extends Partial<DocumentDetail> {
  soHieu?: string;
  soDen?: number;
  ngayDen?: string;
  ngayVanBan?: string;
  ngay_thang_van_ban?: string;
  coQuanBanHanh?: string;
  co_quan_ban_hanh?: string;
  trichYeu?: string;
  danh_muc_ho_so?: string;
  danhMucHoSo?: string;
  ten_loai_van_ban?: string;
  loaiVanBan?: string;
  nguoiKy?: string;
  chucVu?: string;
  hieuLuc?: DocumentStatus;
  ngayHetHieuLuc?: string;
  linkThayThe?: string;
  ghiChu?: string;
  guiMailToanHeThong?: boolean;
  pham_vi?: 'NOI_BO' | 'HAN_CHE';
  nguoi_nhan?: (number | string | { id: number })[];
  don_vi_nhan?: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  initial?: InitialDocType | DocumentFormInput | null;
  onSaved?: (doc: Record<string, unknown> | DocumentFormInput) => void;
  defaultLoai?: 'DEN' | 'DI';
}

const DEFAULT_UNITS = [
  'Ban Giám hiệu',
  'Phòng Hành chính - Tổng hợp',
  'Phòng Đào tạo',
  'Phòng Công tác Sinh viên',
  'Phòng Kế hoạch - Tài chính',
  'Khoa Công nghệ Thông tin',
  'Khoa Điện - Điện tử',
  'Khoa Kinh tế',
];

const MOCK_STAFF_BY_UNIT: Record<string, UserOption[]> = {
  'Ban Giám hiệu': [
    { id: 1, ho_ten: 'Quản trị viên (Admin)', username: 'admin', don_vi_ten: 'Ban Giám hiệu' },
  ],
  'Phòng Hành chính - Tổng hợp': [
    { id: 2, ho_ten: 'Trần Cán Bộ', username: 'canbo', don_vi_ten: 'Phòng Hành chính - Tổng hợp' },
  ],
  'Phòng Đào tạo': [
    { id: 3, ho_ten: 'Lê Cán Bộ 2', username: 'canbo2', don_vi_ten: 'Phòng Đào tạo' },
  ],
};

function toLocalDateString(dateInput?: string | Date | null): string {
  if (!dateInput) return '';
  const d = new Date(dateInput);
  if (isNaN(d.getTime())) return '';
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function formatFileSize(bytes?: number): string {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function getFileIcon(fileName: string) {
  if (/\.pdf$/i.test(fileName)) return 'fa-solid fa-file-pdf text-rose-500';
  if (/\.docx?$/i.test(fileName)) return 'fa-solid fa-file-word text-blue-500';
  if (/\.(png|jpe?g)$/i.test(fileName)) return 'fa-solid fa-file-image text-emerald-500';
  return 'fa-solid fa-file text-slate-400';
}

function buildInitialForm(initDocInput?: InitialDocType | DocumentFormInput | null, defaultLoai: 'DEN' | 'DI' = 'DEN'): FormState {
  const now = new Date();
  const defaultDate = toLocalDateString(now);
  const initDoc = initDocInput as (Partial<DocumentDetail> & Record<string, unknown>) | null | undefined;

  if (!initDoc) {
    return {
      loai: defaultLoai,
      nam: now.getFullYear(),
      so_hieu: '',
      so_thu_tu: undefined,
      ngay_den: defaultDate,
      ngay_van_ban: defaultDate,
      noi_ban_hanh: '',
      trich_yeu: '',
      danh_muc_ho_so: '',
      ten_loai_van_ban: 'Công văn',
      nguoi_ky: '',
      chuc_vu: '',
      hieu_luc: 'CON_HIEU_LUC',
      ngay_het_hieu_luc: '',
      link_thay_the: '',
      ghi_chu: '',
      pham_vi: 'NOI_BO',
      hien_thi: true,
      gui_mail_toan_he_thong: false,
      nguoi_nhan: [],
    };
  }

  const recipients: (number | string)[] = [];
  if (Array.isArray(initDoc.nguoi_nhan)) {
    initDoc.nguoi_nhan.forEach((u: unknown) => recipients.push(typeof u === 'object' && u !== null && 'id' in u ? (u as { id: number | string }).id : (u as number | string)));
  } else if (Array.isArray(initDoc.nguoi_nhan_list)) {
    initDoc.nguoi_nhan_list.forEach((u: unknown) => { if (typeof u === 'object' && u !== null && 'id' in u) recipients.push((u as { id: number | string }).id); });
  }

  return {
    loai: ((initDoc.loai as 'DEN' | 'DI') || defaultLoai),
    nam: (initDoc.nam as number) ?? now.getFullYear(),
    so_hieu: (initDoc.so_hieu as string) ?? (initDoc.soHieu as string) ?? '',
    so_thu_tu: (initDoc.so_thu_tu as number) ?? (initDoc.soDen as number) ?? undefined,
    ngay_den: toLocalDateString((initDoc.ngay_den || initDoc.ngayDen || initDoc.ngay_ban_hanh || initDoc.ngayBanHanh) as string) || defaultDate,
    ngay_van_ban: toLocalDateString((initDoc.ngay_van_ban || initDoc.ngayVanBan || initDoc.ngay_thang_van_ban) as string) || defaultDate,
    noi_ban_hanh: (initDoc.noi_ban_hanh || initDoc.coQuanBanHanh || initDoc.co_quan_ban_hanh || '') as string,
    trich_yeu: (initDoc.trich_yeu || initDoc.trichYeu || '') as string,
    danh_muc_ho_so: (initDoc.danh_muc_ho_so || initDoc.danhMucHoSo || '') as string,
    ten_loai_van_ban: (initDoc.ten_loai_van_ban || initDoc.loaiVanBan || 'Công văn') as string,
    nguoi_ky: (initDoc.nguoi_ky || initDoc.nguoiKy || '') as string,
    chuc_vu: (initDoc.chuc_vu || initDoc.chucVu || '') as string,
    hieu_luc: ((initDoc.hieu_luc || initDoc.hieuLuc) as FormState['hieu_luc']) || 'CON_HIEU_LUC',
    ngay_het_hieu_luc: toLocalDateString((initDoc.ngay_het_hieu_luc || initDoc.ngayHetHieuLuc) as string),
    link_thay_the: (initDoc.link_thay_the || initDoc.linkThayThe || '') as string,
    ghi_chu: (initDoc.ghi_chu || initDoc.ghiChu || '') as string,
    pham_vi: (initDoc.pham_vi === 'HAN_CHE' ? 'HAN_CHE' : 'NOI_BO'),
    hien_thi: initDoc.hien_thi !== undefined ? Boolean(initDoc.hien_thi) : true,
    gui_mail_toan_he_thong: Boolean(initDoc.gui_mail_toan_he_thong ?? initDoc.guiMailToanHeThong),
    nguoi_nhan: recipients,
  };
}

export default function DocumentFormModal({ open, onClose, initial, onSaved, defaultLoai = 'DEN' }: Props) {
  const initDoc = initial as (Partial<DocumentDetail> & Record<string, unknown>) | null | undefined;
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<FormState>(() => buildInitialForm(initial, defaultLoai));
  const [units, setUnits] = useState<string[]>(DEFAULT_UNITS);
  const [staff, setStaff] = useState<UserOption[]>([]);
  const [selectedUnit, setSelectedUnit] = useState<string>(() => (initDoc?.don_vi_nhan as string) || '');
  const [existingAttachments, setExistingAttachments] = useState<ExistingAttachment[]>(() =>
    initDoc?.attachments && Array.isArray(initDoc.attachments) ? (initDoc.attachments as ExistingAttachment[]) : []
  );
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMsg, setAlertMsg] = useState('');

  // Gợi ý và tìm kiếm văn bản thay thế (theo yêu cầu của Kiệt)
  const [replacementSuggestions, setReplacementSuggestions] = useState<SuggestedDoc[]>([]);
  const [isSearchingReplacement, setIsSearchingReplacement] = useState(false);
  const [showReplacementDropdown, setShowReplacementDropdown] = useState(false);
  const [selectedReplacementDoc, setSelectedReplacementDoc] = useState<SuggestedDoc | null>(null);
  const [isReplacingOther, setIsReplacingOther] = useState(() => {
    const hasReplacement = Boolean(initDoc?.link_thay_the || initDoc?.linkThayThe);
    return hasReplacement && initDoc?.hieu_luc !== 'HET_VA_THAY_THE';
  });
  const [autoUpdateReplaced, setAutoUpdateReplaced] = useState(true);
  const replacementDropdownRef = useRef<HTMLDivElement | null>(null);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const filePattern = /\.(pdf|docx?|png|jpe?g)$/i;
  const maxFiles = 10;

  const [previousProps, setPreviousProps] = useState({ open, initial });
  if (previousProps.open !== open || previousProps.initial !== initial) {
    setPreviousProps({ open, initial });
    if (open) {
      setForm(buildInitialForm(initial, defaultLoai));
      setFiles([]);
      setIsDragging(false);
      setReplacementSuggestions([]);
      setShowReplacementDropdown(false);
      setSelectedReplacementDoc(null);
      setAutoUpdateReplaced(true);
      const hasReplacement = Boolean(initDoc?.link_thay_the || initDoc?.linkThayThe);
      setIsReplacingOther(hasReplacement && initDoc?.hieu_luc !== 'HET_VA_THAY_THE');
      if (initDoc?.attachments && Array.isArray(initDoc.attachments)) {
        setExistingAttachments(initDoc.attachments as ExistingAttachment[]);
      } else {
        setExistingAttachments([]);
      }
      setSelectedUnit((initDoc?.don_vi_nhan as string) || '');
      setStaff([]);
    }
  }

  async function fetchUnits() {
    try {
      const data = await apiClient.get<UserOption[] | PaginatedResponse<UserOption>>('/api/accounts/staffs/');
      const items = Array.isArray(data) ? data : data?.results || [];
      const depts = Array.from(new Set(items.map((u) => u.don_vi_ten || u.department).filter(Boolean))) as string[];
      if (depts.length > 0) {
        const merged = Array.from(new Set([...depts, ...DEFAULT_UNITS]));
        setUnits(merged);
        return;
      }
    } catch {
      // Fallback to default units
    }
    setUnits(DEFAULT_UNITS);
  }

  async function fetchStaffByUnit(unit: string) {
    if (!unit) {
      setStaff([]);
      return;
    }
    try {
      const data = await apiClient.get<UserOption[] | PaginatedResponse<UserOption>>(
        `/api/accounts/staffs/?department=${encodeURIComponent(unit)}`
      );
      const list: UserOption[] = Array.isArray(data) ? data : data?.results || [];
      if (list.length > 0) {
        setStaff(list);
        return;
      }
    } catch {
      // Use fallback
    }
    setStaff(MOCK_STAFF_BY_UNIT[unit] || []);
  }

  useEffect(() => {
    let cancelled = false;
    if (open) {
      const targetSoHieu = (initDoc?.link_thay_the || initDoc?.linkThayThe) as string | undefined;
      if (targetSoHieu) {
        apiClient.get<PaginatedResponse<SuggestedDoc> | SuggestedDoc[]>(`/api/documents/?q=${encodeURIComponent(targetSoHieu)}&page_size=3`)
          .then(res => {
            if (cancelled) return;
            const items = Array.isArray(res) ? res : res?.results || [];
            const found = items.find((document) => document.so_hieu === targetSoHieu);
            if (found) setSelectedReplacementDoc(found);
          })
          .catch(() => undefined);
      }

      const initialUnit = (initDoc?.don_vi_nhan as string) || '';
      Promise.resolve().then(() => {
        if (cancelled) return;
        void fetchUnits();
        if (initialUnit) void fetchStaffByUnit(initialUnit);
      });
    }
    return () => {
      cancelled = true;
    };
  }, [open, initDoc?.don_vi_nhan, initDoc?.linkThayThe, initDoc?.link_thay_the]);

  function handleUnitChange(unit: string) {
    setSelectedUnit(unit);
    fetchStaffByUnit(unit);
  }

  // Đóng dropdown gợi ý khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (replacementDropdownRef.current && !replacementDropdownRef.current.contains(e.target as Node)) {
        setShowReplacementDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    };
  }, []);

  const searchReplacementDocs = (query: string) => {
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);

    const trimmed = query.trim();
    setIsSearchingReplacement(true);
    setShowReplacementDropdown(true);

    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const endpoint = trimmed
          ? `/api/documents/?q=${encodeURIComponent(trimmed)}&page_size=8`
          : `/api/documents/?page_size=6`;
        const res = await apiClient.get<PaginatedResponse<SuggestedDoc> | SuggestedDoc[]>(endpoint);
        const items: SuggestedDoc[] = Array.isArray(res) ? res : res?.results || [];
        const currentSoHieu = (form.so_hieu || '').trim().toLowerCase();
        const filtered = items.filter(d => {
          if (d.id === (initial?.id as number | undefined)) return false;
          if (d.so_hieu && d.so_hieu.trim().toLowerCase() === currentSoHieu) return false;
          // Chặn chọn văn bản đang trỏ ngược lại văn bản hiện tại
          const otherLinks = (d.link_thay_the || '').toLowerCase().split(',').map(s => s.trim());
          if (currentSoHieu && otherLinks.includes(currentSoHieu)) return false;
          return true;
        });
        setReplacementSuggestions(filtered);
      } catch {
        setReplacementSuggestions([]);
      } finally {
        setIsSearchingReplacement(false);
      }
    }, 250);
  };

  const handleReplacementInputChange = (val: string) => {
    setForm(prev => ({ ...prev, link_thay_the: val }));
    if (selectedReplacementDoc && selectedReplacementDoc.so_hieu !== val.trim()) {
      setSelectedReplacementDoc(null);
    }
    searchReplacementDocs(val);
  };

  const handleSelectReplacementDoc = (doc: SuggestedDoc) => {
    setForm(prev => ({ ...prev, link_thay_the: doc.so_hieu }));
    setSelectedReplacementDoc(doc);
    setShowReplacementDropdown(false);
  };

  const handleReplacementInputFocus = () => {
    if (replacementSuggestions.length > 0) {
      setShowReplacementDropdown(true);
    } else {
      searchReplacementDocs(form.link_thay_the);
    }
  };

  function pushFiles(list: File[]) {
    const invalidFiles = list.filter(file => !filePattern.test(file.name));
    const validFiles = list.filter(file => filePattern.test(file.name));
    const remainingSlots = Math.max(maxFiles - files.length, 0);
    const acceptedFiles = validFiles.slice(0, remainingSlots);
    const warnings: string[] = [];

    if (invalidFiles.length) {
      warnings.push(`${invalidFiles.map(file => file.name).join(', ')} không được hỗ trợ. Chỉ chấp nhận PDF, DOC, DOCX, PNG, JPG.`);
    }

    if (validFiles.length > acceptedFiles.length) {
      warnings.push(`Chỉ được tải tối đa ${maxFiles} tệp.`);
    }

    if (warnings.length) {
      setAlertMsg(warnings.join(' '));
      setAlertOpen(true);
    }

    if (!acceptedFiles.length) return;

    setFiles(prev => [...prev, ...acceptedFiles].slice(0, maxFiles));
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const list = e.target.files ? Array.from(e.target.files) : [];
    pushFiles(list);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  function handleRemoveFile(index: number) {
    setFiles(prev => prev.filter((_, i) => i !== index));
  }


  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();

    if (!form.so_hieu?.trim()) {
      setAlertMsg('Vui lòng nhập Số, ký hiệu văn bản (*)');
      setAlertOpen(true);
      return;
    }
    if (!form.noi_ban_hanh?.trim()) {
      setAlertMsg('Vui lòng nhập Cơ quan / Đơn vị ban hành văn bản (*)');
      setAlertOpen(true);
      return;
    }
    if (!form.trich_yeu?.trim()) {
      setAlertMsg('Vui lòng nhập Trích yếu nội dung văn bản (*)');
      setAlertOpen(true);
      return;
    }
    if ((form.hieu_luc === 'HET_VA_THAY_THE' || isReplacingOther)) {
      if (!form.link_thay_the?.trim()) {
        setAlertMsg('Vui lòng nhập hoặc chọn Số hiệu văn bản thay thế (*)');
        setAlertOpen(true);
        return;
      }
      const targetSoHieu = form.link_thay_the.trim().toLowerCase();
      const currentSoHieu = (form.so_hieu || '').trim().toLowerCase();
      if (currentSoHieu && targetSoHieu === currentSoHieu) {
        setAlertMsg('Văn bản không thể tự thiết lập thay thế chính nó (*)');
        setAlertOpen(true);
        return;
      }

      // Khóa nghiệp vụ: Bắt buộc văn bản thay thế phải tồn tại trong hệ thống
      const matchedSuggestion = replacementSuggestions.find(
        d => d.so_hieu && d.so_hieu.trim().toLowerCase() === targetSoHieu
      );
      if (!selectedReplacementDoc && !matchedSuggestion) {
        try {
          const checkRes = await apiClient.get<{ results?: SuggestedDoc[] } | SuggestedDoc[]>(
            `/api/documents/?q=${encodeURIComponent(form.link_thay_the.trim())}&page_size=10`
          );
          const items: SuggestedDoc[] = Array.isArray(checkRes) ? checkRes : checkRes?.results || [];
          const exists = items.some(
            d => d.so_hieu && d.so_hieu.trim().toLowerCase() === targetSoHieu
          );
          if (!exists) {
            setAlertMsg(`Văn bản mục tiêu "${form.link_thay_the.trim()}" không tồn tại trong hệ thống. Vui lòng chọn văn bản từ danh sách gợi ý (*).`);
            setAlertOpen(true);
            return;
          }
        } catch {
          // Bỏ qua lỗi mạng cục bộ để backend serializer thực thi chốt chặn cuối cùng
        }
      }
    }
    if (form.pham_vi === 'HAN_CHE' && (!form.nguoi_nhan || form.nguoi_nhan.length === 0)) {
      setAlertMsg('Văn bản hạn chế bắt buộc phải chọn ít nhất một cán bộ nhận / xử lý (*)');
      setAlertOpen(true);
      return;
    }

    setLoading(true);
    try {
      const payload = new FormData();
      payload.append('loai', form.loai || defaultLoai);
      payload.append('nam', String(form.nam));
      payload.append('so_hieu', form.so_hieu.trim());
      payload.append('noi_ban_hanh', form.noi_ban_hanh.trim());
      payload.append('trich_yeu', form.trich_yeu.trim());
      payload.append('hieu_luc', form.hieu_luc);
      payload.append('pham_vi', form.pham_vi || 'NOI_BO');
      payload.append('hien_thi', form.hien_thi ? 'true' : 'false');
      payload.append('gui_mail_toan_he_thong', form.pham_vi === 'HAN_CHE' ? 'false' : (form.gui_mail_toan_he_thong ? 'true' : 'false'));

      if (form.loai === 'DI') {
        if (form.ngay_den) {
          payload.append('ngay_ban_hanh', form.ngay_den);
        }
      } else {
        if (form.ngay_den) {
          payload.append('ngay_den', form.ngay_den);
        }
      }
      if (form.ngay_van_ban) {
        payload.append('ngay_van_ban', form.ngay_van_ban);
      }
      if (form.nguoi_ky?.trim()) {
        payload.append('nguoi_ky', form.nguoi_ky.trim());
      }
      if (form.chuc_vu?.trim()) {
        payload.append('chuc_vu', form.chuc_vu.trim());
      }
      if (form.ghi_chu?.trim()) {
        payload.append('ghi_chu', form.ghi_chu.trim());
      }
      if ((form.hieu_luc === 'HET_VA_THAY_THE' || isReplacingOther) && form.link_thay_the?.trim()) {
        payload.append('link_thay_the', form.link_thay_the.trim());
        payload.append('auto_update_replaced_doc', autoUpdateReplaced ? 'true' : 'false');
      } else {
        payload.append('link_thay_the', '');
      }
      if (form.ngay_het_hieu_luc) {
        payload.append('ngay_het_hieu_luc', form.ngay_het_hieu_luc);
      }

      if (Array.isArray(form.nguoi_nhan)) {
        form.nguoi_nhan.forEach(userId => {
          if (userId) payload.append('nguoi_nhan', String(userId));
        });
      }

      files.forEach(f => payload.append('files', f));

      const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token') || '';

      // Mock giả lập khi chạy offline ở chế độ Dev
      if (import.meta.env.DEV && !token) {
        setTimeout(() => {
          const fakeData = {
            id: (initial?.id as number) || Date.now(),
            ...form,
            so_thu_tu: (initial?.so_thu_tu as number) || Math.floor(Math.random() * 50 + 1),
            ngay_den: form.ngay_den || toLocalDateString(new Date()),
            created_at: new Date().toISOString(),
            attachment_count: files.length + existingAttachments.length,
          };
          onSaved?.(fakeData);
          onClose();
        }, 500);
        return;
      }

      let res: Response;
      if (initial && initial.id) {
        res = await fetch(`/api/documents/${initial.id}/`, {
          method: 'PUT',
          body: payload,
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
      } else {
        res = await fetch('/api/documents/', {
          method: 'POST',
          body: payload,
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
      }

      if (res.ok) {
        const data = await res.json() as Record<string, unknown>;
        onSaved?.(data);
        onClose();
      } else {
        const err = await res.json().catch(() => ({ error: 'Không thể xử lý yêu cầu' }));
        let msg = err.error || err.detail;
        if (!msg) {
          const fieldErrors = Object.entries(err)
            .map(([field, errs]) => `${field}: ${Array.isArray(errs) ? errs.join(', ') : errs}`)
            .join('; ');
          msg = fieldErrors || JSON.stringify(err);
        }
        setAlertMsg('Lỗi từ máy chủ: ' + msg);
        setAlertOpen(true);
      }
    } catch (err: unknown) {
      setAlertMsg('Lỗi kết nối máy chủ: ' + (err instanceof Error ? err.message : String(err)));
      setAlertOpen(true);
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-4 md:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity" onClick={onClose} />

      {/* Modal Dialog Card */}
      <form
        className="bg-surface border border-border-subtle rounded-2xl shadow-2xl z-10 w-[940px] max-w-full flex flex-col max-h-[88vh] my-auto animate-in fade-in zoom-in-95 duration-150"
        onSubmit={handleSubmit}
      >
        {/* Sticky Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle shrink-0">
          <div className="flex items-center gap-3">
            <span className="w-10 h-10 rounded-xl bg-primary-subtle text-primary flex items-center justify-center text-lg">
              <i className={initial?.id ? 'fa-solid fa-file-pen' : 'fa-solid fa-file-circle-plus'} />
            </span>
            <div>
              <h3 className="text-base font-bold text-main m-0">
                {initial?.id
                  ? (form.loai === 'DI' ? 'Cập Nhật Văn Bản Đi' : 'Cập Nhật Văn Bản Đến')
                  : (form.loai === 'DI' ? 'Thêm Mới Văn Bản Đi' : 'Thêm Mới Văn Bản Đến')}
              </h3>
              <p className="text-xs text-muted m-0">
                {initial?.id
                  ? `Chỉnh sửa thông tin hồ sơ văn bản ${form.so_hieu || ''}`
                  : (form.loai === 'DI' ? 'Vào sổ công văn đi và quản lý phát hành nội bộ' : 'Tiếp nhận, vào sổ công văn đến và phân phối xử lý nội bộ')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-muted hover:text-main hover:bg-hover flex items-center justify-center transition-fast"
            title="Đóng cửa sổ"
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {/* PHẦN 1: TIẾP NHẬN & VÀO SỔ */}
          <div className="bg-canvas/40 border border-border-subtle rounded-xl p-4.5 space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle/60">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-blue-500/10 text-blue-600 flex items-center justify-center text-xs font-bold">
                  <i className="fa-solid fa-inbox" />
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-main m-0">
                  1. Tiếp nhận & Vào sổ công văn
                </h4>
              </div>
              <span className="text-xs text-muted">Thông tin định danh văn bản</span>
            </div>

            <div className="grid grid-cols-12 gap-3.5">
              {/* Năm */}
              <div className="col-span-12 sm:col-span-2">
                <label className="block text-xs font-semibold text-secondary mb-1.5">Năm</label>
                <input
                  type="number"
                  value={form.nam}
                  onChange={e => setForm({ ...form, nam: Number(e.target.value) })}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main text-center focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Số đến / Số đi */}
              <div className="col-span-12 sm:col-span-3">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {form.loai === 'DI' ? 'Số đi' : 'Số đến'} <span className="text-muted font-normal text-xs">(Tự động)</span>
                </label>
                <input
                  readOnly
                  value={form.so_thu_tu ? `#${form.so_thu_tu}` : 'Tự động cấp tăng dần'}
                  className="w-full text-sm bg-hover/70 border border-border-subtle rounded-xl px-3 py-2 text-muted font-medium cursor-not-allowed select-none"
                  title="Số thứ tự được hệ thống tự động sinh tăng dần theo năm"
                />
              </div>

              {/* Ngày đến / Ngày ban hành */}
              <div className="col-span-12 sm:col-span-4">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {form.loai === 'DI' ? 'Ngày ban hành' : 'Ngày đến'} <span className="text-danger">*</span>
                </label>
                <input
                  type="date"
                  value={form.ngay_den}
                  onChange={e => setForm({ ...form, ngay_den: e.target.value })}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                  required
                />
              </div>

              {/* Số, ký hiệu */}
              <div className="col-span-12 sm:col-span-3">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Số, ký hiệu <span className="text-danger">*</span>
                </label>
                <input
                  value={form.so_hieu}
                  onChange={e => setForm({ ...form, so_hieu: e.target.value })}
                  placeholder="VD: 125/BGDDT-VP"
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main font-medium placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                  required
                />
              </div>

              {/* Ngày văn bản */}
              <div className="col-span-12 sm:col-span-4">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Ngày ban hành trên VB
                </label>
                <input
                  type="date"
                  value={form.ngay_van_ban}
                  onChange={e => setForm({ ...form, ngay_van_ban: e.target.value })}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Danh mục hồ sơ (chia danh mục trước rồi mới chia theo loại văn bản) */}
              <div className="col-span-12 sm:col-span-4">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Danh mục hồ sơ
                </label>
                <input
                  list="folder-types-list"
                  value={form.danh_muc_ho_so}
                  onChange={e => setForm({ ...form, danh_muc_ho_so: e.target.value })}
                  placeholder="VD: Hồ sơ công văn đến..."
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
                <datalist id="folder-types-list">
                  <option value="Hồ sơ công văn đến năm 2026" />
                  <option value="Hồ sơ chỉ đạo điều hành năm 2026" />
                  <option value="Hồ sơ nhân sự & tổ chức" />
                  <option value="Hồ sơ tài chính & dự án" />
                </datalist>
              </div>

              {/* Loại văn bản */}
              <div className="col-span-12 sm:col-span-4">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Loại văn bản
                </label>
                <input
                  list="doc-types-list"
                  value={form.ten_loai_van_ban}
                  onChange={e => setForm({ ...form, ten_loai_van_ban: e.target.value })}
                  placeholder="VD: Công văn, Quyết định..."
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
                <datalist id="doc-types-list">
                  <option value="Công văn" />
                  <option value="Quyết định" />
                  <option value="Thông báo" />
                  <option value="Tờ trình" />
                  <option value="Kế hoạch" />
                  <option value="Chỉ thị" />
                  <option value="Nghị quyết" />
                  <option value="Báo cáo" />
                  <option value="Hướng dẫn" />
                </datalist>
              </div>

              {/* Phạm vi lưu hành (Issue #82) */}
              <div className="col-span-12 sm:col-span-4">
                <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center justify-between">
                  <span>Phạm vi lưu hành</span>
                  {form.pham_vi === 'HAN_CHE' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-600 font-bold uppercase">
                      Hạn chế
                    </span>
                  )}
                </label>
                <select
                  value={form.pham_vi}
                  disabled={Boolean(initial?.id)}
                  onChange={e => setForm({
                    ...form,
                    pham_vi: e.target.value as 'NOI_BO' | 'HAN_CHE',
                    gui_mail_toan_he_thong: e.target.value === 'HAN_CHE' ? false : form.gui_mail_toan_he_thong,
                  })}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  <option value="NOI_BO">Nội bộ (Toàn cơ quan)</option>
                  <option value="HAN_CHE">Hạn chế (Chỉ người nhận xem)</option>
                </select>
              </div>
            </div>
          </div>

          {/* PHẦN 2: NGUỒN BAN HÀNH & NỘI DUNG VĂN BẢN */}
          <div className="bg-canvas/40 border border-border-subtle rounded-xl p-4.5 space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle/60">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-indigo-500/10 text-indigo-600 flex items-center justify-center text-xs font-bold">
                  <i className="fa-solid fa-building-columns" />
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-main m-0">
                  2. Nguồn ban hành & Nội dung văn bản
                </h4>
              </div>
              <span className="text-xs text-muted">Cơ quan gửi & Trích yếu</span>
            </div>

            <div className="space-y-3.5">
              {/* Cơ quan ban hành */}
              <div>
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Cơ quan / Đơn vị ban hành <span className="text-danger">*</span>
                </label>
                <input
                  value={form.noi_ban_hanh}
                  onChange={e => setForm({ ...form, noi_ban_hanh: e.target.value })}
                  placeholder="Ví dụ: Bộ Giáo dục và Đào tạo, UBND Thành phố Hồ Chí Minh, ..."
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                  required
                />
              </div>

              {/* Trích yếu nội dung */}
              <div>
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Trích yếu nội dung văn bản <span className="text-danger">*</span>
                </label>
                <textarea
                  rows={3}
                  value={form.trich_yeu}
                  onChange={e => setForm({ ...form, trich_yeu: e.target.value })}
                  placeholder="Nhập tóm tắt ngắn gọn mục đích và nội dung cốt lõi của văn bản..."
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl p-3 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast resize-y"
                  required
                />
              </div>
            </div>
          </div>

          {/* PHẦN 3: KÝ DUYỆT & HIỆU LỰC VĂN BẢN */}
          <div className="bg-canvas/40 border border-border-subtle rounded-xl p-4.5 space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle/60">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-emerald-500/10 text-emerald-600 flex items-center justify-center text-xs font-bold">
                  <i className="fa-solid fa-stamp" />
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-main m-0">
                  3. Ký duyệt & Hiệu lực văn bản
                </h4>
              </div>
              <span className="text-xs text-muted">Thông tin người ký & Trạng thái pháp lý</span>
            </div>

            <div className="grid grid-cols-12 gap-3.5">
              {/* Người ký */}
              <div className="col-span-12 sm:col-span-6">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Người ký văn bản
                </label>
                <input
                  value={form.nguoi_ky}
                  onChange={e => setForm({ ...form, nguoi_ky: e.target.value })}
                  placeholder="Họ và tên người ký (VD: Nguyễn Văn A)"
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Chức vụ */}
              <div className="col-span-12 sm:col-span-6">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Chức vụ người ký
                </label>
                <input
                  value={form.chuc_vu}
                  onChange={e => setForm({ ...form, chuc_vu: e.target.value })}
                  placeholder="VD: Thứ trưởng, Giám đốc, Hiệu trưởng..."
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Trạng thái hiệu lực (Hiển thị màu sắc động & hiệu ứng tương ứng với trạng thái) */}
              <div className="col-span-12 sm:col-span-6">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-secondary m-0">
                    Trạng thái hiệu lực
                  </label>
                  {form.hieu_luc === 'CON_HIEU_LUC' && (
                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      Đang áp dụng
                    </span>
                  )}
                  {form.hieu_luc === 'CON_HIEU_LUC_1_PHAN' && (
                    <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
                      Hiệu lực 1 phần
                    </span>
                  )}
                  {form.hieu_luc === 'HET_HIEU_LUC' && (
                    <span className="text-xs font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                      Hết giá trị
                    </span>
                  )}
                  {form.hieu_luc === 'HET_VA_THAY_THE' && (
                    <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                      Đã bị thay thế
                    </span>
                  )}
                </div>

                <div className="relative">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none flex items-center">
                    {form.hieu_luc === 'CON_HIEU_LUC' && (
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                      </span>
                    )}
                    {form.hieu_luc === 'CON_HIEU_LUC_1_PHAN' && (
                      <span className="relative flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-purple-500" />
                      </span>
                    )}
                    {form.hieu_luc === 'HET_HIEU_LUC' && (
                      <span className="inline-flex rounded-full h-2.5 w-2.5 bg-rose-500" />
                    )}
                    {form.hieu_luc === 'HET_VA_THAY_THE' && (
                      <span className="inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
                    )}
                  </div>

                  <select
                    value={form.hieu_luc}
                    onChange={e => {
                      const newHieuLuc = e.target.value as FormState['hieu_luc'];
                      setForm({ ...form, hieu_luc: newHieuLuc });
                      if (newHieuLuc !== 'HET_VA_THAY_THE' && !isReplacingOther) {
                        setForm(prev => ({ ...prev, link_thay_the: '' }));
                        setSelectedReplacementDoc(null);
                        setShowReplacementDropdown(false);
                      }
                    }}
                    className={`w-full text-sm rounded-xl pl-8 pr-8 py-2 font-semibold transition-all duration-200 border cursor-pointer ${
                      form.hieu_luc === 'CON_HIEU_LUC'
                        ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-700 dark:text-emerald-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 shadow-xs'
                        : form.hieu_luc === 'CON_HIEU_LUC_1_PHAN'
                        ? 'bg-purple-500/10 border-purple-500/40 text-purple-700 dark:text-purple-400 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 shadow-xs'
                        : form.hieu_luc === 'HET_HIEU_LUC'
                        ? 'bg-rose-500/10 border-rose-500/40 text-rose-700 dark:text-rose-400 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 shadow-xs'
                        : 'bg-amber-500/10 border-amber-500/40 text-amber-700 dark:text-amber-400 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 shadow-xs'
                    }`}
                  >
                    {form.hieu_luc === 'HET_VA_THAY_THE' && (
                      <option value="HET_VA_THAY_THE" disabled className="bg-surface text-main font-normal">
                        Đã bị thay thế (Hệ thống tự động)
                      </option>
                    )}
                    <option value="CON_HIEU_LUC" className="bg-surface text-emerald-600 font-semibold">
                      Còn hiệu lực
                    </option>
                    <option value="CON_HIEU_LUC_1_PHAN" className="bg-surface text-purple-600 font-semibold">
                      Còn hiệu lực 1 phần
                    </option>
                    <option value="HET_HIEU_LUC" className="bg-surface text-rose-600 font-semibold">
                      Hết hiệu lực
                    </option>
                  </select>
                </div>
              </div>

              {/* Ngày hết hiệu lực */}
              <div className="col-span-12 sm:col-span-6">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Ngày hết hiệu lực <span className="text-muted font-normal text-xs">(Tùy chọn)</span>
                </label>
                <input
                  type="date"
                  value={form.ngay_het_hieu_luc}
                  onChange={e => setForm({ ...form, ngay_het_hieu_luc: e.target.value })}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Tùy chọn thay thế cho văn bản khác khi trạng thái Còn hiệu lực hoặc Còn hiệu lực 1 phần */}
              {(form.hieu_luc === 'CON_HIEU_LUC' || form.hieu_luc === 'CON_HIEU_LUC_1_PHAN') && (
                <div className="col-span-12 pt-1">
                  <label className="inline-flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={isReplacingOther}
                      onChange={e => {
                        setIsReplacingOther(e.target.checked);
                        if (!e.target.checked) {
                          setForm(prev => ({ ...prev, link_thay_the: '' }));
                          setSelectedReplacementDoc(null);
                          setShowReplacementDropdown(false);
                        }
                      }}
                      className="w-4 h-4 text-primary rounded border-border-subtle focus:ring-primary/20 transition-fast"
                    />
                    <span className="text-xs font-semibold text-main">
                      <i className="fa-solid fa-repeat text-primary mr-1" />
                      Văn bản này thay thế cho văn bản khác trong hệ thống
                    </span>
                  </label>
                </div>
              )}

              {/* Link văn bản thay thế (Hiển thị linh hoạt kèm bộ gợi ý tìm kiếm văn bản tương ứng) */}
              {(form.hieu_luc === 'HET_VA_THAY_THE' || isReplacingOther) && (
                <div className="col-span-12 animate-in fade-in duration-150" ref={replacementDropdownRef}>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-semibold text-warning-text m-0">
                      <i className="fa-solid fa-link mr-1.5" />
                      {isReplacingOther || form.hieu_luc === 'CON_HIEU_LUC' || form.hieu_luc === 'CON_HIEU_LUC_1_PHAN'
                        ? 'Văn bản bị thay thế (Số hiệu hoặc liên kết) *'
                        : 'Văn bản mới thay thế (Số hiệu hoặc liên kết) *'}
                    </label>
                    <span className="text-xs text-muted">
                      {isReplacingOther || form.hieu_luc === 'CON_HIEU_LUC' || form.hieu_luc === 'CON_HIEU_LUC_1_PHAN'
                        ? 'Gõ số hiệu văn bản cũ để tìm nhanh'
                        : 'Gõ số hiệu hoặc từ khóa để gợi ý'}
                    </span>
                  </div>

                  <div className="relative">
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none">
                      <i className="fa-solid fa-magnifying-glass" />
                    </div>

                    <input
                      type="text"
                      value={form.link_thay_the}
                      onChange={e => handleReplacementInputChange(e.target.value)}
                      onFocus={handleReplacementInputFocus}
                      placeholder="Nhập số hiệu văn bản (VD: 88/QD-SNN), trích yếu hoặc liên kết..."
                      className="w-full text-sm bg-surface border border-warning-border rounded-xl pl-9 pr-9 py-2 text-main placeholder:text-muted focus:outline-none focus:border-warning focus:ring-1 focus:ring-warning transition-fast"
                      required
                      autoComplete="off"
                    />

                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                      {isSearchingReplacement && (
                        <i className="fa-solid fa-circle-notch fa-spin text-warning-text text-xs" />
                      )}
                      {form.link_thay_the && !isSearchingReplacement && (
                        <button
                          type="button"
                          onClick={() => handleReplacementInputChange('')}
                          className="text-muted hover:text-danger p-0.5 rounded transition-colors"
                          title="Xóa nội dung"
                        >
                          <i className="fa-solid fa-xmark text-xs" />
                        </button>
                      )}
                    </div>

                    {/* Dropdown danh sách văn bản gợi ý */}
                    {showReplacementDropdown && (
                      <div className="absolute z-50 left-0 right-0 top-full mt-1.5 bg-surface border border-border-subtle rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto animate-in fade-in slide-in-from-top-1 duration-150">
                        <div className="px-3 py-2 bg-canvas/80 border-b border-border-subtle/80 flex items-center justify-between text-xs font-semibold text-secondary sticky top-0 backdrop-blur-sm z-10">
                          <span className="flex items-center gap-1.5">
                            <i className="fa-solid fa-list-check text-primary" />
                            {form.link_thay_the.trim() ? (
                              <>Kết quả tìm kiếm ({replacementSuggestions.length})</>
                            ) : (
                              <>Văn bản trong hệ thống ({replacementSuggestions.length})</>
                            )}
                          </span>
                          <span className="text-xs text-muted">Nhấp vào để chọn</span>
                        </div>

                        {replacementSuggestions.length > 0 ? (
                          <div className="divide-y divide-border-subtle/40">
                            {replacementSuggestions.map(doc => (
                              <div
                                key={doc.id}
                                onClick={() => handleSelectReplacementDoc(doc)}
                                className="p-3 hover:bg-primary/5 cursor-pointer transition-colors group text-left"
                              >
                                <div className="flex items-center justify-between gap-2 mb-1">
                                  <div className="flex items-center gap-2">
                                    <span className="font-semibold text-xs text-primary font-mono group-hover:underline">
                                      {doc.so_hieu}
                                    </span>
                                    {doc.loai_display && (
                                      <span className="text-xs px-1.5 py-0.5 rounded bg-muted/20 text-secondary font-medium">
                                        {doc.loai_display}
                                      </span>
                                    )}
                                  </div>
                                  {(doc.ngay_ban_hanh || doc.ngay_den) && (
                                    <span className="text-xs text-muted font-mono">
                                      {new Date(doc.ngay_ban_hanh || doc.ngay_den!).toLocaleDateString('vi-VN')}
                                    </span>
                                  )}
                                </div>
                                <p className="text-xs text-main line-clamp-2 m-0 group-hover:text-primary transition-colors leading-relaxed">
                                  {doc.trich_yeu}
                                </p>
                                {doc.noi_ban_hanh && (
                                  <div className="text-xs text-muted mt-1 flex items-center gap-1.5">
                                    <i className="fa-solid fa-building text-xs" />
                                    <span className="truncate">{doc.noi_ban_hanh}</span>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : !isSearchingReplacement ? (
                          <div className="p-4 text-center text-xs text-muted">
                            <i className="fa-solid fa-circle-info text-muted mr-1.5" />
                            Không tìm thấy văn bản phù hợp trong hệ thống. Vui lòng chọn số hiệu văn bản có sẵn trong danh mục.
                          </div>
                        ) : null}
                      </div>
                    )}
                  </div>

                  {/* Thẻ hiển thị văn bản đã liên kết thành công */}
                  {selectedReplacementDoc && (
                    <div className="mt-2.5 p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-start justify-between gap-2.5 animate-in fade-in duration-150">
                      <div className="flex items-start gap-2.5 min-w-0">
                        <div className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-600 flex items-center justify-center text-xs shrink-0 mt-0.5">
                          <i className="fa-solid fa-file-circle-check" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-emerald-700 font-mono">
                              {selectedReplacementDoc.so_hieu}
                            </span>
                            {selectedReplacementDoc.noi_ban_hanh && (
                              <span className="text-xs text-secondary truncate">
                                • {selectedReplacementDoc.noi_ban_hanh}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-secondary line-clamp-1 m-0 mt-0.5">
                            {selectedReplacementDoc.trich_yeu}
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedReplacementDoc(null);
                          setForm(prev => ({ ...prev, link_thay_the: '' }));
                        }}
                        className="text-xs text-secondary hover:text-danger p-1 rounded transition-colors shrink-0"
                        title="Hủy liên kết"
                      >
                        <i className="fa-solid fa-xmark" />
                      </button>
                    </div>
                  )}

                  {/* Phương án 2: Checkbox xác nhận tự động cập nhật văn bản liên quan */}
                  <div className="mt-2.5 p-2.5 bg-surface border border-border-subtle rounded-xl flex items-center justify-between gap-2 select-none">
                    <label className="inline-flex items-center gap-2 cursor-pointer text-xs text-main m-0">
                      <input
                        type="checkbox"
                        checked={autoUpdateReplaced}
                        onChange={e => setAutoUpdateReplaced(e.target.checked)}
                        className="w-4 h-4 text-primary rounded border-border-subtle focus:ring-primary/20 transition-fast"
                      />
                      <span>
                        {isReplacingOther || form.hieu_luc === 'CON_HIEU_LUC' || form.hieu_luc === 'CON_HIEU_LUC_1_PHAN' ? (
                          <>Tự động cập nhật văn bản cũ sang trạng thái <strong className="text-warning-text">Đã thay thế</strong></>
                        ) : (
                          <>Tự động đồng bộ liên kết 2 chiều giữa hai văn bản</>
                        )}
                      </span>
                    </label>
                    <span className="text-xs text-muted hidden sm:inline">(Tự động hóa)</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* PHẦN 4: PHÂN PHỐI XỬ LÝ & TỆP ĐÍNH KÈM */}
          <div className="bg-canvas/40 border border-border-subtle rounded-xl p-4.5 space-y-4">
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle/60">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-md bg-amber-500/10 text-amber-600 flex items-center justify-center text-xs font-bold">
                  <i className="fa-solid fa-share-nodes" />
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-main m-0">
                  4. Phân phối xử lý & Tệp đính kèm
                </h4>
              </div>
              <span className="text-xs text-muted">Điều phối đơn vị & Tải lên tệp</span>
            </div>

            {form.pham_vi === 'HAN_CHE' && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl flex items-center gap-2.5 text-xs text-amber-600 dark:text-amber-400">
                <i className="fa-solid fa-shield-halved text-sm shrink-0" />
                <span>
                  <strong>Văn bản hạn chế (Mật nội bộ):</strong> Bắt buộc chọn ít nhất một cán bộ nhận / xử lý. Hệ thống tự động vô hiệu hóa tính năng gửi email toàn trường và chỉ người nhận cùng người tạo mới có quyền xem.
                </span>
              </div>
            )}

            {/* Phân phối đơn vị & cán bộ */}
            <div className="grid grid-cols-12 gap-3.5">
              <div className="col-span-12 sm:col-span-6">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Đơn vị nhận / chủ trì xử lý
                </label>
                <select
                  value={selectedUnit}
                  onChange={e => handleUnitChange(e.target.value)}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                >
                  <option value="">-- Chọn đơn vị nhận --</option>
                  {units.map(u => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
              </div>

              <div className="col-span-12 sm:col-span-6">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Cán bộ nhận / xử lý
                </label>
                {staff.length === 0 ? (
                  <div className="w-full text-xs text-muted border border-border-subtle rounded-xl p-2.5 bg-surface text-center">
                    {selectedUnit ? 'Không có cán bộ trong danh sách' : 'Vui lòng chọn đơn vị để hiển thị cán bộ'}
                  </div>
                ) : (
                  <div className="max-h-28 overflow-y-auto border border-border-subtle rounded-xl p-2 bg-surface space-y-1">
                    {staff.map(s => {
                      const isSelected = form.nguoi_nhan.includes(s.id);
                      return (
                        <label
                          key={s.id}
                          className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-hover cursor-pointer text-xs text-main"
                        >
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={e => {
                              const checked = e.target.checked;
                              setForm(prev => ({
                                ...prev,
                                nguoi_nhan: checked
                                  ? [...prev.nguoi_nhan, s.id]
                                  : prev.nguoi_nhan.filter(id => id !== s.id),
                              }));
                            }}
                            className="rounded border-border-subtle text-primary focus:ring-primary"
                          />
                          <span className="font-medium">{s.ho_ten || s.full_name || s.username}</span>
                          <span className="text-xs text-muted">(@{s.username})</span>
                        </label>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Existing Attachments if editing */}
            {existingAttachments.length > 0 && (
              <div>
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Tệp đính kèm hiện có ({existingAttachments.length})
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {existingAttachments.map(att => (
                    <div
                      key={att.id}
                      className="flex items-center justify-between p-2.5 bg-surface border border-border-subtle rounded-xl text-xs"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <i className={`${getFileIcon(att.file_name)} text-sm shrink-0`} />
                        <span className="truncate text-main font-medium" title={att.file_name}>
                          {att.file_name}
                        </span>
                        {att.file_size && (
                          <span className="text-xs text-muted shrink-0">
                            ({formatFileSize(att.file_size)})
                          </span>
                        )}
                      </div>
                      <a
                        href={att.file}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline text-xs shrink-0 ml-2"
                        title="Xem / Tải về"
                      >
                        <i className="fa-solid fa-download" />
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Drag & Drop Upload Zone */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-secondary">
                  Tải lên tệp đính kèm mới
                </label>
                <span className="text-xs text-muted">
                  Hỗ trợ PDF, DOC, DOCX, PNG, JPG (Tối đa 10 tệp)
                </span>
              </div>

              <div
                onDragOver={e => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={e => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer?.files) {
                    pushFiles(Array.from(e.dataTransfer.files));
                  }
                }}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-fast ${
                  isDragging
                    ? 'border-primary bg-primary-subtle/30 scale-[1.005]'
                    : 'border-border-subtle hover:border-primary/50 hover:bg-hover/60 bg-surface'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
                  className="hidden"
                  onChange={handleFileSelect}
                />
                <div className="w-10 h-10 rounded-full bg-primary-subtle text-primary mx-auto flex items-center justify-center text-lg mb-2">
                  <i className="fa-solid fa-cloud-arrow-up" />
                </div>
                <p className="text-xs font-medium text-main m-0">
                  Kéo thả tệp vào đây hoặc <span className="text-primary underline">chọn từ thiết bị</span>
                </p>
                <p className="text-xs text-muted m-0 mt-1">
                  Tập tin đính kèm minh chứng, công văn scan hoặc bản mềm
                </p>
              </div>

              {/* File List Selected */}
              {files.length > 0 && (
                <div className="mt-2.5 space-y-1.5">
                  <div className="text-xs font-semibold text-secondary">
                    {files.length} tệp đã chọn sẵn sàng tải lên:
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {files.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2 px-3 bg-surface border border-border-subtle rounded-xl text-xs"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <i className={`${getFileIcon(file.name)} text-sm shrink-0`} />
                          <span className="truncate text-main font-medium" title={file.name}>
                            {file.name}
                          </span>
                          <span className="text-xs text-muted shrink-0">
                            ({formatFileSize(file.size)})
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={e => {
                            e.stopPropagation();
                            handleRemoveFile(idx);
                          }}
                          className="w-5 h-5 rounded hover:bg-danger-subtle hover:text-danger text-muted flex items-center justify-center transition-fast ml-2 shrink-0 cursor-pointer"
                          title="Xóa tệp này"
                        >
                          <i className="fa-solid fa-xmark text-xs" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Ghi chú & Cấu hình hệ thống */}
            <div className="pt-2 border-t border-border-subtle/60 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  Ghi chú nội bộ
                </label>
                <input
                  value={form.ghi_chu}
                  onChange={e => setForm({ ...form, ghi_chu: e.target.value })}
                  placeholder="Ghi chú thêm về xử lý, lưu kho hoặc chỉ đạo..."
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Toggle Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                {/* Hiển thị */}
                <label className="flex items-start gap-3 p-3 rounded-xl border border-border-subtle bg-surface hover:bg-hover/50 cursor-pointer transition-fast">
                  <input
                    type="checkbox"
                    checked={form.hien_thi}
                    onChange={e => setForm({ ...form, hien_thi: e.target.checked })}
                    className="mt-0.5 rounded border-border-subtle text-primary focus:ring-primary"
                  />
                  <div>
                    <span className="text-xs font-bold text-main block">Hiển thị trên hệ thống</span>
                    <span className="text-xs text-muted block leading-snug">
                      Cho phép cán bộ nhân viên tra cứu và xem văn bản này
                    </span>
                  </div>
                </label>

                {/* Gửi mail (Chỉ cho Văn bản thông thường, Văn bản Hạn chế không gửi mail toàn trường) */}
                {form.pham_vi !== 'HAN_CHE' ? (
                  <label className="flex items-start gap-3 p-3 rounded-xl border border-border-subtle bg-surface hover:bg-hover/50 cursor-pointer transition-fast">
                    <input
                      type="checkbox"
                      checked={form.gui_mail_toan_he_thong}
                      onChange={e => setForm({ ...form, gui_mail_toan_he_thong: e.target.checked })}
                      className="mt-0.5 rounded border-border-subtle text-primary focus:ring-primary"
                    />
                    <div>
                      <span className="text-xs font-bold text-main block">Gửi email toàn trường</span>
                      <span className="text-xs text-muted block leading-snug">
                        Tự động gửi thông báo văn bản mới tới hòm thư CBNV
                      </span>
                    </div>
                  </label>
                ) : (
                  <div className="flex items-start gap-3 p-3 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-700 dark:text-rose-300">
                    <span className="text-base leading-none">🔒</span>
                    <div>
                      <span className="text-xs font-bold block">
                        {form.pham_vi === 'HAN_CHE' ? 'Văn bản Hạn chế (Mật nội bộ)' : 'Văn bản Mật lưu hành nội bộ'}
                      </span>
                      <span className="text-xs text-muted block leading-snug">
                        Không gửi email diện rộng toàn trường. Chỉ cán bộ nhận được chỉ định mới có quyền tiếp cận.
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Sticky Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-border-subtle bg-surface shrink-0">
          <div className="text-xs text-muted flex items-center gap-1.5">
            <span className="text-danger font-bold">*</span>
            <span>Các trường có dấu sao đỏ là bắt buộc nhập</span>
          </div>
          <div className="flex items-center gap-2.5">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onClose}
              disabled={loading}
            >
              Hủy bỏ
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              icon={loading ? 'fa-spinner fa-spin' : 'fa-floppy-disk'}
              disabled={loading}
            >
              {loading ? 'Đang lưu...' : initial?.id ? 'Cập nhật' : 'Lưu văn bản'}
            </Button>
          </div>
        </div>
      </form>

      <AlertModal
        open={alertOpen}
        onClose={() => setAlertOpen(false)}
        message={alertMsg}
      />
    </div>,
    document.body
  );
}
