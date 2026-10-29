/**
 * Tạo hồ sơ trình ký (#80 mục E): (1) chọn văn bản đi có sẵn hoặc tải PDF dự thảo chưa vào sổ (số hiệu tham chiếu,
 * trích yếu; #275 mục 3), quy trình → lưu nháp;
 * (2) xem trước người ký và tài liệu, đặt vị trí ký, chọn người ký khi chức vụ nhiều ứng viên → gửi.
 * Mở lại nháp: /approvals/tao-moi?ho_so=<id>.
 */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Card } from '@components/common';
import { DangTai, HopThoai, LoiTai, OChonTep, ThongBao, TruongNhap } from '@components/signing/ChungUI';
import XemPdf, { type KhungHienThi } from '@components/signing/XemPdf';
import { docLoi, signingApi } from '@lib/signing/api';
import { GIOI_HAN, hanChotDaQua, kiemTraTepPdf, LOP_O_NHAP, moTaVanBan, tenNguoiKyCauHinh } from '@lib/signing/dinhDang';
import { coQuyen, useKhoaChongTrung, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { HoSoChiTiet, QuyTrinh, VanBanDi, ViTriKy } from '@lib/signing/types';
import { KHUNG_MAC_DINH, khungTuDiemBam, soKhung } from '@lib/signing/viTri';

interface UngVien { cau_hinh: number; ung_vien: Array<{ id: number; ten: string }> }
type NguonVanBan = 'van_ban_di' | 'khac';

function Buoc1({ onXong }: { onXong: (ho_so: HoSoChiTiet, tep: ArrayBuffer | null) => void }) {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const [nguon, setNguon] = useState<NguonVanBan>('van_ban_di');
  const [chon, setChon] = useState<VanBanDi | null>(null);
  const [q, setQ] = useState('');
  const [qTim, setQTim] = useState('');
  // Gõ xong mới tìm (không gửi một request cho mỗi phím)
  useEffect(() => {
    const hen = setTimeout(() => setQTim(q.trim()), 300);
    return () => clearTimeout(hen);
  }, [q]);
  const vanBan = useTai(() => (nguon === 'van_ban_di' ? signingApi.timVanBanDi(qTim) : Promise.resolve([])), [qTim, nguon]);
  const chiTietVanBan = useTai(
    () => chon ? signingApi.chiTietVanBanDi(chon.id) : Promise.resolve(null), [chon?.id],
  );
  const quyTrinh = useTai(() => signingApi.quyTrinh('HOAT_DONG'));
  const [soHieu, setSoHieu] = useState('');
  const [trichYeu, setTrichYeu] = useState('');
  const [qtId, setQtId] = useState('');
  const [hanChot, setHanChot] = useState('');
  const [ghiChu, setGhiChu] = useState('');
  const [tep, setTep] = useState<File | null>(null);
  const [tepDinhKemId, setTepDinhKemId] = useState('');
  const [loiTep, setLoiTep] = useState('');
  const [loiHanChot, setLoiHanChot] = useState('');
  const [dangGui, setDangGui] = useState(false);
  const [thongBao, setThongBao] = useState('');

  // Người tạo chỉ chọn quy trình công ty hoặc quy trình phòng ban của đơn vị mình (server kiểm lại)
  const dungDuoc = (quyTrinh.duLieu || []).filter(
    (p) => p.pham_vi === 'CONG_TY' || (p.don_vi_ap_dung_id != null && p.don_vi_ap_dung_id === toi?.don_vi_id));

  const tepPdf = (chiTietVanBan.duLieu?.attachments || []).filter(
    (item) => !item.is_deleted && item.name.toLowerCase().endsWith('.pdf'),
  );
  const coNguonTaiLieu = nguon === 'van_ban_di'
    ? Boolean(chon && tepPdf.some((item) => String(item.id) === tepDinhKemId))
    : Boolean(trichYeu.trim() && tep && !loiTep);
  const luu = async () => {
    if (!coNguonTaiLieu || !qtId || (nguon === 'khac' && (!tep || loiTep))) return;
    if (hanChotDaQua(hanChot)) {  // giờ có thể đã qua kể từ lúc nhập
      setLoiHanChot(t('tao.loiHanChot'));
      return;
    }
    setDangGui(true);
    setThongBao('');
    try {
      const form = new FormData();
      if (nguon === 'van_ban_di' && chon) {
        form.append('document_type', 'vanbandi');
        form.append('van_ban_id', String(chon.id));
        form.append('tep_dinh_kem_id', tepDinhKemId);
      } else {
        form.append('so_hieu_van_ban', soHieu.trim());
        form.append('trich_yeu_van_ban', trichYeu.trim());
        if (tep) form.append('tep', tep);
      }
      form.append('quy_trinh', qtId);
      if (hanChot) form.append('han_chot', new Date(hanChot).toISOString());
      if (ghiChu) form.append('ghi_chu', ghiChu);
      const ho_so = await signingApi.taoNhap(form);
      onXong(ho_so, nguon === 'khac' && tep ? await tep.arrayBuffer() : null);
    } catch (err) {
      setThongBao(loi(err));
    } finally {
      setDangGui(false);
    }
  };

  return (
    <Card className="p-5 space-y-4">
      <h2 className="text-lg font-bold text-main">1. {t('tao.buoc1')}</h2>
      {/* Desktop: trái chọn văn bản trình ký, phải thông tin trình; tránh một cột ô nhập trải hết chiều rộng */}
      <div className="grid gap-4 lg:grid-cols-2 lg:gap-6">
        <div className="space-y-3 min-w-0">
        <fieldset className="space-y-3">
          <legend className="mb-1.5 text-sm font-semibold text-main">{t('tao.vanBanDi')}</legend>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label={t('tao.vanBanDi')}>
            {(['van_ban_di', 'khac'] as const).map((n) => (
              <label key={n} className={`flex cursor-pointer items-center gap-2 rounded-full border px-3.5 py-1.5 text-sm font-semibold ${
                nguon === n ? 'border-primary bg-primary-subtle text-primary' : 'border-border-subtle text-secondary hover:bg-surface-hover'}`}>
                <input type="radio" name="nguon-van-ban" className="sr-only" checked={nguon === n} onChange={() => setNguon(n)} />
                <i className={`fa-solid ${n === 'van_ban_di' ? 'fa-file-export' : 'fa-file-pen'}`} aria-hidden="true" />
                {t(n === 'van_ban_di' ? 'tao.chonVanBanDi' : 'tao.nhapVanBanKhac')}
              </label>
            ))}
          </div>
          {nguon === 'van_ban_di' ? (
            <>
              <p className="text-xs text-muted">{t('tao.goiYChonVanBanDi')}</p>
              {chon && (
                <div className="flex flex-wrap items-center gap-2 rounded-lg bg-primary-subtle px-3 py-2 text-sm">
                  <span className="font-semibold text-primary">{t('tao.daChonVanBan')}:</span>
                  <span className="min-w-0 flex-1 break-words text-main">{moTaVanBan(chon, chon.id)}</span>
                  <Button size="sm" variant="ghost" icon="fa-xmark" onClick={() => setChon(null)}>{t('tao.boChon')}</Button>
                </div>
              )}
              <input className={LOP_O_NHAP} placeholder={t('tao.timVanBan')} aria-label={t('tao.timVanBan')} value={q}
                onChange={(e) => setQ(e.target.value)} />
              {vanBan.dangTai ? <DangTai /> : vanBan.loi ? <LoiTai thongBao={loi(vanBan.loi)} onThuLai={vanBan.tai} /> : (
                <div className="max-h-48 overflow-y-auto rounded-lg border border-border-subtle">
                  {vanBan.duLieu?.length === 0 && <div className="p-3 text-sm text-muted">{t('tao.khongCoVanBan')}</div>}
                  {vanBan.duLieu?.map((vb) => (
                    <button type="button" key={vb.id} onClick={() => { setChon(vb); setTepDinhKemId(''); }}
                      className={`block w-full px-3 py-2 text-left text-sm border-b border-border-subtle last:border-0 ${
                        chon?.id === vb.id ? 'bg-primary-subtle text-primary font-semibold' : 'hover:bg-surface-hover text-main'}`}>
                      {moTaVanBan(vb, vb.id)}
                    </button>
                  ))}
                </div>
              )}
              {chon && (
                <TruongNhap nhan={t('tao.tepDinhKem')}>
                  {chiTietVanBan.dangTai ? <DangTai /> : chiTietVanBan.loi ? (
                    <LoiTai thongBao={loi(chiTietVanBan.loi)} onThuLai={chiTietVanBan.tai} />
                  ) : tepPdf.length ? (
                    <select className={LOP_O_NHAP} value={tepDinhKemId} onChange={(e) => setTepDinhKemId(e.target.value)}>
                      <option value="">{t('tao.chonTepDinhKem')}</option>
                      {tepPdf.map((item) => (
                        <option key={item.id} value={item.id}>{item.name}</option>
                      ))}
                    </select>
                  ) : <p className="text-sm text-muted">{t('tao.khongCoTepPdf')}</p>}
                </TruongNhap>
              )}
              {chon && <p className="text-xs text-muted">{t('tao.goiYTepDinhKem')}</p>}
            </>
          ) : (
            <div className="grid gap-4 md:grid-cols-[minmax(0,12rem)_minmax(0,1fr)]">
              <p className="text-xs text-muted md:col-span-2">{t('tao.goiYNhapKhac')}</p>
              <TruongNhap nhan={t('tao.soHieu')}>
                <input className={LOP_O_NHAP} maxLength={100} value={soHieu} onChange={(e) => setSoHieu(e.target.value)} />
              </TruongNhap>
              <TruongNhap nhan={t('tao.trichYeu')}>
                <input className={LOP_O_NHAP} maxLength={GIOI_HAN.trichYeu} value={trichYeu} onChange={(e) => { setThongBao(''); setTrichYeu(e.target.value); }} />
              </TruongNhap>
            </div>
          )}
        </fieldset>
        </div>
        <div className="space-y-4 min-w-0">
          <TruongNhap nhan={t('tao.quyTrinh')}>
            <select className={LOP_O_NHAP} value={qtId} onChange={(e) => { setThongBao(''); setQtId(e.target.value); }}>
              <option value="">{t('tao.chonQuyTrinh')}</option>
              {dungDuoc.map((p) => (
                <option key={p.id} value={p.id}>{p.ten_quy_trinh} ({p.ma_quy_trinh} · {t(`phamVi.${p.pham_vi}`)})</option>
              ))}
            </select>
          </TruongNhap>
          {quyTrinh.duLieu && dungDuoc.length === 0 && (
            <ThongBao loai="canh_bao">
              {t('tao.khongCoQuyTrinh')}{' '}
              <Link to="/approvals/quy-trinh" className="inline-flex items-center gap-1 font-normal text-primary underline underline-offset-2 hover:text-primary-hover">
                {t('tao.diDenQuyTrinh')}
              </Link>
            </ThongBao>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <TruongNhap nhan={t('tao.hanChot')} loi={loiHanChot}>
              <input type="datetime-local" className={LOP_O_NHAP} value={hanChot} aria-invalid={loiHanChot ? true : undefined}
                onChange={(e) => {
                  setThongBao('');
                  setHanChot(e.target.value);
                  setLoiHanChot(hanChotDaQua(e.target.value) ? t('tao.loiHanChot') : '');
                }} />
            </TruongNhap>
            {nguon === 'khac' && (
              <TruongNhap nhan={t('tao.tep')} loi={loiTep}>
                <OChonTep accept="application/pdf" onChon={(f) => {
                  setThongBao('');
                  const khoaLoi = f ? kiemTraTepPdf(f) : null;
                  setLoiTep(khoaLoi ? t(khoaLoi) : '');
                  setTep(f && !khoaLoi ? f : null);
                }} />
              </TruongNhap>
            )}
          </div>
          <TruongNhap nhan={t('tao.ghiChu')} ghiChu={t('chung.toiDaKyTu', { so: GIOI_HAN.ghiChu })}>
            <textarea className={LOP_O_NHAP} rows={3} maxLength={GIOI_HAN.ghiChu} value={ghiChu} onChange={(e) => setGhiChu(e.target.value)} />
          </TruongNhap>
        </div>
      </div>
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
      <div className="flex justify-end">
        <Button icon="fa-floppy-disk" isLoading={dangGui} disabled={!coNguonTaiLieu || !qtId || Boolean(loiHanChot)} onClick={luu}>
          {t('tao.taoNhap')}
        </Button>
      </div>
    </Card>
  );
}

export function Buoc2({ hoSo, tep, quyTrinh, onQuyTrinhNgung }: {
  hoSo: HoSoChiTiet; tep: ArrayBuffer; quyTrinh: QuyTrinh; onQuyTrinhNgung?: () => void;
}) {
  const { t, loi } = useSigningT();
  const navigate = useNavigate();
  const khoa = useKhoaChongTrung();
  const [viTri, setViTri] = useState<Record<string, ViTriKy>>({});
  const [dangDat, setDangDat] = useState<string | null>(null);
  const [tongSoTrang, setTongSoTrang] = useState(1);
  const [chonNguoiKy, setChonNguoiKy] = useState<Record<string, number>>({});
  const [ungVien, setUngVien] = useState<UngVien[]>([]);
  const [xacNhan, setXacNhan] = useState(false);
  const [dangGui, setDangGui] = useState(false);
  const [thongBao, setThongBao] = useState('');
  const [tepHienTai, setTepHienTai] = useState(tep);
  const [tepMoi, setTepMoi] = useState<File | null>(null);
  const [loiTepMoi, setLoiTepMoi] = useState('');
  const [dangThayTep, setDangThayTep] = useState(false);
  const [lanChonTep, setLanChonTep] = useState(0);

  const nguoiKy = quyTrinh.cap_ky.flatMap((c) => c.nguoi_ky.map((n) => ({ ...n, cap: c })));
  const ten = (n: (typeof nguoiKy)[number]) => tenNguoiKyCauHinh(n, t);
  const khung: KhungHienThi[] = nguoiKy.filter((n) => viTri[n.id]).map((n) => ({
    id: String(n.id), ...soKhung(viTri[n.id]), nhan: ten(n), phu: t(`vaiTro.${n.vai_tro_ky}`), kieu: 'dat',
  }));

  const gui = async () => {
    if (dangThayTep) return;
    setDangGui(true);
    setThongBao('');
    try {
      await signingApi.gui(hoSo.id, khoa.lay(), chonNguoiKy, viTri);
      khoa.lamMoi();
      navigate(`/approvals/${hoSo.id}`);
    } catch (err) {
      if (docLoi(err).code === 'quy_trinh_khong_hoat_dong' && onQuyTrinhNgung) {
        onQuyTrinhNgung();
        return;
      }
      const l = docLoi(err);
      const ds = (l.fields?.nguoi_ky as Array<{ loai: string } & UngVien>) || [];
      setUngVien(ds.filter((v) => v.loai === 'can_chon_nguoi_ky'));
      setThongBao(loi(err));
      setXacNhan(false);
    } finally {
      setDangGui(false);
    }
  };

  const apDungTepMoi = async () => {
    if (!tepMoi || loiTepMoi || dangThayTep) return;
    const form = new FormData();
    form.append('tep', tepMoi);
    setDangThayTep(true);
    setThongBao('');
    try {
      const noiDung = await tepMoi.arrayBuffer();
      await signingApi.suaNhap(hoSo.id, form);
      setTepHienTai(noiDung);
      setTepMoi(null);
      setLanChonTep((n) => n + 1);
      setViTri({});
      setDangDat(null);
      setTongSoTrang(1);
      setChonNguoiKy({});
      setUngVien([]);
      setXacNhan(false);
      setThongBao(t('tao.thayTepThanhCong'));
    } catch (err) {
      setThongBao(loi(err));
    } finally {
      setDangThayTep(false);
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <Card className="p-4 space-y-3">
        <h2 className="text-lg font-bold text-main">2. {t('tao.buoc2')}</h2>
        <p className="text-sm text-secondary">{t('tao.datViTri')}</p>
        {hoSo.ho_so_goc != null && <div className="space-y-2 rounded-xl border border-border-subtle p-3">
          <TruongNhap nhan={t('tao.thayTepTrinhLai')} ghiChu={t('tao.goiYThayTepTrinhLai')} loi={loiTepMoi}>
            <OChonTep key={lanChonTep} accept="application/pdf,.pdf" nhan={t('tao.thayTepTrinhLai')} disabled={dangThayTep || dangGui}
              onChon={(f) => {
                setThongBao('');
                setTepMoi(f ?? null);
                const loiKiemTra = f ? kiemTraTepPdf(f) : null;
                setLoiTepMoi(loiKiemTra ? t(loiKiemTra) : '');
              }} />
          </TruongNhap>
          <Button size="sm" variant="secondary" icon="fa-file-arrow-up" isLoading={dangThayTep}
            disabled={!tepMoi || Boolean(loiTepMoi) || dangThayTep || dangGui} onClick={apDungTepMoi}>
            {t('tao.apDungTepMoi')}
          </Button>
        </div>}
        <XemPdf duLieu={tepHienTai} khung={khung} khungDangDat={dangDat}
          onSoTrang={(so) => setTongSoTrang(so)}
          onDat={(id, trang, x, y) => {
            setViTri((v) => ({ ...v, [id]: khungTuDiemBam(trang, x, y) }));
            setDangDat(null);
          }}
          onKeo={(id, x, y) => setViTri((v) => ({ ...v, [id]: { ...v[id], toa_do_x: String(x), toa_do_y: String(y) } }))} />
      </Card>
      <Card className="p-4 space-y-3 self-start lg:sticky lg:top-4">
        <h3 className="text-lg font-bold text-main">{t('tao.nguoiKyDuKien')}</h3>
        <ul className="space-y-2">
          {nguoiKy.map((n) => (
            <li key={n.id} className="rounded-lg border border-border-subtle p-2 text-sm space-y-1">
              <div className="font-semibold text-main">{n.cap.cap_ky}. {n.cap.ten_cap_ky}</div>
              <div className="text-secondary">{ten(n)} · {t(`vaiTro.${n.vai_tro_ky}`)}</div>
              <div className="text-xs text-muted">
                {viTri[n.id] ? t('tao.trang', { so: viTri[n.id].trang_ky }) : t('tao.chuaDatViTri')}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant={dangDat === String(n.id) ? 'primary' : 'secondary'} icon="fa-crosshairs"
                  onClick={() => setDangDat(dangDat === String(n.id) ? null : String(n.id))}>{t('tao.datKhung')}</Button>
                <Button size="sm" variant="secondary" icon="fa-file-lines"
                  onClick={() => {
                    setViTri((v) => ({
                      ...v,
                      [n.id]: {
                        trang_ky: tongSoTrang,
                        toa_do_x: '60',
                        toa_do_y: '75',
                        chieu_rong_khung: String(KHUNG_MAC_DINH.w),
                        chieu_cao_khung: String(KHUNG_MAC_DINH.h),
                      },
                    }));
                    setDangDat(null);
                  }}>{t('tao.datTrangCuoi')}</Button>
                {viTri[n.id] && (
                  <Button size="sm" variant="ghost" icon="fa-trash"
                    onClick={() => setViTri((v) => {
                      const con = { ...v };
                      delete con[n.id];
                      return con;
                    })}>{t('tao.boKhung')}</Button>
                )}
              </div>
              {ungVien.filter((u) => u.cau_hinh === n.id).map((u) => (
                <TruongNhap key={u.cau_hinh} nhan={t('tao.chonNguoiKy')}>
                  <select className={LOP_O_NHAP} value={chonNguoiKy[n.id] || ''}
                    onChange={(e) => setChonNguoiKy((c) => ({ ...c, [n.id]: Number(e.target.value) }))}>
                    <option value="">—</option>
                    {u.ung_vien.map((v) => <option key={v.id} value={v.id}>{v.ten}</option>)}
                  </select>
                </TruongNhap>
              ))}
            </li>
          ))}
        </ul>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
        <Button className="w-full" icon="fa-paper-plane" onClick={() => setXacNhan(true)}>{t('tao.gui')}</Button>
      </Card>
      <HopThoai moTieuDe={t('tao.gui')} mo={xacNhan} onDong={() => setXacNhan(false)} dangXuLy={dangGui}
        chanDuoi={<>
          <Button variant="secondary" onClick={() => setXacNhan(false)}>{t('chung.huyBo')}</Button>
          <Button icon="fa-paper-plane" isLoading={dangGui} onClick={gui}>{t('chung.xacNhan')}</Button>
        </>}>
        <p className="text-sm text-main">{t('tao.xacNhanGui')}</p>
      </HopThoai>
    </div>
  );
}

export default function TaoHoSoPage() {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const nhapId = Number(params.get('ho_so')) || null;
  const [hoSo, setHoSo] = useState<HoSoChiTiet | null>(null);
  const [tep, setTep] = useState<ArrayBuffer | null>(null);
  const [quyTrinh, setQuyTrinh] = useState<QuyTrinh | null>(null);
  const [quyTrinhMoi, setQuyTrinhMoi] = useState<QuyTrinh | null>(null);
  const [dangChuyenQuyTrinh, setDangChuyenQuyTrinh] = useState(false);
  const [loiChuyenQuyTrinh, setLoiChuyenQuyTrinh] = useState<unknown>(null);
  const [loiTai, setLoiTai] = useState<unknown>(null);

  const [lanThu, setLanThu] = useState(0);
  const [lanTaiQuyTrinh, setLanTaiQuyTrinh] = useState(0);

  useEffect(() => {
    if (!nhapId) return undefined;
    let huy = false;
    Promise.all([signingApi.chiTiet(nhapId), signingApi.tepGoc(nhapId)])
      .then(async ([ct, blob]) => {
        const buf = await blob.arrayBuffer();
        if (huy) return;
        setHoSo(ct);
        setTep(buf);
      })
      .catch((err) => !huy && setLoiTai(err));
    return () => {
      huy = true;
    };
  }, [nhapId, lanThu]);

  useEffect(() => {
    if (!hoSo || tep) return undefined;
    let huy = false;
    signingApi.tepGoc(hoSo.id).then((blob) => blob.arrayBuffer()).then((buf) => {
      if (!huy) setTep(buf);
    }).catch((err) => { if (!huy) setLoiTai(err); });
    return () => { huy = true; };
  }, [hoSo, tep, lanThu]);

  useEffect(() => {
    if (!hoSo) return;
    let huy = false;
    signingApi.quyTrinh('HOAT_DONG').then((ds) => {
      if (huy) return;
      const p = ds.find((q) => q.id === hoSo.quy_trinh);
      if (p) {
        setQuyTrinh(p);
        setQuyTrinhMoi(null);
        return;
      }
      const moi = ds.find((q) => q.ma_quy_trinh === hoSo.ma_quy_trinh
        && q.phien_ban > hoSo.phien_ban_quy_trinh);
      if (moi) {
        setQuyTrinh(null);
        setQuyTrinhMoi(moi);
      } else setLoiTai(new Error('quy_trinh_khong_hoat_dong'));
    }).catch((err) => { if (!huy) setLoiTai(err); });
    return () => { huy = true; };
  }, [hoSo, lanTaiQuyTrinh]);

  const taiLaiQuyTrinh = () => {
    setQuyTrinh(null);
    setQuyTrinhMoi(null);
    setLoiTai(null);
    setLanTaiQuyTrinh((n) => n + 1);
  };

  const chuyenSangQuyTrinhMoi = async () => {
    if (!hoSo || !quyTrinhMoi || dangChuyenQuyTrinh) return;
    const form = new FormData();
    form.append('quy_trinh', String(quyTrinhMoi.id));
    setDangChuyenQuyTrinh(true);
    setLoiChuyenQuyTrinh(null);
    try {
      const moi = await signingApi.suaNhap(hoSo.id, form);
      setHoSo(moi);
      setQuyTrinh(quyTrinhMoi);
      setQuyTrinhMoi(null);
    } catch (err) {
      setLoiChuyenQuyTrinh(err);
    } finally {
      setDangChuyenQuyTrinh(false);
    }
  };

  // Vào thẳng đường dẫn khi chưa có quyền tạo: báo ngay thay vì để điền form rồi mới bị từ chối
  if (!coQuyen(toi, 'add_trinhky')) return <ThongBao loai="canh_bao">{t('tao.khongCoQuyen')}</ThongBao>;
  if (loiTai) {
    return <LoiTai thongBao={loi(loiTai)} onThuLai={nhapId || hoSo
      ? () => { setLoiTai(null); setLanThu((n) => n + 1); }
      : undefined} />;
  }
  if (!hoSo) {
    return nhapId ? <DangTai /> : <Buoc1 onXong={(h, b) => { setHoSo(h); setTep(b); }} />;
  }
  if (quyTrinhMoi) return (
    <Card className="p-5 space-y-4">
      <h2 className="text-lg font-bold text-main">{t('tao.quyTrinhCapNhat')}</h2>
      <ThongBao loai="canh_bao">{t('tao.goiYChuyenQuyTrinh', {
        tenCu: hoSo.ten_quy_trinh, cu: hoSo.phien_ban_quy_trinh,
        tenMoi: quyTrinhMoi.ten_quy_trinh, moi: quyTrinhMoi.phien_ban,
      })}</ThongBao>
      {loiChuyenQuyTrinh != null && <ThongBao>{loi(loiChuyenQuyTrinh)}</ThongBao>}
      <div className="flex justify-end gap-2">
        <Button variant="secondary" disabled={dangChuyenQuyTrinh} onClick={() => navigate(`/approvals/${hoSo.id}`)}>
          {t('tao.quayLaiHoSo')}
        </Button>
        <Button icon="fa-arrows-rotate" isLoading={dangChuyenQuyTrinh} disabled={dangChuyenQuyTrinh}
          onClick={chuyenSangQuyTrinhMoi}>
          {t('tao.xacNhanChuyenQuyTrinh', { moi: quyTrinhMoi.phien_ban })}
        </Button>
      </div>
    </Card>
  );
  if (!tep || !quyTrinh) return <DangTai />;
  return <Buoc2 hoSo={hoSo} tep={tep} quyTrinh={quyTrinh} onQuyTrinhNgung={taiLaiQuyTrinh} />;
}
