/**
 * Đặt lại PIN bằng mã xác thực gửi qua email (#478): nhập mã và PIN mới sẽ đổi verifier PIN,
 * giữ nguyên khóa ký hiện tại và ciphertext trên máy chủ.
 */
import { useEffect, useState } from 'react';
import { Button } from '@components/common';
import { HopThoai, ThongBao, TruongNhap } from '@components/signing/ChungUI';
import { giayChoThuLai, signingApi } from '@lib/signing/api';
import { dinhDangNgay, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { useSigningT } from '@lib/signing/i18n';
import { kiemTraPin } from '@lib/signing/khoaKy';
import { useTranslation } from '@i18n/translate';

/** Chỉ đếm ngược khi thời gian chờ ngắn; chờ dài hơn (giới hạn theo ngày) hiện thời điểm được thử lại. */
const GIAY_DEM_NGUOC_TOI_DA = 15 * 60;

export default function DatLaiPinDialog({
  mo, onDong, onXong,
}: { mo: boolean; onDong: () => void; onXong: (pin_moi: string) => void }) {
  const { t, loi } = useSigningT();
  const { currentLang } = useTranslation();
  const [hetHan, setHetHan] = useState<string | null>(null);
  const [ma, setMa] = useState('');
  const [pinMoi, setPinMoi] = useState('');
  const [pinMoi2, setPinMoi2] = useState('');
  const [giayCho, setGiayCho] = useState(0);
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState<string | null>(null);

  // Đếm ngược giãn cách gửi lại
  useEffect(() => {
    if (giayCho <= 0) return;
    const hen = setTimeout(() => setGiayCho((g) => g - 1), 1000);
    return () => clearTimeout(hen);
  }, [giayCho]);

  const dong = () => {
    if (dangLam) return;
    setHetHan(null);
    setMa('');
    setPinMoi('');
    setPinMoi2('');
    setGiayCho(0);
    setThongBao(null);
    onDong();
  };

  const guiMa = async () => {
    setDangLam(true);
    setThongBao(null);
    try {
      const r = await signingApi.datLaiPinYeuCau();
      setHetHan(r.het_han);
      setGiayCho(r.gian_cach_giay);
      setMa('');
    } catch (err) {
      setThongBao(loi(err));
      // 429 ngắn hạn (giãn cách gửi mã): khóa nút gửi và đếm ngược; giới hạn theo ngày chỉ hiện giờ được thử lại
      const giay = giayChoThuLai(err);
      if (giay > 0 && giay <= GIAY_DEM_NGUOC_TOI_DA) setGiayCho(giay);
    } finally {
      setDangLam(false);
    }
  };

  const xacNhan = async () => {
    setDangLam(true);
    setThongBao(null);
    try {
      await signingApi.datLaiPinXacNhan(ma, pinMoi);
      setDangLam(false);
      setHetHan(null);
      setMa('');
      setGiayCho(0);
      const pinDaDatLai = pinMoi;
      setPinMoi('');
      setPinMoi2('');
      onXong(pinDaDatLai);
    } catch (err) {
      setThongBao(loi(err));
      setDangLam(false);
    }
  };

  const loiPin = pinMoi ? kiemTraPin(pinMoi) : null;
  const duocXacNhan = ma.length === 6 && !loiPin && pinMoi.length === 6 && pinMoi === pinMoi2;

  return (
    <HopThoai
      moTieuDe={t('khoa.datLaiPinTieuDe')}
      mo={mo}
      onDong={dong}
      dangXuLy={dangLam}
      chieuRong="30rem"
      chanDuoi={(
        <>
          <Button variant="secondary" onClick={dong} disabled={dangLam}>{t('chung.dong')}</Button>
          {hetHan && (
            <Button variant="primary" isLoading={dangLam} disabled={!duocXacNhan} onClick={xacNhan}>
              {t('khoa.datLaiPinXacNhan')}
            </Button>
          )}
        </>
      )}
    >
      <p className="text-sm text-secondary">{t('khoa.datLaiPinMoTa')}</p>
      {thongBao && <ThongBao loai="loi">{thongBao}</ThongBao>}
      {!hetHan ? (
        <Button icon="fa-envelope" isLoading={dangLam} disabled={giayCho > 0} onClick={guiMa}>
          {giayCho > 0 ? t('khoa.datLaiPinGuiLaiSau', { giay: giayCho }) : t('khoa.datLaiPinGuiMa')}
        </Button>
      ) : (
        <div className="space-y-3">
          <ThongBao loai="thong_tin">{t('khoa.datLaiPinDaGui', { han: dinhDangNgay(hetHan, currentLang) })}</ThongBao>
          <TruongNhap nhan={t('khoa.datLaiPinNhapMa')} batBuoc>
            <input
              className={LOP_O_NHAP}
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={ma}
              onChange={(e) => setMa(e.target.value.replace(/\D/g, ''))}
            />
          </TruongNhap>
          <TruongNhap nhan={t('khoa.datLaiPinNhapPinMoi')} batBuoc>
            <input
              className={LOP_O_NHAP}
              type="password"
              inputMode="numeric"
              autoComplete="new-password"
              maxLength={6}
              value={pinMoi}
              onChange={(e) => setPinMoi(e.target.value.replace(/\D/g, ''))}
            />
          </TruongNhap>
          {loiPin && <ThongBao loai="canh_bao">{t(`loi.${loiPin}`)}</ThongBao>}
          <TruongNhap nhan={t('khoa.datLaiPinNhapLaiPinMoi')} batBuoc>
            <input
              className={LOP_O_NHAP}
              type="password"
              inputMode="numeric"
              autoComplete="new-password"
              maxLength={6}
              value={pinMoi2}
              onChange={(e) => setPinMoi2(e.target.value.replace(/\D/g, ''))}
            />
          </TruongNhap>
          {pinMoi2 && pinMoi !== pinMoi2 && (
            <ThongBao loai="canh_bao">{t('khoa.datLaiPinKhongKhop')}</ThongBao>
          )}
          <Button variant="secondary" size="sm" icon="fa-rotate" disabled={dangLam || giayCho > 0} onClick={guiMa}>
            {giayCho > 0 ? t('khoa.datLaiPinGuiLaiSau', { giay: giayCho }) : t('khoa.datLaiPinGuiLai')}
          </Button>
        </div>
      )}
    </HopThoai>
  );
}
