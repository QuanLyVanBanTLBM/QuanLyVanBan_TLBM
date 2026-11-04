/**
 * Hộp thoại "Chi tiết hồ sơ" mở từ danh sách hồ sơ: xem nhanh thông tin, tệp, tiến trình ký và lịch sử, chỉ đọc.
 * Không tải khung xem PDF và không có hành động ký/trả lại/hủy; muốn thao tác thì "Mở hồ sơ" sang trang đầy đủ.
 * Thông tin chính lấy từ dòng danh sách; chỉ phần tiến trình, tệp, lịch sử gọi API chi tiết khi mở.
 */
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@components/common';
import { DangTai, HopThoai, LoiTai, TrangThaiHoSo } from '@components/signing/ChungUI';
import TaiLieuPanel from '@components/signing/TaiLieuPanel';
import TienTrinh from '@components/signing/TienTrinh';
import { signingApi } from '@lib/signing/api';
import { chiTietNhatKy, dinhDangNgay, moTaVanBan } from '@lib/signing/dinhDang';
import { useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { HoSo, NhatKy } from '@lib/signing/types';

const SO_MUC_LICH_SU = 5;

function Dong({ nhan, children }: { nhan: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:justify-between sm:gap-3 text-sm py-1.5 border-b border-border-subtle/50 last:border-0">
      <span className="text-secondary font-medium shrink-0">{nhan}</span>
      <span className="text-main font-semibold sm:text-right min-w-0 break-words">{children}</span>
    </div>
  );
}

/** Các mục mới nhất trước, tối đa SO_MUC_LICH_SU. */
function lichSuGanNhat(ds: NhatKy[]): NhatKy[] {
  return [...ds].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)).slice(0, SO_MUC_LICH_SU);
}

export default function ChiTietNhanh({ hoSo, hop, onDong }: { hoSo: HoSo; hop: string; onDong: () => void }) {
  const { t, loi, lang } = useSigningT();
  const { toi } = useToi();
  const navigate = useNavigate();
  const chiTiet = useTai(() => signingApi.chiTiet(hoSo.id), [hoSo.id]);
  const luot = chiTiet.duLieu?.luot_trinh[0] ?? null;
  const moHoSo = () => navigate(`/approvals/${hoSo.id}`, { state: { hop } });

  return (
    <HopThoai moTieuDe={t('danhSach.chiTietHoSo')} mo onDong={onDong} chieuRong="42rem"
      chanDuoi={<>
        <Button variant="secondary" onClick={onDong}>{t('chung.dong')}</Button>
        <Button icon="fa-arrow-up-right-from-square" onClick={moHoSo}>
          {t(hop === 'can_toi_ky' ? 'danhSach.moDeKyDuyet' : 'danhSach.moHoSo')}
        </Button>
      </>}>
      <div className="space-y-0.5">
        <Dong nhan={t('danhSach.maHoSo')}>#{hoSo.id}</Dong>
        <Dong nhan={hoSo.van_ban_id == null ? t('chiTiet.taiLieu') : t('danhSach.vanBan')}>{moTaVanBan(hoSo.van_ban, t)}</Dong>
        <Dong nhan={t('danhSach.trangThai')}><TrangThaiHoSo hoSo={hoSo} /></Dong>
        <Dong nhan={t('danhSach.quyTrinh')}>{hoSo.ten_quy_trinh}</Dong>
        <Dong nhan={t('danhSach.nguoiTao')}>{hoSo.ten_nguoi_tao}</Dong>
        <Dong nhan={t('danhSach.ngayGui')}>{dinhDangNgay(hoSo.ngay_gui, lang)}</Dong>
        <Dong nhan={t('danhSach.hanChot')}>{dinhDangNgay(hoSo.han_chot, lang)}</Dong>
        {!hoSo.han_chot && hoSo.han_xu_ly_cap && (
          <Dong nhan={t('danhSach.hanCap')}>{dinhDangNgay(hoSo.han_xu_ly_cap, lang)}</Dong>
        )}
        <Dong nhan={t('chiTiet.nguoiDangCho')}>
          {hoSo.dang_cho.length ? hoSo.dang_cho.map((d) => d.ten_nguoi_ky).join(', ') : t('chiTiet.khongAiCho')}
        </Dong>
        {hoSo.ghi_chu && <Dong nhan={t('chiTiet.ghiChu')}><span className="whitespace-pre-wrap">{hoSo.ghi_chu}</span></Dong>}
      </div>
      {chiTiet.dangTai && <DangTai />}
      {chiTiet.loi != null && <LoiTai thongBao={loi(chiTiet.loi)} onThuLai={chiTiet.tai} />}
      {chiTiet.duLieu && !chiTiet.loi && (
        <>
          <TaiLieuPanel hoSo={chiTiet.duLieu} />
          {luot && (
            <section className="space-y-2">
              <h3 className="text-base font-bold text-main">{t('chiTiet.tienTrinh')}</h3>
              <TienTrinh luot={luot} toiId={toi?.id} />
            </section>
          )}
          {chiTiet.duLieu.lich_su.length > 0 && (
            <section className="space-y-2">
              <h3 className="text-base font-bold text-main">{t('danhSach.lichSuGanDay')}</h3>
              <ol className="space-y-1.5 text-sm">
                {lichSuGanNhat(chiTiet.duLieu.lich_su).map((e) => {
                  const chiTietMuc = chiTietNhatKy(e, t);
                  const hanhDong = t(`nhatKy.${e.hanh_dong}`);
                  return (
                    <li key={e.id} className="flex justify-between gap-2">
                      <span className="text-main min-w-0 break-words">
                        {hanhDong === '—' ? t('nhatKy.KHAC') : hanhDong}{chiTietMuc && ` · ${chiTietMuc}`}
                        {e.ten_nguoi_thuc_hien && <span className="block text-xs text-secondary">{e.ten_nguoi_thuc_hien}</span>}
                      </span>
                      <span className="text-muted shrink-0">{dinhDangNgay(e.created_at, lang)}</span>
                    </li>
                  );
                })}
              </ol>
            </section>
          )}
        </>
      )}
    </HopThoai>
  );
}
