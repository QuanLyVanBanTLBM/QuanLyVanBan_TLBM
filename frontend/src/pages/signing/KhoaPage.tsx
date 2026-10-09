/**
 * Khóa ký và PIN cá nhân theo contract #79 (#80 mục E): tạo khóa trên thiết bị (proof-of-possession, đặt PIN,
 * kích hoạt hoặc xoay vòng khóa của thiết bị cũ), đổi PIN, thu hồi. PIN và private key không rời trình duyệt.
 */
import { useEffect, useState } from 'react';
import { Button, Card } from '@components/common';
import { DangTai, LoiTai, ThongBao, TrangThaiBadge, TruongNhap } from '@components/signing/ChungUI';
import { signingApi } from '@lib/signing/api';
import { LOP_O_NHAP } from '@lib/signing/dinhDang';
import { useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import { hoTroEd25519, kiemTraPin, layBanBoc } from '@lib/signing/khoaKy';
import { dangKyKhoaThietBi, doiPin, khoaHoatDong } from '@lib/signing/luongKhoa';

function OPin({ nhan, gia_tri, onDoi }: { nhan: string; gia_tri: string; onDoi: (v: string) => void }) {
  return (
    <TruongNhap nhan={nhan}>
      <input className={LOP_O_NHAP} type="password" inputMode="numeric" autoComplete="new-password" maxLength={8}
        value={gia_tri} onChange={(e) => onDoi(e.target.value.replace(/\D/g, ''))} />
    </TruongNhap>
  );
}

export default function KhoaPage() {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const ds = useTai(() => signingApi.khoa());
  const [hoTro, setHoTro] = useState<boolean | null>(null);
  const [banBoc, setBanBoc] = useState<{ keyId: number; co: boolean } | null>(null);
  const [pin, setPin] = useState('');
  const [pin2, setPin2] = useState('');
  const [pinCu, setPinCu] = useState('');
  const [lyDo, setLyDo] = useState('');
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: 'loi' | 'thanh_cong'; noi_dung: string } | null>(null);
  const hoatDong = khoaHoatDong(ds.duLieu || []);

  useEffect(() => {
    hoTroEd25519().then(setHoTro);
  }, []);
  // Thiết bị này có giữ bản bọc của khóa đang hoạt động không (gắn với id khóa)
  const hoatDongId = hoatDong?.id ?? null;
  const coBanBoc = hoatDongId == null ? false : banBoc?.keyId === hoatDongId ? banBoc.co : null;
  useEffect(() => {
    if (hoatDongId == null || !toi) return;
    layBanBoc(toi.id, hoatDongId).then((b) => setBanBoc({ keyId: hoatDongId, co: Boolean(b) }))
      .catch(() => setBanBoc({ keyId: hoatDongId, co: false }));
  }, [hoatDongId, toi]);

  const loiPin = pin ? kiemTraPin(pin) : null;
  const pinHopLe = !loiPin && pin.length === 8 && pin === pin2;

  const lam = async (ham: () => Promise<unknown>) => {
    setDangLam(true);
    setThongBao(null);
    try {
      await ham();
      setPin('');
      setPin2('');
      setPinCu('');
      setLyDo('');
      setThongBao({ loai: 'thanh_cong', noi_dung: t('hanhDong.thanhCong') });
      ds.tai();
    } catch (err) {
      setThongBao({ loai: 'loi', noi_dung: loi(err) });
    } finally {
      setDangLam(false);
    }
  };

  if (ds.dangTai && !ds.duLieu) return <DangTai />;
  if (ds.loi) return <LoiTai thongBao={loi(ds.loi)} onThuLai={ds.tai} />;
  if (hoTro === false) return <ThongBao>{t('khoa.khongHoTro')}</ThongBao>;

  const sanSang = hoatDong && coBanBoc;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="p-4 space-y-3">
        <p className="text-sm text-secondary">{t('khoa.gioiThieu')}</p>
        {sanSang ? <ThongBao loai="thanh_cong">{t('khoa.sanSang')}</ThongBao>
          : hoatDong ? <ThongBao loai="canh_bao">{t('khoa.khacThietBi')}</ThongBao>
            : <ThongBao loai="thong_tin">{t('khoa.chuaCo')}</ThongBao>}
        {!sanSang && (
          <div className="space-y-3">
            <OPin nhan={t('khoa.pin')} gia_tri={pin} onDoi={setPin} />
            <OPin nhan={t('khoa.pinNhapLai')} gia_tri={pin2} onDoi={setPin2} />
            {loiPin && <ThongBao loai="canh_bao">{t(`loi.${loiPin}`)}</ThongBao>}
            {pin2 && pin !== pin2 && <ThongBao loai="canh_bao">{t('khoa.pinKhongKhop')}</ThongBao>}
            {dangLam && <ThongBao loai="thong_tin">{t('khoa.dangTao')}</ThongBao>}
            <Button icon="fa-key" isLoading={dangLam} disabled={!pinHopLe}
              onClick={() => lam(() => dangKyKhoaThietBi(toi.id, pin, ds.duLieu || []))}>{t('khoa.taoKhoa')}</Button>
          </div>
        )}
        {sanSang && (
          <div className="space-y-3 border-t border-border-subtle pt-3">
            <h3 className="text-sm font-bold text-main">{t('khoa.doiPin')}</h3>
            <OPin nhan={t('khoa.pinCu')} gia_tri={pinCu} onDoi={setPinCu} />
            <OPin nhan={t('khoa.pin')} gia_tri={pin} onDoi={setPin} />
            <OPin nhan={t('khoa.pinNhapLai')} gia_tri={pin2} onDoi={setPin2} />
            {loiPin && <ThongBao loai="canh_bao">{t(`loi.${loiPin}`)}</ThongBao>}
            <Button variant="secondary" icon="fa-rotate" isLoading={dangLam} disabled={!pinHopLe || pinCu.length !== 8}
              onClick={() => lam(() => doiPin(toi.id, hoatDong, pinCu, pin))}>{t('khoa.doiPin')}</Button>
          </div>
        )}
        {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.noi_dung}</ThongBao>}
      </Card>
      <Card className="p-4 space-y-3">
        {(ds.duLieu || []).map((k) => (
          <div key={k.id} className="space-y-1 rounded-lg border border-border-subtle p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold text-main">{k.ma_khoa}</span>
              <TrangThaiBadge trangThai={k.trang_thai} />
            </div>
            <div className="text-xs text-secondary break-all">{t('khoa.dauVanTay')}: <code>{k.dau_van_tay}</code></div>
            {k.trang_thai === 'HOAT_DONG' && (
              <div className="flex gap-2 pt-1">
                <input className={LOP_O_NHAP} placeholder={t('khoa.lyDoThuHoi')} value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
                <Button size="sm" variant="danger" icon="fa-ban" disabled={!lyDo.trim()} isLoading={dangLam}
                  onClick={() => lam(() => signingApi.thuHoiKhoa(k.id, lyDo))}>{t('khoa.thuHoi')}</Button>
              </div>
            )}
          </div>
        ))}
      </Card>
    </div>
  );
}
