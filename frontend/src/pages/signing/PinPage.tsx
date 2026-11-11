import { useEffect, useRef, useState } from 'react';
import { Button, Card } from '@components/common';
import { DangTai, LoiTai, ThongBao, TruongNhap } from '@components/signing/ChungUI';
import CropChuKyModal from '@components/signing/CropChuKyModal';
import { docLoi, signingApi } from '@lib/signing/api';
import { LOP_O_NHAP } from '@lib/signing/dinhDang';
import { coQuyen, useAnhChuKyCaNhan, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { KenhOtpPin, PinOtpYeuCau } from '@lib/signing/types';

const GIOI_HAN_ANH_SAU_CAT = 2 * 1024 * 1024;

export default function PinPage() {
  const { t, loi } = useSigningT();
  const { toi, taiLaiToi } = useToi();
  const pinState = useTai(() => signingApi.pinTrangThai());
  const [pin, setPin] = useState('');
  const [pinXacNhan, setPinXacNhan] = useState('');
  const [kenh, setKenh] = useState<KenhOtpPin>('SMS');
  const [ma, setMa] = useState('');
  const [challenge, setChallenge] = useState<PinOtpYeuCau | null>(null);
  const [giayGuiLai, setGiayGuiLai] = useState(0);
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: 'loi' | 'thanh_cong'; noi_dung: string } | null>(null);
  const [anhChuKyTuyChinh, setAnhChuKyTuyChinh] = useState<string | null | undefined>(undefined);
  const [tepChon, setTepChon] = useState<File | null>(null);
  const [moCrop, setMoCrop] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const anhChuKyServer = useAnhChuKyCaNhan(toi?.co_anh_chu_ky, toi?.id);
  const anhChuKy = anhChuKyTuyChinh !== undefined ? anhChuKyTuyChinh : anhChuKyServer;
  const dangChoGuiLai = giayGuiLai > 0;

  useEffect(() => {
    if (!dangChoGuiLai) return undefined;
    const timer = window.setInterval(() => setGiayGuiLai((n) => Math.max(0, n - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [dangChoGuiLai]);

  const huyTaoPin = async () => {
    if (dangLam) return;
    setDangLam(true);
    try {
      if (challenge) await signingApi.pinOtpHuy(challenge.challenge_id);
      setChallenge(null);
      setPin('');
      setPinXacNhan('');
      setMa('');
      setGiayGuiLai(0);
      setThongBao(null);
    } catch (err) {
      setThongBao({ loai: 'loi', noi_dung: loi(err) });
    } finally {
      setDangLam(false);
    }
  };

  const yeuCauOtp = async () => {
    setDangLam(true);
    setThongBao(null);
    try {
      const result = await signingApi.pinOtpYeuCau(pin, pinXacNhan, kenh);
      setChallenge(result);
      setMa('');
      setGiayGuiLai(result.gian_cach_giay);
    } catch (err) {
      setThongBao({ loai: 'loi', noi_dung: loi(err) });
    } finally {
      setDangLam(false);
    }
  };

  const xacNhanOtp = async () => {
    if (!challenge) return;
    setDangLam(true);
    setThongBao(null);
    try {
      await signingApi.pinOtpXacNhan(challenge.challenge_id, ma);
      setChallenge(null);
      setPin('');
      setPinXacNhan('');
      setMa('');
      setThongBao({ loai: 'thanh_cong', noi_dung: t('pin.daLuu') });
      pinState.tai();
      taiLaiToi?.();
    } catch (err) {
      const { code, fields } = docLoi(err);
      const conLai = (fields as Record<string, unknown[]> | undefined)?.so_lan_con_lai?.[0];
      if (code === 'otp_het_han' || (code === 'otp_sai' && conLai === 0)) setChallenge(null);
      setThongBao({ loai: 'loi', noi_dung: loi(err) });
    } finally {
      setDangLam(false);
    }
  };

  const chonAnh = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setThongBao(null);
      setTepChon(file);
      setMoCrop(true);
    }
    e.target.value = '';
  };

  const luuAnh = async (blob: Blob, dataUrl: string) => {
    if (blob.size > GIOI_HAN_ANH_SAU_CAT) {
      setMoCrop(false);
      setTepChon(null);
      setThongBao({ loai: 'loi', noi_dung: t('pin.anhQuaLon') });
      return;
    }
    setDangLam(true);
    try {
      try {
        await signingApi.taiLenAnhChuKy(blob);
      } catch (uploadErr) {
        if (!dataUrl) throw uploadErr;
        await signingApi.taiLenAnhChuKy(dataUrl);
      }
      setAnhChuKyTuyChinh(dataUrl);
      taiLaiToi?.();
      setMoCrop(false);
      setTepChon(null);
      setThongBao({ loai: 'thanh_cong', noi_dung: t('pin.daLuuChuKy') });
    } catch (err) {
      setThongBao({ loai: 'loi', noi_dung: loi(err) });
    } finally {
      setDangLam(false);
    }
  };

  const xoaAnh = async () => {
    setDangLam(true);
    try {
      await signingApi.xoaAnhChuKy();
      setAnhChuKyTuyChinh(null);
      taiLaiToi?.();
      setThongBao({ loai: 'thanh_cong', noi_dung: t('pin.daXoaChuKy') });
    } catch (err) {
      setThongBao({ loai: 'loi', noi_dung: loi(err) });
    } finally {
      setDangLam(false);
    }
  };

  if (pinState.dangTai && !pinState.duLieu) return <DangTai />;
  if (pinState.loi) return <LoiTai thongBao={loi(pinState.loi)} onThuLai={pinState.tai} />;
  if (!coQuyen(toi, 'sign_trinhky')) return <ThongBao loai="thong_tin">{t('pin.khongCoQuyen')}</ThongBao>;

  const daDatPin = Boolean(pinState.duLieu?.da_dat_pin);
  const pinHopLe = /^\d{6}$/.test(pin) && pin === pinXacNhan;

  return (
    <div className="space-y-4">
      <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp" className="hidden" onChange={chonAnh} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="min-w-0 space-y-3 p-4">
          <h3 className="text-base font-bold text-main">{t('pin.tieuDe')}</h3>
          <p className="text-sm text-secondary">{daDatPin ? t('pin.moTaDaDat') : t('pin.moTaChuaDat')}</p>
          {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.noi_dung}</ThongBao>}
          {!challenge ? (
            <div className="space-y-3">
              <TruongNhap nhan={t('pin.pinMoi')} batBuoc>
                <input className={LOP_O_NHAP} type="password" inputMode="numeric" autoComplete="new-password" maxLength={6}
                  value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))} />
              </TruongNhap>
              <TruongNhap nhan={t('pin.pinXacNhan')} batBuoc>
                <input className={LOP_O_NHAP} type="password" inputMode="numeric" autoComplete="new-password" maxLength={6}
                  value={pinXacNhan} onChange={(e) => setPinXacNhan(e.target.value.replace(/\D/g, ''))} />
              </TruongNhap>
              {pinXacNhan && pin !== pinXacNhan && <ThongBao loai="canh_bao">{t('pin.pinKhongKhop')}</ThongBao>}
              <TruongNhap nhan={t('pin.kenhNhan')}>
                <select className={LOP_O_NHAP} value={kenh} onChange={(e) => setKenh(e.target.value as KenhOtpPin)}>
                  <option value="SMS">{t('pin.sms')}</option>
                  <option value="EMAIL">{t('pin.email')}</option>
                </select>
              </TruongNhap>
              <Button icon="fa-paper-plane" isLoading={dangLam} disabled={!pinHopLe}
                onClick={yeuCauOtp}>{t('pin.guiOtp')}</Button>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-secondary">{t('pin.otpDaGui', { kenh: challenge.kenh === 'SMS' ? t('pin.sms') : t('pin.email') })}</p>
              <TruongNhap nhan={t('pin.maOtp')} batBuoc>
                <input className={LOP_O_NHAP} type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                  value={ma} onChange={(e) => setMa(e.target.value.replace(/\D/g, ''))} />
              </TruongNhap>
              <div className="flex flex-wrap gap-2">
                <Button icon="fa-check" isLoading={dangLam} disabled={!/^\d{6}$/.test(ma)} onClick={xacNhanOtp}>
                  {t('pin.xacNhanOtp')}
                </Button>
                <Button variant="secondary" disabled={dangLam || giayGuiLai > 0} onClick={yeuCauOtp}>
                  {giayGuiLai > 0 ? t('pin.guiLaiSau', { giay: giayGuiLai }) : t('pin.guiLaiOtp')}
                </Button>
                <Button variant="outline" disabled={dangLam} onClick={huyTaoPin}>{t('chung.huyBo')}</Button>
              </div>
            </div>
          )}
        </Card>

        <Card className="min-w-0 space-y-3 p-4">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-base font-bold text-main">{t('pin.chuKyCaNhan')}</h3>
            {anhChuKy && <span className="rounded-full bg-success-subtle px-2 py-0.5 text-xs font-semibold text-success">{t('pin.daThietLap')}</span>}
          </div>
          <p className="text-sm text-secondary">{t('pin.chuKyCaNhanMoTa')}</p>
          {anhChuKy ? (
            <div className="space-y-3">
              <div className="signing-chuky-giay flex items-center justify-center rounded-lg p-4" data-testid="nen-anh-chu-ky">
                <img src={anhChuKy} alt={t('pin.chuKyCaNhan')} className="max-h-32 rounded object-contain" />
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" icon="fa-pen" onClick={() => fileInputRef.current?.click()}>{t('pin.thayChuKy')}</Button>
                <Button size="sm" variant="danger" icon="fa-trash" isLoading={dangLam} onClick={xoaAnh}>{t('pin.xoaChuKy')}</Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border-subtle p-6 text-center">
              <i className="fa-solid fa-signature mb-2 text-3xl text-secondary" aria-hidden="true" />
              <p className="mb-1 text-sm font-medium text-main">{t('pin.chuaCoChuKy')}</p>
              <p className="mb-4 text-xs text-secondary">{t('pin.yeuCauAnh')}</p>
              <Button variant="primary" icon="fa-upload" size="sm" onClick={() => fileInputRef.current?.click()}>{t('pin.taiLenChuKy')}</Button>
            </div>
          )}
        </Card>
      </div>
      <CropChuKyModal mo={moCrop} onDong={() => { setMoCrop(false); setTepChon(null); }} tep={tepChon} onLuu={luuAnh} dangXuLy={dangLam} />
    </div>
  );
}
