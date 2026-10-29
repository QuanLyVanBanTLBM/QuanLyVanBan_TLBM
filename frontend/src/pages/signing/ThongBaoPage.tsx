/**
 * Thông báo trình ký của tôi (kênh trong ứng dụng; email gửi song song khi tài khoản có email). Mở trang thì đánh
 * dấu đã xem trên trình duyệt này (số thông báo mới ở tab).
 */
import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card } from '@components/common';
import { DangTai, LoiTai, Rong, TrangThaiBadge } from '@components/signing/ChungUI';
import { SO_THONG_BAO_TOI_DA, signingApi } from '@lib/signing/api';
import { dinhDangNgay } from '@lib/signing/dinhDang';
import { danhDauDaXemThongBao, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { LoaiThongBao } from '@lib/signing/types';

const BIEU_TUONG: Record<LoaiThongBao, string> = {
  CAN_KY: 'fa-pen-nib text-primary',
  HOAN_THANH: 'fa-circle-check text-success',
  TU_CHOI: 'fa-circle-xmark text-danger',
  YEU_CAU_SUA: 'fa-rotate-left text-warning',
  HUY: 'fa-ban text-secondary',
  UY_QUYEN: 'fa-user-group text-primary',
  TIN_NHAN: 'fa-comments text-primary',
  NHAC_HAN: 'fa-clock text-warning',
  QUA_HAN: 'fa-triangle-exclamation text-danger',
};

export default function ThongBaoPage() {
  const { t, loi, lang } = useSigningT();
  const { toi, daXemThongBao } = useToi();
  const ds = useTai(() => signingApi.thongBao(), []);
  const da_tai = Boolean(ds.duLieu);
  useEffect(() => {
    if (da_tai && toi) {
      danhDauDaXemThongBao(toi.id);
      daXemThongBao?.();
    }
  }, [da_tai, toi, daXemThongBao]);
  return (
    <Card className="p-4 space-y-3">
      {ds.dangTai && <DangTai />}
      {ds.loi && <LoiTai thongBao={loi(ds.loi)} onThuLai={ds.tai} />}
      {!ds.dangTai && !ds.loi && ds.duLieu?.length === 0 && <Rong icon="fa-bell">{t('thongBao.rong')}</Rong>}
      <ul className="divide-y divide-border-subtle">
        {ds.duLieu?.map((tb) => (
          <li key={tb.id}>
            <Link to={`/approvals/${tb.trinh_ky}`} className="flex items-start gap-3 px-2 py-3 hover:bg-surface-hover">
              <i className={`fa-solid ${BIEU_TUONG[tb.loai_thong_bao] ?? 'fa-bell text-secondary'} mt-1`} aria-hidden="true" />
              <div className="min-w-0 flex-1 space-y-0.5">
                <div className="font-semibold text-main">{t(`thongBao.loai.${tb.loai_thong_bao}`)}</div>
                <div className="truncate text-sm text-main" title={tb.van_ban}>{t('danhSach.maHoSo')} #{tb.trinh_ky} · {tb.van_ban}</div>
                {(tb.nguoi_thao_tac || tb.ly_do) && (
                  <div className="text-xs text-secondary break-words">
                    {tb.nguoi_thao_tac && <span>{t('thongBao.nguoiThaoTac')}: {tb.nguoi_thao_tac}</span>}
                    {tb.nguoi_thao_tac && tb.ly_do && ' · '}
                    {tb.ly_do && <span>{t(tb.loai_thong_bao === 'TIN_NHAN' ? 'thongBao.noiDung' : 'thongBao.lyDo')}: {tb.ly_do}</span>}
                  </div>
                )}
                {tb.han_xu_ly && (
                  <div className="text-xs text-secondary">
                    <i className="fa-regular fa-clock mr-1" aria-hidden="true" />
                    {t('thongBao.hanXuLy')}: <span className="font-semibold text-main">{dinhDangNgay(tb.han_xu_ly, lang)}</span>
                  </div>
                )}
                <div className="text-xs text-muted">{tb.ten_quy_trinh}</div>
              </div>
              {/* Cột phải: thời điểm, trạng thái hiện tại của hồ sơ (ghi rõ để không nhầm với sự kiện), kênh email */}
              <div className="flex shrink-0 flex-col items-end gap-1 text-right text-xs text-secondary">
                <time dateTime={tb.created_at}>{dinhDangNgay(tb.created_at, lang)}</time>
                <span className="inline-flex items-center gap-1">
                  {t('thongBao.hoSoHien')}: <TrangThaiBadge trangThai={tb.trang_thai_ho_so} />
                </span>
                {tb.email_trang_thai && (
                  <span className={tb.email_da_gui ? 'text-success' : 'text-warning'}
                    title={tb.email_nguoi_nhan ? `${t('thongBao.kenh.emailNguoiNhan')}: ${tb.email_nguoi_nhan}` : undefined}>
                    <i className="fa-solid fa-envelope mr-1" aria-hidden="true" />
                    {tb.email_da_gui ? t('thongBao.kenh.emailDaGui') : t('thongBao.kenh.emailChoGui')}
                  </span>
                )}
              </div>
            </Link>
          </li>
        ))}
      </ul>
      {(ds.duLieu?.length ?? 0) >= SO_THONG_BAO_TOI_DA && (
        <p className="border-t border-border-subtle pt-3 text-center text-xs text-muted">
          {t('thongBao.toiDa', { so: SO_THONG_BAO_TOI_DA })}
        </p>
      )}
    </Card>
  );
}
