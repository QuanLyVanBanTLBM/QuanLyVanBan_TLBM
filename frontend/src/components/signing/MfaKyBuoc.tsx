/**
 * Bước xác thực mã gửi qua email trong hộp thoại ký (#510, MFA khi ký của #447). Chỉ hiện khi máy chủ báo MFA bật
 * và access token hiện tại chưa xác thực. Gồm: gửi mã, 6 ô nhập số (tự chuyển ô, dán 6 số), đếm ngược hiệu lực mã
 * theo mốc máy chủ trả, nút gửi lại đếm ngược theo giãn cách, khóa ô nhập có đếm ngược khi nhận HTTP 429.
 */
import { useEffect, useRef, useState } from 'react';
import { Button } from '@components/common';
import { ThongBao } from '@components/signing/ChungUI';
import { docLoi, giayChoThuLai, signingApi } from '@lib/signing/api';
import { LOP_O_NHAP } from '@lib/signing/dinhDang';
import { useSigningT } from '@lib/signing/i18n';

const SO_O = 6;
/** Khóa ô nhập khi 429 mà máy chủ không nêu thời điểm thử lại. */
const GIAY_KHOA_MAC_DINH = 60;
/** Mã không còn dùng được: người dùng phải gửi mã mới. */
const MA_LOI_HUY_MA = ['mfa_vuot_gioi_han_nhap', 'mfa_ma_het_han', 'mfa_ma_da_dung', 'mfa_ma_khong_co'];

const oTrong = () => Array<string>(SO_O).fill('');

export default function MfaKyBuoc({ onXacThuc }: { onXacThuc: () => void }) {
  const { t, loi } = useSigningT();
  const [hetHan, setHetHan] = useState<number | null>(null);
  const [bayGio, setBayGio] = useState(() => Date.now());
  const [cacSo, setCacSo] = useState<string[]>(oTrong);
  const [giayGuiLai, setGiayGuiLai] = useState(0);
  const [giayKhoa, setGiayKhoa] = useState(0);
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState<string | null>(null);
  const [daXacThuc, setDaXacThuc] = useState(false);
  const oRef = useRef<Array<HTMLInputElement | null>>([]);

  // Một nhịp mỗi giây cho các đồng hồ đếm ngược
  const canNhip = hetHan !== null || giayGuiLai > 0 || giayKhoa > 0;
  useEffect(() => {
    if (!canNhip) return undefined;
    const hen = setInterval(() => {
      setBayGio(Date.now());
      setGiayGuiLai((g) => Math.max(0, g - 1));
      setGiayKhoa((g) => Math.max(0, g - 1));
    }, 1000);
    return () => clearInterval(hen);
  }, [canNhip]);

  const conHan = hetHan === null ? 0 : Math.max(0, Math.ceil((hetHan - bayGio) / 1000));
  const maHetHan = hetHan !== null && conHan === 0;
  const maDayDu = cacSo.every(Boolean);
  const khoaNhap = dangLam || giayKhoa > 0 || maHetHan;

  const guiMa = async () => {
    setDangLam(true);
    setThongBao(null);
    try {
      const r = await signingApi.mfaKyYeuCau();
      setHetHan(new Date(r.het_han).getTime());
      setBayGio(Date.now());
      setGiayGuiLai(r.gian_cach_giay);
      setCacSo(oTrong());
      setTimeout(() => oRef.current[0]?.focus(), 0);
    } catch (err) {
      setThongBao(loi(err));
      const giay = giayChoThuLai(err);
      if (giay > 0) setGiayGuiLai(giay);
    } finally {
      setDangLam(false);
    }
  };

  const xacNhan = async () => {
    if (!maDayDu || khoaNhap) return;
    setDangLam(true);
    setThongBao(null);
    try {
      await signingApi.mfaKyXacMinh(cacSo.join(''));
      setDaXacThuc(true);
      onXacThuc();
    } catch (err) {
      setThongBao(loi(err));
      const l = docLoi(err);
      if (l.status === 429) setGiayKhoa(giayChoThuLai(err) || GIAY_KHOA_MAC_DINH);
      if (l.code && MA_LOI_HUY_MA.includes(l.code)) setHetHan(null);
      setCacSo(oTrong());
      setTimeout(() => oRef.current[0]?.focus(), 0);
    } finally {
      setDangLam(false);
    }
  };

  const datSo = (vi_tri: number, chuoi: string) => {
    const so = chuoi.replace(/\D/g, '');
    if (!so) {
      setCacSo((cu) => cu.map((v, i) => (i === vi_tri ? '' : v)));
      return;
    }
    // Nhập nhiều số một lần (dán, gợi ý của trình duyệt): rải vào các ô từ vị trí hiện tại
    setCacSo((cu) => {
      const moi = [...cu];
      so.slice(0, SO_O - vi_tri).split('').forEach((c, i) => {
        moi[vi_tri + i] = c;
      });
      return moi;
    });
    oRef.current[Math.min(vi_tri + so.length, SO_O - 1)]?.focus();
  };

  if (daXacThuc) return <ThongBao loai="thanh_cong">{t('mfa.daXacThuc')}</ThongBao>;

  const phut = Math.floor(conHan / 60);
  const giay = String(conHan % 60).padStart(2, '0');

  return (
    <section className="space-y-3 rounded-lg border border-border-subtle p-3" aria-label={t('mfa.tieuDe')}>
      <div>
        <h3 className="text-sm font-semibold text-primary-text">{t('mfa.tieuDe')}</h3>
        <p className="text-xs text-secondary">{t('mfa.moTa')}</p>
      </div>
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
      {hetHan === null ? (
        <Button size="sm" icon="fa-envelope" isLoading={dangLam} disabled={giayGuiLai > 0} onClick={guiMa}>
          {giayGuiLai > 0 ? t('mfa.guiLaiSau', { giay: giayGuiLai }) : t('mfa.guiMa')}
        </Button>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-secondary">{t('mfa.daGui')}</p>
          <div role="group" aria-label={t('mfa.nhapMa')} className="flex gap-2">
            {cacSo.map((so, i) => (
              <input
                key={i}
                ref={(el) => {
                  oRef.current[i] = el;
                }}
                className={`${LOP_O_NHAP} w-11 text-center`}
                inputMode="numeric"
                autoComplete={i === 0 ? 'one-time-code' : 'off'}
                aria-label={t('mfa.oSo', { so: i + 1 })}
                value={so}
                disabled={khoaNhap}
                onChange={(e) => datSo(i, e.target.value)}
                onFocus={(e) => e.target.select()}
                onKeyDown={(e) => {
                  if (e.key === 'Backspace' && !cacSo[i] && i > 0) {
                    oRef.current[i - 1]?.focus();
                  } else if (e.key === 'Enter') {
                    e.preventDefault();
                    xacNhan();
                  }
                }}
              />
            ))}
          </div>
          {giayKhoa > 0 && <p className="text-xs text-danger" role="status">{t('mfa.khoaNhap', { giay: giayKhoa })}</p>}
          <p className="text-xs text-secondary" role="timer">
            {maHetHan ? t('mfa.hetHan') : t('mfa.conHan', { phut, giay })}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" isLoading={dangLam} disabled={!maDayDu || khoaNhap} onClick={xacNhan}>
              {t('mfa.xacNhan')}
            </Button>
            <Button size="sm" variant="secondary" icon="fa-rotate" disabled={dangLam || giayGuiLai > 0} onClick={guiMa}>
              {giayGuiLai > 0 ? t('mfa.guiLaiSau', { giay: giayGuiLai }) : t('mfa.guiLai')}
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}
