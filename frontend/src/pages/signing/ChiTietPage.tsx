/**
 * Chi tiết hồ sơ (#80 mục E): PDF của lượt hiện hành kèm lớp phủ chữ ký, tiến trình, người đang chờ, vai trò,
 * hạn xử lý, lịch sử; hành động theo quyền/trạng thái; trao đổi khi trả sửa; kết quả khi hoàn tất; sửa hồ sơ nháp;
 * danh sách tệp mọi lượt (trang tài liệu).
 */
import { type ReactNode, useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Button, Card } from '@components/common';
import { DangTai, HopThoai, KhongTimThay, LoiTai, ThongBao, TrangThaiHoSo } from '@components/signing/ChungUI';
import HanhDong from '@components/signing/HanhDong';
import KetQuaPanel from '@components/signing/KetQuaPanel';
import SuaNhapDialog from '@components/signing/SuaNhapDialog';
import TaiLieuPanel from '@components/signing/TaiLieuPanel';
import TienTrinh from '@components/signing/TienTrinh';
import TraoDoiPanel from '@components/signing/TraoDoiPanel';
import XemPdf, { type KhungHienThi } from '@components/signing/XemPdf';
import { docLoi, signingApi } from '@lib/signing/api';
import { dinhDangNgay, loiTepHoanTatHienThi, moTaVanBan } from '@lib/signing/dinhDang';
import { useTai, useToi } from '@lib/signing/hooks';
import { useSigningT, type HamDich } from '@lib/signing/i18n';
import { sha256Hex } from '@lib/signing/khoaKy';
import type { HoSoChiTiet, NhatKy } from '@lib/signing/types';
import { soKhung, viTriCuaNguoiKy } from '@lib/signing/viTri';

function DongThongTin({ nhan, children }: { nhan: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:justify-between sm:gap-3 text-sm py-1.5 border-b border-border-subtle/50 last:border-0">
      <span className="text-secondary font-medium shrink-0">{nhan}</span>
      <span className="text-main font-semibold sm:text-right min-w-0 break-words">{children}</span>
    </div>
  );
}

function chiTietNhatKy(e: NhatKy, t: HamDich): string {
  if (!e.chi_tiet || e.hanh_dong === 'THEM_CAP_KY' || e.hanh_dong === 'MO_CAP_KY') return '';
  if (e.hanh_dong === 'LOI_TAO_TEP_HOAN_TAT') return loiTepHoanTatHienThi(e.chi_tiet, t);
  if (e.hanh_dong === 'LIEN_KET_VAN_BAN_DI') {
    const soHieu = e.chi_tiet.match(/^#\d+\s*·\s*(.+)$/)?.[1];
    return soHieu ? t('chiTiet.soHieuVanBanLienKet', { soHieu }) : '';
  }
  if (e.hanh_dong === 'NGUNG_QUY_TRINH') {
    const phienBan = e.chi_tiet.match(/^Thay bằng phiên bản (\d+)$/)?.[1];
    return phienBan ? t('chiTiet.quyTrinhThayThe', { so: Number(phienBan) }) : '';
  }
  return ['KY', 'TU_CHOI', 'YEU_CAU_SUA', 'HUY_TRINH_KY', 'UY_QUYEN_KY'].includes(e.hanh_dong)
    ? e.chi_tiet
    : '';
}

/** Mã hồ sơ trên đường dẫn phải là số nguyên dương; sai dạng thì báo không tìm thấy, không gọi API. */
export default function ChiTietPage() {
  const { t } = useSigningT();
  const ma = useParams().id ?? '';
  if (!/^[1-9]\d{0,9}$/.test(ma)) return <KhongTimThay thongBao={t('loi.khong_tim_thay')} />;
  return <ChiTietHoSo id={Number(ma)} />;
}

function ChiTietHoSo({ id }: { id: number }) {
  const { t, loi, lang } = useSigningT();
  const { toi, lamMoiDem } = useToi();
  const ct = useTai(() => signingApi.chiTiet(id), [id]);
  const hoSo = ct.duLieu;
  const luot = hoSo?.luot_trinh[0] || null;
  const coTheLienKet = Boolean(hoSo && toi?.id === hoSo.create_by && hoSo.van_ban_id == null
    && hoSo.trang_thai === 'HOAN_THANH' && luot?.trang_thai_tep_hoan_tat === 'THANH_CONG');
  const [tepTai, setTepTai] = useState<{ khoa: string; buf: ArrayBuffer | null; maBam: string | null; loi: unknown } | null>(null);
  const [anh, setAnh] = useState<Record<number, string>>({});
  const [dangSua, setDangSua] = useState(false);
  const [qVanBan, setQVanBan] = useState('');
  const [qVanBanTim, setQVanBanTim] = useState('');
  const [vanBanDinhLienKet, setVanBanDinhLienKet] = useState('');
  const [moXacNhanLienKet, setMoXacNhanLienKet] = useState(false);
  const [dangLienKet, setDangLienKet] = useState(false);
  const [loiLienKet, setLoiLienKet] = useState<unknown>(null);
  const vanBanDi = useTai(() => coTheLienKet ? signingApi.timVanBanDi(qVanBanTim) : Promise.resolve([]),
    [coTheLienKet, qVanBanTim]);

  const { setDuLieu, tai } = ct;
  const capNhat = useCallback((moi?: HoSoChiTiet) => {
    if (moi && moi.id === id) setDuLieu(moi);
    else tai();
    // Có kết quả thao tác (ký, từ chối, hủy…): số ở thanh tab đổi theo; lần tải lại định kỳ không có kết quả thì bỏ qua
    if (moi) lamMoiDem?.();
  }, [setDuLieu, tai, id, lamMoiDem]);

  useEffect(() => {
    const hen = setTimeout(() => setQVanBanTim(qVanBan.trim()), 300);
    return () => clearTimeout(hen);
  }, [qVanBan]);

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
  if (ct.loi) {
    return docLoi(ct.loi).status === 404
      ? <KhongTimThay thongBao={t('loi.khong_tim_thay')} />
      : <LoiTai thongBao={loi(ct.loi)} onThuLai={ct.tai} />;
  }
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
  const vanBanChon = (vanBanDi.duLieu || []).find((vb) => String(vb.id) === vanBanDinhLienKet) || null;
  const lienKetVanBan = async () => {
    if (!vanBanChon || dangLienKet) return;
    setDangLienKet(true);
    setLoiLienKet(null);
    try {
      const moi = await signingApi.lienKetVanBanDi(hoSo.id, vanBanChon.id);
      setMoXacNhanLienKet(false);
      setVanBanDinhLienKet('');
      capNhat(moi);
    } catch (err) {
      setLoiLienKet(err);
    } finally {
      setDangLienKet(false);
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="space-y-4 min-w-0">
        <Card className="p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-bold text-main">{t('danhSach.maHoSo')} #{hoSo.id}</h2>
            {hoSo.van_ban_id == null && <>
              <span className="rounded-full bg-info-subtle px-2 py-1 text-xs text-info">{t('chiTiet.taiLieuDocLap')}</span>
            </>}
            <TrangThaiHoSo hoSo={hoSo} />
          </div>
          <div className="text-base font-semibold text-main break-words">{moTaVanBan(hoSo.van_ban, t)}</div>
          {hoSo.trang_thai === 'NHAP' && toi?.id === hoSo.create_by && (
            <Button size="sm" variant="secondary" icon="fa-pen" onClick={() => setDangSua(true)}>{t('chiTiet.suaHoSo')}</Button>
          )}
          <HanhDong hoSo={hoSo} luot={luot} maBamTepDangXem={maBam} onXong={capNhat} />
          {hoSo.trang_thai === 'TU_CHOI' && hoSo.ly_do_tu_choi && (
            <ThongBao>{t('chiTiet.lyDoTuChoi')}: {hoSo.ly_do_tu_choi}</ThongBao>
          )}
          {hoSo.trang_thai === 'HUY' && hoSo.ly_do_huy && <ThongBao loai="canh_bao">{t('chiTiet.lyDoHuy')}: {hoSo.ly_do_huy}</ThongBao>}
        </Card>
        <Card className="p-4 space-y-2">
          <h3 className="text-xl font-bold text-main">{t('chiTiet.taiLieu')}</h3>
          {/* PDF cuộn trong khung riêng để trang không dài theo số trang tài liệu */}
          <div className="max-h-[calc(100vh-12rem)] overflow-y-auto rounded-lg bg-surface-subtle p-3">
            {loiTep ? <LoiTai thongBao={loi(loiTep)} /> : tep ? <XemPdf duLieu={tep} khung={khung} /> : <DangTai />}
          </div>
        </Card>
      </div>
      {/* lg:pb-20: nút trợ lý AI nổi ở góc dưới không che khối cuối của cột khi cuộn hết */}
      <div className="space-y-4 lg:sticky lg:top-0 lg:self-start lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto lg:pb-20">
        <Card className="p-4 space-y-2">
          <h3 className="text-base font-bold text-main pb-2 border-b border-border-subtle">{t('chiTiet.thongTinHoSo')}</h3>
          <DongThongTin nhan={hoSo.van_ban_id == null ? t('chiTiet.taiLieu') : t('danhSach.vanBan')}>
            {moTaVanBan(hoSo.van_ban, t)}
          </DongThongTin>
          <DongThongTin nhan={t('danhSach.quyTrinh')}>{hoSo.ten_quy_trinh}</DongThongTin>
          <DongThongTin nhan={t('danhSach.nguoiTao')}>{hoSo.ten_nguoi_tao}</DongThongTin>
          <DongThongTin nhan={t('danhSach.ngayGui')}>{dinhDangNgay(hoSo.ngay_gui, lang)}</DongThongTin>
          <DongThongTin nhan={t('danhSach.hanChot')}>{dinhDangNgay(hoSo.han_chot, lang)}</DongThongTin>
          <DongThongTin nhan={t('chiTiet.nguoiDangCho')}>
            {hoSo.dang_cho.length ? hoSo.dang_cho.map((d) => d.ten_nguoi_ky).join(', ') : t('chiTiet.khongAiCho')}
          </DongThongTin>
          {hoSo.ghi_chu && <DongThongTin nhan={t('chiTiet.ghiChu')}><span className="whitespace-pre-wrap">{hoSo.ghi_chu}</span></DongThongTin>}
          {coTheLienKet && (
            <div className="space-y-2 border-t border-border-subtle pt-3">
              <h3 className="text-sm font-semibold text-main">{t('chiTiet.dangKyVanBanDi')}</h3>
              <p className="text-xs text-muted">{t('chiTiet.goiYLienKetVanBan')}</p>
              <Link to="/documents/outgoing" className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
                <i className="fa-solid fa-arrow-up-right-from-square" aria-hidden="true" />
                {t('chiTiet.moPhanVanBanDi')}
              </Link>
              <input className="w-full rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-main"
                aria-label={t('chiTiet.timVanBanDi')} placeholder={t('chiTiet.timVanBanDi')}
                value={qVanBan} onChange={(e) => {
                  setQVanBan(e.target.value);
                  setVanBanDinhLienKet('');
                  setLoiLienKet(null);
                }} />
              {vanBanDi.dangTai ? <DangTai /> : vanBanDi.loi ? (
                <LoiTai thongBao={loi(vanBanDi.loi)} onThuLai={vanBanDi.tai} />
              ) : (
                <select className="w-full rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-main"
                  aria-label={t('chiTiet.chonVanBanDi')} value={vanBanDinhLienKet}
                  onChange={(e) => setVanBanDinhLienKet(e.target.value)}>
                  <option value="">{t('chiTiet.chonVanBanDi')}</option>
                  {(vanBanDi.duLieu || []).map((vb) => (
                    <option key={vb.id} value={vb.id}>{moTaVanBan(vb, t)}</option>
                  ))}
                </select>
              )}
              {vanBanDi.duLieu?.length === 0 && !vanBanDi.dangTai && !vanBanDi.loi && (
                <p className="text-xs text-muted">{t('chiTiet.khongCoVanBanDi')}</p>
              )}
              {loiLienKet != null && <ThongBao>{loi(loiLienKet)}</ThongBao>}
              <Button size="sm" icon="fa-link" disabled={!vanBanChon || vanBanDi.dangTai}
                onClick={() => setMoXacNhanLienKet(true)}>{t('chiTiet.lienKetVanBanDi')}</Button>
            </div>
          )}
          {hoSo.ho_so_goc && (
            <Link to={`/approvals/${hoSo.ho_so_goc}`} className="text-sm font-medium text-primary hover:underline">
              {t('chiTiet.hoSoGoc', { so: hoSo.ho_so_goc })}
            </Link>
          )}
        </Card>
        {hoSo.trang_thai === 'HOAN_THANH' && luot && <KetQuaPanel hoSo={hoSo} luot={luot} onTaiLai={capNhat} />}
        <TaiLieuPanel hoSo={hoSo} />
        {coTraoDoi && luot?.trang_thai === 'YEU_CAU_SUA' && <TraoDoiPanel hoSo={hoSo} onXong={capNhat} />}
        {luot && (
          <Card className="p-4 space-y-2">
            <h3 className="text-xl font-bold text-main">{t('chiTiet.tienTrinh')}</h3>
            <TienTrinh luot={luot} toiId={toi?.id} />
          </Card>
        )}
        {hoSo.luot_trinh.slice(1).map((l) => (
          <details key={l.id} className="rounded-xl border border-border-subtle bg-surface p-4">
            <summary className="cursor-pointer text-sm font-bold text-secondary">
              {t('chiTiet.luot', { so: l.so_luot })} · {t(`trangThai.${l.trang_thai}`)}
            </summary>
            {l.yeu_cau_sua.length > 0 && (
              <div className="mt-3 rounded-lg border border-purple-border bg-purple-subtle p-3 text-sm">
                <div className="font-bold text-purple break-words">{l.yeu_cau_sua[0].tieu_de}</div>
                <div className="text-main whitespace-pre-wrap break-words mt-0.5">{l.yeu_cau_sua[0].ly_do}</div>
              </div>
            )}
            {l.ly_do && l.yeu_cau_sua.length === 0 && (
              <div className="mt-3 rounded-lg border border-danger-border bg-danger-subtle p-3 text-sm">
                <div className="text-danger break-words">{l.ly_do}</div>
              </div>
            )}
            <div className="mt-3"><TienTrinh luot={l} toiId={toi?.id} /></div>
          </details>
        ))}
        <Card className="p-4 space-y-2">
          <h3 className="text-xl font-bold text-main">{t('chiTiet.lichSu')}</h3>
          <ol className="space-y-1.5 text-sm">
            {hoSo.lich_su.map((e) => {
              const chiTiet = chiTietNhatKy(e, t);
              const hanhDong = t(`nhatKy.${e.hanh_dong}`);
              return (
                <li key={e.id} className="flex justify-between gap-2">
                  <span className="text-main min-w-0 break-words">
                    {hanhDong === '—' ? t('nhatKy.KHAC') : hanhDong}{chiTiet && ` · ${chiTiet}`}
                    {e.ten_nguoi_thuc_hien && <span className="block text-xs text-secondary">{e.ten_nguoi_thuc_hien}</span>}
                  </span>
                  <span className="text-muted shrink-0">{dinhDangNgay(e.created_at, lang)}</span>
                </li>
              );
            })}
          </ol>
        </Card>
      </div>
      {dangSua && <SuaNhapDialog hoSo={hoSo} onDong={() => setDangSua(false)} onXong={(moi) => { setDangSua(false); capNhat(moi); }} />}
      <HopThoai moTieuDe={t('chiTiet.lienKetVanBanDi')} mo={moXacNhanLienKet}
        onDong={() => setMoXacNhanLienKet(false)} dangXuLy={dangLienKet}
        chanDuoi={<>
          <Button variant="secondary" disabled={dangLienKet} onClick={() => setMoXacNhanLienKet(false)}>
            {t('chung.quayLai')}
          </Button>
          <Button icon="fa-link" isLoading={dangLienKet} disabled={!vanBanChon} onClick={lienKetVanBan}>
            {t('chung.xacNhan')}
          </Button>
        </>}>
        <p className="text-sm text-main">{t('chiTiet.xacNhanLienKetVanBan', {
          vanBan: vanBanChon ? moTaVanBan(vanBanChon, t) : '',
        })}</p>
      </HopThoai>
    </div>
  );
}
