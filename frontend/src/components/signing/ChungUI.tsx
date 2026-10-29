/**
 * Thành phần giao diện dùng chung của phân hệ Trình ký: badge trạng thái, hộp thoại, thông báo, trạng thái tải.
 * CSS theo Design Tokens (class Tailwind ngữ nghĩa), không mã màu cứng.
 */
import React, { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router-dom';
import { Badge, Button } from '@components/common';
import type { BadgeProps } from '@components/common/Badge';
import { useSigningT } from '@lib/signing/i18n';

const MAU_TRANG_THAI: Record<string, BadgeProps['variant']> = {
  NHAP: 'secondary', CHO_KY: 'warning', HOAN_THANH: 'success', TU_CHOI: 'danger', HUY: 'secondary',
  YEU_CAU_SUA: 'purple', CHUA_MO: 'secondary', DANG_KY: 'primary', TAM_DUNG: 'purple', DA_KY: 'success',
  HOAT_DONG: 'success', NGUNG: 'secondary', CHO_KICH_HOAT: 'info', DA_XOAY_VONG: 'secondary', THU_HOI: 'danger',
  HET_HAN: 'secondary', KHONG_CAN_KY: 'secondary',
};

/** `nhom = 'trangThaiCap'` cho trạng thái cấp ký (HOAN_THANH của cấp là "Đã xong", khác hồ sơ hoàn tất).
 * `size = 'md'` cho cột trạng thái của bảng và tiêu đề hồ sơ (cỡ sm khó đọc cạnh chữ 14px). */
export function TrangThaiBadge({ trangThai, nhom = 'trangThai', size = 'sm' }: {
  trangThai: string; nhom?: 'trangThai' | 'trangThaiCap'; size?: 'sm' | 'md' }) {
  const { t } = useSigningT();
  return (
    <Badge variant={MAU_TRANG_THAI[trangThai] || 'secondary'} size={size} withDot>
      {t(`${nhom}.${trangThai}`)}
    </Badge>
  );
}

/**
 * Trạng thái hồ sơ trên danh sách và chi tiết: chỉ hiển thị duy nhất một badge trạng thái.
 * Thứ tự ưu tiên:
 * 1. Quá hạn tổng thể hồ sơ -> "Quá hạn"
 * 2. Đang chờ ký mà lượt hiện hành bị trả lại để sửa -> "Đang trả lại để sửa"
 * 3. Trạng thái cơ bản của hồ sơ (Đang chờ ký, Hoàn tất, Không đồng ý, Đã hủy, Nháp).
 */
export function TrangThaiHoSo({ hoSo, size = 'md' }: {
  hoSo: {
    trang_thai: string;
    trang_thai_luot?: string | null;
    qua_han?: boolean;
    qua_han_cap?: boolean;
    han_xu_ly_cap?: string | null;
  };
  size?: 'sm' | 'md';
}) {
  const { t } = useSigningT();
  const tra_lai = hoSo.trang_thai === 'CHO_KY' && hoSo.trang_thai_luot === 'YEU_CAU_SUA';
  const qua_han_tong = Boolean(hoSo.qua_han && !hoSo.qua_han_cap);
  if (qua_han_tong) {
    return (
      <Badge variant="danger" size={size} withDot>
        <i className="fa-regular fa-clock mr-1" aria-hidden="true" />
        {t('danhSach.quaHan')}
      </Badge>
    );
  }

  if (tra_lai) {
    return <TrangThaiBadge trangThai="YEU_CAU_SUA" size={size} />;
  }

  return <TrangThaiBadge trangThai={hoSo.trang_thai} size={size} />;
}


export function ThongBao({ loai = 'loi', children }: { loai?: 'loi' | 'thanh_cong' | 'thong_tin' | 'canh_bao';
  children: React.ReactNode }) {
  const kieu = {
    loi: 'bg-danger-subtle border-danger-border text-danger',
    thanh_cong: 'bg-success-subtle border-success-border text-success',
    thong_tin: 'bg-info-subtle border-info-border text-info',
    canh_bao: 'bg-warning-subtle border-warning-border text-warning-text',
  }[loai];
  const icon = { loi: 'fa-circle-exclamation', thanh_cong: 'fa-circle-check', thong_tin: 'fa-circle-info',
    canh_bao: 'fa-triangle-exclamation' }[loai];
  return (
    <div role={loai === 'loi' ? 'alert' : 'status'} className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${kieu}`}>
      <i className={`fa-solid ${icon} mt-0.5`} aria-hidden="true" />
      <div className="min-w-0 break-words">{children}</div>
    </div>
  );
}

export function DangTai() {
  const { t } = useSigningT();
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-secondary text-sm" role="status">
      <i className="fa-solid fa-spinner fa-spin" aria-hidden="true" /> {t('chung.dangTai')}
    </div>
  );
}

export function Rong({ icon = 'fa-inbox', children }: { icon?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-muted text-sm text-center">
      <i className={`fa-solid ${icon} text-2xl`} aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}

export function LoiTai({ thongBao, onThuLai }: { thongBao: string; onThuLai?: () => void }) {
  const { t } = useSigningT();
  return (
    <div className="flex flex-col items-start gap-3 py-6">
      <ThongBao>{thongBao}</ThongBao>
      {onThuLai && <Button variant="secondary" size="sm" icon="fa-rotate-right" onClick={onThuLai}>{t('chung.thuLai')}</Button>}
    </div>
  );
}

const PHAN_TU_FOCUS = 'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]):not([type="hidden"]),'
  + 'select:not([disabled]),[tabindex]:not([tabindex="-1"])';
/** Hộp thoại đang mở theo thứ tự mở: Esc chỉ đóng hộp trên cùng. */
const dangMo: HTMLElement[] = [];

/**
 * Khung modal dùng chung của phân hệ (hộp thoại thao tác, xem tệp): render vào body, giữ tiêu điểm bàn phím trong
 * khung (Tab quay vòng), đưa tiêu điểm vào ô nhập đầu tiên khi mở và trả về nút đã mở khi đóng, Esc và bấm nền để
 * đóng. `khoaDong` chặn đóng khi đang gửi yêu cầu để không mất kết quả thao tác.
 */
export function KhungModal({ nhanId, onDong, khoaDong = false, lopNen = 'p-4', lopKhung = '', children }: {
  nhanId: string; onDong: () => void; khoaDong?: boolean; lopNen?: string; lopKhung?: string; children: React.ReactNode;
}) {
  const khung = useRef<HTMLDivElement>(null);
  const nhanNen = useRef(false);  // lần nhấn chuột bắt đầu ở nền (không phải kéo chọn chữ từ trong hộp thoại ra ngoài)
  const dongRef = useRef({ onDong, khoaDong });
  useEffect(() => {
    dongRef.current = { onDong, khoaDong };
  });

  useEffect(() => {
    const el = khung.current;
    if (!el) return undefined;
    const truoc = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dangMo.push(el);
    const dsFocus = () => Array.from(el.querySelectorAll<HTMLElement>(PHAN_TU_FOCUS));
    (el.querySelector<HTMLElement>('input:not([type="file"]):not([disabled]),textarea:not([disabled]),select:not([disabled])') ?? el).focus();

    const phim = (e: KeyboardEvent) => {
      if (dangMo[dangMo.length - 1] !== el) return;
      if (e.key === 'Escape') {
        if (!dongRef.current.khoaDong) dongRef.current.onDong();
        return;
      }
      if (e.key !== 'Tab') return;
      const ds = dsFocus();
      if (ds.length === 0) {
        e.preventDefault();
        el.focus();
        return;
      }
      const dau = ds[0];
      const cuoi = ds[ds.length - 1];
      const hienTai = document.activeElement;
      if (!el.contains(hienTai) || hienTai === el) {
        e.preventDefault();
        (e.shiftKey ? cuoi : dau).focus();
      } else if (e.shiftKey && hienTai === dau) {
        e.preventDefault();
        cuoi.focus();
      } else if (!e.shiftKey && hienTai === cuoi) {
        e.preventDefault();
        dau.focus();
      }
    };
    document.addEventListener('keydown', phim);
    return () => {
      document.removeEventListener('keydown', phim);
      dangMo.splice(dangMo.indexOf(el), 1);
      if (truoc?.isConnected) truoc.focus();
    };
  }, []);

  return createPortal(
    <div className={`fixed inset-0 z-[9999] flex items-center justify-center bg-backdrop animate-fade-in ${lopNen}`}
      onMouseDown={(e) => {
        nhanNen.current = e.target === e.currentTarget;
      }}
      onClick={(e) => {
        if (nhanNen.current && e.target === e.currentTarget && !dongRef.current.khoaDong) dongRef.current.onDong();
      }}>
      <div ref={khung} role="dialog" aria-modal="true" aria-labelledby={nhanId} tabIndex={-1}
        className={`signing-zoom shadow-xl animate-slide-in-bottom outline-none ${lopKhung}`}
        style={{ width: '84vw', maxWidth: 'none', maxHeight: '84vh', overflowY: 'auto' }}>
        {children}
      </div>
    </div>,
    document.body,
  );
}

export function HopThoai({ moTieuDe, mo, onDong, children, chanDuoi, dangXuLy = false }: {
  moTieuDe: string; mo: boolean; onDong: () => void; children: React.ReactNode; chanDuoi?: React.ReactNode;
  /** Đang gửi yêu cầu: chặn đóng bằng Esc, bấm nền và nút đóng. */
  dangXuLy?: boolean;
}) {
  const id = useId();
  const { t } = useSigningT();
  if (!mo) return null;
  return (
    <KhungModal nhanId={id} onDong={onDong} khoaDong={dangXuLy}
      lopKhung="w-full max-w-2xl rounded-2xl border border-border-subtle bg-surface-elevated">
      <div className="flex items-center justify-between border-b border-border-subtle px-6 py-4">
        <h2 id={id} className="text-xl font-bold text-main">{moTieuDe}</h2>
        <button type="button" onClick={onDong} disabled={dangXuLy}
          className="rounded-full p-1.5 text-secondary hover:text-main hover:bg-surface-hover transition-colors disabled:opacity-50"
          aria-label={t('chung.dong')}>
          <i className="fa-solid fa-xmark" aria-hidden="true" />
        </button>
      </div>
      <div className="px-6 py-5 space-y-4">{children}</div>
      {chanDuoi && <div className="flex justify-end gap-2.5 border-t border-border-subtle px-6 py-4">{chanDuoi}</div>}
    </KhungModal>
  );
}

/** Nhãn + ô nhập; `loi` hiện dưới ô (đọc to bằng role=alert), thay cho ghi chú. */
export function TruongNhap({ nhan, children, ghiChu, loi, batBuoc = false, className = '' }: {
  nhan: string; children: React.ReactNode; ghiChu?: string; loi?: string; batBuoc?: boolean; className?: string }) {
  const { t } = useSigningT();
  return (
    <label className={`block space-y-1.5 ${className}`}>
      <span className="flex items-center gap-1.5 text-sm font-medium text-main">
        {nhan}
        {batBuoc && <span className="text-danger" aria-label={t('chung.batBuoc')}>*</span>}
      </span>
      {children}
      {loi
        ? <span role="alert" className="flex items-start gap-1.5 text-xs font-semibold text-danger">
          <i className="fa-solid fa-circle-exclamation mt-0.5" aria-hidden="true" />{loi}
        </span>
        : ghiChu && <span className="block text-xs text-muted">{ghiChu}</span>}
    </label>
  );
}

/** Trang hoặc hồ sơ không tồn tại: thông báo rõ kèm đường về danh sách (không có "Thử lại" vì thử lại không đổi kết quả). */
export function KhongTimThay({ thongBao }: { thongBao: string }) {
  const { t } = useSigningT();
  return (
    <div className="flex flex-col items-start gap-3 py-6">
      <ThongBao>{thongBao}</ThongBao>
      <Link to="/approvals" className="text-sm font-semibold text-primary hover:underline">
        <i className="fa-solid fa-arrow-left mr-1.5" aria-hidden="true" />{t('chung.veDanhSach')}
      </Link>
    </div>
  );
}

/** Ô chọn tệp có nhãn theo ngôn ngữ giao diện (ô file gốc hiện "Choose File" theo trình duyệt).
 * Đặt trong `<label>` (TruongNhap) hoặc bọc `<label>` riêng để bấm cả khung mở hộp chọn tệp. */
export function OChonTep({ accept, onChon, nhan, disabled = false }: {
  accept: string; onChon: (tep: File | undefined) => void; nhan?: string; disabled?: boolean;
}) {
  const { t } = useSigningT();
  const [ten, setTen] = useState('');
  return (
    <span className={`flex w-full items-center gap-3 rounded-xl border border-border-subtle bg-surface px-2 py-1.5 text-sm focus-within:border-focus focus-within:ring-2 focus-within:ring-primary-subtle ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}>
      <input type="file" accept={accept} aria-label={nhan} className="sr-only" disabled={disabled}
        onChange={(e) => { const tep = e.target.files?.[0]; setTen(tep?.name ?? ''); onChon(tep); }} />
      <span className="shrink-0 rounded-lg border border-border-subtle bg-surface-subtle px-2.5 py-1 font-medium text-main">
        {t('chung.chonTep')}
      </span>
      <span className={`min-w-0 truncate ${ten ? 'text-main' : 'text-muted'}`}>{ten || t('chung.chuaChonTep')}</span>
    </span>
  );
}
