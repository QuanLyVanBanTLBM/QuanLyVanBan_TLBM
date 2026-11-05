import React, { useState, useMemo, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { ActivePageId } from '@app-types/navigation';
import { useTranslation } from '@i18n/translate';
import { formatUserName } from '@lib/roleUtils';
import { apiClient } from '@lib/apiClient';
import { Badge } from '@components/common';
import BirthdaysWidget, { BirthdayEmployee } from './BirthdaysWidget';
import DocumentPreviewModal from './DocumentPreviewModal';
import TaskDetailModal from './TaskDetailModal';

export interface TaskItem {
  id: string;
  title: string;
  due: string;
  status: 'processing' | 'completed' | 'overdue' | 'pending';
  statusLabel: string;
  workStatus?: string;
  variant: 'success' | 'warning' | 'info' | 'danger';
  assignee?: string;
  creator?: string;
  description?: string;
  createdDate?: string;
}

export interface DocumentAttachment {
  name: string;
  size: string;
  type?: 'pdf' | 'excel' | 'word' | 'docx' | 'xlsx' | string;
  format?: 'pdf' | 'docx' | 'xlsx';
  date?: string;
  url?: string;
}

export interface DocumentItem {
  code: string;
  title: string;
  date: string;
  id?: string | number;
  sender?: string;
  recipient?: string;
  arrivalNumber?: string | number;
  bookYear?: number | string;
  arrivalDate?: string;
  issuingPlace?: string;
  signer?: string;
  signerRole?: string;
  validityStatus?: 'valid' | 'expired' | 'partial';
  validityStatusLabel?: string;
  replacedBy?: string;
  note?: string;
  attachments?: DocumentAttachment[];
  creator?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ResourceTemplateItem {
  code: string;
  title: string;
  format: string;
}

export interface SigningRequestItem {
  id: number | string;
  code?: string;
  ma_trinh_ky?: string;
  title?: string;
  tieu_de?: string;
  submitter?: string;
  nguoi_trinh?: string;
  date?: string;
  ngay_gui?: string;
  status?: string;
  trang_thai?: string;
  trang_thai_luot?: string;
  statusLabel?: string;
  nhan_trang_thai?: string;
  trang_thai_display?: string;
  can_toi_ky?: boolean;
  variant?: 'success' | 'warning' | 'info' | 'danger';
}

export interface YearlyComparisonItem {
  year: number;
  incoming: number;
  outgoing: number;
}

export interface ModernDashboardViewProps {
  onNavigate?: (page: ActivePageId) => void;
  incomingCount?: number;
  outgoingCount?: number;
  tasksCount?: number;
  signingCount?: number;
  selectedYear?: number;
  availableYears?: number[];
  yearlyComparison?: YearlyComparisonItem[];
  onYearChange?: (year: number) => void;
  incomingDocuments?: DocumentItem[];
  outgoingDocuments?: DocumentItem[];
  tasks?: TaskItem[];
  resources?: ResourceTemplateItem[];
  signingRequests?: SigningRequestItem[];
  birthdays?: BirthdayEmployee[];
}

interface ApiDocumentSearchAttachment {
  ten_file?: string;
  duong_dan?: string;
}

interface ApiDocumentSearchItem {
  id: number | string;
  so_hieu?: string;
  trich_yeu?: string;
  ngay_den?: string;
  ngay_ban_hanh?: string;
  noi_ban_hanh?: string;
  nguoi_ky?: string;
  dinh_kem?: ApiDocumentSearchAttachment[];
}

export default function ModernDashboardView({
  onNavigate = () => {},
  incomingCount = 0,
  outgoingCount = 0,
  tasksCount = 0,
  signingCount = 0,
  selectedYear = new Date().getFullYear(),
  availableYears = [2024, 2025, 2026],
  yearlyComparison = [],
  onYearChange,
  incomingDocuments = [],
  outgoingDocuments = [],
  tasks = [],
  resources = [],
  signingRequests = [],
  birthdays,
}: ModernDashboardViewProps) {
  const { t, currentLang } = useTranslation();
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [taskFilter, setTaskFilter] = useState<'processing' | 'completed' | 'overdue' | 'pending'>('processing');
  const [selectedTask, setSelectedTask] = useState<TaskItem | null>(null);
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [previewType, setPreviewType] = useState<'incoming' | 'outgoing' | 'resource'>('incoming');
  const [previewList, setPreviewList] = useState<DocumentItem[]>([]);
  const [previewIndex, setPreviewIndex] = useState<number>(0);
  const [isScrolled, setIsScrolled] = useState<boolean>(false);
  const [portalTarget, setPortalTarget] = useState<HTMLElement | null>(null);
  const compactInputRef = useRef<HTMLInputElement>(null);
  const [isSearchingServer, setIsSearchingServer] = useState<boolean>(false);
  const [serverIncoming, setServerIncoming] = useState<DocumentItem[] | null>(null);
  const [serverOutgoing, setServerOutgoing] = useState<DocumentItem[] | null>(null);

  useEffect(() => {
    const trimmed = searchTerm.trim();
    const timer = setTimeout(async () => {
      if (!trimmed) {
        setServerIncoming(null);
        setServerOutgoing(null);
        setIsSearchingServer(false);
        return;
      }

      setIsSearchingServer(true);
      try {
        const [resDen, resDi] = await Promise.allSettled([
          apiClient<{ results: ApiDocumentSearchItem[] }>(`/api/documents/den/?q=${encodeURIComponent(trimmed)}`),
          apiClient<{ results: ApiDocumentSearchItem[] }>(`/api/documents/di/?q=${encodeURIComponent(trimmed)}`),
        ]);

        if (resDen.status === 'fulfilled' && resDen.value?.results) {
          const mappedDen: DocumentItem[] = resDen.value.results.map((d: ApiDocumentSearchItem) => ({
            id: d.id,
            code: d.so_hieu || '',
            title: d.trich_yeu || '',
            date: d.ngay_den ? new Date(d.ngay_den).toLocaleDateString('vi-VN') : '',
            sender: d.noi_ban_hanh,
            attachments: (d.dinh_kem || []).map((att: ApiDocumentSearchAttachment) => ({
              name: att.ten_file || '',
              url: att.duong_dan || '',
              size: '',
            })),
          }));
          setServerIncoming(mappedDen);
        }

        if (resDi.status === 'fulfilled' && resDi.value?.results) {
          const mappedDi: DocumentItem[] = resDi.value.results.map((d: ApiDocumentSearchItem) => ({
            id: d.id,
            code: d.so_hieu || '',
            title: d.trich_yeu || '',
            date: d.ngay_ban_hanh ? new Date(d.ngay_ban_hanh).toLocaleDateString('vi-VN') : '',
            sender: d.nguoi_ky,
            recipient: d.noi_ban_hanh,
            attachments: (d.dinh_kem || []).map((att: ApiDocumentSearchAttachment) => ({
              name: att.ten_file || '',
              url: att.duong_dan || '',
              size: '',
            })),
          }));
          setServerOutgoing(mappedDi);
        }
      } catch {
        // Fallback to client search
      } finally {
        setIsSearchingServer(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => {
    const updateTarget = () => {
      const target = document.getElementById('header-search-slot') || document.getElementById('top-subnav-slot');
      if (target) {
        setPortalTarget(target);
      }
    };
    updateTarget();
    const timer = setTimeout(updateTarget, 100);

    const scrollContainer = document.querySelector('.page-viewport');

    const handleScroll = () => {
      const scrollY = (scrollContainer ? scrollContainer.scrollTop : 0) || window.scrollY || document.documentElement.scrollTop || 0;
      setIsScrolled(scrollY > 60);
    };

    if (scrollContainer) {
      scrollContainer.addEventListener('scroll', handleScroll, { passive: true });
    }
    window.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      clearTimeout(timer);
      if (scrollContainer) {
        scrollContainer.removeEventListener('scroll', handleScroll);
      }
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  const handleOpenPreview = (doc: DocumentItem, type: 'incoming' | 'outgoing' | 'resource', list: DocumentItem[]) => {
    setPreviewDoc(doc);
    setPreviewType(type);
    setPreviewList(list);
    const idx = list.findIndex((item) => item.code === doc.code);
    setPreviewIndex(idx >= 0 ? idx : 0);
  };

  const handleNextPreview = () => {
    if (previewIndex < previewList.length - 1) {
      const nextIdx = previewIndex + 1;
      setPreviewIndex(nextIdx);
      setPreviewDoc(previewList[nextIdx]);
    }
  };

  const handlePrevPreview = () => {
    if (previewIndex > 0) {
      const prevIdx = previewIndex - 1;
      setPreviewIndex(prevIdx);
      setPreviewDoc(previewList[prevIdx]);
    }
  };

  const filteredIncoming = useMemo(() => {
    if (serverIncoming !== null) return serverIncoming;
    if (!searchTerm.trim()) return incomingDocuments;
    const term = searchTerm.toLowerCase();
    return incomingDocuments.filter(
      (doc) => doc.code.toLowerCase().includes(term) || doc.title.toLowerCase().includes(term)
    );
  }, [incomingDocuments, searchTerm, serverIncoming]);

  const filteredOutgoing = useMemo(() => {
    if (serverOutgoing !== null) return serverOutgoing;
    if (!searchTerm.trim()) return outgoingDocuments;
    const term = searchTerm.toLowerCase();
    return outgoingDocuments.filter(
      (doc) => doc.code.toLowerCase().includes(term) || doc.title.toLowerCase().includes(term)
    );
  }, [outgoingDocuments, searchTerm, serverOutgoing]);

  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => task.status === taskFilter);
  }, [tasks, taskFilter]);

  const filteredResources = useMemo(() => {
    if (!searchTerm.trim()) return resources;
    const term = searchTerm.toLowerCase();
    return resources.filter(
      (r) => r.code.toLowerCase().includes(term) || r.title.toLowerCase().includes(term)
    );
  }, [resources, searchTerm]);

  const filteredSigning = useMemo(() => {
    let list = signingRequests;
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      list = signingRequests.filter((s) => {
        const code = (s.ma_trinh_ky || s.code || '').toLowerCase();
        const title = (s.tieu_de || s.title || '').toLowerCase();
        const submitter = (s.nguoi_trinh || s.submitter || '').toLowerCase();
        return code.includes(term) || title.includes(term) || submitter.includes(term);
      });
    }
    // Sắp xếp ưu tiên: Phiếu "Ký ngay" (can_toi_ky === true) ĐƯA LÊN ĐẦU DANH SÁCH
    return [...list].sort((a, b) => {
      const aCanSign = a.can_toi_ky ? 1 : 0;
      const bCanSign = b.can_toi_ky ? 1 : 0;
      if (bCanSign !== aCanSign) {
        return bCanSign - aCanSign;
      }
      return 0;
    });
  }, [signingRequests, searchTerm]);

  return (
    <>
      {/* Thanh tìm kiếm thu nhỏ tự động dời lên khoảng trống trên Header khi lăn chuột xuống */}
      {portalTarget &&
        createPortal(
          <div
            className={`transition-all duration-300 ease-out flex items-center w-full max-w-xs sm:max-w-md ${
              isScrolled
                ? 'opacity-100 translate-x-0 scale-100 pointer-events-auto'
                : 'opacity-0 -translate-x-4 scale-95 pointer-events-none'
            }`}
          >
            <div className="relative w-full flex items-center">
              <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-muted text-xs pointer-events-none" />
              <input
                ref={compactInputRef}
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder={t('dashboardDetails.compactSearchPlaceholder')}
                className="w-full pl-8 pr-7 py-1.5 h-8 sm:h-9 rounded-xl border border-border-subtle bg-surface text-main text-xs sm:text-sm shadow-2xs focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all placeholder:text-muted"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchTerm('');
                    compactInputRef.current?.focus();
                  }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-main text-xs p-0.5 rounded-full hover:bg-surface-hover cursor-pointer transition-colors"
                  title="Xóa tìm kiếm nhanh"
                  aria-label="Xóa nội dung tìm kiếm nhanh"
                >
                  <i className="fa-solid fa-xmark text-xs" />
                </button>
              )}
            </div>
          </div>,
          portalTarget
        )}

      <div className="flex flex-col gap-6">
      {/* 1. Thanh tìm kiếm nhanh & Nút Đặt phòng họp đặt ngang hàng */}
      <div className="flex items-center gap-3 w-full">
        <div className="flex-1 relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={t('dashboardDetails.searchPlaceholder')}
            className="w-full pl-12 pr-10 py-3.5 rounded-xl border border-border-subtle bg-surface text-main text-base shadow-xs focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-muted"
          />
          <i className={`fa-solid ${isSearchingServer ? 'fa-spinner fa-spin text-primary' : 'fa-magnifying-glass text-muted'} absolute left-4 top-1/2 -translate-y-1/2 text-lg pointer-events-none transition-colors`} />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted hover:text-main text-sm p-1.5 rounded-full hover:bg-surface-hover cursor-pointer transition-colors"
              title="Xóa tìm kiếm"
              aria-label="Xóa nội dung tìm kiếm"
            >
              <i className="fa-solid fa-xmark text-base" />
            </button>
          )}
        </div>

        <button
          type="button"
          className="px-5 py-3.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-bold text-base flex items-center gap-2.5 shrink-0 border border-primary cursor-pointer shadow-xs transition-all hover:scale-[1.02]"
          onClick={() => onNavigate('meetings')}
          title="Chuyển tới phân hệ Đặt phòng họp"
        >
          <i className="fa-solid fa-calendar-plus text-white text-base" />
          <span className="whitespace-nowrap">{t('dashboardDetails.bookMeetingRoomBtn') || 'Đặt phòng họp'}</span>
        </button>
      </div>

      {/* Khối Thống kê theo năm & Đối chiếu nhiều năm (Bug 2) */}
      <div className="bg-surface border border-border-subtle rounded-2xl p-4 sm:p-5 shadow-xs flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-sm font-bold">
              <i className="fa-solid fa-chart-simple" />
            </div>
            <div>
              <h3 className="text-base font-bold text-main leading-tight">
                Thống Kê Số Lượng Văn Bản Đi & Đến Theo Năm ({availableYears.length > 0 ? `${availableYears[0]} - ${availableYears[availableYears.length - 1]}` : '2024 - 2026'})
              </h3>
              <span className="text-xs text-secondary">
                Dữ liệu đồng bộ trực tiếp từ CSDL PostgreSQL (Nhóm 1 & Nhóm 2)
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="dashboard-year-select" className="text-xs font-semibold text-secondary whitespace-nowrap">
              Chọn năm:
            </label>
            <select
              id="dashboard-year-select"
              value={selectedYear}
              onChange={(e) => onYearChange?.(Number(e.target.value))}
              className="px-3 py-1.5 rounded-xl border border-border-subtle bg-surface-elevated text-main text-sm font-bold focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary cursor-pointer transition-all shadow-2xs"
            >
              {availableYears.map((y) => (
                <option key={y} value={y}>
                  Năm {y}
                </option>
              ))}
            </select>
          </div>
        </div>

        {yearlyComparison.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 border-t border-border-subtle">
            {yearlyComparison.map((item) => (
              <div
                key={item.year}
                onClick={() => onYearChange?.(item.year)}
                className={`p-3 rounded-xl border transition-all cursor-pointer ${
                  item.year === selectedYear
                    ? 'bg-primary-subtle/40 border-primary/40 shadow-xs'
                    : 'bg-surface-elevated border-border-subtle hover:bg-surface-hover'
                }`}
              >
                <div className="flex items-center justify-between text-xs font-bold text-secondary mb-1.5">
                  <span className={item.year === selectedYear ? 'text-primary' : ''}>Năm {item.year}</span>
                  {item.year === selectedYear && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-primary text-white font-semibold">Đang chọn</span>
                  )}
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-primary font-medium">Đến: <b>{item.incoming}</b></span>
                  <span className="text-success font-medium">Đi: <b>{item.outgoing}</b></span>
                  <span className="text-main font-bold">Tổng: {item.incoming + item.outgoing}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 2. Modern KPI Deck (4 cards cân đối: Đến, Đi, Nhiệm vụ, Chờ Ký) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-1.5 sm:gap-3 md:gap-5">
        {/* Card 1: VB Đến */}
        <div
          onClick={() => onNavigate('documents_incoming')}
          className="bg-surface border border-border-subtle rounded-xl md:rounded-2xl p-2 sm:p-3 md:p-5 flex flex-col justify-between shadow-2xs md:shadow-sm cursor-pointer hover:border-primary-border transition-all"
        >
          <div>
            <div className="text-[10px] sm:text-xs md:text-sm uppercase tracking-tight sm:tracking-normal md:tracking-wider font-semibold text-muted leading-tight md:leading-normal truncate">
              <span className="md:hidden">{t('dashboardDetails.incomingCardShort') || 'VĂN BẢN ĐẾN'}</span>
              <span className="hidden md:inline">{t('dashboardDetails.incomingCard')} ({new Date().getFullYear()})</span>
            </div>
            <div className="flex items-center gap-1.5 sm:gap-2.5 mt-1 sm:mt-1.5 md:mt-2">
              <div className="w-6 h-6 sm:w-8 sm:h-8 md:w-12 md:h-12 rounded-md md:rounded-2xl bg-primary-subtle text-primary flex items-center justify-center text-xs sm:text-base md:text-2xl shrink-0 shadow-2xs">
                <i className="fa-solid fa-inbox" />
              </div>
              <div className="text-base sm:text-2xl md:text-4xl font-extrabold text-main leading-none">
                {incomingCount.toLocaleString()}
              </div>
            </div>
          </div>
          <div className="hidden md:block text-sm text-secondary md:mt-1 truncate">
            {incomingCount > 0 ? `+${incomingCount} ${t('dashboardDetails.newIncomingToday')}` : t('dashboardDetails.noIncomingToday')}
          </div>
        </div>

        {/* Card 2: VB Đi */}
        <div
          onClick={() => onNavigate('documents_outgoing')}
          className="bg-surface border border-border-subtle rounded-xl md:rounded-2xl p-2 sm:p-3 md:p-5 flex flex-col justify-between shadow-2xs md:shadow-sm cursor-pointer hover:border-success-border transition-all"
        >
          <div>
            <div className="text-[10px] sm:text-xs md:text-sm uppercase tracking-tight sm:tracking-normal md:tracking-wider font-semibold text-muted leading-tight md:leading-normal truncate">
              <span className="md:hidden">{t('dashboardDetails.outgoingCardShort') || 'VĂN BẢN ĐI'}</span>
              <span className="hidden md:inline">{t('dashboardDetails.outgoingCard')}</span>
            </div>
            <div className="flex items-center gap-1.5 sm:gap-2.5 mt-1 sm:mt-1.5 md:mt-2">
              <div className="w-6 h-6 sm:w-8 sm:h-8 md:w-12 md:h-12 rounded-md md:rounded-2xl bg-success-subtle text-success flex items-center justify-center text-xs sm:text-base md:text-2xl shrink-0 shadow-2xs">
                <i className="fa-solid fa-paper-plane" />
              </div>
              <div className="text-base sm:text-2xl md:text-4xl font-extrabold text-main leading-none">
                {outgoingCount.toLocaleString()}
              </div>
            </div>
          </div>
          <div className="hidden md:block text-sm text-secondary md:mt-1 truncate">
            {outgoingCount > 0 ? `+${outgoingCount} ${t('dashboardDetails.issuedToday')}` : t('dashboardDetails.noOutgoingToday')}
          </div>
        </div>

        {/* Card 3: Nhiệm vụ */}
        <div
          onClick={() => onNavigate('tasks')}
          className="bg-surface border border-border-subtle rounded-xl md:rounded-2xl p-2 sm:p-3 md:p-5 flex flex-col justify-between shadow-2xs md:shadow-sm cursor-pointer hover:border-purple-border transition-all"
        >
          <div>
            <div className="text-[10px] sm:text-xs md:text-sm uppercase tracking-tight sm:tracking-normal md:tracking-wider font-semibold text-muted leading-tight md:leading-normal truncate">
              <span className="md:hidden">{t('dashboardDetails.tasksCardShort') || 'NHIỆM VỤ'}</span>
              <span className="hidden md:inline">{t('dashboardDetails.tasksCard')}</span>
            </div>
            <div className="flex items-center gap-1.5 sm:gap-2.5 mt-1 sm:mt-1.5 md:mt-2">
              <div className="w-6 h-6 sm:w-8 sm:h-8 md:w-12 md:h-12 rounded-md md:rounded-2xl bg-purple-subtle text-purple flex items-center justify-center text-xs sm:text-base md:text-2xl shrink-0 shadow-2xs">
                <i className="fa-solid fa-list-check" />
              </div>
              <div className="text-base sm:text-2xl md:text-4xl font-extrabold text-main leading-none">
                {tasksCount.toLocaleString()}
              </div>
            </div>
          </div>
          <div className="hidden md:block text-sm text-secondary md:mt-1 truncate">
            {tasksCount > 0 ? `${tasksCount} ${t('dashboardDetails.tasksToProcess')}` : t('dashboardDetails.noTasksPending')}
          </div>
        </div>

        {/* Card 4: Hồ sơ chờ ký */}
        <div
          onClick={() => onNavigate('approvals')}
          className="bg-surface border border-border-subtle rounded-xl md:rounded-2xl p-2 sm:p-3 md:p-5 flex flex-col justify-between shadow-2xs md:shadow-sm cursor-pointer hover:border-warning-border transition-all"
        >
          <div>
            <div className="text-[10px] sm:text-xs md:text-sm uppercase tracking-tight sm:tracking-normal md:tracking-wider font-semibold text-muted leading-tight md:leading-normal truncate">
              <span className="md:hidden">{t('dashboardDetails.signingCardShort') || 'CHỜ KÝ'}</span>
              <span className="hidden md:inline">{t('dashboardDetails.signingCard')}</span>
            </div>
            <div className="flex items-center gap-1.5 sm:gap-2.5 mt-1 sm:mt-1.5 md:mt-2">
              <div className="w-6 h-6 sm:w-8 sm:h-8 md:w-12 md:h-12 rounded-md md:rounded-2xl bg-warning-subtle text-warning flex items-center justify-center text-xs sm:text-base md:text-2xl shrink-0 shadow-2xs">
                <i className="fa-solid fa-file-signature" />
              </div>
              <div className="text-base sm:text-2xl md:text-4xl font-extrabold text-main leading-none">
                {signingCount.toLocaleString()}
              </div>
            </div>
          </div>
          <div className="hidden md:block text-sm text-secondary md:mt-1 truncate">
            {signingCount > 0 ? `${signingCount} ${t('dashboardDetails.signingToProcess')}` : t('dashboardDetails.noSigningPending')}
          </div>
        </div>
      </div>

      {/* Dải Marquee Chúc Mừng Sinh Nhật CBNV */}
      <BirthdaysWidget birthdays={birthdays} />

      {/* 4. Hai Bảng Song Song: Văn Bản Đến & Văn Bản Đi (Cỡ chữ to rõ ràng) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Top Văn Bản Đến */}
        <div className="bg-surface border border-border-subtle rounded-2xl p-3 sm:p-4 md:p-5 shadow-sm flex flex-col">
          <div className="flex justify-between items-center mb-3">
            <div className="font-bold text-sm sm:text-base text-main flex items-center gap-2 sm:gap-2.5">
              <i className="fa-solid fa-inbox text-primary text-sm sm:text-base md:text-lg shrink-0" />
              <span>{t('dashboardDetails.recentIncomingTitle')}</span>
            </div>
          </div>

          <div className="flex-1 min-h-[160px] flex flex-col justify-start">
            {filteredIncoming.length === 0 ? (
              <div className="flex-1 p-8 text-center text-muted flex flex-col items-center justify-center">
                <i className="fa-solid fa-inbox text-3xl mb-2 opacity-30 text-primary" />
                <span className="text-sm font-medium">{t('dashboardDetails.noIncomingData')}</span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle text-muted text-left">
                      <th className="p-2.5 whitespace-nowrap min-w-[130px] sm:min-w-[140px]">{t('dashboardDetails.docNumber')}</th>
                      <th className="p-2.5">{t('dashboardDetails.docSummary')}</th>
                      <th className="p-2.5 w-28 whitespace-nowrap">{t('dashboardDetails.docDate')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredIncoming.map((row, idx) => (
                      <tr
                        key={idx}
                        onClick={() => handleOpenPreview(row, 'incoming', filteredIncoming)}
                        className="border-b border-border-subtle hover:bg-primary-subtle/30 transition-colors cursor-pointer group"
                        title={t('documentPreview.clickToPreview') || 'Bấm để xem chi tiết văn bản'}
                      >
                        <td className="p-2.5 font-semibold text-primary group-hover:underline whitespace-nowrap">
                          <div className="flex items-center justify-between gap-1.5 whitespace-nowrap">
                            <span className="whitespace-nowrap">{row.code}</span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenPreview(row, 'incoming', filteredIncoming);
                              }}
                              className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-primary-subtle text-primary transition-all text-xs cursor-pointer shrink-0"
                              title={t('documentPreview.clickToPreview') || 'Xem chi tiết văn bản'}
                            >
                              <i className="fa-solid fa-arrow-up-right-from-square" />
                            </button>
                          </div>
                        </td>
                        <td className="p-2.5 text-main group-hover:text-primary transition-colors">
                          <div className="line-clamp-2 leading-snug break-words" title={row.title}>
                            {row.title}
                          </div>
                        </td>
                        <td className="p-2.5 text-muted whitespace-nowrap">{row.date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="mt-auto pt-3 border-t border-border-subtle text-left">
            <button
              type="button"
              onClick={() => onNavigate('documents_incoming')}
              className="text-sm font-semibold text-primary hover:underline inline-flex items-center gap-1.5 cursor-pointer"
            >
              <span>{t('dashboardDetails.viewMoreIncoming')}</span>
              <i className="fa-solid fa-arrow-right text-xs" />
            </button>
          </div>
        </div>

        {/* Top Văn Bản Đi */}
        <div className="bg-surface border border-border-subtle rounded-2xl p-3 sm:p-4 md:p-5 shadow-sm flex flex-col">
          <div className="flex justify-between items-center mb-3">
            <div className="font-bold text-sm sm:text-base text-main flex items-center gap-2 sm:gap-2.5">
              <i className="fa-solid fa-paper-plane text-success text-sm sm:text-base md:text-lg shrink-0" />
              <span>{t('dashboardDetails.recentOutgoingTitle')}</span>
            </div>
          </div>

          <div className="flex-1 min-h-[160px] flex flex-col justify-start">
            {filteredOutgoing.length === 0 ? (
              <div className="flex-1 p-8 text-center text-muted flex flex-col items-center justify-center">
                <i className="fa-solid fa-paper-plane text-3xl mb-2 opacity-30 text-success" />
                <span className="text-sm font-medium">{t('dashboardDetails.noOutgoingData')}</span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle text-muted text-left">
                      <th className="p-2.5 whitespace-nowrap min-w-[130px] sm:min-w-[140px]">{t('dashboardDetails.docNumber')}</th>
                      <th className="p-2.5">{t('dashboardDetails.docSummary')}</th>
                      <th className="p-2.5 w-28 whitespace-nowrap">{t('dashboardDetails.docDate')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredOutgoing.map((row, idx) => (
                      <tr
                        key={idx}
                        onClick={() => handleOpenPreview(row, 'outgoing', filteredOutgoing)}
                        className="border-b border-border-subtle hover:bg-success-subtle/30 transition-colors cursor-pointer group"
                        title={t('documentPreview.clickToPreview') || 'Bấm để xem chi tiết văn bản'}
                      >
                        <td className="p-2.5 font-semibold text-success group-hover:underline whitespace-nowrap">
                          <div className="flex items-center justify-between gap-1.5 whitespace-nowrap">
                            <span className="whitespace-nowrap">{row.code}</span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenPreview(row, 'outgoing', filteredOutgoing);
                              }}
                              className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-success-subtle text-success transition-all text-xs cursor-pointer shrink-0"
                              title={t('documentPreview.clickToPreview') || 'Xem chi tiết văn bản'}
                            >
                              <i className="fa-solid fa-arrow-up-right-from-square" />
                            </button>
                          </div>
                        </td>
                        <td className="p-2.5 text-main group-hover:text-success transition-colors">
                          <div className="line-clamp-2 leading-snug break-words" title={row.title}>
                            {row.title}
                          </div>
                        </td>
                        <td className="p-2.5 text-muted whitespace-nowrap">{row.date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="mt-auto pt-3 border-t border-border-subtle text-left">
            <button
              type="button"
              onClick={() => onNavigate('documents_outgoing')}
              className="text-sm font-semibold text-success hover:underline inline-flex items-center gap-1.5 cursor-pointer"
            >
              <span>{t('dashboardDetails.viewMoreOutgoing')}</span>
              <i className="fa-solid fa-arrow-right text-xs" />
            </button>
          </div>
        </div>
      </div>

      {/* 5. Hai Bảng Song Song: Nhiệm Vụ Được Giao & Tài Liệu Biểu Mẫu (Hàng dưới chia đôi - Chữ to rõ ràng) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Cột Trái: Danh Sách Nhiệm Vụ Được Giao (Top 5) */}
        <div className="bg-surface border border-border-subtle rounded-2xl p-3 sm:p-4 md:p-5 shadow-sm flex flex-col">
          <div className="flex justify-between items-center mb-3">
            <div className="font-bold text-sm sm:text-base text-main flex items-center gap-2 sm:gap-2.5">
              <i className="fa-solid fa-list-check text-purple text-sm sm:text-base md:text-lg shrink-0" />
              <span>{t('dashboardDetails.recentTasksTitle')}</span>
            </div>
          </div>

          {/* Filter Pills: Đang xử lý / Hoàn thành / Quá hạn / Chờ duyệt - Đảm bảo chỉ hiện trên 1 hàng */}
          <div className="grid grid-cols-4 gap-1 sm:gap-2 mb-3">
            {(
              [
                { id: 'processing', label: t('dashboardDetails.filterProcessing') },
                { id: 'completed', label: t('dashboardDetails.filterCompleted') },
                { id: 'overdue', label: t('dashboardDetails.filterOverdue') },
                { id: 'pending', label: t('dashboardDetails.filterPending') },
              ] as const
            ).map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setTaskFilter(item.id)}
                className={`w-full py-1 sm:py-1.5 px-0.5 sm:px-3 rounded-full text-[11px] sm:text-sm font-semibold border border-border-subtle transition-colors cursor-pointer text-center truncate ${
                  taskFilter === item.id
                    ? 'bg-purple text-white border-purple shadow-xs'
                    : 'bg-surface-elevated text-secondary hover:text-main'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Task Rows or Clean Empty State */}
          <div className="flex-1 min-h-[160px] flex flex-col justify-start">
            {filteredTasks.length === 0 ? (
              <div className="flex-1 p-8 text-center text-muted flex flex-col items-center justify-center">
                <i className="fa-solid fa-list-check text-3xl mb-2 opacity-30 text-purple" />
                <span className="text-sm font-medium">{t('dashboardDetails.noTasksData')}</span>
              </div>
            ) : (
              <div className="divide-y divide-border-subtle">
                {filteredTasks.slice(0, 5).map((task) => (
                  <div
                    key={task.id}
                    onClick={() => setSelectedTask(task)}
                    className="py-3 flex items-center justify-between gap-3 hover:bg-surface-hover transition-colors cursor-pointer text-sm group"
                    title="Bấm để xem chi tiết nhiệm vụ"
                  >
                    <div className="flex-1 min-w-0 pr-2">
                      <span className="font-semibold text-main group-hover:text-primary transition-colors truncate block">
                        {task.title}
                      </span>
                    </div>
                    <span className="text-muted text-xs shrink-0 whitespace-nowrap">{task.due}</span>
                    <div className="shrink-0 text-right">
                      <Badge variant={task.variant} size="sm">
                        {t(`dashboardDetails.taskStatuses.${task.workStatus ?? task.status}`)}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="mt-auto pt-3 border-t border-border-subtle text-left">
            <button
              type="button"
              onClick={() => onNavigate('tasks')}
              className="text-sm font-semibold text-purple hover:underline inline-flex items-center gap-1.5 cursor-pointer"
            >
              <span>{t('dashboardDetails.viewMoreTasks')}</span>
              <i className="fa-solid fa-arrow-right text-xs" />
            </button>
          </div>
        </div>

        {/* Cột Phải: Danh Sách Tài Liệu & Biểu Mẫu Mới Nhất (Top 5) - Nhóm 4 */}
        <div className="bg-surface border border-border-subtle rounded-2xl p-3 sm:p-4 md:p-5 shadow-sm flex flex-col">
          <div className="flex justify-between items-center mb-3">
            <div className="font-bold text-sm sm:text-base text-main flex items-center gap-2 sm:gap-2.5">
              <i className="fa-solid fa-file-lines text-primary text-sm sm:text-base md:text-lg shrink-0" />
              <span>{t('dashboardDetails.recentResourcesTitle')}</span>
            </div>
          </div>

          <div className="flex-1 min-h-[160px] flex flex-col justify-start">
            {filteredResources.length === 0 ? (
              <div className="flex-1 p-8 text-center text-muted flex flex-col items-center justify-center">
                <i className="fa-solid fa-file-lines text-3xl mb-2 opacity-30 text-primary" />
                <span className="text-sm font-medium">{t('dashboardDetails.noResourcesData')}</span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-border-subtle text-muted text-left">
                      <th className="p-2.5 whitespace-nowrap min-w-[120px]">{t('dashboardDetails.resourceCode')}</th>
                      <th className="p-2.5">{t('dashboardDetails.resourceName')}</th>
                      <th className="p-2.5 w-24 text-center whitespace-nowrap">{t('dashboardDetails.resourceFormat')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredResources.slice(0, 5).map((row, idx) => {
                      const ext = (row.format || 'docx').toLowerCase();
                      const sanitizedCode = row.code.replace(/[/\\?%*:|"<>]/g, '_');
                      const resourceAsDoc: DocumentItem = {
                        code: row.code,
                        title: row.title,
                        date: '01/10/2026',
                        attachments: [
                          {
                            name: `${sanitizedCode}.${ext}`,
                            size: ext === 'docx' ? '145 KB' : ext === 'xlsx' ? '180 KB' : '2.1 MB',
                            date: '01/10/2026',
                            type: ext === 'docx' ? 'word' : ext === 'xlsx' ? 'excel' : 'pdf',
                            format: (ext === 'xlsx' || ext === 'docx' || ext === 'pdf') ? ext : undefined,
                          },
                        ],
                      };
                      const resourceDocsList: DocumentItem[] = filteredResources.slice(0, 5).map((r) => {
                        const rExt = (r.format || 'docx').toLowerCase();
                        const rCode = r.code.replace(/[/\\?%*:|"<>]/g, '_');
                        return {
                          code: r.code,
                          title: r.title,
                          date: '01/10/2026',
                          attachments: [
                            {
                              name: `${rCode}.${rExt}`,
                              size: rExt === 'docx' ? '145 KB' : rExt === 'xlsx' ? '180 KB' : '2.1 MB',
                              date: '01/10/2026',
                              type: rExt === 'docx' ? 'word' : rExt === 'xlsx' ? 'excel' : 'pdf',
                              format: (rExt === 'xlsx' || rExt === 'docx' || rExt === 'pdf') ? rExt : undefined,
                            },
                          ],
                        };
                      });
                      return (
                        <tr
                          key={idx}
                          onClick={() => handleOpenPreview(resourceAsDoc, 'resource', resourceDocsList)}
                          className="border-b border-border-subtle hover:bg-purple-subtle/30 transition-colors cursor-pointer group"
                          title={t('documentPreview.clickToPreview') || 'Bấm để xem chi tiết biểu mẫu'}
                        >
                          <td className="p-2.5 font-semibold text-primary group-hover:underline whitespace-nowrap">
                            <div className="flex items-center gap-1.5 whitespace-nowrap">
                              <i className="fa-solid fa-file-lines text-purple text-xs opacity-70 group-hover:opacity-100 shrink-0" />
                              <span className="whitespace-nowrap">{row.code}</span>
                            </div>
                          </td>
                          <td className="p-2.5 text-main group-hover:text-primary transition-colors">
                            <div className="line-clamp-2 leading-snug break-words" title={row.title}>
                              {row.title}
                            </div>
                          </td>
                          <td className="p-2.5 text-center whitespace-nowrap">
                            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-primary-subtle text-primary uppercase">
                              {row.format}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="mt-auto pt-3 border-t border-border-subtle text-left">
            <button
              type="button"
              onClick={() => onNavigate('resources')}
              className="text-sm font-semibold text-primary hover:underline inline-flex items-center gap-1.5 cursor-pointer"
            >
              <span>{t('dashboardDetails.viewMoreResources')}</span>
              <i className="fa-solid fa-arrow-right text-xs" />
            </button>
          </div>
        </div>
      </div>

      {/* Danh sách phiếu trình ký gần nhất */}
      <div className="bg-surface border border-border-subtle rounded-2xl p-3 sm:p-4 md:p-5 shadow-sm flex flex-col">
        <div className="flex justify-between items-center mb-3">
          <div className="font-bold text-sm sm:text-base text-main flex items-center gap-2 sm:gap-2.5">
            <i className="fa-solid fa-file-signature text-warning text-sm sm:text-base md:text-lg shrink-0" />
            <span>{t('dashboardDetails.recentSigningTitle')}</span>
          </div>
        </div>

        <div className="flex-1 min-h-[160px] flex flex-col justify-start">
          {filteredSigning.length === 0 ? (
            <div className="flex-1 p-8 text-center text-muted flex flex-col items-center justify-center">
              <i className="fa-solid fa-file-signature text-3xl mb-2 opacity-30 text-warning" />
              <span className="text-sm font-medium">{t('dashboardDetails.noSigningData') || 'Không có phiếu trình ký nào cần xử lý'}</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b border-border-subtle text-muted text-left">
                    <th className="p-2.5 whitespace-nowrap min-w-[120px]">{t('dashboardDetails.signingCode')}</th>
                    <th className="p-2.5 min-w-[280px]">{t('dashboardDetails.signingTitle')}</th>
                    <th className="p-2.5 whitespace-nowrap min-w-[140px]">{t('dashboardDetails.signingSubmitter')}</th>
                    <th className="p-2.5 w-28 whitespace-nowrap">{t('dashboardDetails.signingDate')}</th>
                    <th className="p-2.5 w-28 text-center whitespace-nowrap">{t('dashboardDetails.signingStatus')}</th>
                    <th className="p-2.5 w-28 text-center whitespace-nowrap">{t('dashboardDetails.signingAction') || 'Thao tác'}</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSigning.slice(0, 5).map((row) => {
                    const code = row.ma_trinh_ky || row.code || `TK-${row.id}`;
                    const title = row.tieu_de || row.title || 'Hồ sơ trình ký';
                    const submitter = formatUserName(row.nguoi_trinh || row.submitter || 'Cán bộ', currentLang);
                    const date = row.ngay_gui || row.date || '';
                    const rawStatus = row.trang_thai || row.status || 'CHO_KY';
                    const displayStatus = (rawStatus === 'CHO_KY' || rawStatus === 'pending') && row.trang_thai_luot === 'YEU_CAU_SUA'
                      ? 'YEU_CAU_SUA'
                      : rawStatus;

                    const canSign = !!row.can_toi_ky;

                    const getSigningStatusInfo = (st: string) => {
                      if (canSign) {
                        return {
                          variant: 'primary' as const,
                          label: t('dashboardDetails.signingStatuses.KY_NGAY') || 'Ký ngay',
                        };
                      }
                      switch (st) {
                        case 'CHO_KY':
                        case 'pending':
                          return {
                            variant: 'warning' as const,
                            label: t('dashboardDetails.signingStatuses.CHO_KY') || 'Đang chờ ký',
                          };
                        case 'YEU_CAU_SUA':
                          return {
                            variant: 'info' as const,
                            label: t('dashboardDetails.signingStatuses.YEU_CAU_SUA') || 'Chờ người trình sửa',
                          };
                        case 'DANG_XU_LY':
                        case 'processing':
                          return {
                            variant: 'info' as const,
                            label: t('dashboardDetails.signingStatuses.DANG_XU_LY') || 'Đang xử lý',
                          };
                        case 'DA_KY':
                        case 'signed':
                          return {
                            variant: 'success' as const,
                            label: t('dashboardDetails.signingStatuses.DA_KY') || 'Đã ký',
                          };
                        case 'HOAN_THANH':
                        case 'completed':
                          return {
                            variant: 'success' as const,
                            label: t('dashboardDetails.signingStatuses.HOAN_THANH') || 'Hoàn tất duyệt nội bộ',
                          };
                        case 'TU_CHOI':
                        case 'rejected':
                          return {
                            variant: 'danger' as const,
                            label: t('dashboardDetails.signingStatuses.TU_CHOI') || 'Đã từ chối',
                          };
                        case 'HUY':
                        case 'cancelled':
                          return {
                            variant: 'danger' as const,
                            label: t('dashboardDetails.signingStatuses.HUY') || 'Đã hủy',
                          };
                        case 'NHAP':
                        case 'draft':
                          return {
                            variant: 'secondary' as const,
                            label: t('dashboardDetails.signingStatuses.NHAP') || 'Nháp',
                          };
                        default:
                          return {
                            variant: 'secondary' as const,
                            label: row.nhan_trang_thai || row.trang_thai_display || row.statusLabel || st,
                          };
                      }
                    };

                    const statusInfo = getSigningStatusInfo(displayStatus);
                    const statusVariant = canSign ? 'primary' : (row.variant || statusInfo.variant);
                    const statusLabel = statusInfo.label || row.nhan_trang_thai || row.trang_thai_display || row.statusLabel || rawStatus;

                    return (
                      <tr
                        key={row.id}
                        onClick={() => navigate(`/approvals/${row.id}`)}
                        className="border-b border-border-subtle hover:bg-warning-subtle/20 transition-colors cursor-pointer group"
                        title={title}
                      >
                        <td className="p-2.5 font-semibold text-primary group-hover:underline whitespace-nowrap">
                          <div className="flex items-center gap-1.5 whitespace-nowrap font-mono text-xs">
                            <i className="fa-solid fa-file-signature text-warning text-xs opacity-80 shrink-0" />
                            <span>{code}</span>
                          </div>
                        </td>
                        <td className="p-2.5 text-main group-hover:text-primary transition-colors">
                          <div className="line-clamp-2 leading-snug break-words font-medium" title={title}>
                            {title}
                          </div>
                        </td>
                        <td className="p-2.5 text-secondary whitespace-nowrap">
                          <div className="flex items-center gap-1.5 text-xs">
                            <i className="fa-regular fa-user text-muted shrink-0" />
                            <span>{submitter}</span>
                          </div>
                        </td>
                        <td className="p-2.5 text-muted whitespace-nowrap text-xs">{date}</td>
                        <td className="p-2.5 text-center whitespace-nowrap">
                          <Badge variant={statusVariant} size="sm">
                            {statusLabel}
                          </Badge>
                        </td>
                        <td className="p-2.5 text-center whitespace-nowrap">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/approvals/${row.id}`);
                            }}
                            className={`px-2.5 py-1 rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition-all shadow-2xs cursor-pointer ${
                              canSign
                                ? 'bg-primary hover:bg-primary-hover text-white'
                                : 'bg-surface-elevated hover:bg-surface-hover text-secondary border border-border-subtle'
                            }`}
                            title={canSign ? (t('dashboardDetails.signNowBtn') || 'Ký ngay') : (t('dashboardDetails.viewDetailBtn') || 'Xem chi tiết')}
                          >
                            <i className={`fa-solid ${canSign ? 'fa-pen-nib text-[10px]' : 'fa-eye text-[10px]'}`} />
                            <span>{canSign ? (t('dashboardDetails.signNowBtn') || 'Ký ngay') : (t('dashboardDetails.viewDetailBtn') || 'Xem chi tiết')}</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-auto pt-3 border-t border-border-subtle text-left">
          <button
            type="button"
            onClick={() => onNavigate('approvals')}
            className="text-sm font-semibold text-warning hover:underline inline-flex items-center gap-1.5 cursor-pointer"
          >
            <span>{t('dashboardDetails.viewMoreSigning')}</span>
            <i className="fa-solid fa-arrow-right text-xs" />
          </button>
        </div>
      </div>

      {/* Modal Xem Trước Văn Bản Số Hóa (PDF Reader) */}
      <DocumentPreviewModal
        key={previewDoc?.code || 'empty'}
        isOpen={!!previewDoc}
        onClose={() => setPreviewDoc(null)}
        document={previewDoc}
        docType={previewType}
        onNext={handleNextPreview}
        onPrev={handlePrevPreview}
        hasNext={previewIndex < previewList.length - 1}
        hasPrev={previewIndex > 0}
        currentIndex={previewIndex}
        totalDocs={previewList.length}
      />

      {/* Modal Xem Chi Tiết Nhiệm Vụ Được Giao (Nhóm 6) */}
      <TaskDetailModal
        isOpen={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        task={selectedTask}
        onNavigateTasks={() => onNavigate('tasks')}
      />
    </div>
    </>
  );
}



