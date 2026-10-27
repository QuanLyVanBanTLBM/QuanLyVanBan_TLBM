/* eslint-disable react-refresh/only-export-components -- file này export kèm các helper tiện ích parse và format chuỗi thay thế dùng chung cho modal và test */
import React, { useEffect, useState, useRef, useMemo } from 'react';
import { createPortal } from 'react-dom';
import apiClient, { ApiError } from '@lib/apiClient';
import { authService } from '@lib/authService';
import { DocumentDetail, DocumentItem, DocumentStatus, PaginatedResponse } from '@app-types/document';
import { Button } from '@components/common';
import AlertModal from '@components/common/AlertModal';
import { useTranslation } from '@i18n/translate';

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
  so_thu_tu?: number;
  so_den?: number;
  trich_yeu: string;
  noi_ban_hanh?: string;
  nguoi_ky?: string;
  loai_display?: string;
  nam?: number;
  ngay_ban_hanh?: string;
  ngay_den?: string;
  hieu_luc?: string;
  link_thay_the?: string;
}

interface FormState {
  loai: 'DEN' | 'DI' | 'MAT';
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
  defaultLoai?: 'DEN' | 'DI' | 'MAT';
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

const DEFAULT_DOC_TYPES = [
  'Công văn',
  'Quyết định',
  'Thông báo',
  'Kế hoạch',
  'Hướng dẫn',
  'Báo cáo',
  'Tờ trình',
  'Chỉ thị',
  'Nghị quyết',
];

const DEFAULT_INTERNAL_FOLDERS: Record<string, string[]> = {
  'Hồ sơ Hành chính - Quản trị': ['Công văn', 'Thông báo', 'Tờ trình', 'Kế hoạch', 'Báo cáo'],
  'Hồ sơ Tổ chức - Cán bộ': ['Quyết định', 'Thông báo', 'Hướng dẫn', 'Tờ trình'],
  'Hồ sơ Kế hoạch - Tài chính': ['Kế hoạch', 'Quyết định', 'Báo cáo', 'Tờ trình'],
  'Hồ sơ Chuyên môn - Nghiệp vụ': ['Hướng dẫn', 'Công văn', 'Kế hoạch', 'Quyết định'],
  'Hồ sơ Thanh tra - Pháp chế': ['Quyết định', 'Chỉ thị', 'Nghị quyết', 'Báo cáo'],
  'Hồ sơ Kế hoạch - Dự án': ['Kế hoạch', 'Báo cáo', 'Quyết định', 'Tờ trình'],
  'Hồ sơ Lưu trữ cơ quan': ['Công văn', 'Quyết định', 'Thông báo', 'Báo cáo'],
};

const MOCK_STAFF_BY_UNIT: Record<string, UserOption[]> = {
  'Ban công nghệ thông tin': [
    { id: 1, ho_ten: 'Quản trị hệ thống', username: 'admin', don_vi_ten: 'Ban công nghệ thông tin' },
    { id: 2, ho_ten: 'Trưởng Phòng CNTT', username: 'truongphong_cntt', don_vi_ten: 'Ban công nghệ thông tin' },
    { id: 3, ho_ten: 'Chuyên Viên CNTT', username: 'chuyenvien_cntt', don_vi_ten: 'Ban công nghệ thông tin' },
    { id: 4, ho_ten: 'Văn Thư Lưu Trữ', username: 'vanthu_cntt', don_vi_ten: 'Ban công nghệ thông tin' },
  ],
  'Hội đồng quản trị': [
    { id: 5, ho_ten: 'Cán bộ Văn thư', username: 'canbo', don_vi_ten: 'Hội đồng quản trị' },
  ],
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

export interface ParsedReplacement {
  raw: string;
  baseSoHieu: string;
  stt?: number;
  extraInfo?: string;
}

export const parseReplacementString = (str: string): ParsedReplacement => {
  const raw = (str || '').trim();
  if (!raw) return { raw: '', baseSoHieu: '' };
  const match = raw.match(/^(.+?)\s*(?:\[|\()([^\])]+)(?:\]|\))$/);
  if (match) {
    const baseSoHieu = match[1].trim();
    const bracketContent = match[2].trim();
    const sttMatch = bracketContent.match(/#(\d+)/) || bracketContent.match(/(?:Số đến|Số đi|STT)\s*[:#]?\s*(\d+)/i);
    const stt = sttMatch ? parseInt(sttMatch[1], 10) : undefined;
    let extra = bracketContent;
    if (sttMatch) {
      extra = extra.replace(/(?:Số đến|Số đi|STT)\s*[:#]?\s*\d+/gi, '');
      extra = extra.replace(/#\d+/g, '');
      extra = extra.replace(/Nơi ban hành\s*:\s*/gi, '');
      extra = extra.replace(/Người ký\s*:\s*/gi, '');
      extra = extra.replace(/^[\s-:;,]+|[\s-:;,]+$/g, '').trim();
    }
    return { raw, baseSoHieu, stt, extraInfo: extra };
  }
  return { raw, baseSoHieu: raw };
};

export const matchDocWithReplacement = (doc: SuggestedDoc, sh: string): boolean => {
  const parsed = parseReplacementString(sh);
  if (!doc.so_hieu) return false;
  const docSoHieu = doc.so_hieu.trim().toLowerCase();
  const baseSoHieu = parsed.baseSoHieu.trim().toLowerCase();
  if (docSoHieu !== baseSoHieu) return false;

  if (parsed.stt !== undefined && doc.so_thu_tu !== undefined) {
    return doc.so_thu_tu === parsed.stt;
  }
  if (parsed.extraInfo && doc.noi_ban_hanh) {
    return doc.noi_ban_hanh.toLowerCase().includes(parsed.extraInfo.toLowerCase());
  }
  return true;
};

export const formatDocReplacementString = (doc: SuggestedDoc, isDen: boolean): string => {
  const soHieu = (doc.so_hieu || '').trim();
  if (!doc.so_thu_tu) return soHieu;
  if (isDen) {
    return doc.noi_ban_hanh
      ? `${soHieu} [Nơi ban hành: ${doc.noi_ban_hanh.trim()} - Số đến #${doc.so_thu_tu}]`
      : `${soHieu} [Số đến #${doc.so_thu_tu}]`;
  } else {
    return doc.nguoi_ky
      ? `${soHieu} [Người ký: ${doc.nguoi_ky.trim()} - Số đi #${doc.so_thu_tu}]`
      : `${soHieu} [Số đi #${doc.so_thu_tu}]`;
  }
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

function formatDateTimePayload(dateStr: string, originalDateStr?: string | null): string {
  if (!dateStr) return '';
  if (dateStr.includes('T') || (dateStr.includes(':') && dateStr.length > 10)) return dateStr;

  if (originalDateStr) {
    const orig = new Date(originalDateStr);
    if (!isNaN(orig.getTime()) && (orig.getHours() !== 0 || orig.getMinutes() !== 0 || orig.getSeconds() !== 0)) {
      const h = String(orig.getHours()).padStart(2, '0');
      const m = String(orig.getMinutes()).padStart(2, '0');
      const s = String(orig.getSeconds()).padStart(2, '0');
      return `${dateStr}T${h}:${m}:${s}`;
    }
  }

  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  return `${dateStr}T${hours}:${minutes}:${seconds}`;
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

function buildInitialForm(initDocInput?: InitialDocType | DocumentFormInput | null, defaultLoai: 'DEN' | 'DI' | 'MAT' = 'DEN'): FormState {
  const now = new Date();
  const defaultDate = toLocalDateString(now);
  const initDoc = initDocInput as (Partial<DocumentDetail> & Record<string, unknown>) | null | undefined;
  const targetLoai = ((initDoc?.loai as 'DEN' | 'DI' | 'MAT') || defaultLoai);
  const isMat = targetLoai === 'MAT';

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
      ten_loai_van_ban: '',
      nguoi_ky: '',
      chuc_vu: '',
      hieu_luc: 'CON_HIEU_LUC',
      ngay_het_hieu_luc: '',
      link_thay_the: '',
      ghi_chu: '',
      pham_vi: isMat ? 'HAN_CHE' : 'NOI_BO',
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
    loai: targetLoai,
    nam: (initDoc.nam as number) ?? now.getFullYear(),
    so_hieu: (initDoc.so_hieu as string) ?? (initDoc.soHieu as string) ?? '',
    so_thu_tu: isMat ? undefined : ((initDoc.so_thu_tu as number) ?? (initDoc.soDen as number) ?? undefined),
    ngay_den: toLocalDateString((initDoc.ngay_den || initDoc.ngayDen || initDoc.ngay_ban_hanh || initDoc.ngayBanHanh) as string) || defaultDate,
    ngay_van_ban: toLocalDateString((initDoc.ngay_van_ban || initDoc.ngayVanBan || initDoc.ngay_thang_van_ban) as string) || defaultDate,
    noi_ban_hanh: (initDoc.noi_ban_hanh || initDoc.coQuanBanHanh || initDoc.co_quan_ban_hanh || '') as string,
    trich_yeu: (initDoc.trich_yeu || initDoc.trichYeu || '') as string,
    danh_muc_ho_so: (initDoc.danh_muc_ho_so || initDoc.danhMucHoSo || '') as string,
    ten_loai_van_ban: (initDoc.ten_loai_van_ban || initDoc.loaiVanBan || 'Công văn') as string,
    nguoi_ky: (initDoc.nguoi_ky || initDoc.nguoiKy || '') as string,
    chuc_vu: (initDoc.chuc_vu || initDoc.chucVu || '') as string,
    hieu_luc: ((initDoc.hieu_luc || initDoc.hieuLuc) === 'HET_VA_THAY_THE'
      ? 'HET_HIEU_LUC'
      : ((initDoc.hieu_luc || initDoc.hieuLuc) as FormState['hieu_luc'])) || 'CON_HIEU_LUC',
    ngay_het_hieu_luc: toLocalDateString((initDoc.ngay_het_hieu_luc || initDoc.ngayHetHieuLuc) as string),
    link_thay_the: (initDoc.link_thay_the || initDoc.linkThayThe || '') as string,
    ghi_chu: (initDoc.ghi_chu || initDoc.ghiChu || '') as string,
    pham_vi: isMat ? 'HAN_CHE' : (initDoc.pham_vi === 'HAN_CHE' ? 'HAN_CHE' : 'NOI_BO'),
    hien_thi: initDoc.hien_thi !== undefined ? Boolean(initDoc.hien_thi) : true,
    gui_mail_toan_he_thong: isMat ? false : Boolean(initDoc.gui_mail_toan_he_thong ?? initDoc.guiMailToanHeThong),
    nguoi_nhan: recipients,
  };
}

export default function DocumentFormModal({ open, onClose, initial, onSaved, defaultLoai = 'DEN' }: Props) {
  const { t } = useTranslation();
  const currentSession = useMemo(() => authService.getSession(), []);
  const isAdmin = currentSession?.role === 'admin' || currentSession?.username === 'admin';
  const initDoc = initial as (Partial<DocumentDetail> & Record<string, unknown>) | null | undefined;
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<FormState>(() => buildInitialForm(initial, defaultLoai));
  const [units, setUnits] = useState<string[]>(DEFAULT_UNITS);
  const [staff, setStaff] = useState<UserOption[]>([]);
  const [isStaffLoading, setIsStaffLoading] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState<string>(() => (initDoc?.don_vi_nhan as string) || '');
  const [existingAttachments, setExistingAttachments] = useState<ExistingAttachment[]>(() =>
    initDoc?.attachments && Array.isArray(initDoc.attachments) ? (initDoc.attachments as ExistingAttachment[]) : []
  );
  const [deletedAttachmentIds, setDeletedAttachmentIds] = useState<number[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [alertOpen, setAlertOpen] = useState(false);
  const [alertMsg, setAlertMsg] = useState('');

  // Gợi ý và tìm kiếm văn bản thay thế (hỗ trợ chọn nhiều văn bản cùng hệ & cùng phạm vi)
  const [replacementSuggestions, setReplacementSuggestions] = useState<SuggestedDoc[]>([]);
  const [isSearchingReplacement, setIsSearchingReplacement] = useState(false);
  const [showReplacementDropdown, setShowReplacementDropdown] = useState(false);
  const [selectedReplacementDocs, setSelectedReplacementDocs] = useState<SuggestedDoc[]>([]);
  const [replacementSearchText, setReplacementSearchText] = useState('');
  const [isReplacingOther, setIsReplacingOther] = useState(() => {
    return Boolean(initDoc?.link_thay_the || initDoc?.linkThayThe);
  });
  const [autoUpdateReplaced, setAutoUpdateReplaced] = useState(true);
  const [isReplacementListModalOpen, setIsReplacementListModalOpen] = useState(false);
  const [replacementListPage, setReplacementListPage] = useState(1);
  const replacementDropdownRef = useRef<HTMLDivElement | null>(null);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Tìm kiếm và lọc nhanh phòng ban ban hành theo thời gian thực
  const [unitSearch, setUnitSearch] = useState('');
  const [isUnitDropdownOpen, setIsUnitDropdownOpen] = useState(false);
  const unitDropdownRef = useRef<HTMLDivElement | null>(null);
  const unitSearchInputRef = useRef<HTMLInputElement | null>(null);

  // Tìm kiếm và chọn đơn vị nhận / chủ trì xử lý (Dropdown Custom chống lỗi văng tọa độ)
  const [recipientUnitSearch, setRecipientUnitSearch] = useState('');
  const [isRecipientUnitDropdownOpen, setIsRecipientUnitDropdownOpen] = useState(false);
  const recipientUnitDropdownRef = useRef<HTMLDivElement | null>(null);

  const filePattern = /\.(pdf|docx?|png|jpe?g)$/i;
  const maxFiles = 10;

  const [previousProps, setPreviousProps] = useState({ open, initial });
  if (previousProps.open !== open || previousProps.initial !== initial) {
    setPreviousProps({ open, initial });
    if (open) {
      setForm(buildInitialForm(initial, defaultLoai));
      setFiles([]);
      setDeletedAttachmentIds([]);
      setIsDragging(false);
      setReplacementSuggestions([]);
      setShowReplacementDropdown(false);
      setSelectedReplacementDocs([]);
      setReplacementSearchText('');
      setAutoUpdateReplaced(true);
      setIsReplacementListModalOpen(false);
      setReplacementListPage(1);
      const hasReplacement = Boolean(initDoc?.link_thay_the || initDoc?.linkThayThe);
      setIsReplacingOther(hasReplacement);
      if (initDoc?.attachments && Array.isArray(initDoc.attachments)) {
        setExistingAttachments(initDoc.attachments as ExistingAttachment[]);
      } else {
        setExistingAttachments([]);
      }
      setSelectedUnit((initDoc?.don_vi_nhan as string) || '');
      setStaff([]);
      setUnitSearch('');
      setIsUnitDropdownOpen(false);
      setRecipientUnitSearch('');
      setIsRecipientUnitDropdownOpen(false);
    }
  }

  async function fetchUnits() {
    try {
      // 1. Ưu tiên nạp trực tiếp từ danh mục phòng ban CSDL (organizations_donvi)
      const res = await apiClient.get<PaginatedResponse<{ id: number; ten: string }> | { id: number; ten: string }[]>(
        '/api/organizations/units/?page_size=100'
      );
      const items = Array.isArray(res) ? res : res?.results || [];
      const depts = items.map(d => d.ten?.trim()).filter(Boolean) as string[];
      if (depts.length > 0) {
        setUnits(Array.from(new Set(depts)));
        return;
      }
    } catch {
      // Fallback nếu endpoint organizations chưa sẵn sàng
    }

    try {
      // 2. Fallback từ staffs
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
      setIsStaffLoading(false);
      return;
    }
    setIsStaffLoading(true);
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
    } finally {
      setIsStaffLoading(false);
    }
    setStaff(MOCK_STAFF_BY_UNIT[unit] || []);
  }

  useEffect(() => {
    let cancelled = false;
    if (open) {
      const targetSoHieu = (initDoc?.link_thay_the || initDoc?.linkThayThe) as string | undefined;
      if (targetSoHieu) {
        const targetLoai = form.loai || defaultLoai || (initDoc as { loai?: string })?.loai || 'DEN';
        const targetPhamVi = form.loai === 'MAT' ? 'HAN_CHE' : (form.pham_vi || (initDoc as { pham_vi?: string })?.pham_vi || 'NOI_BO');
        const codes = targetSoHieu.split(',').map(s => s.trim()).filter(Boolean);
        if (codes.length > 0) {
          Promise.all(
            codes.map(code =>
              apiClient.get<PaginatedResponse<SuggestedDoc> | SuggestedDoc[]>(
                `/api/documents/?loai=${encodeURIComponent(targetLoai)}&pham_vi=${encodeURIComponent(targetPhamVi)}&q=${encodeURIComponent(code)}&page_size=5`
              ).then(res => {
                const items = Array.isArray(res) ? res : res?.results || [];
                return items.find(d => d.so_hieu && d.so_hieu.trim().toLowerCase() === code.toLowerCase()) || {
                  id: Math.random(),
                  so_hieu: code,
                  trich_yeu: 'Văn bản thay thế trong hệ thống',
                };
              }).catch(() => ({
                id: Math.random(),
                so_hieu: code,
                trich_yeu: 'Văn bản thay thế trong hệ thống',
              }))
            )
          ).then(docs => {
            if (cancelled) return;
            setSelectedReplacementDocs(docs);
          });
        }
      }

      const initialUnit = (initDoc?.don_vi_nhan as string) || '';
      Promise.resolve().then(() => {
        if (cancelled) return;
        void fetchUnits();
        if (initialUnit) {
          void fetchStaffByUnit(initialUnit);
        } else {
          // Bắt buộc chọn đơn vị trước, không nạp trước tất cả cán bộ khi chưa chọn đơn vị
          setStaff([]);
        }
      });

      // Tự động nạp chi tiết đầy đủ khi đang ở chế độ Chỉnh sửa văn bản (Edit mode)
      if (initial && initial.id) {
        const targetLoai = form.loai || defaultLoai || (initial as { loai?: string })?.loai || 'DEN';
        const req = apiClient.get<DocumentDetail>(`/api/documents/${initial.id}/?loai=${encodeURIComponent(targetLoai)}`);
        if (req && typeof req.then === 'function') {
          req.then((detail) => {
            if (cancelled || !detail) return;
            // 1. Cập nhật danh sách tệp đính kèm hiện có
            if (detail.attachments && Array.isArray(detail.attachments)) {
              setExistingAttachments(
                detail.attachments.map((a: unknown) => {
                  const item = a as Record<string, unknown>;
                  return {
                    id: Number(item.id),
                    file: String(item.file || item.path || ''),
                    file_name: String(item.name || item.file_name || 'Tệp đính kèm'),
                    file_size: item.file_size ? Number(item.file_size) : undefined,
                  };
                })
              );
            }
            // 2. Tự động xác định đơn vị nhận và nạp/tích chọn đúng cán bộ nhận đã phân công
            let resolvedUnit = (detail.don_vi_nhan as string) || '';
            const recipientList = (detail.nguoi_nhan_list || []) as Array<{
              id: number;
              username?: string;
              full_name?: string;
              ho_ten?: string;
              department?: string;
              don_vi_ten?: string;
            }>;
            if (!resolvedUnit && recipientList.length > 0) {
              resolvedUnit = recipientList[0].don_vi_ten || recipientList[0].department || '';
            }

            if (resolvedUnit) {
              setSelectedUnit(resolvedUnit);
              void fetchStaffByUnit(resolvedUnit);
            }

            if (recipientList.length > 0) {
              const userIds = recipientList.map(u => u.id);
              setForm(prev => ({ ...prev, nguoi_nhan: userIds }));
            } else if (Array.isArray(detail.nguoi_nhan) && detail.nguoi_nhan.length > 0) {
              const userIds = detail.nguoi_nhan.map((u: unknown) =>
                typeof u === 'object' && u !== null && 'id' in u ? (u as { id: number }).id : Number(u)
              );
              setForm(prev => ({ ...prev, nguoi_nhan: userIds }));
            }
            // 3. Tự động điền nơi ban hành
            if (detail.noi_ban_hanh) {
              setForm(prev => ({ ...prev, noi_ban_hanh: detail.noi_ban_hanh || prev.noi_ban_hanh }));
            }
            // 4. Tự động điền người ký
            if (detail.nguoi_ky) {
              setForm(prev => ({ ...prev, nguoi_ky: detail.nguoi_ky || prev.nguoi_ky }));
            }
            // 5. Tự động điền chức vụ
            if (detail.chuc_vu) {
              setForm(prev => ({ ...prev, chuc_vu: detail.chuc_vu || prev.chuc_vu }));
            }
          })
          .catch(() => undefined);
        }
      }
    }
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, initDoc?.don_vi_nhan, initDoc?.linkThayThe, initDoc?.link_thay_the, initial?.id]);

  function handleUnitChange(unit: string) {
    setSelectedUnit(unit);
    if (!unit) {
      setStaff([]);
      // Xóa cán bộ đã chọn khi hủy chọn đơn vị
      setForm(prev => ({ ...prev, nguoi_nhan: [] }));
    } else {
      // Khi đổi sang đơn vị khác, làm mới lại danh sách cán bộ nhận đã chọn
      if (unit !== selectedUnit) {
        setForm(prev => ({ ...prev, nguoi_nhan: [] }));
      }
      void fetchStaffByUnit(unit);
    }
  }

  // Quản lý ManyToMany đơn vị phòng ban nội bộ (chỉ chọn từ CSDL, không tự tạo)
  const selectedUnitsList = form.noi_ban_hanh
    ? form.noi_ban_hanh.split(',').map(s => s.trim()).filter(Boolean)
    : [];

  function handleAddUnit(unitName: string) {
    if (!unitName) return;
    if (!selectedUnitsList.includes(unitName)) {
      const nextList = [...selectedUnitsList, unitName];
      setForm(prev => ({ ...prev, noi_ban_hanh: nextList.join(', ') }));
    }
  }

  function handleRemoveUnit(unitName: string) {
    const nextList = selectedUnitsList.filter(u => u !== unitName);
    setForm(prev => ({ ...prev, noi_ban_hanh: nextList.join(', ') }));
  }

  function handleClearAllUnits() {
    setForm(prev => ({ ...prev, noi_ban_hanh: '' }));
  }

  // Danh sách phòng ban được lọc theo từ khóa tìm kiếm (lọc ngay khi gõ từng ký tự)
  const filteredUnits = units.filter(u =>
    u.toLowerCase().includes(unitSearch.trim().toLowerCase())
  );

  // Danh sách đơn vị nhận được lọc theo từ khóa tìm kiếm
  const filteredRecipientUnits = units.filter(u =>
    u.toLowerCase().includes(recipientUnitSearch.trim().toLowerCase())
  );

  // Đóng dropdown gợi ý khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (replacementDropdownRef.current && !replacementDropdownRef.current.contains(e.target as Node)) {
        setShowReplacementDropdown(false);
      }
      if (unitDropdownRef.current && !unitDropdownRef.current.contains(e.target as Node)) {
        setIsUnitDropdownOpen(false);
      }
      if (recipientUnitDropdownRef.current && !recipientUnitDropdownRef.current.contains(e.target as Node)) {
        setIsRecipientUnitDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    };
  }, []);

  // Tự động cấp và hiển thị sẵn số thứ tự tiếp theo (Số đến / Số đi) khi tạo mới
  useEffect(() => {
    let cancelled = false;
    if (open && !initial?.id && form.loai !== 'MAT') {
      try {
        const req = apiClient.get<{ next_so: number }>(`/api/documents/next-so/?loai=${form.loai || 'DEN'}&nam=${form.nam || new Date().getFullYear()}`);
        if (req && typeof req.then === 'function') {
          req
            .then((res) => {
              if (!cancelled && res && res.next_so) {
                setForm((prev) => ({ ...prev, so_thu_tu: res.next_so }));
              }
            })
            .catch(() => undefined);
        }
      } catch {
        // Safe fallback
      }
    }
    return () => {
      cancelled = true;
    };
  }, [open, initial?.id, form.loai, form.nam]);

  const selectedSoHieus = useMemo(() => {
    return (form.link_thay_the || '')
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
  }, [form.link_thay_the]);

  // Tự động tải trước siêu dữ liệu (Số đến/Số đi, Trích yếu, Nơi ban hành) cho các văn bản bị thay thế đã chọn
  useEffect(() => {
    let cancelled = false;
    if (!open || selectedSoHieus.length === 0) return;

    const missing = selectedSoHieus.filter(
      sh => !selectedReplacementDocs.some(d => matchDocWithReplacement(d, sh))
    );
    if (missing.length === 0) return;

    const targetLoai = form.loai || defaultLoai || 'DEN';
    const targetPhamVi = form.loai === 'MAT' ? 'HAN_CHE' : (form.pham_vi || 'NOI_BO');

    Promise.all(
      missing.map(sh => {
        const parsed = parseReplacementString(sh);
        return apiClient.get<PaginatedResponse<SuggestedDoc> | SuggestedDoc[]>(
          `/api/documents/?loai=${encodeURIComponent(targetLoai)}&pham_vi=${encodeURIComponent(targetPhamVi)}&q=${encodeURIComponent(parsed.baseSoHieu)}&page_size=5`
        ).catch(() => null);
      })
    ).then(results => {
      if (cancelled) return;
      const fetchedDocs: SuggestedDoc[] = [];
      results.forEach(res => {
        const items = Array.isArray(res) ? res : res?.results || [];
        items.forEach(doc => {
          if (doc && doc.so_hieu && selectedSoHieus.some(sh => matchDocWithReplacement(doc, sh))) {
            if (!fetchedDocs.some(fd => fd.id === doc.id || (fd.so_hieu === doc.so_hieu && fd.so_thu_tu === doc.so_thu_tu))) {
              fetchedDocs.push(doc);
            }
          }
        });
      });
      if (fetchedDocs.length > 0) {
        setSelectedReplacementDocs(prev => {
          const map = new Map<string, SuggestedDoc>();
          prev.forEach(d => {
            const key = `${d.so_hieu?.trim().toLowerCase()}_#${d.so_thu_tu || ''}`;
            map.set(key, d);
          });
          fetchedDocs.forEach(d => {
            const key = `${d.so_hieu?.trim().toLowerCase()}_#${d.so_thu_tu || ''}`;
            if (!map.has(key)) {
              map.set(key, d);
            }
          });
          return Array.from(map.values());
        });
      }
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, selectedSoHieus, form.loai, form.pham_vi]);

  const searchReplacementDocs = (query: string) => {
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);

    const trimmed = (query || '').trim();
    setIsSearchingReplacement(true);
    setShowReplacementDropdown(true);

    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const targetLoai = form.loai || defaultLoai || 'DEN';
        const targetPhamVi = form.loai === 'MAT' ? 'HAN_CHE' : (form.pham_vi || 'NOI_BO');
        const endpoint = trimmed
          ? `/api/documents/?loai=${encodeURIComponent(targetLoai)}&pham_vi=${encodeURIComponent(targetPhamVi)}&q=${encodeURIComponent(trimmed)}&page_size=10`
          : `/api/documents/?loai=${encodeURIComponent(targetLoai)}&pham_vi=${encodeURIComponent(targetPhamVi)}&page_size=8`;
        const res = await apiClient.get<PaginatedResponse<SuggestedDoc> | SuggestedDoc[]>(endpoint);
        const items: SuggestedDoc[] = Array.isArray(res) ? res : res?.results || [];
        const currentSoHieu = (form.so_hieu || '').trim().toLowerCase();
        const filtered = items.filter(d => {
          // 1. Chặn chọn chính bản ghi đang chỉnh sửa
          if (initial?.id && d.id === initial.id) return false;
          // 2. Chặn chọn văn bản đang trỏ ngược lại văn bản hiện tại (tránh vòng lặp)
          if (initial?.id && currentSoHieu) {
            const otherLinks = (d.link_thay_the || '').toLowerCase().split(',').map(s => s.trim());
            const pointsToCurrent = otherLinks.some(link => {
              const p = parseReplacementString(link);
              if (p.baseSoHieu.toLowerCase() !== currentSoHieu) return false;
              if (initial.so_thu_tu !== undefined && p.stt !== undefined) {
                return p.stt === initial.so_thu_tu;
              }
              return true;
            });
            if (pointsToCurrent) return false;
          }
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

  const handleReplacementSearchChange = (val: string) => {
    setReplacementSearchText(val);
    searchReplacementDocs(val);
  };

  const handleToggleReplacementDoc = (doc: SuggestedDoc) => {
    const docSoHieu = (doc.so_hieu || '').trim();
    if (!docSoHieu) return;

    const isDen = (form.loai || defaultLoai || 'DEN') === 'DEN';
    const docStr = formatDocReplacementString(doc, isDen);
    const isAlreadySelected = selectedSoHieus.some(s => matchDocWithReplacement(doc, s));
    let nextList: string[];
    let nextDocs: SuggestedDoc[];

    if (isAlreadySelected) {
      nextList = selectedSoHieus.filter(s => !matchDocWithReplacement(doc, s));
      nextDocs = selectedReplacementDocs.filter(d => !matchDocWithReplacement(d, docStr) && d.id !== doc.id);
    } else {
      nextList = [...selectedSoHieus, docStr];
      nextDocs = [...selectedReplacementDocs.filter(d => !matchDocWithReplacement(d, docStr) && d.id !== doc.id), doc];
    }

    setForm(prev => ({ ...prev, link_thay_the: nextList.join(', ') }));
    setSelectedReplacementDocs(nextDocs);
    // Tự động xóa trắng ô tìm kiếm để người dùng gõ tìm tiếp văn bản khác
    setReplacementSearchText('');
    searchReplacementDocs('');
  };

  const handleRemoveReplacementDoc = (soHieuToRemove: string) => {
    const trimmedToRemove = soHieuToRemove.trim().toLowerCase();
    const nextList = selectedSoHieus.filter(s => s.trim().toLowerCase() !== trimmedToRemove);
    const nextDocs = selectedReplacementDocs.filter(d => !matchDocWithReplacement(d, soHieuToRemove));
    setForm(prev => ({ ...prev, link_thay_the: nextList.join(', ') }));
    setSelectedReplacementDocs(nextDocs);
  };

  const handleClearAllReplacementDocs = () => {
    setForm(prev => ({ ...prev, link_thay_the: '' }));
    setSelectedReplacementDocs([]);
    setReplacementSearchText('');
    searchReplacementDocs('');
  };

  const handleReplacementKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const trimmed = replacementSearchText.trim().replace(/^,|,$/g, '').trim();
      if (trimmed) {
        if (!selectedSoHieus.some(s => parseReplacementString(s).baseSoHieu.toLowerCase() === trimmed.toLowerCase())) {
          const nextList = [...selectedSoHieus, trimmed];
          setForm(prev => ({ ...prev, link_thay_the: nextList.join(', ') }));
        }
        setReplacementSearchText('');
        searchReplacementDocs('');
      }
    }
  };

  const handleReplacementInputFocus = () => {
    setShowReplacementDropdown(true);
    searchReplacementDocs(replacementSearchText);
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

  function handleRemoveExistingAttachment(id: number) {
    setExistingAttachments(prev => prev.filter(att => att.id !== id));
    setDeletedAttachmentIds(prev => (prev.includes(id) ? prev : [...prev, id]));
  }


  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();

    if (!form.so_hieu?.trim()) {
      setAlertMsg('Vui lòng nhập Số, ký hiệu văn bản (*)');
      setAlertOpen(true);
      return;
    }
    if (!form.danh_muc_ho_so?.trim()) {
      setAlertMsg('Vui lòng nhập Danh mục hồ sơ (*)');
      setAlertOpen(true);
      return;
    }
    if (!form.ten_loai_van_ban?.trim()) {
      setAlertMsg('Vui lòng nhập Loại văn bản (*)');
      setAlertOpen(true);
      return;
    }
    if (form.loai === 'DEN') {
      if (!form.noi_ban_hanh?.trim()) {
        setAlertMsg('Vui lòng nhập Cơ quan / Đơn vị ban hành văn bản (*)');
        setAlertOpen(true);
        return;
      }
    } else {
      const selectedList = form.noi_ban_hanh
        ? form.noi_ban_hanh.split(',').map(s => s.trim()).filter(Boolean)
        : [];
      if (selectedList.length === 0) {
        setAlertMsg('Vui lòng chọn ít nhất một Đơn vị / Phòng ban ban hành từ danh mục hệ thống (*)');
        setAlertOpen(true);
        return;
      }
      const invalidUnits = selectedList.filter(u => !units.includes(u));
      if (invalidUnits.length > 0 && units.length > 0) {
        setAlertMsg(`Đơn vị "${invalidUnits.join(', ')}" không tồn tại trong danh mục hệ thống. Vui lòng chỉ chọn các phòng ban có sẵn (*).`);
        setAlertOpen(true);
        return;
      }
    }
    if (!form.trich_yeu?.trim()) {
      setAlertMsg('Vui lòng nhập Trích yếu nội dung văn bản (*)');
      setAlertOpen(true);
      return;
    }
    if (isReplacingOther) {
      let rawLink = (form.link_thay_the || '').trim();
      if (replacementSearchText.trim()) {
        const extra = replacementSearchText.trim().replace(/^,|,$/g, '').trim();
        const curTargets = rawLink.split(',').map(s => s.trim()).filter(Boolean);
        if (extra && !curTargets.some(t => t.toLowerCase() === extra.toLowerCase())) {
          curTargets.push(extra);
          rawLink = curTargets.join(', ');
          setForm(prev => ({ ...prev, link_thay_the: rawLink }));
        }
      }
      if (!rawLink) {
        setAlertMsg('Vui lòng chọn hoặc nhập ít nhất một Số hiệu văn bản thay thế (*)');
        setAlertOpen(true);
        return;
      }
      const targets = rawLink.split(',').map(s => s.trim()).filter(Boolean);
      if (targets.length === 0) {
        setAlertMsg('Vui lòng chọn hoặc nhập ít nhất một Số hiệu văn bản thay thế (*)');
        setAlertOpen(true);
        return;
      }
      const currentSoHieu = (form.so_hieu || '').trim().toLowerCase();
      if (currentSoHieu && targets.some(t => parseReplacementString(t).baseSoHieu.toLowerCase() === currentSoHieu)) {
        setAlertMsg('Văn bản không thể tự thiết lập thay thế chính nó (*)');
        setAlertOpen(true);
        return;
      }

      // Khóa nghiệp vụ: Bắt buộc văn bản thay thế phải tồn tại trong đúng phân hệ và phạm vi
      const targetLoai = form.loai || defaultLoai || 'DEN';
      const targetPhamVi = form.loai === 'MAT' ? 'HAN_CHE' : (form.pham_vi || 'NOI_BO');
      for (const target of targets) {
        const parsed = parseReplacementString(target);
        const inSelected = selectedReplacementDocs.some(
          d => matchDocWithReplacement(d, target)
        );
        const inSuggestions = replacementSuggestions.some(
          d => matchDocWithReplacement(d, target)
        );
        if (!inSelected && !inSuggestions) {
          try {
            const checkRes = await apiClient.get<{ results?: SuggestedDoc[] } | SuggestedDoc[]>(
              `/api/documents/?loai=${encodeURIComponent(targetLoai)}&pham_vi=${encodeURIComponent(targetPhamVi)}&q=${encodeURIComponent(parsed.baseSoHieu)}&page_size=5`
            );
            const items: SuggestedDoc[] = Array.isArray(checkRes) ? checkRes : checkRes?.results || [];
            const exists = items.some(
              d => matchDocWithReplacement(d, target)
            );
            if (!exists) {
              const loaiLabel = targetLoai === 'DI' ? 'Văn bản Đi' : targetLoai === 'MAT' ? 'Văn bản Mật' : 'Văn bản Đến';
              const scopeLabel = targetPhamVi === 'HAN_CHE' ? 'Hạn chế' : 'Nội bộ';
              setAlertMsg(`Văn bản mục tiêu "${parsed.baseSoHieu}" không tồn tại trong hệ thống (${loaiLabel} - ${scopeLabel}). Vui lòng chọn văn bản từ danh sách gợi ý (*).`);
              setAlertOpen(true);
              return;
            }
          } catch {
            // Bỏ qua lỗi mạng cục bộ để backend serializer thực thi chốt chặn cuối cùng
          }
        }
      }
    }
    if (form.pham_vi === 'HAN_CHE') {
      if (!selectedUnit) {
        setAlertMsg('Văn bản hạn chế bắt buộc phải chọn Đơn vị nhận trước (*)');
        setAlertOpen(true);
        return;
      }
      if (!form.nguoi_nhan || form.nguoi_nhan.length === 0) {
        setAlertMsg('Văn bản hạn chế bắt buộc phải chọn ít nhất một cán bộ nhận / xử lý (*)');
        setAlertOpen(true);
        return;
      }
    }
    if (form.nguoi_nhan && form.nguoi_nhan.length > 0 && !selectedUnit) {
      setAlertMsg('Vui lòng chọn đơn vị nhận trước khi chọn cán bộ (*)');
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
      payload.append('pham_vi', form.loai === 'MAT' ? 'HAN_CHE' : (form.pham_vi || 'NOI_BO'));
      payload.append('hien_thi', form.hien_thi ? 'true' : 'false');
      payload.append('gui_mail_toan_he_thong', (form.loai === 'MAT' || form.pham_vi === 'HAN_CHE') ? 'false' : (form.gui_mail_toan_he_thong ? 'true' : 'false'));

      const origDate = initial ? ((initial as Partial<DocumentDetail>).ngay_den || (initial as Partial<DocumentDetail>).ngay_ban_hanh) : null;
      if (form.loai === 'DI') {
        if (form.ngay_den) {
          payload.append('ngay_ban_hanh', formatDateTimePayload(form.ngay_den, origDate));
        }
      } else {
        if (form.ngay_den) {
          payload.append('ngay_den', formatDateTimePayload(form.ngay_den, origDate));
        }
      }
      if (form.ngay_van_ban) {
        payload.append('ngay_van_ban', form.ngay_van_ban);
      }
      if (form.danh_muc_ho_so?.trim()) {
        payload.append('danh_muc_ho_so', form.danh_muc_ho_so.trim());
      }
      if (form.ten_loai_van_ban?.trim()) {
        payload.append('ten_loai_van_ban', form.ten_loai_van_ban.trim());
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
      if (isReplacingOther && form.link_thay_the?.trim()) {
        payload.append('link_thay_the', form.link_thay_the.trim());
        payload.append('auto_update_replaced_doc', autoUpdateReplaced ? 'true' : 'false');
      } else {
        payload.append('link_thay_the', '');
      }
      payload.append(
        'ngay_het_hieu_luc',
        form.hieu_luc === 'CON_HIEU_LUC' ? '' : (form.ngay_het_hieu_luc || '')
      );

      if (Array.isArray(form.nguoi_nhan)) {
        form.nguoi_nhan.forEach(userId => {
          if (userId) payload.append('nguoi_nhan', String(userId));
        });
      }

      if (selectedUnit) {
        payload.append('don_vi_nhan', selectedUnit);
      }

      if (deletedAttachmentIds.length > 0) {
        deletedAttachmentIds.forEach(id => {
          payload.append('delete_attachment_ids', String(id));
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

      const targetLoai = form.loai || defaultLoai || (initial as { loai?: string })?.loai || 'DEN';
      const endpoint = initial && initial.id
        ? `/api/documents/${initial.id}/?loai=${encodeURIComponent(targetLoai)}`
        : `/api/documents/?loai=${encodeURIComponent(targetLoai)}`;
      const method = initial && initial.id ? 'PUT' : 'POST';

      const data = await apiClient<Record<string, unknown>>(endpoint, {
        method,
        body: payload,
      });

      onSaved?.(data);
      onClose();
    } catch (err: unknown) {
      let msg = 'Không thể kết nối đến máy chủ';
      if (err instanceof ApiError) {
        msg = err.data?.error || err.data?.detail || err.message;
        if (typeof err.data === 'object' && err.data !== null && !err.data.error && !err.data.detail) {
          const fieldErrors = Object.entries(err.data)
            .map(([field, errs]) => `${field}: ${Array.isArray(errs) ? errs.join(', ') : errs}`)
            .join('; ');
          if (fieldErrors) msg = fieldErrors;
        }
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setAlertMsg('Lỗi: ' + msg);
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
        className="bg-surface border border-border-subtle rounded-2xl shadow-2xl z-10 w-[940px] max-w-full flex flex-col max-h-[88vh] my-auto animate-in fade-in duration-150"
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
                  ? (form.loai === 'MAT'
                      ? (t('documents_ui.formModal.titleEditConfidential') || 'Cập Nhật Văn Bản Mật')
                      : form.loai === 'DI'
                      ? (t('documents_ui.formModal.titleEditOutbound') || 'Cập Nhật Văn Bản Đi')
                      : (t('documents_ui.formModal.titleEditInbound') || 'Cập Nhật Văn Bản Đến'))
                  : (form.loai === 'MAT'
                      ? (t('documents_ui.formModal.titleAddConfidential') || 'Thêm Mới Văn Bản Mật')
                      : form.loai === 'DI'
                      ? (t('documents_ui.formModal.titleAddOutbound') || 'Thêm Mới Văn Bản Đi')
                      : (t('documents_ui.formModal.titleAddInbound') || 'Thêm Mới Văn Bản Đến'))}
              </h3>
              <p className="text-xs text-muted m-0">
                {initial?.id
                  ? (t('documents_ui.formModal.subtitleEdit', { code: form.so_hieu || '' }) || `Chỉnh sửa thông tin hồ sơ văn bản ${form.so_hieu || ''}`)
                  : (form.loai === 'MAT'
                      ? (t('documents_ui.formModal.subtitleAddConfidential') || 'Lưu trữ và phân quyền văn bản mật theo quy định bảo mật')
                      : form.loai === 'DI'
                      ? (t('documents_ui.formModal.subtitleAddOutbound') || 'Vào sổ công văn đi và quản lý phát hành nội bộ')
                      : (t('documents_ui.formModal.subtitleAddInbound') || 'Tiếp nhận, vào sổ công văn đến và phân phối xử lý nội bộ'))}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-muted hover:text-main hover:bg-hover flex items-center justify-center transition-fast"
            title={t('documents_ui.formModal.close') || 'Đóng cửa sổ'}
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {/* PHẦN 1: TIẾP NHẬN & VÀO SỔ */}
          <div className="bg-canvas/40 border border-border-subtle rounded-xl p-4 sm:p-5 space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle/60 gap-4">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-6 h-6 rounded-md bg-blue-500/10 text-blue-600 flex items-center justify-center text-xs font-bold shrink-0">
                  <i className="fa-solid fa-inbox" />
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-main m-0 truncate">
                  {t('documents_ui.formModal.section1Title') || '1. Tiếp nhận & Vào sổ công văn'}
                </h4>
              </div>
              <span className="text-xs text-muted shrink-0 text-right">{t('documents_ui.formModal.section1Subtitle') || 'Thông tin định danh văn bản'}</span>
            </div>

            <div className="grid grid-cols-12 gap-3.5">
              {/* Năm */}
              <div className={`col-span-12 ${form.loai === 'MAT' ? 'sm:col-span-3' : 'sm:col-span-2'}`}>
                <label className="block text-xs font-semibold text-secondary mb-1.5">{t('documents_ui.formModal.year') || 'Năm'}</label>
                <input
                  type="number"
                  value={form.nam}
                  onChange={e => setForm({ ...form, nam: Number(e.target.value) })}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main text-center focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Số đến / Số đi (Ẩn khi là Văn bản Mật) */}
              {form.loai !== 'MAT' && (
                <div className="col-span-12 sm:col-span-3">
                  <label className="block text-xs font-semibold text-secondary mb-1.5">
                    {form.loai === 'DI' ? (t('documents_ui.formModal.outboundNo') || 'Số đi') : (t('documents_ui.formModal.inboundNo') || 'Số đến')} <span className="text-muted font-normal text-xs">{t('documents_ui.formModal.autoGenerated') || '(Tự động)'}</span>
                  </label>
                  <input
                    readOnly
                    value={form.so_thu_tu ? `#${form.so_thu_tu}` : (t('documents_ui.formModal.fetchingNumber') || 'Đang lấy số...')}
                    className="w-full text-sm bg-hover/70 border border-border-subtle rounded-xl px-3 py-2 text-main font-semibold cursor-not-allowed select-none"
                    title={t('documents_ui.formModal.numberTooltip') || 'Số thứ tự được hệ thống tự động sinh tăng dần theo năm (chỉ xem, không thể sửa)'}
                  />
                </div>
              )}

              {/* Ngày đến / Ngày ban hành */}
              <div className={`col-span-12 ${form.loai === 'MAT' ? 'sm:col-span-4' : 'sm:col-span-4'}`}>
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {form.loai === 'MAT' 
                    ? (t('documents_ui.formModal.confidentialDate') || 'Ngày lưu văn bản mật') 
                    : form.loai === 'DI' 
                    ? (t('documents_ui.formModal.issueDate') || 'Ngày ban hành') 
                    : (t('documents_ui.formModal.receivedDate') || 'Ngày đến')} <span className="text-danger">*</span>
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
              <div className={`col-span-12 ${form.loai === 'MAT' ? 'sm:col-span-5' : 'sm:col-span-3'}`}>
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {form.loai === 'MAT' ? (t('documents_ui.formModal.confidentialCode') || 'Số, ký hiệu VB mật') : (t('documents_ui.formModal.refCode') || 'Số, ký hiệu')} <span className="text-danger">*</span>
                </label>
                <input
                  value={form.so_hieu}
                  onChange={e => setForm({ ...form, so_hieu: e.target.value })}
                  placeholder={form.loai === 'MAT' ? 'VD: 01/BC-MẬT' : 'VD: 125/BGDDT-VP'}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main font-medium placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                  required
                />
              </div>

              {/* Ngày văn bản */}
              <div className="col-span-12 sm:col-span-4">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {t('documents_ui.formModal.docDateOnPaper') || 'Ngày ban hành trên VB'}
                </label>
                <input
                  type="date"
                  value={form.ngay_van_ban}
                  onChange={e => setForm({ ...form, ngay_van_ban: e.target.value })}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Danh mục hồ sơ */}
              <div className="col-span-12 sm:col-span-4">
                <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center justify-between">
                  <span>{t('documents_ui.formModal.dossierCatalog') || 'Danh mục hồ sơ'} <span className="text-rose-500 font-bold">*</span></span>
                  {form.loai !== 'DEN' && (
                    <span className="text-[10px] text-primary font-medium">{t('documents_ui.formModal.internalBadge') || 'Nội bộ'}</span>
                  )}
                </label>
                {form.loai === 'DEN' ? (
                  <input
                    type="text"
                    value={form.danh_muc_ho_so}
                    onChange={e => {
                      const newFolder = e.target.value;
                      setForm({
                        ...form,
                        danh_muc_ho_so: newFolder,
                        ten_loai_van_ban: newFolder.trim() ? form.ten_loai_van_ban : '',
                      });
                    }}
                    placeholder={t('documents_ui.formModal.dossierPlaceholderInbound') || 'Nhập danh mục hồ sơ (VD: Hồ sơ công văn đến)...'}
                    className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                    required
                  />
                ) : (
                  <select
                    value={form.danh_muc_ho_so}
                    onChange={e => {
                      const newFolder = e.target.value;
                      setForm({
                        ...form,
                        danh_muc_ho_so: newFolder,
                        ten_loai_van_ban: '', // Khóa nghiệp vụ: Reset loại văn bản để bắt buộc chọn lại theo hồ sơ mới
                      });
                    }}
                    className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                    required
                  >
                    <option value="">{t('documents_ui.formModal.dossierSelectPlaceholder') || '-- Chọn danh mục hồ sơ nội bộ --'}</option>
                    {Object.keys(DEFAULT_INTERNAL_FOLDERS).map(f => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                    {form.danh_muc_ho_so && !DEFAULT_INTERNAL_FOLDERS[form.danh_muc_ho_so] && (
                      <option value={form.danh_muc_ho_so}>{form.danh_muc_ho_so}</option>
                    )}
                  </select>
                )}
              </div>

              {/* Loại văn bản */}
              <div className="col-span-12 sm:col-span-4">
                <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center justify-between">
                  <span>{t('documents_ui.formModal.docType') || 'Loại văn bản'} <span className="text-rose-500 font-bold">*</span></span>
                  {!form.danh_muc_ho_so?.trim() ? (
                    <span className="text-[10px] text-amber-600 dark:text-amber-400 font-medium italic flex items-center gap-1">
                      <i className="fa-solid fa-lock text-[9px]" /> {t('documents_ui.formModal.needDossierFirst') || 'Cần nhập hồ sơ trước'}
                    </span>
                  ) : (
                    form.loai !== 'DEN' ? (
                      <span className="text-[10px] text-primary font-medium">{t('documents_ui.formModal.bySelectedDossier') || 'Theo hồ sơ đã chọn'}</span>
                    ) : (
                      <span className="text-[10px] text-muted italic">{t('documents_ui.formModal.freeText') || 'Gõ tay tự do'}</span>
                    )
                  )}
                </label>
                {form.loai === 'DEN' ? (
                  <input
                    type="text"
                    disabled={!form.danh_muc_ho_so?.trim()}
                    value={form.ten_loai_van_ban}
                    onChange={e => setForm({ ...form, ten_loai_van_ban: e.target.value })}
                    placeholder={!form.danh_muc_ho_so?.trim() 
                      ? (t('documents_ui.formModal.docTypePromptInbound') || '— Vui lòng nhập Danh mục hồ sơ trước —') 
                      : (t('documents_ui.formModal.docTypePlaceholderInbound') || 'Nhập loại văn bản (VD: Công văn, Quyết định...)')}
                    className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-hover/60"
                    required
                  />
                ) : (
                  <select
                    disabled={!form.danh_muc_ho_so?.trim()}
                    value={form.ten_loai_van_ban}
                    onChange={e => setForm({ ...form, ten_loai_van_ban: e.target.value })}
                    className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-hover/60"
                    required
                  >
                    <option value="">
                      {!form.danh_muc_ho_so?.trim()
                        ? (t('documents_ui.formModal.docTypePromptSelect') || '— Vui lòng chọn danh mục hồ sơ trước —')
                        : (t('documents_ui.formModal.docTypeSelectPlaceholder') || '-- Chọn loại văn bản --')}
                    </option>
                    {form.danh_muc_ho_so?.trim() &&
                      (DEFAULT_INTERNAL_FOLDERS[form.danh_muc_ho_so] || DEFAULT_DOC_TYPES).map(tOpt => (
                        <option key={tOpt} value={tOpt}>{tOpt}</option>
                      ))}
                    {form.ten_loai_van_ban &&
                      form.danh_muc_ho_so?.trim() &&
                      !(DEFAULT_INTERNAL_FOLDERS[form.danh_muc_ho_so] || DEFAULT_DOC_TYPES).includes(form.ten_loai_van_ban) && (
                        <option value={form.ten_loai_van_ban}>{form.ten_loai_van_ban}</option>
                      )}
                  </select>
                )}
              </div>

              {/* Phạm vi lưu hành (Issue #82) */}
              <div className="col-span-12 sm:col-span-4">
                <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center justify-between">
                  <span>{t('documents_ui.formModal.scope') || 'Phạm vi lưu hành'}</span>
                  {(form.pham_vi === 'HAN_CHE' || form.loai === 'MAT') && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-600 font-bold uppercase">
                      {t('documents_ui.formModal.scopeRestricted') || 'Hạn chế'}
                    </span>
                  )}
                </label>
                {form.loai === 'MAT' ? (
                  <select
                    value="HAN_CHE"
                    disabled
                    className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none transition-fast opacity-80 cursor-not-allowed"
                    title="Văn bản mật bắt buộc lưu hành ở phạm vi hạn chế"
                  >
                    <option value="HAN_CHE">{t('documents_ui.formModal.scopeConfidentialOnly') || 'Hạn chế (Chỉ người nhận xem)'}</option>
                  </select>
                ) : (
                  <select
                    value={form.pham_vi}
                    disabled={Boolean(initial?.id) && !isAdmin}
                    onChange={e => {
                      const newScope = e.target.value as 'NOI_BO' | 'HAN_CHE';
                      setForm(prev => ({
                        ...prev,
                        pham_vi: newScope,
                        gui_mail_toan_he_thong: newScope === 'HAN_CHE' ? false : prev.gui_mail_toan_he_thong,
                      }));
                      setReplacementSuggestions([]);
                    }}
                    className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast disabled:opacity-60 disabled:cursor-not-allowed"
                    title={
                      Boolean(initial?.id) && !isAdmin
                        ? (t('documents_ui.formModal.scopeAdminOnlyTooltip') || 'Chỉ Quản trị viên (Admin) mới có quyền thay đổi phạm vi lưu hành của văn bản sau khi thêm.')
                        : 'Chọn phạm vi lưu hành'
                    }
                  >
                    <option value="NOI_BO">{t('documents_ui.formModal.scopeInternal') || 'Nội bộ (Toàn cơ quan)'}</option>
                    <option value="HAN_CHE">{t('documents_ui.formModal.scopeRestrictedOption') || 'Hạn chế (Chỉ người nhận xem)'}</option>
                  </select>
                )}
              </div>
            </div>
          </div>

          {/* PHẦN 2: NGUỒN BAN HÀNH & NỘI DUNG VĂN BẢN */}
          <div className="bg-canvas/40 border border-border-subtle rounded-xl p-4 sm:p-5 space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle/60 gap-4">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-6 h-6 rounded-md bg-indigo-500/10 text-indigo-600 flex items-center justify-center text-xs font-bold shrink-0">
                  <i className="fa-solid fa-building-columns" />
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-main m-0 truncate">
                  {t('documents_ui.formModal.section2Title') || '2. Nguồn ban hành & Nội dung văn bản'}
                </h4>
              </div>
              <span className="text-xs text-muted shrink-0 text-right">{t('documents_ui.formModal.section2Subtitle') || 'Cơ quan gửi & Trích yếu'}</span>
            </div>

            <div className="space-y-3.5">
              {/* Cơ quan ban hành (Phân định rõ Văn bản Đến vs Văn bản Đi & Mật theo CSDL) */}
              {form.loai === 'DEN' ? (
                <div>
                  <label className="block text-xs font-semibold text-secondary mb-1.5">
                    {t('documents_ui.formModal.issuerInbound') || 'Cơ quan / Đơn vị ban hành'} <span className="text-danger">*</span>
                  </label>
                  <input
                    value={form.noi_ban_hanh}
                    onChange={e => setForm({ ...form, noi_ban_hanh: e.target.value })}
                    placeholder={t('documents_ui.formModal.issuerInboundPlaceholder') || 'Ví dụ: Bộ Giáo dục và Đào tạo, UBND Thành phố Hồ Chí Minh, ...'}
                    className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                    required
                  />
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center justify-between mb-0.5">
                    <label className="block text-xs font-semibold text-secondary m-0">
                      {t('documents_ui.formModal.issuerOutbound') || 'Đơn vị ban hành (Phòng / Ban nội bộ)'} <span className="text-danger">*</span>
                    </label>
                    <span className="text-[10px] text-muted hidden sm:inline">
                      {t('documents_ui.formModal.multipleUnitsHint') || '(Có thể chọn nhiều đơn vị)'}
                    </span>
                  </div>

                  {/* Thanh tìm kiếm chứa trực tiếp các thẻ phòng ban đã chọn */}
                  <div className="relative" ref={unitDropdownRef}>
                    <div
                      className="w-full min-h-[42px] bg-surface border border-border-subtle rounded-xl p-1.5 flex flex-wrap items-center gap-1.5 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-fast cursor-text"
                      onClick={() => {
                        unitSearchInputRef.current?.focus();
                        setIsUnitDropdownOpen(true);
                      }}
                    >
                      <div className="pl-1.5 text-muted text-xs pointer-events-none">
                        <i className="fa-solid fa-building-columns text-primary/70" />
                      </div>

                      {/* Các phòng ban đã chọn hiện NGAY TRÊN THANH TÌM KIẾM */}
                      {selectedUnitsList.map(unitName => (
                        <span
                          key={unitName}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-primary/10 border border-primary/20 text-primary text-xs font-medium animate-fadeIn shrink-0"
                        >
                          <span>{unitName}</span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRemoveUnit(unitName);
                            }}
                            className="w-4 h-4 rounded-full flex items-center justify-center hover:bg-rose-500/20 hover:text-rose-600 transition-fast text-[11px] ml-0.5 cursor-pointer"
                            title={`Bỏ chọn ${unitName}`}
                          >
                            <i className="fa-solid fa-xmark text-[10px]" />
                          </button>
                        </span>
                      ))}

                      {/* Ô gõ tìm kiếm co dãn tự nhiên ngay sau các thẻ */}
                      <input
                        ref={unitSearchInputRef}
                        type="text"
                        value={unitSearch}
                        onChange={e => {
                          setUnitSearch(e.target.value);
                          setIsUnitDropdownOpen(true);
                        }}
                        onFocus={() => setIsUnitDropdownOpen(true)}
                        placeholder={selectedUnitsList.length === 0 ? "Tìm kiếm và chọn phòng / ban..." : "Gõ để tìm thêm..."}
                        className="flex-1 min-w-[130px] bg-transparent text-sm text-main placeholder:text-muted focus:outline-none px-2 py-0.5"
                      />

                      {/* Nút xóa nhanh / toggle danh sách */}
                      <div className="ml-auto flex items-center gap-1 pr-1">
                        {unitSearch ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setUnitSearch('');
                              setIsUnitDropdownOpen(true);
                            }}
                            className="text-muted hover:text-main text-xs p-1 cursor-pointer"
                            title="Xóa chữ tìm kiếm"
                          >
                            <i className="fa-solid fa-xmark text-xs" />
                          </button>
                        ) : selectedUnitsList.length > 0 ? (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleClearAllUnits();
                            }}
                            className="text-[11px] text-muted hover:text-rose-500 transition-fast px-1 cursor-pointer"
                            title="Bỏ chọn tất cả"
                          >
                            <i className="fa-solid fa-xmark text-xs" />
                          </button>
                        ) : null}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setIsUnitDropdownOpen(prev => !prev);
                          }}
                          className="text-muted hover:text-main text-xs p-1 cursor-pointer"
                          title="Đóng / mở danh sách"
                        >
                          <i className={`fa-solid fa-chevron-down text-[11px] transition-transform ${isUnitDropdownOpen ? 'rotate-180' : ''}`} />
                        </button>
                      </div>
                    </div>

                    {/* Popover danh sách phòng ban: Sạch sẽ, không chữ rườm rà */}
                    {isUnitDropdownOpen && (
                      <div className="absolute left-0 right-0 top-full mt-1.5 bg-surface border border-border-subtle rounded-xl shadow-xl z-30 max-h-56 overflow-y-auto p-1.5 animate-fadeIn">
                        <div className="px-2.5 py-1 text-[11px] text-muted border-b border-border-subtle/50 mb-1">
                          {unitSearch.trim() ? (
                            <>Kết quả: <strong className="text-primary">{filteredUnits.length}</strong> phòng/ban</>
                          ) : (
                            <>Danh sách phòng/ban ({units.length}):</>
                          )}
                        </div>

                        {filteredUnits.length > 0 ? (
                          <div className="space-y-0.5">
                            {filteredUnits.map(u => {
                              const isChosen = selectedUnitsList.includes(u);
                              return (
                                <button
                                  key={u}
                                  type="button"
                                  onClick={() => {
                                    if (isChosen) {
                                      handleRemoveUnit(u);
                                    } else {
                                      handleAddUnit(u);
                                      setUnitSearch('');
                                    }
                                    unitSearchInputRef.current?.focus();
                                  }}
                                  className={`w-full text-left px-3 py-2 rounded-lg text-xs flex items-center justify-between transition-fast cursor-pointer ${
                                    isChosen
                                      ? 'bg-primary/10 text-primary font-semibold'
                                      : 'hover:bg-hover text-secondary hover:text-main'
                                  }`}
                                >
                                  <div className="flex items-center gap-2 min-w-0 pr-2">
                                    <i className={`fa-solid fa-building-columns text-[10px] ${isChosen ? 'text-primary' : 'text-muted'}`} />
                                    <span className="truncate">{u}</span>
                                  </div>
                                  {isChosen && (
                                    <i className="fa-solid fa-check text-primary text-xs shrink-0" />
                                  )}
                                </button>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="p-3 text-center text-xs text-muted">
                            <i className="fa-solid fa-magnifying-glass text-muted/60 text-base mb-1 block" />
                            Không tìm thấy phòng/ban nào khớp với "<strong>{unitSearch}</strong>"
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Trích yếu nội dung */}
              <div>
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {t('documents_ui.formModal.summary') || 'Trích yếu nội dung văn bản'} <span className="text-danger">*</span>
                </label>
                <textarea
                  rows={3}
                  value={form.trich_yeu}
                  onChange={e => setForm({ ...form, trich_yeu: e.target.value })}
                  placeholder={t('documents_ui.formModal.summaryPlaceholder') || 'Nhập tóm tắt ngắn gọn mục đích và nội dung cốt lõi của văn bản...'}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl p-3 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast resize-y"
                  required
                />
              </div>
            </div>
          </div>

          {/* PHẦN 3: KÝ DUYỆT & HIỆU LỰC VĂN BẢN */}
          <div className="bg-canvas/40 border border-border-subtle rounded-xl p-4 sm:p-5 space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle/60 gap-4">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-6 h-6 rounded-md bg-emerald-500/10 text-emerald-600 flex items-center justify-center text-xs font-bold shrink-0">
                  <i className="fa-solid fa-stamp" />
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-main m-0 truncate">
                  {t('documents_ui.formModal.section3Title') || '3. Ký duyệt & Hiệu lực văn bản'}
                </h4>
              </div>
              <span className="text-xs text-muted shrink-0 text-right">{t('documents_ui.formModal.section3Subtitle') || 'Thông tin người ký & Trạng thái pháp lý'}</span>
            </div>

            <div className="grid grid-cols-12 gap-3.5">
              {/* Người ký */}
              <div className="col-span-12 sm:col-span-6">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {t('documents_ui.formModal.signer') || 'Người ký văn bản'}
                </label>
                <input
                  value={form.nguoi_ky}
                  onChange={e => setForm({ ...form, nguoi_ky: e.target.value })}
                  placeholder={t('documents_ui.formModal.signerPlaceholder') || 'Họ và tên người ký (VD: Nguyễn Văn A)'}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Chức vụ */}
              <div className="col-span-12 sm:col-span-6">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {t('documents_ui.formModal.position') || 'Chức vụ người ký'}
                </label>
                <input
                  value={form.chuc_vu}
                  onChange={e => setForm({ ...form, chuc_vu: e.target.value })}
                  placeholder={t('documents_ui.formModal.positionPlaceholder') || 'VD: Thứ trưởng, Giám đốc, Hiệu trưởng...'}
                  className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                />
              </div>

              {/* Trạng thái hiệu lực (Hiển thị màu sắc động & hiệu ứng tương ứng với trạng thái) */}
              <div className="col-span-12 sm:col-span-6">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-secondary m-0">
                    {t('documents_ui.formModal.validityStatus') || 'Trạng thái hiệu lực'}
                  </label>
                  {form.hieu_luc === 'CON_HIEU_LUC' && (
                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      {t('documents_ui.formModal.statusInEffect') || 'Đang áp dụng'}
                    </span>
                  )}
                  {form.hieu_luc === 'CON_HIEU_LUC_1_PHAN' && (
                    <span className="text-xs font-semibold text-purple-600 dark:text-purple-400 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
                      {t('documents_ui.formModal.statusPartiallyInEffect') || 'Hiệu lực 1 phần'}
                    </span>
                  )}
                  {form.hieu_luc === 'HET_HIEU_LUC' && (
                    <span className="text-xs font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                      {t('documents_ui.formModal.statusExpired') || 'Hết giá trị'}
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
                    {(form.hieu_luc === 'HET_HIEU_LUC' || form.hieu_luc === 'HET_VA_THAY_THE') && (
                      <span className="inline-flex rounded-full h-2.5 w-2.5 bg-rose-500" />
                    )}
                  </div>

                  <select
                    value={form.hieu_luc === 'HET_VA_THAY_THE' ? 'HET_HIEU_LUC' : form.hieu_luc}
                    onChange={e => {
                      const newHieuLuc = e.target.value as FormState['hieu_luc'];
                      setForm(prev => ({
                        ...prev,
                        hieu_luc: newHieuLuc,
                        ngay_het_hieu_luc: newHieuLuc === 'CON_HIEU_LUC' ? '' : prev.ngay_het_hieu_luc,
                        link_thay_the: (newHieuLuc === 'CON_HIEU_LUC' && !isReplacingOther) ? '' : prev.link_thay_the,
                      }));
                      if (newHieuLuc === 'CON_HIEU_LUC' && !isReplacingOther) {
                        setShowReplacementDropdown(false);
                      }
                    }}
                    className={`w-full text-sm rounded-xl pl-8 pr-8 py-2 font-semibold transition-all duration-200 border cursor-pointer ${
                      form.hieu_luc === 'CON_HIEU_LUC'
                        ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-700 dark:text-emerald-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 shadow-xs'
                        : form.hieu_luc === 'CON_HIEU_LUC_1_PHAN'
                        ? 'bg-purple-500/10 border-purple-500/40 text-purple-700 dark:text-purple-400 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 shadow-xs'
                        : 'bg-rose-500/10 border-rose-500/40 text-rose-700 dark:text-rose-400 focus:outline-none focus:border-rose-500 focus:ring-1 focus:ring-rose-500 shadow-xs'
                    }`}
                  >
                    <option value="CON_HIEU_LUC" className="bg-surface text-emerald-600 font-semibold">
                      {t('documents_ui.formModal.statusActive') || 'Còn hiệu lực'}
                    </option>
                    <option value="CON_HIEU_LUC_1_PHAN" className="bg-surface text-purple-600 font-semibold">
                      {t('documents_ui.formModal.statusPartiallyActive') || 'Còn hiệu lực 1 phần'}
                    </option>
                    <option value="HET_HIEU_LUC" className="bg-surface text-rose-600 font-semibold">
                      {t('documents_ui.formModal.statusInactive') || 'Hết hiệu lực'}
                    </option>
                  </select>
                </div>
              </div>

              {/* Ngày hết hiệu lực */}
              <div className="col-span-12 sm:col-span-6">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {t('documents_ui.formModal.expirationDate') || 'Ngày hết hiệu lực'} <span className="text-muted font-normal text-xs">{t('documents_ui.formModal.optional') || '(Tùy chọn)'}</span>
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
                          setSelectedReplacementDocs([]);
                          setShowReplacementDropdown(false);
                        }
                      }}
                      className="w-4 h-4 text-primary rounded border-border-subtle focus:ring-primary/20 transition-fast"
                    />
                    <span className="text-xs font-semibold text-main">
                      <i className="fa-solid fa-repeat text-primary mr-1" />
                      {t('documents_ui.formModal.replacesOtherCheckbox') || 'Văn bản này thay thế cho văn bản khác trong hệ thống'}
                    </span>
                  </label>
                </div>
              )}

              {/* Link văn bản thay thế (Hỗ trợ 1-nhiều văn bản, phân hệ & phạm vi riêng biệt) */}
              {(isReplacingOther || form.hieu_luc === 'CON_HIEU_LUC_1_PHAN' || Boolean(form.link_thay_the)) && (
                <div className="col-span-12 animate-in fade-in duration-150" ref={replacementDropdownRef}>
                  <div className="flex flex-wrap items-center justify-between gap-1 mb-1.5">
                    <label className="block text-xs font-semibold text-warning-text m-0">
                      <i className="fa-solid fa-link mr-1.5" />
                      {isReplacingOther || form.hieu_luc === 'CON_HIEU_LUC' || form.hieu_luc === 'CON_HIEU_LUC_1_PHAN'
                        ? 'Văn bản bị thay thế (Số hiệu hoặc liên kết) *'
                        : 'Văn bản mới thay thế (Số hiệu hoặc liên kết) *'}
                    </label>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="px-2 py-0.5 rounded-md bg-warning/15 text-warning-text font-medium text-[11px]">
                        {form.loai === 'DI' ? 'Hệ VB Đi' : form.loai === 'MAT' ? 'Hệ VB Mật' : 'Hệ VB Đến'} • {form.pham_vi === 'HAN_CHE' ? 'Phạm vi Hạn chế' : 'Phạm vi Nội bộ'}
                      </span>
                      <span className="text-muted hidden sm:inline text-[11px]">
                        (Chọn một hoặc nhiều văn bản)
                      </span>
                    </div>
                  </div>

                  {/* Danh sách các văn bản đã chọn dạng Chip Tags (Giải pháp 2: 1 văn bản chính + Hộp thoại xem danh sách) */}
                  {selectedSoHieus.length > 0 && (
                    <div className="mb-2 p-2.5 bg-emerald-500/10 border border-emerald-500/25 rounded-xl transition-all duration-200">
                      <div className="flex items-center justify-between gap-2 mb-1.5 pb-1 border-b border-emerald-500/20 text-xs">
                        <span className="text-[11px] font-semibold text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                          <i className="fa-solid fa-layer-group text-emerald-600" />
                          <span>Đã chọn ({selectedSoHieus.length}):</span>
                        </span>
                        {selectedSoHieus.length > 1 && (
                          <button
                            type="button"
                            onClick={handleClearAllReplacementDocs}
                            className="text-[11px] text-muted hover:text-danger hover:underline pl-1 cursor-pointer"
                            title="Xóa tất cả các văn bản đã chọn"
                          >
                            Xóa tất cả
                          </button>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-1.5 p-0.5">
                        {/* 1. Luôn hiển thị văn bản đầu tiên */}
                        {(() => {
                          const firstSh = selectedSoHieus[0];
                          const parsedFirst = parseReplacementString(firstSh);
                          const matchedDoc = selectedReplacementDocs.find(
                            d => matchDocWithReplacement(d, firstSh)
                          );
                          const displayStt = matchedDoc?.so_thu_tu ?? matchedDoc?.so_den ?? parsedFirst.stt;
                          const displayExtra = matchedDoc?.noi_ban_hanh || parsedFirst.extraInfo;
                          const isDen = (form.loai || defaultLoai || 'DEN') === 'DEN';
                          return (
                            <span
                              key={firstSh}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface border border-emerald-500/40 text-emerald-700 dark:text-emerald-300 text-xs font-medium shadow-xs animate-in fade-in max-w-full"
                            >
                              <i className="fa-solid fa-file-circle-check text-emerald-600 text-[11px] shrink-0" />
                              <strong className="font-mono text-emerald-800 dark:text-emerald-200 shrink-0">{parsedFirst.baseSoHieu}</strong>
                              {displayStt && (
                                <span
                                  className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-700 dark:text-blue-300 font-bold font-mono"
                                  title={`${isDen ? 'Số đến' : 'Số đi'}: #${displayStt}`}
                                >
                                  #{displayStt}
                                </span>
                              )}
                              {displayExtra && (
                                <span className="max-w-[150px] sm:max-w-[200px] truncate text-muted text-[11px]" title={displayExtra}>
                                  ({displayExtra})
                                </span>
                              )}
                              {matchedDoc?.trich_yeu && (
                                <span className="max-w-[180px] sm:max-w-[240px] truncate text-muted/80 text-[11px]" title={matchedDoc.trich_yeu}>
                                  - {matchedDoc.trich_yeu}
                                </span>
                              )}
                              <button
                                type="button"
                                onClick={() => handleRemoveReplacementDoc(firstSh)}
                                className="text-muted hover:text-danger hover:bg-danger/10 rounded-full w-4 h-4 flex items-center justify-center transition-colors ml-0.5 cursor-pointer shrink-0"
                                title={`Bỏ chọn ${parsedFirst.baseSoHieu}`}
                              >
                                <i className="fa-solid fa-xmark text-[10px]" />
                              </button>
                            </span>
                          );
                        })()}

                        {/* 2. Nếu có nhiều hơn 1 văn bản: Nút mở Hộp thoại danh sách chi tiết (Giải pháp 2) */}
                        {selectedSoHieus.length > 1 && (
                          <button
                            type="button"
                            onClick={() => {
                              setReplacementListPage(1);
                              setIsReplacementListModalOpen(true);
                            }}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-800 dark:text-emerald-300 border border-emerald-500/40 transition-all cursor-pointer shadow-2xs hover:-translate-y-[0.5px]"
                            title="Bấm để mở hộp thoại xem và quản lý danh sách các văn bản đã chọn"
                          >
                            <i className="fa-solid fa-layer-group text-[11px]" />
                            <span>+{selectedSoHieus.length - 1} văn bản khác</span>
                            <i className="fa-solid fa-arrow-up-right-from-square text-[9px] text-emerald-700/70" />
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Thanh tìm kiếm & chọn văn bản dạng Multi-Select Tag Input */}
                  <div className="relative" ref={replacementDropdownRef}>
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none">
                      <i className="fa-solid fa-magnifying-glass" />
                    </div>

                    <input
                      type="text"
                      value={replacementSearchText}
                      onChange={e => handleReplacementSearchChange(e.target.value)}
                      onKeyDown={handleReplacementKeyDown}
                      onFocus={handleReplacementInputFocus}
                      placeholder={
                        selectedSoHieus.length > 0
                          ? "Gõ số hiệu hoặc trích yếu để chọn thêm văn bản khác..."
                          : "Nhập số hiệu văn bản (VD: 88/QĐ-SNN), trích yếu để tìm kiếm..."
                      }
                      className="w-full text-sm bg-surface border border-warning-border rounded-xl pl-9 pr-9 py-2 text-main placeholder:text-muted focus:outline-none focus:border-warning focus:ring-1 focus:ring-warning transition-fast"
                      autoComplete="off"
                    />

                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                      {isSearchingReplacement && (
                        <i className="fa-solid fa-circle-notch fa-spin text-warning-text text-xs" />
                      )}
                      {replacementSearchText && !isSearchingReplacement && (
                        <button
                          type="button"
                          onClick={() => {
                            setReplacementSearchText('');
                            searchReplacementDocs('');
                          }}
                          className="text-muted hover:text-danger p-0.5 rounded transition-colors"
                          title="Xóa nội dung tìm kiếm"
                        >
                          <i className="fa-solid fa-xmark text-xs" />
                        </button>
                      )}
                    </div>

                    {/* Danh sách văn bản gợi ý dạng Panel mở rộng liền mạch (Inline Accordion) */}
                    {showReplacementDropdown && (
                      <div className="relative mt-2 bg-surface border border-border-subtle rounded-xl shadow-md overflow-hidden max-h-64 overflow-y-auto animate-in fade-in duration-150">
                        <div className="px-3 py-2 bg-canvas/90 border-b border-border-subtle/80 flex items-center justify-between text-xs font-semibold text-secondary sticky top-0 backdrop-blur-sm z-10">
                          <span className="flex items-center gap-1.5">
                            <i className="fa-solid fa-list-check text-primary" />
                            {replacementSearchText.trim() ? (
                              <>Kết quả tìm kiếm ({replacementSuggestions.length})</>
                            ) : (
                              <>Văn bản phù hợp trong hệ thống ({replacementSuggestions.length})</>
                            )}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-[11px] text-muted hidden sm:inline">
                              Hệ: <strong>{form.loai === 'DI' ? 'VB Đi' : 'VB Đến'}</strong> • Phạm vi: <strong>{form.pham_vi === 'HAN_CHE' ? 'Hạn chế' : 'Nội bộ'}</strong>
                            </span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setShowReplacementDropdown(false);
                              }}
                              className="px-2 py-0.5 rounded text-[11px] text-muted hover:text-main hover:bg-canvas transition-colors border border-border-subtle flex items-center gap-1"
                              title="Đóng danh sách gợi ý"
                            >
                              <i className="fa-solid fa-xmark text-[10px]" />
                              <span>Đóng</span>
                            </button>
                          </div>
                        </div>

                        {replacementSuggestions.length > 0 ? (
                          <div className="divide-y divide-border-subtle/40">
                            {replacementSuggestions.map(doc => {
                              const isSelected = selectedSoHieus.some(
                                s => matchDocWithReplacement(doc, s)
                              );
                              return (
                                <div
                                  key={doc.id}
                                  onClick={() => handleToggleReplacementDoc(doc)}
                                  className={`p-3 cursor-pointer transition-colors group text-left flex items-start gap-2.5 ${
                                    isSelected ? 'bg-primary/10 hover:bg-primary/15' : 'hover:bg-primary/5'
                                  }`}
                                >
                                  <div className="mt-0.5 shrink-0">
                                    <div
                                      className={`w-4 h-4 rounded flex items-center justify-center text-[10px] transition-colors ${
                                        isSelected
                                          ? 'bg-emerald-600 text-white font-bold'
                                          : 'border border-border-subtle group-hover:border-primary text-transparent'
                                      }`}
                                    >
                                      <i className="fa-solid fa-check" />
                                    </div>
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-2 mb-1">
                                      <div className="flex items-center gap-2">
                                        <span className={`font-semibold text-xs font-mono group-hover:underline ${isSelected ? 'text-emerald-700 dark:text-emerald-400 font-bold' : 'text-primary'}`}>
                                          {doc.so_hieu}
                                        </span>
                                        {doc.so_thu_tu && (
                                          <span
                                            className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-700 dark:text-blue-300 font-bold font-mono"
                                            title={`${form.loai === 'DI' ? 'Số đi' : 'Số đến'}: #${doc.so_thu_tu}`}
                                          >
                                            #{doc.so_thu_tu}
                                          </span>
                                        )}
                                        {doc.loai_display && (
                                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted/20 text-secondary font-medium">
                                            {doc.loai_display}
                                          </span>
                                        )}
                                        {isSelected && (
                                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 font-semibold">
                                            ✓ Đã chọn
                                          </span>
                                        )}
                                      </div>
                                      {(doc.ngay_ban_hanh || doc.ngay_den) && (
                                        <span className="text-[11px] text-muted font-mono">
                                          {new Date(doc.ngay_ban_hanh || doc.ngay_den!).toLocaleDateString('vi-VN')}
                                        </span>
                                      )}
                                    </div>
                                    <p className="text-xs text-main line-clamp-2 m-0 group-hover:text-primary transition-colors leading-relaxed">
                                      {doc.trich_yeu}
                                    </p>
                                    {doc.noi_ban_hanh && (
                                      <div className="text-[11px] text-muted mt-1 flex items-center gap-1.5">
                                        <i className="fa-solid fa-building text-[10px]" />
                                        <span className="truncate">{doc.noi_ban_hanh}</span>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : !isSearchingReplacement ? (
                          <div className="p-4 text-center text-xs text-muted space-y-1">
                            <i className="fa-solid fa-circle-info text-muted text-sm block" />
                            <div>
                              Không tìm thấy văn bản phù hợp trong hệ thống ({form.loai === 'DI' ? 'Văn bản Đi' : 'Văn bản Đến'} - {form.pham_vi === 'HAN_CHE' ? 'Hạn chế' : 'Nội bộ'}). Vui lòng chọn số hiệu văn bản có sẵn trong danh mục.
                            </div>
                            <div className="text-[11px] text-muted/70">
                              Chỉ được phép liên kết thay thế văn bản cùng phân hệ và cùng phạm vi lưu hành.
                            </div>
                          </div>
                        ) : null}
                      </div>
                    )}
                  </div>

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
                          <>Tự động cập nhật {selectedSoHieus.length > 1 ? `tất cả ${selectedSoHieus.length} văn bản cũ` : 'văn bản cũ'} sang trạng thái <strong className="text-purple-600 dark:text-purple-400">Còn hiệu lực 1 phần</strong></>
                        ) : (
                          <>Tự động đồng bộ liên kết 2 chiều giữa các văn bản</>
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
          <div className="bg-canvas/40 border border-border-subtle rounded-xl p-4 sm:p-5 space-y-4">
            <div className="flex items-center justify-between pb-2.5 border-b border-border-subtle/60 gap-4">
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-6 h-6 rounded-md bg-amber-500/10 text-amber-600 flex items-center justify-center text-xs font-bold shrink-0">
                  <i className="fa-solid fa-share-nodes" />
                </span>
                <h4 className="text-xs font-bold uppercase tracking-wider text-main m-0 truncate">
                  {t('documents_ui.formModal.section4Title') || '4. Phân phối xử lý & Tệp đính kèm'}
                </h4>
              </div>
              <span className="text-xs text-muted shrink-0 text-right">{t('documents_ui.formModal.section4Subtitle') || 'Điều phối đơn vị & Tải lên tệp'}</span>
            </div>

            {form.pham_vi === 'HAN_CHE' && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl flex items-center gap-2.5 text-xs text-amber-600 dark:text-amber-400">
                <i className="fa-solid fa-shield-halved text-sm shrink-0" />
                <span>
                  <strong>{t('documents_ui.formModal.restrictedDocLabel') || 'Văn bản hạn chế (Mật nội bộ)'}:</strong> {t('documents_ui.formModal.restrictedNotice') || 'Bắt buộc chọn ít nhất một cán bộ nhận / xử lý. Hệ thống tự động vô hiệu hóa tính năng gửi email toàn trường và chỉ người nhận cùng người tạo mới có quyền xem.'}
                </span>
              </div>
            )}

            {/* Phân phối đơn vị & cán bộ */}
            <div className="grid grid-cols-12 gap-3.5">
              <div className="col-span-12 sm:col-span-6">
                <label className="block text-xs font-semibold text-secondary mb-1.5">
                  {t('documents_ui.formModal.receivingUnit') || 'Đơn vị nhận / chủ trì xử lý'}
                </label>
                <div className="relative" ref={recipientUnitDropdownRef}>
                  <button
                    type="button"
                    onClick={() => setIsRecipientUnitDropdownOpen(prev => !prev)}
                    className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3 py-2 text-main flex items-center justify-between text-left focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast cursor-pointer"
                  >
                    <span className={`truncate ${selectedUnit ? 'font-medium text-main' : 'text-muted'}`}>
                      {selectedUnit || (t('documents_ui.formModal.selectReceivingUnit') || '-- Chọn đơn vị nhận --')}
                    </span>
                    <div className="flex items-center gap-1.5 ml-2 shrink-0">
                      {selectedUnit && (
                        <span
                          role="button"
                          tabIndex={0}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleUnitChange('');
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.stopPropagation();
                              handleUnitChange('');
                            }
                          }}
                          className="w-4 h-4 rounded-full flex items-center justify-center hover:bg-rose-500/20 text-muted hover:text-rose-500 transition-fast text-[11px] cursor-pointer"
                          title="Bỏ chọn đơn vị"
                        >
                          <i className="fa-solid fa-xmark text-[10px]" />
                        </span>
                      )}
                      <i className={`fa-solid fa-chevron-down text-muted text-xs transition-transform duration-200 ${isRecipientUnitDropdownOpen ? 'rotate-180' : ''}`} />
                    </div>
                  </button>

                  {isRecipientUnitDropdownOpen && (
                    <div className="absolute left-0 right-0 top-full mt-1 bg-surface border border-border-subtle rounded-xl shadow-2xl z-30 overflow-hidden animate-fadeIn">
                      <div className="p-2 border-b border-border-subtle/70 bg-canvas/40">
                        <div className="relative">
                          <i className="fa-solid fa-magnifying-glass absolute left-2.5 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none" />
                          <input
                            type="text"
                            value={recipientUnitSearch}
                            onChange={e => setRecipientUnitSearch(e.target.value)}
                            placeholder={t('documents_ui.formModal.searchUnitPlaceholder') || 'Gõ để tìm nhanh đơn vị...'}
                            autoFocus
                            className="w-full text-xs bg-surface border border-border-subtle rounded-lg pl-7 pr-7 py-1.5 text-main placeholder:text-muted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-fast"
                          />
                          {recipientUnitSearch && (
                            <button
                              type="button"
                              onClick={() => setRecipientUnitSearch('')}
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-main text-xs"
                            >
                              <i className="fa-solid fa-xmark text-[10px]" />
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="max-h-52 overflow-y-auto p-1 space-y-0.5 custom-scrollbar">
                        <button
                          type="button"
                          onClick={() => {
                            handleUnitChange('');
                            setIsRecipientUnitDropdownOpen(false);
                            setRecipientUnitSearch('');
                          }}
                          className={`w-full text-left px-3 py-2 rounded-lg text-xs flex items-center justify-between transition-fast cursor-pointer ${
                            !selectedUnit ? 'bg-primary/10 text-primary font-semibold' : 'text-muted hover:bg-hover hover:text-main'
                          }`}
                        >
                          <span>{t('documents_ui.formModal.selectReceivingUnit') || '-- Chọn đơn vị nhận --'}</span>
                          {!selectedUnit && <i className="fa-solid fa-check text-xs text-primary" />}
                        </button>

                        {filteredRecipientUnits.map(u => {
                          const isSelected = selectedUnit === u;
                          return (
                            <button
                              key={u}
                              type="button"
                              onClick={() => {
                                handleUnitChange(u);
                                setIsRecipientUnitDropdownOpen(false);
                                setRecipientUnitSearch('');
                              }}
                              className={`w-full text-left px-3 py-2 rounded-lg text-xs flex items-center justify-between transition-fast cursor-pointer ${
                                isSelected ? 'bg-primary/10 text-primary font-semibold' : 'hover:bg-hover text-secondary hover:text-main'
                              }`}
                            >
                              <span className="truncate pr-2">{u}</span>
                              {isSelected && <i className="fa-solid fa-check text-xs text-primary shrink-0" />}
                            </button>
                          );
                        })}

                        {filteredRecipientUnits.length === 0 && (
                          <div className="px-3 py-4 text-center text-xs text-muted">
                            <i className="fa-solid fa-folder-open text-base mb-1 block opacity-50" />
                            Không tìm thấy đơn vị nào khớp với "{recipientUnitSearch}"
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="col-span-12 sm:col-span-6">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-secondary flex items-center gap-1">
                    <span>Cán bộ nhận / xử lý</span>
                    {!selectedUnit ? (
                      <span className="text-[11px] text-muted font-normal">(Chưa chọn đơn vị)</span>
                    ) : (
                      <span className="text-[11px] text-primary font-medium">
                        ({form.nguoi_nhan.length > 0 ? `Đã chọn ${form.nguoi_nhan.length}/${staff.length}` : `${staff.length} cán bộ`})
                      </span>
                    )}
                  </label>
                  {selectedUnit && staff.length > 0 && form.nguoi_nhan.length > 0 && (
                    <button
                      type="button"
                      onClick={() => setForm(prev => ({ ...prev, nguoi_nhan: [] }))}
                      className="text-[11px] text-muted hover:text-rose-500 transition-colors cursor-pointer"
                    >
                      Bỏ chọn tất cả
                    </button>
                  )}
                </div>

                {!selectedUnit ? (
                  <div className="h-[116px] w-full border border-dashed border-border-subtle/80 rounded-xl bg-canvas/30 p-3 flex flex-col items-center justify-center text-center transition-all select-none">
                    <div className="w-8 h-8 rounded-full bg-surface border border-border-subtle/60 flex items-center justify-center mb-1.5 shadow-xs text-muted">
                      <i className="fa-solid fa-lock text-xs" />
                    </div>
                    <p className="text-xs font-semibold text-secondary m-0">Vui lòng chọn đơn vị nhận trước</p>
                    <p className="text-[11px] text-muted m-0 mt-0.5">Danh sách cán bộ sẽ hiển thị theo đơn vị đã chọn</p>
                  </div>
                ) : isStaffLoading ? (
                  <div className="h-[116px] w-full border border-border-subtle rounded-xl bg-surface p-3 flex items-center justify-center text-center gap-2 text-muted">
                    <i className="fa-solid fa-circle-notch fa-spin text-primary text-sm" />
                    <span className="text-xs">Đang tải danh sách cán bộ...</span>
                  </div>
                ) : staff.length === 0 ? (
                  <div className="h-[116px] w-full border border-border-subtle rounded-xl bg-surface p-3 flex flex-col items-center justify-center text-center text-muted select-none">
                    <i className="fa-solid fa-user-slash text-base mb-1 text-muted/60" />
                    <p className="text-xs font-medium text-secondary m-0">Đơn vị này hiện chưa có cán bộ nào</p>
                    <p className="text-[11px] text-muted m-0 mt-0.5">Vui lòng chọn đơn vị khác hoặc liên hệ Quản trị viên</p>
                  </div>
                ) : (
                  <div className="h-[116px] overflow-y-auto border border-border-subtle rounded-xl p-2 bg-surface space-y-1 custom-scrollbar">
                    {staff.map(s => {
                      const isSelected = form.nguoi_nhan.includes(s.id);
                      return (
                        <label
                          key={s.id}
                          className={`flex items-center gap-2 p-1.5 rounded-lg cursor-pointer text-xs transition-colors ${
                            isSelected ? 'bg-primary/10 text-primary font-medium' : 'hover:bg-hover text-main'
                          }`}
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
                            className="rounded border-border-subtle text-primary focus:ring-primary cursor-pointer"
                          />
                          <span className="truncate">{s.ho_ten || s.full_name || s.username}</span>
                          <span className="text-xs text-muted shrink-0">(@{s.username})</span>
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
                      <div className="flex items-center gap-1 shrink-0 ml-2">
                        <a
                          href={att.file}
                          target="_blank"
                          rel="noreferrer"
                          className="w-7 h-7 rounded-lg hover:bg-surface-elevated text-primary flex items-center justify-center transition-fast"
                          title="Xem / Tải về"
                        >
                          <i className="fa-solid fa-download text-xs" />
                        </a>
                        <button
                          type="button"
                          onClick={() => handleRemoveExistingAttachment(att.id)}
                          className="w-7 h-7 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-500 hover:text-rose-600 flex items-center justify-center transition-fast cursor-pointer"
                          title="Xóa tệp đính kèm này"
                        >
                          <i className="fa-solid fa-trash-can text-xs" />
                        </button>
                      </div>
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
                    <span className="text-xs font-bold text-main block">{t('documents_ui.formModal.displayOnSystem') || 'Hiển thị trên hệ thống'}</span>
                    <span className="text-xs text-muted block leading-snug">
                      {t('documents_ui.formModal.displayOnSystemDesc') || 'Cho phép cán bộ nhân viên tra cứu và xem văn bản này'}
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
                      <span className="text-xs font-bold text-main block">{t('documents_ui.formModal.sendEmailToAll') || 'Gửi email toàn trường'}</span>
                      <span className="text-xs text-muted block leading-snug">
                        {t('documents_ui.formModal.sendEmailToAllDesc') || 'Tự động gửi thông báo văn bản mới tới hòm thư CBNV'}
                      </span>
                    </div>
                  </label>
                ) : (
                  <div className="flex items-start gap-3 p-3 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-700 dark:text-rose-300">
                    <span className="text-base leading-none">🔒</span>
                    <div>
                      <span className="text-xs font-bold block">
                        {form.pham_vi === 'HAN_CHE' 
                          ? (t('documents_ui.formModal.restrictedDocLabel') || 'Văn bản Hạn chế (Mật nội bộ)') 
                          : (t('documents_ui.formModal.confidentialDocLabel') || 'Văn bản Mật lưu hành nội bộ')}
                      </span>
                      <span className="text-xs text-muted block leading-snug">
                        {t('documents_ui.formModal.restrictedEmailNotice') || 'Không gửi email diện rộng toàn trường. Chỉ cán bộ nhận được chỉ định mới có quyền tiếp cận.'}
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
            <span>{t('documents_ui.formModal.requiredFieldNotice') || 'Các trường có dấu sao đỏ là bắt buộc nhập'}</span>
          </div>
          <div className="flex items-center gap-2.5">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onClose}
              disabled={loading}
            >
              {t('documents_ui.formModal.cancel') || 'Hủy bỏ'}
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              icon={loading ? 'fa-spinner fa-spin' : 'fa-floppy-disk'}
              disabled={loading}
            >
              {loading 
                ? (t('documents_ui.formModal.saving') || 'Đang lưu...') 
                : initial?.id 
                ? (t('documents_ui.formModal.update') || 'Cập nhật') 
                : (t('documents_ui.formModal.save') || 'Lưu văn bản')}
            </Button>
          </div>
        </div>
      </form>

      <AlertModal
        open={alertOpen}
        onClose={() => setAlertOpen(false)}
        message={alertMsg}
      />

      {/* Hộp thoại xem và quản lý danh sách văn bản thay thế đã chọn (Giải pháp 2) */}
      {isReplacementListModalOpen && (
        <div
          className="fixed inset-0 z-[10050] flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150"
          onClick={() => setIsReplacementListModalOpen(false)}
        >
          <div
            className="bg-surface border border-border-subtle rounded-2xl shadow-2xl w-[600px] max-w-full flex flex-col max-h-[85vh] overflow-hidden animate-in zoom-in-95 duration-150"
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border-subtle bg-canvas/60 shrink-0">
              <div className="flex items-center gap-2.5">
                <span className="w-8 h-8 rounded-lg bg-emerald-500/15 text-emerald-600 flex items-center justify-center text-sm font-bold">
                  <i className="fa-solid fa-layer-group" />
                </span>
                <div>
                  <h4 className="text-sm font-bold text-main m-0">
                    Danh Sách Văn Bản Bị Thay Thế Đã Chọn ({selectedSoHieus.length})
                  </h4>
                  <p className="text-[11px] text-muted m-0">
                    {form.loai === 'DI' ? 'Hệ Văn bản Đi' : 'Hệ Văn bản Đến'} • {form.pham_vi === 'HAN_CHE' ? 'Phạm vi Hạn chế' : 'Phạm vi Nội bộ'}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsReplacementListModalOpen(false)}
                className="w-7 h-7 rounded-lg text-muted hover:text-main hover:bg-hover flex items-center justify-center transition-colors cursor-pointer"
                title="Đóng cửa sổ"
              >
                <i className="fa-solid fa-xmark text-sm" />
              </button>
            </div>

            {/* Body List with Pagination (5 items per page) */}
            {(() => {
              const REPLACEMENT_PAGE_SIZE = 5;
              const totalReplacementPages = Math.max(1, Math.ceil(selectedSoHieus.length / REPLACEMENT_PAGE_SIZE));
              const safeReplacementPage = Math.min(Math.max(1, replacementListPage), totalReplacementPages);
              const replacementStartIdx = (safeReplacementPage - 1) * REPLACEMENT_PAGE_SIZE;
              const paginatedReplacementSoHieus = selectedSoHieus.slice(
                replacementStartIdx,
                replacementStartIdx + REPLACEMENT_PAGE_SIZE
              );

              return (
                <>
                  <div className="flex-1 overflow-y-auto p-3 divide-y divide-border-subtle/40 custom-scrollbar">
                    {selectedSoHieus.length === 0 ? (
                      <div className="py-8 text-center text-xs text-muted">
                        <i className="fa-solid fa-inbox text-2xl text-muted/50 mb-2 block" />
                        Chưa có văn bản nào được chọn
                      </div>
                    ) : (
                      paginatedReplacementSoHieus.map((sh, pageRelativeIdx) => {
                        const globalIdx = replacementStartIdx + pageRelativeIdx;
                        const parsedSh = parseReplacementString(sh);
                        const matchedDoc = selectedReplacementDocs.find(
                          d => matchDocWithReplacement(d, sh)
                        );
                        const actualNumber = matchedDoc?.so_thu_tu ?? matchedDoc?.so_den ?? parsedSh.stt;
                        const badgeLabel = actualNumber ? `#${actualNumber}` : `#${globalIdx + 1}`;
                        const badgeTooltip = actualNumber
                          ? (form.loai === 'DI' ? `Số đi: #${actualNumber}` : `Số đến: #${actualNumber}`)
                          : (form.loai === 'DI' ? 'Số đi trong sổ' : 'Số đến trong sổ');
                        const displayExtra = matchedDoc?.noi_ban_hanh || parsedSh.extraInfo;

                        return (
                          <div
                            key={sh}
                            className="py-2.5 px-2 hover:bg-surface-elevated rounded-xl flex items-start justify-between gap-3 transition-colors group"
                          >
                            <div className="flex items-start gap-2.5 min-w-0 flex-1">
                              <span
                                className="mt-0.5 shrink-0 min-w-[28px] px-1.5 h-5 rounded-md bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-mono text-[10px] font-bold flex items-center justify-center"
                                title={badgeTooltip}
                              >
                                {badgeLabel}
                              </span>
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono font-bold text-xs text-emerald-800 dark:text-emerald-300">
                                    {parsedSh.baseSoHieu}
                                  </span>
                                </div>
                                {matchedDoc?.trich_yeu && (
                                  <p className="text-xs text-main leading-relaxed mt-1 m-0">
                                    {matchedDoc.trich_yeu}
                                  </p>
                                )}
                                {displayExtra && (
                                  <div className="text-[11px] text-muted mt-1 flex items-center gap-1.5">
                                    <i className="fa-solid fa-building text-[10px]" />
                                    <span className="truncate">{displayExtra}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                handleRemoveReplacementDoc(sh);
                                if (selectedSoHieus.length <= 1) {
                                  setIsReplacementListModalOpen(false);
                                } else {
                                  const remainingCount = selectedSoHieus.length - 1;
                                  const newTotal = Math.max(1, Math.ceil(remainingCount / REPLACEMENT_PAGE_SIZE));
                                  if (safeReplacementPage > newTotal) {
                                    setReplacementListPage(newTotal);
                                  }
                                }
                              }}
                              className="px-2 py-1 rounded-lg text-xs font-medium text-danger hover:bg-danger/10 border border-danger/20 hover:border-danger/40 transition-colors shrink-0 flex items-center gap-1 cursor-pointer"
                              title={`Xóa văn bản ${parsedSh.baseSoHieu}`}
                            >
                              <i className="fa-solid fa-trash-can text-[11px]" />
                              <span>Xóa</span>
                            </button>
                          </div>
                        );
                      })
                    )}
                  </div>

                  {/* Footer */}
                  <div className="px-5 py-3 border-t border-border-subtle bg-canvas/60 flex flex-wrap items-center justify-between gap-3 shrink-0">
                    <span className="text-xs text-secondary">
                      Tổng cộng: <strong className="text-main">{selectedSoHieus.length}</strong> văn bản
                    </span>

                    {/* Phân trang (5 văn bản / trang khi danh sách > 5) */}
                    {totalReplacementPages > 1 && (
                      <div className="flex items-center gap-1.5 text-xs text-secondary">
                        <button
                          type="button"
                          disabled={safeReplacementPage <= 1}
                          onClick={() => setReplacementListPage(p => Math.max(1, p - 1))}
                          className="w-7 h-7 rounded-lg border border-border-subtle hover:bg-surface-elevated disabled:opacity-30 disabled:pointer-events-none flex items-center justify-center transition-colors cursor-pointer"
                          title="Trang trước"
                          aria-label="Trang trước"
                        >
                          <i className="fa-solid fa-chevron-left text-[11px]" />
                        </button>
                        <span
                          data-testid="replacement-pagination-page"
                          className="font-medium px-2.5 py-1 rounded-md bg-surface border border-border-subtle/80 text-[11px]"
                        >
                          Trang <strong className="text-main">{safeReplacementPage}</strong> / {totalReplacementPages}
                        </span>
                        <button
                          type="button"
                          disabled={safeReplacementPage >= totalReplacementPages}
                          onClick={() => setReplacementListPage(p => Math.min(totalReplacementPages, p + 1))}
                          className="w-7 h-7 rounded-lg border border-border-subtle hover:bg-surface-elevated disabled:opacity-30 disabled:pointer-events-none flex items-center justify-center transition-colors cursor-pointer"
                          title="Trang tiếp theo"
                          aria-label="Trang tiếp theo"
                        >
                          <i className="fa-solid fa-chevron-right text-[11px]" />
                        </button>
                      </div>
                    )}

                    <div className="flex items-center gap-2">
                      {selectedSoHieus.length > 1 && (
                        <button
                          type="button"
                          onClick={() => {
                            handleClearAllReplacementDocs();
                            setIsReplacementListModalOpen(false);
                          }}
                          className="px-3 py-1.5 rounded-xl text-xs font-semibold text-danger hover:bg-danger/10 border border-danger/30 transition-colors cursor-pointer"
                        >
                          Xóa tất cả
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setIsReplacementListModalOpen(false)}
                        className="px-4 py-1.5 rounded-xl text-xs font-semibold bg-surface-elevated hover:bg-surface-elevated/80 border border-border-subtle text-main transition-colors cursor-pointer"
                      >
                        Đóng
                      </button>
                    </div>
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      )}
    </div>,
    document.body
  );
}
