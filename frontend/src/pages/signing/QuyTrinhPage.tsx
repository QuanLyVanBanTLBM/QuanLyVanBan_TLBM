/**
 * Cấu hình quy trình ký (#80 mục A, E): quy trình CONG_TY do quản trị, PHONG_BAN do lãnh đạo đơn vị áp dụng.
 * Người ký cấu hình theo tài khoản; cấu hình theo chức vụ chờ danh mục chức vụ của Nhóm 7 lên staging.
 */
import { useState } from 'react';
import { Badge, Button, Card } from '@components/common';
import { DangTai, HopThoai, LoiTai, Rong, ThongBao, TrangThaiBadge, TruongNhap } from '@components/signing/ChungUI';
import { signingApi } from '@lib/signing/api';
import { LOP_O_NHAP } from '@lib/signing/dinhDang';
import { coQuyen, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { NguoiDungTim, PhamViQuyTrinh, QuyTrinh, VaiTroKy } from '@lib/signing/types';

interface NguoiKyNhap { nguoi: NguoiDungTim; vai_tro_ky: VaiTroKy; chan_ky_chinh: boolean }
interface CapNhap { ten_cap_ky: string; so_gio_xu_ly: string; nguoi_ky: NguoiKyNhap[] }

function ChonNguoiDung({ onChon }: { onChon: (u: NguoiDungTim) => void }) {
  const { t } = useSigningT();
  const [q, setQ] = useState('');
  const ds = useTai(() => (q.trim().length >= 2 ? signingApi.timNguoiDung(q) : Promise.resolve([])), [q]);
  return (
    <div className="space-y-1">
      <input className={LOP_O_NHAP} placeholder={t('quyTrinh.timNguoiDung')} value={q} onChange={(e) => setQ(e.target.value)} />
      {!!ds.duLieu?.length && (
        <div className="max-h-32 overflow-y-auto rounded-lg border border-border-subtle">
          {ds.duLieu.map((u) => (
            <button type="button" key={u.id} className="block w-full px-3 py-1.5 text-left text-sm hover:bg-surface-hover text-main"
              onClick={() => { onChon(u); setQ(''); }}>
              {u.ten} <span className="text-muted">({u.ten_dang_nhap}{u.chuc_vu ? ` · ${u.chuc_vu}` : ''})</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function FormTao({ mo, onDong, onXong }: { mo: boolean; onDong: () => void; onXong: () => void }) {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const [ma, setMa] = useState('');
  const [ten, setTen] = useState('');
  const [phamVi, setPhamVi] = useState<PhamViQuyTrinh>(toi?.la_quan_tri ? 'CONG_TY' : 'PHONG_BAN');
  const [donVi, setDonVi] = useState(toi?.don_vi_id ? String(toi.don_vi_id) : '');
  const [cap, setCap] = useState<CapNhap[]>([{ ten_cap_ky: '', so_gio_xu_ly: '', nguoi_ky: [] }]);
  const [dangLuu, setDangLuu] = useState(false);
  const [thongBao, setThongBao] = useState('');

  const sua = (i: number, gia_tri: Partial<CapNhap>) => setCap((c) => c.map((x, j) => (j === i ? { ...x, ...gia_tri } : x)));
  const hopLe = ma.trim() && ten.trim() && (phamVi === 'CONG_TY' || donVi)
    && cap.every((c) => c.ten_cap_ky.trim() && c.nguoi_ky.length);

  const luu = async () => {
    setDangLuu(true);
    setThongBao('');
    try {
      await signingApi.taoQuyTrinh({
        ma_quy_trinh: ma.trim(), ten_quy_trinh: ten.trim(), pham_vi: phamVi,
        don_vi_ap_dung_id: phamVi === 'PHONG_BAN' ? Number(donVi) : null,
        cap_ky: cap.map((c, i) => ({
          cap_ky: i + 1, thu_tu: i + 1, ten_cap_ky: c.ten_cap_ky.trim(),
          so_gio_xu_ly: c.so_gio_xu_ly ? Number(c.so_gio_xu_ly) : null,
          nguoi_ky: c.nguoi_ky.map((n, j) => ({
            nguoi_ky: n.nguoi.id, thu_tu: j + 1, vai_tro_ky: n.vai_tro_ky, chan_ky_chinh: n.chan_ky_chinh,
          })),
        })),
      });
      onXong();
    } catch (err) {
      setThongBao(loi(err));
    } finally {
      setDangLuu(false);
    }
  };

  return (
    <HopThoai moTieuDe={t('quyTrinh.tao')} mo={mo} onDong={onDong}
      chanDuoi={<>
        <Button variant="secondary" onClick={onDong}>{t('chung.huyBo')}</Button>
        <Button icon="fa-floppy-disk" isLoading={dangLuu} disabled={!hopLe} onClick={luu}>{t('chung.luu')}</Button>
      </>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <TruongNhap nhan={t('quyTrinh.ma')}><input className={LOP_O_NHAP} maxLength={50} value={ma} onChange={(e) => setMa(e.target.value)} /></TruongNhap>
        <TruongNhap nhan={t('quyTrinh.ten')}><input className={LOP_O_NHAP} value={ten} onChange={(e) => setTen(e.target.value)} /></TruongNhap>
        <TruongNhap nhan={t('quyTrinh.phamVi')}>
          <select className={LOP_O_NHAP} value={phamVi} onChange={(e) => setPhamVi(e.target.value as PhamViQuyTrinh)}>
            <option value="CONG_TY">{t('phamVi.CONG_TY')}</option>
            <option value="PHONG_BAN">{t('phamVi.PHONG_BAN')}</option>
          </select>
        </TruongNhap>
        {phamVi === 'PHONG_BAN' && (
          <TruongNhap nhan={t('quyTrinh.donVi')}>
            <input className={LOP_O_NHAP} inputMode="numeric" value={donVi} onChange={(e) => setDonVi(e.target.value.replace(/\D/g, ''))} />
          </TruongNhap>
        )}
      </div>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        <div className="text-xs font-bold text-secondary">{t('quyTrinh.capKy')}</div>
        {cap.map((c, i) => (
          <div key={i} className="space-y-2 rounded-lg border border-border-subtle p-2">
            <div className="flex gap-2">
              <span className="pt-2 text-sm font-bold text-main">{i + 1}.</span>
              <input className={LOP_O_NHAP} placeholder={t('quyTrinh.ten')} value={c.ten_cap_ky}
                onChange={(e) => sua(i, { ten_cap_ky: e.target.value })} />
              <input className={`${LOP_O_NHAP} w-32`} inputMode="numeric" placeholder={t('quyTrinh.soGio')} value={c.so_gio_xu_ly}
                onChange={(e) => sua(i, { so_gio_xu_ly: e.target.value.replace(/\D/g, '') })} />
            </div>
            {c.nguoi_ky.map((n, j) => (
              <div key={n.nguoi.id} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-main">{n.nguoi.ten}</span>
                <select className={`${LOP_O_NHAP} w-auto`} value={n.vai_tro_ky}
                  onChange={(e) => sua(i, { nguoi_ky: c.nguoi_ky.map((x, k) => (k === j ? { ...x, vai_tro_ky: e.target.value as VaiTroKy } : x)) })}>
                  <option value="KY_CHINH">{t('vaiTro.KY_CHINH')}</option>
                  <option value="KY_NHAY">{t('vaiTro.KY_NHAY')}</option>
                </select>
                {n.vai_tro_ky === 'KY_NHAY' && (
                  <label className="flex items-center gap-1 text-xs text-secondary">
                    <input type="checkbox" checked={n.chan_ky_chinh}
                      onChange={(e) => sua(i, { nguoi_ky: c.nguoi_ky.map((x, k) => (k === j ? { ...x, chan_ky_chinh: e.target.checked } : x)) })} />
                    {t('quyTrinh.chanKyChinh')}
                  </label>
                )}
                <button type="button" className="text-danger" aria-label={t('quyTrinh.boNguoiKy')}
                  onClick={() => sua(i, { nguoi_ky: c.nguoi_ky.filter((_, k) => k !== j) })}>
                  <i className="fa-solid fa-trash" aria-hidden="true" />
                </button>
              </div>
            ))}
            <ChonNguoiDung onChon={(u) => !c.nguoi_ky.some((n) => n.nguoi.id === u.id)
              && sua(i, { nguoi_ky: [...c.nguoi_ky, { nguoi: u, vai_tro_ky: 'KY_CHINH', chan_ky_chinh: true }] })} />
          </div>
        ))}
        <Button size="sm" variant="ghost" icon="fa-plus"
          onClick={() => setCap((c) => [...c, { ten_cap_ky: '', so_gio_xu_ly: '', nguoi_ky: [] }])}>{t('quyTrinh.themCap')}</Button>
      </div>
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
    </HopThoai>
  );
}

export default function QuyTrinhPage() {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const ds = useTai(() => signingApi.quyTrinh());
  const [taoMo, setTaoMo] = useState(false);
  const [thongBao, setThongBao] = useState('');
  const quanLy = coQuyen(toi, 'manage_signing_process');

  const thaoTac = async (q: QuyTrinh, loai: 'kich-hoat' | 'ngung' | 'nhan-ban') => {
    setThongBao('');
    try {
      await signingApi.thaoTacQuyTrinh(q.id, loai);
      ds.tai();
    } catch (err) {
      setThongBao(loi(err));
    }
  };

  return (
    <div className="space-y-3">
      {quanLy ? (
        <div className="flex justify-end">
          <Button icon="fa-plus" onClick={() => setTaoMo(true)}>{t('quyTrinh.tao')}</Button>
        </div>
      ) : <ThongBao loai="thong_tin">{t('quyTrinh.chiQuanLy')}</ThongBao>}
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
      {ds.dangTai && <DangTai />}
      {ds.loi && <LoiTai thongBao={loi(ds.loi)} onThuLai={ds.tai} />}
      {ds.duLieu?.length === 0 && <Rong icon="fa-diagram-project">{t('quyTrinh.rong')}</Rong>}
      <div className="grid gap-3 md:grid-cols-2">
        {ds.duLieu?.map((q) => (
          <Card key={q.id} className="p-4 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-main">{q.ten_quy_trinh}</span>
              <TrangThaiBadge trangThai={q.trang_thai} />
              <Badge variant="info" size="sm">{t(`phamVi.${q.pham_vi}`)}{q.don_vi_ap_dung_id ? ` #${q.don_vi_ap_dung_id}` : ''}</Badge>
            </div>
            <div className="text-xs text-secondary">{q.ma_quy_trinh} · {t('quyTrinh.phienBan', { so: q.phien_ban })}</div>
            <ol className="space-y-1 text-sm">
              {q.cap_ky.map((c) => (
                <li key={c.id} className="text-main">
                  {c.cap_ky}. {c.ten_cap_ky}:{' '}
                  <span className="text-secondary">
                    {c.nguoi_ky.map((n) => `${n.ten_nguoi_ky || t('tao.theoChucVu')} (${t(`vaiTro.${n.vai_tro_ky}`)})`).join(', ')}
                  </span>
                </li>
              ))}
            </ol>
            {quanLy && (
              <div className="flex flex-wrap gap-2">
                {q.trang_thai === 'NHAP' && <Button size="sm" icon="fa-play" onClick={() => thaoTac(q, 'kich-hoat')}>{t('quyTrinh.kichHoat')}</Button>}
                {q.trang_thai === 'HOAT_DONG' && <Button size="sm" variant="secondary" icon="fa-stop" onClick={() => thaoTac(q, 'ngung')}>{t('quyTrinh.ngung')}</Button>}
                <Button size="sm" variant="ghost" icon="fa-copy" onClick={() => thaoTac(q, 'nhan-ban')}>{t('quyTrinh.nhanBan')}</Button>
              </div>
            )}
          </Card>
        ))}
      </div>
      {taoMo && <FormTao mo={taoMo} onDong={() => setTaoMo(false)} onXong={() => { setTaoMo(false); ds.tai(); }} />}
    </div>
  );
}
