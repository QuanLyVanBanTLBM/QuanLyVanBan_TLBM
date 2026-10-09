/**
 * Chi tiết hồ sơ (#80 mục E): PDF của lượt hiện hành kèm lớp phủ chữ ký, tiến trình, người đang chờ, vai trò,
 * hạn xử lý, lịch sử; hành động theo quyền/trạng thái; trao đổi khi trả sửa; kết quả khi hoàn tất.
 */
import { type ReactNode, useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Card } from '@components/common';
import { DangTai, LoiTai, MucDoBadge, ThongBao, TrangThaiBadge } from '@components/signing/ChungUI';
import HanhDong from '@components/signing/HanhDong';
import KetQuaPanel from '@components/signing/KetQuaPanel';
import TienTrinh from '@components/signing/TienTrinh';
import TraoDoiPanel from '@components/signing/TraoDoiPanel';
import XemPdf, { type KhungHienThi } from '@components/signing/XemPdf';
import { signingApi } from '@lib/signing/api';
import { dinhDangNgay, moTaVanBan } from '@lib/signing/dinhDang';
import { useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import { sha256Hex } from '@lib/signing/khoaKy';
import type { HoSoChiTiet } from '@lib/signing/types';
import { soKhung, viTriCuaNguoiKy } from '@lib/signing/viTri';

function DongThongTin({ nhan, children }: { nhan: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 text-sm">
      <span className="text-secondary shrink-0">{nhan}</span>
      <span className="text-main text-right min-w-0 break-words">{children}</span>
    </div>
  );
}

export default function ChiTietPage() {
  const id = Number(useParams().id);
  const { t, loi, lang } = useSigningT();
  const { toi } = useToi();
  const ct = useTai(() => signingApi.chiTiet(id), [id]);
  const hoSo = ct.duLieu;
  const luot = hoSo?.luot_trinh[0] || null;
  const [tepTai, setTepTai] = useState<{ khoa: string; buf: ArrayBuffer | null; maBam: string | null; loi: unknown } | null>(null);
  const [anh, setAnh] = useState<Record<number, string>>({});

  const { setDuLieu, tai } = ct;
  const capNhat = useCallback((moi?: HoSoChiTiet) => {
    if (moi && moi.id === id) setDuLieu(moi);
    else tai();
  }, [setDuLieu, tai, id]);

  // Tệp của lượt hiện hành; băm lại để người ký đối chiếu mã băm đã khóa. Kết quả gắn với khóa tệp nên đổi lượt
  // thì tệp cũ không còn được dùng để ký (mã băm chưa có cho đến khi tải xong tệp mới).
  const coHoSo = Boolean(hoSo);
  const khoaTep = `${id}:${luot?.id ?? 'nhap'}:${hoSo?.ma_bam_tai_lieu ?? ''}`;
  const tepHienTai = tepTai?.khoa === khoaTep ? tepTai : null;
  const tep = tepHienTai?.buf ?? null;
  const maBam = tepHienTai?.maBam ?? null;
  const loiTep = tepHienTai?.loi ?? null;
  useEffect(() => {
    if (!coHoSo) return undefined;
    let huy = false;
    signingApi.tepGoc(id).then(async (b) => {
      const buf = await b.arrayBuffer();
      const ma_bam = await sha256Hex(buf);
      if (!huy) setTepTai({ khoa: khoaTep, buf, maBam: ma_bam, loi: null });
    }).catch((err) => !huy && setTepTai({ khoa: khoaTep, buf: null, maBam: null, loi: err }));
    return () => {
      huy = true;
    };
  }, [id, khoaTep, coHoSo]);

  // Ảnh snapshot chữ ký để vẽ lớp phủ
  const khoaAnh = (luot?.cap_ky || []).flatMap((c) => c.nguoi_ky)
    .filter((n) => n.chu_ky?.co_anh_chu_ky).map((n) => n.chu_ky.id).join(',');
  useEffect(() => {
    const urls: string[] = [];
    let huy = false;
    const chuKyCoAnh = khoaAnh ? khoaAnh.split(',').map(Number) : [];
    Promise.all(chuKyCoAnh.map((ck) => signingApi.anhChuKy(id, ck).then((b) => [ck, URL.createObjectURL(b)] as const)
      .catch(() => null))).then((ds) => {
      const map: Record<number, string> = {};
      ds.forEach((d) => {
        if (d) {
          map[d[0]] = d[1];
          urls.push(d[1]);
        }
      });
      if (!huy) setAnh(map);
    });
    return () => {
      huy = true;
      urls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [id, khoaAnh]);

  if (ct.dangTai && !hoSo) return <DangTai />;
  if (ct.loi) return <LoiTai thongBao={loi(ct.loi)} onThuLai={ct.tai} />;
  if (!hoSo) return null;

  const khung: KhungHienThi[] = (luot?.cap_ky || []).flatMap((c) => c.nguoi_ky).flatMap((n) => {
    const v = viTriCuaNguoiKy(n);
    if (!v) return [];
    const da_ky = n.trang_thai === 'DA_KY' && n.chu_ky;
    return [{
      id: String(n.id), ...soKhung(v), nhan: n.ten_nguoi_ky,
      phu: da_ky ? dinhDangNgay(n.chu_ky.ngay_ky, lang) : t(`vaiTro.${n.vai_tro_ky}`),
      anhUrl: da_ky ? anh[n.chu_ky.id] : undefined, kieu: da_ky ? 'da_ky' : 'cho',
    } as KhungHienThi];
  });
  const coTraoDoi = hoSo.luot_trinh.some((l) => l.yeu_cau_sua.length > 0);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="space-y-4 min-w-0">
        <Card className="p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-bold text-main">#{hoSo.id}</h2>
            <TrangThaiBadge trangThai={hoSo.trang_thai} />
            {luot && luot.trang_thai !== hoSo.trang_thai && <TrangThaiBadge trangThai={luot.trang_thai} />}
            <MucDoBadge mucDo={hoSo.muc_do} />
          </div>
          <div className="text-sm text-main">{moTaVanBan(hoSo.van_ban, hoSo.van_ban_id)}</div>
          <HanhDong hoSo={hoSo} luot={luot} maBamTepDangXem={maBam} onXong={capNhat} />
          {hoSo.trang_thai === 'TU_CHOI' && hoSo.ly_do_tu_choi && (
            <ThongBao>{t('chiTiet.lyDoTuChoi')}: {hoSo.ly_do_tu_choi}</ThongBao>
          )}
          {hoSo.trang_thai === 'HUY' && hoSo.ly_do_huy && <ThongBao loai="canh_bao">{t('chiTiet.lyDoHuy')}: {hoSo.ly_do_huy}</ThongBao>}
        </Card>
        <Card className="p-4 space-y-2">
          <h3 className="font-bold text-sm text-main">{t('chiTiet.taiLieu')}</h3>
          {loiTep ? <LoiTai thongBao={loi(loiTep)} /> : tep ? <XemPdf duLieu={tep} khung={khung} /> : <DangTai />}
        </Card>
      </div>
      <div className="space-y-4">
        <Card className="p-4 space-y-2">
          <DongThongTin nhan={t('danhSach.quyTrinh')}>{hoSo.ten_quy_trinh} ({hoSo.ma_quy_trinh} v{hoSo.phien_ban_quy_trinh})</DongThongTin>
          <DongThongTin nhan={t('danhSach.nguoiTao')}>{hoSo.ten_nguoi_tao}</DongThongTin>
          <DongThongTin nhan={t('danhSach.ngayGui')}>{dinhDangNgay(hoSo.ngay_gui, lang)}</DongThongTin>
          <DongThongTin nhan={t('danhSach.hanChot')}>{dinhDangNgay(hoSo.han_chot, lang)}</DongThongTin>
          <DongThongTin nhan={t('chiTiet.nguoiDangCho')}>
            {hoSo.dang_cho.length ? hoSo.dang_cho.map((d) => d.ten_nguoi_ky).join(', ') : t('chiTiet.khongAiCho')}
          </DongThongTin>
          {hoSo.ho_so_goc && (
            <Link to={`/approvals/${hoSo.ho_so_goc}`} className="text-xs text-primary hover:underline">
              {t('chiTiet.hoSoGoc', { so: hoSo.ho_so_goc })}
            </Link>
          )}
        </Card>
        {hoSo.trang_thai === 'HOAN_THANH' && luot && <KetQuaPanel hoSo={hoSo} luot={luot} onTaiLai={capNhat} />}
        {coTraoDoi && luot?.trang_thai === 'YEU_CAU_SUA' && <TraoDoiPanel hoSo={hoSo} onXong={capNhat} />}
        {luot && (
          <Card className="p-4 space-y-2">
            <h3 className="font-bold text-sm text-main">{t('chiTiet.tienTrinh')} · {t('chiTiet.luot', { so: luot.so_luot })}</h3>
            <TienTrinh luot={luot} toiId={toi?.id} />
          </Card>
        )}
        {hoSo.luot_trinh.slice(1).map((l) => (
          <details key={l.id} className="rounded-xl border border-border-subtle bg-surface p-4">
            <summary className="cursor-pointer text-sm font-bold text-secondary">
              {t('chiTiet.luot', { so: l.so_luot })} · {t(`trangThai.${l.trang_thai}`)}
            </summary>
            <div className="mt-3"><TienTrinh luot={l} toiId={toi?.id} /></div>
          </details>
        ))}
        <Card className="p-4 space-y-2">
          <h3 className="font-bold text-sm text-main">{t('chiTiet.lichSu')}</h3>
          <ol className="space-y-1 text-xs">
            {hoSo.lich_su.map((e) => (
              <li key={e.id} className="flex justify-between gap-2">
                <span className="text-main">
                  {t(`nhatKy.${e.hanh_dong}`)}{e.chi_tiet && e.hanh_dong !== 'MO_CAP_KY' ? ` · ${e.chi_tiet}` : ''}
                </span>
                <span className="text-muted shrink-0">{dinhDangNgay(e.created_at, lang)}</span>
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  );
}
