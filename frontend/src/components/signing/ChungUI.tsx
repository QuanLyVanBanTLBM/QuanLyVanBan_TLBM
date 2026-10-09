/**
 * Thành phần giao diện dùng chung của phân hệ Trình ký: badge trạng thái, hộp thoại, thông báo, trạng thái tải.
 * CSS theo Design Tokens (class Tailwind ngữ nghĩa), không mã màu cứng.
 */
import React, { useEffect, useId } from 'react';
import { Badge, Button } from '@components/common';
import type { BadgeProps } from '@components/common/Badge';
import { useSigningT } from '@lib/signing/i18n';

const MAU_TRANG_THAI: Record<string, BadgeProps['variant']> = {
  NHAP: 'secondary', CHO_KY: 'warning', HOAN_THANH: 'success', TU_CHOI: 'danger', HUY: 'secondary',
  YEU_CAU_SUA: 'purple', CHUA_MO: 'secondary', DANG_KY: 'primary', TAM_DUNG: 'purple', DA_KY: 'success',
  HOAT_DONG: 'success', NGUNG: 'secondary', CHO_KICH_HOAT: 'info', DA_XOAY_VONG: 'secondary', THU_HOI: 'danger',
  HET_HAN: 'secondary',
};

/** `nhom = 'trangThaiCap'` cho trạng thái cấp ký (HOAN_THANH của cấp là "Đã xong", khác hồ sơ hoàn tất). */
export function TrangThaiBadge({ trangThai, nhom = 'trangThai' }: { trangThai: string; nhom?: 'trangThai' | 'trangThaiCap' }) {
  const { t } = useSigningT();
  return (
    <Badge variant={MAU_TRANG_THAI[trangThai] || 'secondary'} size="sm" withDot>
      {t(`${nhom}.${trangThai}`)}
    </Badge>
  );
}

export function MucDoBadge({ mucDo }: { mucDo: string }) {
  const { t } = useSigningT();
  const mau: BadgeProps['variant'] = mucDo === 'HOA_TOC' ? 'danger' : mucDo === 'KHAN' ? 'warning' : 'secondary';
  return <Badge variant={mau} size="sm">{t(`mucDo.${mucDo}`)}</Badge>;
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

export function HopThoai({ moTieuDe, mo, onDong, children, chanDuoi }: {
  moTieuDe: string; mo: boolean; onDong: () => void; children: React.ReactNode; chanDuoi?: React.ReactNode;
}) {
  const id = useId();
  const { t } = useSigningT();
  useEffect(() => {
    if (!mo) return undefined;
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onDong();
    window.addEventListener('keydown', esc);
    return () => window.removeEventListener('keydown', esc);
  }, [mo, onDong]);
  if (!mo) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-backdrop p-4 animate-fade-in">
      <div role="dialog" aria-modal="true" aria-labelledby={id}
        className="w-full max-w-lg rounded-xl border border-border-subtle bg-surface-elevated shadow-lg animate-slide-in-bottom">
        <div className="flex items-center justify-between border-b border-border-subtle px-5 py-3">
          <h2 id={id} className="text-base font-bold text-main">{moTieuDe}</h2>
          <button type="button" onClick={onDong} className="text-secondary hover:text-main" aria-label={t('chung.dong')}>
            <i className="fa-solid fa-xmark" aria-hidden="true" />
          </button>
        </div>
        <div className="px-5 py-4 space-y-3">{children}</div>
        {chanDuoi && <div className="flex justify-end gap-2 border-t border-border-subtle px-5 py-3">{chanDuoi}</div>}
      </div>
    </div>
  );
}

export function TruongNhap({ nhan, children, ghiChu }: { nhan: string; children: React.ReactNode; ghiChu?: string }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-bold text-secondary">{nhan}</span>
      {children}
      {ghiChu && <span className="block text-xs text-muted">{ghiChu}</span>}
    </label>
  );
}
