/**
 * Thông báo trình ký của tôi (kênh trong ứng dụng; email gửi song song khi tài khoản có email). Tìm kiếm, lọc theo
 * loại sự kiện, phân trang phía server (10 mỗi trang; đổi bộ lọc thì về trang 1).
 * Thông báo mới kể từ lần xem trang này gần nhất (mốc lưu trên trình duyệt) được tô đậm; mốc chỉ đọc một lần lúc
 * vào trang nên việc tô đậm không đổi giữa chừng trong lúc đang xem/lọc/đổi trang, dù mốc trên trình duyệt đã được
 * cập nhật ngay (để huy hiệu số thông báo mới ở tab về 0).
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, Card } from '@components/common';
import { DangTai, LoiTai, Rong, TrangThaiBadge } from '@components/signing/ChungUI';
import { PhanTrang } from '@components/signing/PhanTrang';
import { SO_HO_SO_MOI_TRANG, docLoi, signingApi } from '@lib/signing/api';
import { dinhDangNgay, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { danhDauDaXemThongBao, lanXemThongBao, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { BoLocThongBao, LoaiThongBao } from '@lib/signing/types';

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
const CAC_LOAI: LoaiThongBao[] = [
  'CAN_KY', 'HOAN_THANH', 'TU_CHOI', 'YEU_CAU_SUA', 'HUY', 'UY_QUYEN', 'TIN_NHAN', 'NHAC_HAN', 'QUA_HAN',
];
const LOP_NHAN = 'mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-secondary';
const TRE_TIM_KIEM_MS = 300;

export default function ThongBaoPage() {
  const { t, loi, lang } = useSigningT();
  const { toi, daXemThongBao } = useToi();
  const [loc, setLoc] = useState<BoLocThongBao>({});
  const [tuKhoa, setTuKhoa] = useState('');
  const [trang, setTrang] = useState(1);
  // Mốc đọc một lần lúc vào trang, trước khi effect dưới đây cập nhật nó: dùng để tô đậm thông báo mới, không bị
  // chính lượt xem này ghi đè ngay lập tức (nên không còn chuyện huy hiệu về 0 mà không có gì được đánh dấu mới).
  const [mocTruocKhiXem] = useState(() => (toi ? lanXemThongBao(toi.id) : 0));
  const ds = useTai(() => signingApi.thongBao(loc, trang).catch((err) => {
    if (trang > 1 && docLoi(err).status === 404) setTrang(1);  // trang cuối không còn: về trang 1
    throw err;
  }), [loc.q, loc.loai_thong_bao, trang]);
  const da_tai = Boolean(ds.duLieu);
  const dsThongBao = ds.duLieu?.results ?? [];
  const coLoc = Object.values(loc).some(Boolean);

  useEffect(() => {
    if (da_tai && toi) {
      danhDauDaXemThongBao(toi.id);
      daXemThongBao?.();
    }
  }, [da_tai, toi, daXemThongBao]);

  useEffect(() => {
    const q = tuKhoa.trim();
    if (q === (loc.q ?? '')) return undefined;
    const hen = setTimeout(() => {
      setLoc((cu) => ({ ...cu, q }));
      setTrang(1);
    }, TRE_TIM_KIEM_MS);
    return () => clearTimeout(hen);
  }, [tuKhoa, loc.q]);

  const datLoai = (loai_thong_bao: string) => {
    setLoc((cu) => ({ ...cu, loai_thong_bao: loai_thong_bao as LoaiThongBao | '' }));
    setTrang(1);
  };
  const xoaLoc = () => {
    setTuKhoa('');
    setLoc({});
    setTrang(1);
  };

  return (
    <div className="space-y-4">
      <Card className="p-4 sm:p-5">
        <div className="grid grid-cols-1 items-end gap-3 md:grid-cols-2 lg:grid-cols-12">
          <label className="block lg:col-span-6">
            <span className={LOP_NHAN}><i className="fa-solid fa-magnifying-glass text-primary" aria-hidden="true" />{t('danhSach.timKiem')}</span>
            <span className="relative block">
              <input className={`${LOP_O_NHAP} pl-9`} type="search" value={tuKhoa} placeholder={t('thongBao.goiYTim')}
                onChange={(e) => setTuKhoa(e.target.value)} />
              <i className="fa-solid fa-search pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted" aria-hidden="true" />
            </span>
          </label>
          <label className="block lg:col-span-4">
            <span className={LOP_NHAN}><i className="fa-solid fa-filter text-primary" aria-hidden="true" />{t('thongBao.locLoai')}</span>
            <select className={LOP_O_NHAP} value={loc.loai_thong_bao ?? ''} onChange={(e) => datLoai(e.target.value)}>
              <option value="">{t('danhSach.tatCa')}</option>
              {CAC_LOAI.map((l) => <option key={l} value={l}>{t(`thongBao.loai.${l}`)}</option>)}
            </select>
          </label>
          {coLoc && (
            <div className="lg:col-span-2">
              <Button type="button" size="sm" variant="secondary" icon="fa-rotate-left" className="w-full justify-center" onClick={xoaLoc}>
                {t('danhSach.xoaLoc')}
              </Button>
            </div>
          )}
        </div>
      </Card>
      <Card className="p-4 space-y-3">
        {ds.dangTai && <DangTai />}
        {ds.loi && <LoiTai thongBao={loi(ds.loi)} onThuLai={ds.tai} />}
        {!ds.dangTai && !ds.loi && dsThongBao.length === 0 && (
          <Rong icon="fa-bell">{t(coLoc ? 'thongBao.khongKhopLoc' : 'thongBao.rong')}</Rong>
        )}
        <ul className="divide-y divide-border-subtle">
          {dsThongBao.map((tb) => {
            const moi = new Date(tb.created_at).getTime() > mocTruocKhiXem;
            return (
              <li key={tb.id}>
                <Link to={`/approvals/${tb.trinh_ky}`}
                  className={`flex items-start gap-3 rounded-lg px-2 py-3 hover:bg-surface-hover ${moi ? 'bg-primary-subtle/40' : ''}`}>
                  <span className="relative mt-1 shrink-0">
                    <i className={`fa-solid ${BIEU_TUONG[tb.loai_thong_bao] ?? 'fa-bell text-secondary'}`} aria-hidden="true" />
                    {moi && <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-danger" aria-hidden="true" />}
                  </span>
                  <div className="min-w-0 flex-1 space-y-0.5">
                    <div className={moi ? 'font-bold text-main' : 'font-semibold text-secondary'}>
                      {moi && <span className="sr-only">{t('thongBao.chuaXem')} — </span>}
                      <span>{t(`thongBao.loai.${tb.loai_thong_bao}`)}</span>
                    </div>
                    <div className={`truncate text-sm ${moi ? 'text-main' : 'text-secondary'}`} title={tb.van_ban}>{t('danhSach.maHoSo')} #{tb.trinh_ky} · {tb.van_ban}</div>
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
            );
          })}
        </ul>
        <PhanTrang trang={trang} soMoiTrang={SO_HO_SO_MOI_TRANG} tong={ds.duLieu?.count ?? 0} onDoi={setTrang}
          khoaTomTat="phanTrang.tomTatThongBao" />
      </Card>
    </div>
  );
}
