/**
 * Tạo hồ sơ trình ký (#80 mục E): (1) chọn văn bản đi, quy trình, mức độ, tệp PDF → lưu nháp;
 * (2) xem trước người ký và tài liệu, đặt vị trí ký, chọn người ký khi chức vụ nhiều ứng viên → gửi.
 * Mở lại nháp: /approvals/tao-moi?ho_so=<id>.
 */
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Card } from '@components/common';
import { DangTai, HopThoai, LoiTai, ThongBao, TruongNhap } from '@components/signing/ChungUI';
import XemPdf, { type KhungHienThi } from '@components/signing/XemPdf';
import { docLoi, signingApi } from '@lib/signing/api';
import { LOP_O_NHAP, moTaVanBan } from '@lib/signing/dinhDang';
import { useKhoaChongTrung, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { HoSoChiTiet, MucDo, QuyTrinh, VanBanDi, ViTriKy } from '@lib/signing/types';
import { khungTuDiemBam, soKhung } from '@lib/signing/viTri';

interface UngVien { cau_hinh: number; ung_vien: Array<{ id: number; ten: string }> }

function Buoc1({ onXong }: { onXong: (ho_so: HoSoChiTiet, tep: ArrayBuffer) => void }) {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const [q, setQ] = useState('');
  const vanBan = useTai(() => signingApi.timVanBanDi(q), [q]);
  const quyTrinh = useTai(() => signingApi.quyTrinh('HOAT_DONG'));
  const [chon, setChon] = useState<VanBanDi | null>(null);
  const [qtId, setQtId] = useState('');
  const [mucDo, setMucDo] = useState<MucDo>('THUONG');
  const [hanChot, setHanChot] = useState('');
  const [ghiChu, setGhiChu] = useState('');
  const [tep, setTep] = useState<File | null>(null);
  const [dangGui, setDangGui] = useState(false);
  const [thongBao, setThongBao] = useState('');

  // Người tạo chỉ chọn quy trình công ty hoặc quy trình phòng ban của đơn vị mình (server kiểm lại)
  const dungDuoc = (quyTrinh.duLieu || []).filter(
    (p) => p.pham_vi === 'CONG_TY' || (p.don_vi_ap_dung_id != null && p.don_vi_ap_dung_id === toi?.don_vi_id));

  const luu = async () => {
    if (!chon || !qtId || !tep) return;
    setDangGui(true);
    setThongBao('');
    try {
      const form = new FormData();
      form.append('document_type', 'vanbandi');
      form.append('van_ban_id', String(chon.id));
      form.append('quy_trinh', qtId);
      form.append('muc_do', mucDo);
      if (hanChot) form.append('han_chot', new Date(hanChot).toISOString());
      if (ghiChu) form.append('ghi_chu', ghiChu);
      form.append('tep', tep);
      const ho_so = await signingApi.taoNhap(form);
      onXong(ho_so, await tep.arrayBuffer());
    } catch (err) {
      setThongBao(loi(err));
    } finally {
      setDangGui(false);
    }
  };

  return (
    <Card className="p-5 space-y-4">
      <h2 className="font-bold text-main">1. {t('tao.buoc1')}</h2>
      <TruongNhap nhan={t('tao.vanBanDi')}>
        <input className={LOP_O_NHAP} placeholder={t('tao.timVanBan')} value={q} onChange={(e) => setQ(e.target.value)} />
      </TruongNhap>
      {vanBan.dangTai ? <DangTai /> : vanBan.loi ? <LoiTai thongBao={loi(vanBan.loi)} onThuLai={vanBan.tai} /> : (
        <div className="max-h-48 overflow-y-auto rounded-lg border border-border-subtle">
          {vanBan.duLieu?.length === 0 && <div className="p-3 text-sm text-muted">{t('tao.khongCoVanBan')}</div>}
          {vanBan.duLieu?.map((vb) => (
            <button type="button" key={vb.id} onClick={() => setChon(vb)}
              className={`block w-full px-3 py-2 text-left text-sm border-b border-border-subtle last:border-0 ${
                chon?.id === vb.id ? 'bg-primary-subtle text-primary font-semibold' : 'hover:bg-surface-hover text-main'}`}>
              {moTaVanBan(vb, vb.id)}
            </button>
          ))}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <TruongNhap nhan={t('tao.quyTrinh')}>
          <select className={LOP_O_NHAP} value={qtId} onChange={(e) => setQtId(e.target.value)}>
            <option value="">{t('tao.chonQuyTrinh')}</option>
            {dungDuoc.map((p) => (
              <option key={p.id} value={p.id}>{p.ten_quy_trinh} ({p.ma_quy_trinh} · {t(`phamVi.${p.pham_vi}`)})</option>
            ))}
          </select>
        </TruongNhap>
        <TruongNhap nhan={t('tao.mucDo')}>
          <select className={LOP_O_NHAP} value={mucDo} onChange={(e) => setMucDo(e.target.value as MucDo)}>
            {(['THUONG', 'KHAN', 'HOA_TOC'] as MucDo[]).map((m) => <option key={m} value={m}>{t(`mucDo.${m}`)}</option>)}
          </select>
        </TruongNhap>
        <TruongNhap nhan={t('tao.hanChot')}>
          <input type="datetime-local" className={LOP_O_NHAP} value={hanChot} onChange={(e) => setHanChot(e.target.value)} />
        </TruongNhap>
        <TruongNhap nhan={t('tao.tep')}>
          <input type="file" accept="application/pdf" className={LOP_O_NHAP}
            onChange={(e) => setTep(e.target.files?.[0] || null)} />
        </TruongNhap>
      </div>
      {quyTrinh.duLieu && dungDuoc.length === 0 && <ThongBao loai="canh_bao">{t('tao.khongCoQuyTrinh')}</ThongBao>}
      <TruongNhap nhan={t('tao.ghiChu')}>
        <textarea className={LOP_O_NHAP} rows={2} value={ghiChu} onChange={(e) => setGhiChu(e.target.value)} />
      </TruongNhap>
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
      <div className="flex justify-end">
        <Button icon="fa-floppy-disk" isLoading={dangGui} disabled={!chon || !qtId || !tep} onClick={luu}>
          {t('tao.taoNhap')}
        </Button>
      </div>
    </Card>
  );
}

function Buoc2({ hoSo, tep, quyTrinh }: { hoSo: HoSoChiTiet; tep: ArrayBuffer; quyTrinh: QuyTrinh }) {
  const { t, loi } = useSigningT();
  const navigate = useNavigate();
  const khoa = useKhoaChongTrung();
  const [viTri, setViTri] = useState<Record<string, ViTriKy>>({});
  const [dangDat, setDangDat] = useState<string | null>(null);
  const [chonNguoiKy, setChonNguoiKy] = useState<Record<string, number>>({});
  const [ungVien, setUngVien] = useState<UngVien[]>([]);
  const [xacNhan, setXacNhan] = useState(false);
  const [dangGui, setDangGui] = useState(false);
  const [thongBao, setThongBao] = useState('');

  const nguoiKy = quyTrinh.cap_ky.flatMap((c) => c.nguoi_ky.map((n) => ({ ...n, cap: c })));
  const ten = (n: (typeof nguoiKy)[number]) => n.ten_nguoi_ky || t('tao.theoChucVu');
  const khung: KhungHienThi[] = nguoiKy.filter((n) => viTri[n.id]).map((n) => ({
    id: String(n.id), ...soKhung(viTri[n.id]), nhan: ten(n), phu: t(`vaiTro.${n.vai_tro_ky}`), kieu: 'dat',
  }));

  const gui = async () => {
    setDangGui(true);
    setThongBao('');
    try {
      await signingApi.gui(hoSo.id, khoa.lay(), chonNguoiKy, viTri);
      khoa.lamMoi();
      navigate(`/approvals/${hoSo.id}`);
    } catch (err) {
      const l = docLoi(err);
      const ds = (l.fields?.nguoi_ky as Array<{ loai: string } & UngVien>) || [];
      setUngVien(ds.filter((v) => v.loai === 'can_chon_nguoi_ky'));
      setThongBao(loi(err));
      setXacNhan(false);
    } finally {
      setDangGui(false);
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <Card className="p-4 space-y-3">
        <h2 className="font-bold text-main">2. {t('tao.buoc2')}</h2>
        <p className="text-xs text-secondary">{t('tao.datViTri')}</p>
        <XemPdf duLieu={tep} khung={khung} khungDangDat={dangDat}
          onDat={(id, trang, x, y) => {
            setViTri((v) => ({ ...v, [id]: khungTuDiemBam(trang, x, y) }));
            setDangDat(null);
          }}
          onKeo={(id, x, y) => setViTri((v) => ({ ...v, [id]: { ...v[id], toa_do_x: String(x), toa_do_y: String(y) } }))} />
      </Card>
      <Card className="p-4 space-y-3 self-start lg:sticky lg:top-4">
        <div className="text-xs text-secondary break-all">{t('tao.maBam')}: <code>{hoSo.ma_bam_tai_lieu}</code></div>
        <h3 className="font-bold text-sm text-main">{t('tao.nguoiKyDuKien')}</h3>
        <ul className="space-y-2">
          {nguoiKy.map((n) => (
            <li key={n.id} className="rounded-lg border border-border-subtle p-2 text-sm space-y-1">
              <div className="font-semibold text-main">{n.cap.cap_ky}. {n.cap.ten_cap_ky}</div>
              <div className="text-secondary">{ten(n)} · {t(`vaiTro.${n.vai_tro_ky}`)}</div>
              <div className="text-xs text-muted">
                {viTri[n.id] ? t('tao.trang', { so: viTri[n.id].trang_ky }) : t('tao.chuaDatViTri')}
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant={dangDat === String(n.id) ? 'primary' : 'secondary'} icon="fa-crosshairs"
                  onClick={() => setDangDat(dangDat === String(n.id) ? null : String(n.id))}>{t('tao.datKhung')}</Button>
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
      <HopThoai moTieuDe={t('tao.gui')} mo={xacNhan} onDong={() => setXacNhan(false)}
        chanDuoi={<>
          <Button variant="secondary" onClick={() => setXacNhan(false)}>{t('chung.huyBo')}</Button>
          <Button icon="fa-paper-plane" isLoading={dangGui} onClick={gui}>{t('chung.xacNhan')}</Button>
        </>}>
        <p className="text-sm text-main">{t('tao.xacNhanGui')}</p>
        <p className="text-xs text-secondary break-all">{t('tao.maBam')}: <code>{hoSo.ma_bam_tai_lieu}</code></p>
      </HopThoai>
    </div>
  );
}

export default function TaoHoSoPage() {
  const { loi } = useSigningT();
  const [params] = useSearchParams();
  const nhapId = Number(params.get('ho_so')) || null;
  const [hoSo, setHoSo] = useState<HoSoChiTiet | null>(null);
  const [tep, setTep] = useState<ArrayBuffer | null>(null);
  const [quyTrinh, setQuyTrinh] = useState<QuyTrinh | null>(null);
  const [loiTai, setLoiTai] = useState<unknown>(null);

  const [lanThu, setLanThu] = useState(0);

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
    if (!hoSo) return;
    signingApi.quyTrinh().then((ds) => {
      const p = ds.find((q) => q.id === hoSo.quy_trinh);
      if (p) setQuyTrinh(p);
      else setLoiTai(new Error('quy_trinh_khong_hoat_dong'));
    }).catch(setLoiTai);
  }, [hoSo]);

  if (loiTai) {
    return <LoiTai thongBao={loi(loiTai)} onThuLai={nhapId ? () => { setLoiTai(null); setLanThu((n) => n + 1); } : undefined} />;
  }
  if (!hoSo) {
    return nhapId ? <DangTai /> : <Buoc1 onXong={(h, b) => { setHoSo(h); setTep(b); }} />;
  }
  if (!tep || !quyTrinh) return <DangTai />;
  return <Buoc2 hoSo={hoSo} tep={tep} quyTrinh={quyTrinh} />;
}
