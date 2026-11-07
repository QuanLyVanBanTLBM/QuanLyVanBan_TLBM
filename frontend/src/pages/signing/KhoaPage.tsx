/**
 * Khóa ký và PIN cá nhân: tạo khóa Ed25519, gửi PKCS#8 qua HTTPS để máy chủ mã hóa, đổi PIN, thu hồi.
 * Server ký bằng private key giải mã trong bộ nhớ; trình duyệt không giữ file khóa.
 */
import { useEffect, useRef, useState } from 'react';
import { Button, Card } from '@components/common';
import type { KhoaKy } from '@lib/signing/types';
import { DangTai, HopThoai, LoiTai, ThongBao, TrangThaiBadge, TruongNhap } from '@components/signing/ChungUI';
import CropChuKyModal from '@components/signing/CropChuKyModal';
import DatLaiPinDialog from '@components/signing/DatLaiPinDialog';
import { signingApi } from '@lib/signing/api';
import { GIOI_HAN, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { coQuyen, useAnhChuKyCaNhan, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import { hoTroEd25519, kiemTraPin } from '@lib/signing/khoaKy';
import { dangKyKhoaThietBi, doiPin, khoaHoatDong } from '@lib/signing/luongKhoa';

// Dung lượng tối đa của ảnh chữ ký PNG sau khi cắt (bằng giới hạn 2 MB của máy chủ)
const GIOI_HAN_ANH_SAU_CAT = 2 * 1024 * 1024;

function OPin({ nhan, gia_tri, onDoi }: { nhan: string; gia_tri: string; onDoi: (v: string) => void }) {
  return (
    <TruongNhap nhan={nhan}>
      <input className={LOP_O_NHAP} type="password" inputMode="numeric" autoComplete="new-password" maxLength={6}
        value={gia_tri} onChange={(e) => onDoi(e.target.value.replace(/\D/g, ''))} />
    </TruongNhap>
  );
}

export default function KhoaPage() {
  const { t, loi } = useSigningT();
  const { toi, taiLaiToi } = useToi();
  const ds = useTai(() => signingApi.khoa());
  const [hoTro, setHoTro] = useState<boolean | null>(null);
  const [pin, setPin] = useState('');
  const [pin2, setPin2] = useState('');
  const [pinCu, setPinCu] = useState('');
  const [lyDo, setLyDo] = useState('');
  const [loiLyDo, setLoiLyDo] = useState('');
  const [canThuHoi, setCanThuHoi] = useState<KhoaKy | null>(null);
  const [moDatLaiPin, setMoDatLaiPin] = useState(false);
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: 'loi' | 'thanh_cong'; noi_dung: string } | null>(null);
  const [thongBaoChuKy, setThongBaoChuKy] = useState<{ loai: 'loi' | 'thanh_cong'; noi_dung: string } | null>(null);
  const [anhChuKyTuyChinh, setAnhChuKyTuyChinh] = useState<string | null | undefined>(undefined);
  // Ảnh từ máy chủ tải qua Bearer; chưa có ảnh/đang tải/lỗi thì null và hiện trạng thái trống
  const anhChuKyServer = useAnhChuKyCaNhan(toi?.co_anh_chu_ky, toi?.id);
  const anhChuKy = anhChuKyTuyChinh !== undefined ? anhChuKyTuyChinh : anhChuKyServer;
  const [tepChon, setTepChon] = useState<File | null>(null);
  const [moCrop, setMoCrop] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const hoatDong = khoaHoatDong(ds.duLieu || []);

  const onChonTepAnh = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setThongBao(null);
      setThongBaoChuKy(null);
      setTepChon(files[0]);
      setMoCrop(true);
    }
    e.target.value = '';
  };

  const onLuuAnhChuKy = async (blob: Blob, dataUrl: string) => {
    // Giới hạn chỉ tính trên ảnh PNG sau khi cắt (khớp giới hạn của máy chủ), không tính tệp gốc
    if (blob.size > GIOI_HAN_ANH_SAU_CAT) {
      setMoCrop(false);
      setTepChon(null);
      setThongBaoChuKy({ loai: 'loi', noi_dung: t('khoa.anhQuaLon') });
      return;
    }
    setDangLam(true);
    setThongBaoChuKy(null);
    try {
      try {
        await signingApi.taiLenAnhChuKy(blob);
      } catch (uploadErr) {
        if (dataUrl) {
          await signingApi.taiLenAnhChuKy(dataUrl);
        } else {
          throw uploadErr;
        }
      }
      setAnhChuKyTuyChinh(dataUrl);
      taiLaiToi?.();
      setMoCrop(false);
      setTepChon(null);
      setThongBaoChuKy({ loai: 'thanh_cong', noi_dung: t('khoa.daLuuChuKy') });
    } catch (err) {
      setThongBaoChuKy({ loai: 'loi', noi_dung: loi(err) });
    } finally {
      setDangLam(false);
    }
  };

  const onXoaAnhChuKy = async () => {
    setDangLam(true);
    setThongBaoChuKy(null);
    try {
      await signingApi.xoaAnhChuKy();
      setAnhChuKyTuyChinh(null);
      taiLaiToi?.();
      setThongBaoChuKy({ loai: 'thanh_cong', noi_dung: t('khoa.daXoaChuKy') });
    } catch (err) {
      setThongBaoChuKy({ loai: 'loi', noi_dung: loi(err) });
    } finally {
      setDangLam(false);
    }
  };

  useEffect(() => {
    hoTroEd25519().then(setHoTro);
  }, []);
  const loiPin = pin ? kiemTraPin(pin) : null;
  const pinHopLe = !loiPin && pin.length === 6 && pin === pin2;

  const lam = async (ham: () => Promise<unknown>, thanh_cong = t('hanhDong.thanhCong')) => {
    setDangLam(true);
    setThongBao(null);
    try {
      await ham();
      setPin('');
      setPin2('');
      setPinCu('');
      setLyDo('');
      setLoiLyDo('');
      setThongBao({ loai: 'thanh_cong', noi_dung: thanh_cong });
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
  // Vào thẳng đường dẫn khi chưa có quyền ký: không cho nhập PIN rồi mới báo 403
  if (!coQuyen(toi, 'sign_trinhky')) return <ThongBao loai="thong_tin">{t('khoa.khongCoQuyen')}</ThongBao>;

  const sanSang = Boolean(hoatDong?.da_dat_pin);
  return (
    <div className="space-y-4">
      <DatLaiPinDialog
        mo={moDatLaiPin}
        onDong={() => setMoDatLaiPin(false)}
        onXong={() => {
          setMoDatLaiPin(false);
          setThongBao({ loai: 'thanh_cong', noi_dung: t('khoa.datLaiPinXong') });
          ds.tai();
        }}
      />
      {/* Input file ẩn để chọn ảnh chữ ký */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={onChonTepAnh}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Cột trái: Khóa ký trên thiết bị & PIN */}
        <Card className="min-w-0 p-4 space-y-3">
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
                onClick={() => lam(async () => {
                  await dangKyKhoaThietBi(toi.id, pin, ds.duLieu || []);
                }, t('khoa.daTaoVaTaiFile'))}>{t('khoa.taoKhoa')}</Button>
              {hoatDong && (
                <button type="button" className="text-sm font-medium text-primary hover:underline" onClick={() => setMoDatLaiPin(true)}>
                  {t('khoa.quenPin')}
                </button>
              )}
            </div>
          )}
          {sanSang && (
            <div className="space-y-2">
              <p className="text-sm text-secondary">{t('khoa.fileGhiChu')}</p>
            </div>
          )}
          {sanSang && (
            <div className="space-y-3 border-t border-border-subtle pt-3">
              <h3 className="text-xl font-bold text-main">{t('khoa.doiPin')}</h3>
              <OPin nhan={t('khoa.pinCu')} gia_tri={pinCu} onDoi={setPinCu} />
              <OPin nhan={t('khoa.pin')} gia_tri={pin} onDoi={setPin} />
              <OPin nhan={t('khoa.pinNhapLai')} gia_tri={pin2} onDoi={setPin2} />
              {loiPin && <ThongBao loai="canh_bao">{t(`loi.${loiPin}`)}</ThongBao>}
              <div className="flex flex-wrap items-center gap-3">
                <Button variant="secondary" icon="fa-rotate" isLoading={dangLam} disabled={!pinHopLe || !/^\d{6}$/.test(pinCu)}
                  onClick={() => lam(async () => {
                    if (!hoatDong) throw new Error('chua_co_khoa_ky');
                    await doiPin(hoatDong, pinCu, pin);
                  }, t('khoa.daDoiPinTaiFile'))}>{t('khoa.doiPin')}</Button>
                <button type="button" className="text-sm font-medium text-primary hover:underline" onClick={() => setMoDatLaiPin(true)}>
                  {t('khoa.quenPin')}
                </button>
              </div>
            </div>
          )}
          {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.noi_dung}</ThongBao>}
        </Card>

        {/* Cột phải: Quản lý ảnh chữ ký cá nhân */}
        <Card className="min-w-0 p-4 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-base font-bold text-main">{t('khoa.chuKyCaNhan')}</h3>
            {anhChuKy && (
              <span className="rounded-full bg-success-subtle text-success text-xs font-semibold px-2 py-0.5">
                {t('trangThai.HOAT_DONG')}
              </span>
            )}
          </div>
          <p className="text-sm text-secondary">{t('khoa.chuKyCaNhanGhiChu')}</p>
          {thongBaoChuKy && <ThongBao loai={thongBaoChuKy.loai}>{thongBaoChuKy.noi_dung}</ThongBao>}

          {anhChuKy ? (
            <div className="space-y-3">
              <div
                className="flex items-center justify-center p-4 rounded-lg border border-border-subtle"
                style={{
                  backgroundImage:
                    'linear-gradient(45deg, #eee 25%, transparent 25%), linear-gradient(-45deg, #eee 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #eee 75%), linear-gradient(-45deg, transparent 75%, #eee 75%)',
                  backgroundSize: '16px 16px',
                  backgroundPosition: '0 0, 0 8px, 8px -8px, -8px 0px',
                }}
              >
                <img
                  src={anhChuKy}
                  alt={t('khoa.chuKyCaNhan')}
                  className="max-h-32 object-contain rounded drop-shadow-sm"
                />
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  icon="fa-pen"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {t('khoa.thayDoiChuKy')}
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  icon="fa-trash"
                  isLoading={dangLam}
                  onClick={onXoaAnhChuKy}
                >
                  {t('khoa.xoaChuKy')}
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-border-subtle p-6 text-center">
              <div className="mb-2 text-3xl text-secondary">
                <i className="fa-solid fa-signature" />
              </div>
              <p className="text-sm font-medium text-main mb-1">{t('khoa.chuaCoChuKy')}</p>
              <p className="text-xs text-secondary mb-4">{t('khoa.yeuCauKichThuoc')}</p>
              <Button
                variant="primary"
                icon="fa-upload"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
              >
                {t('khoa.taiLenChuKy')}
              </Button>
            </div>
          )}
        </Card>
      </div>

      {/* Hàng dưới: Thu hồi khóa ký đang hoạt động (ở trên) & Bảng lịch sử hoạt động ký (ở dưới) */}
      <Card className="min-w-0 p-4 space-y-4">
        {/* Phần trên: Thu hồi khóa ký đang hoạt động */}
        <div className="rounded-lg border border-border-subtle p-3 bg-surface-subtle space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="font-bold text-main">{t('khoa.thuHoiKhoaHienTai')}</span>
            {hoatDong ? (
              <TrangThaiBadge trangThai={hoatDong.trang_thai} />
            ) : (
              <span className="text-xs text-muted font-medium">{t('khoa.chuaCoKhoaHoatDong')}</span>
            )}
          </div>
          <div className="pt-1">
            <TruongNhap nhan={t('khoa.lyDoThuHoi')} batBuoc loi={loiLyDo}>
              <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                <input
                  className={`${LOP_O_NHAP} flex-1 ${loiLyDo ? 'border-danger focus:ring-danger' : ''}`}
                  placeholder={t('khoa.lyDoThuHoi')}
                  aria-label={t('khoa.lyDoThuHoi')}
                  maxLength={GIOI_HAN.lyDo}
                  value={lyDo}
                  disabled={!hoatDong || dangLam}
                  onChange={(e) => {
                    setLyDo(e.target.value);
                    if (e.target.value.trim().length >= 10) setLoiLyDo('');
                  }}
                />
                <Button
                  size="sm"
                  variant="danger"
                  disabled={!hoatDong || dangLam}
                  isLoading={dangLam}
                  onClick={() => {
                    if (!hoatDong) return;
                    const clean = lyDo.trim();
                    if (!clean) {
                      setLoiLyDo(t('khoa.lyDoBatBuoc'));
                      return;
                    }
                    if (clean.length < 10) {
                      setLoiLyDo(t('khoa.lyDoThuHoiToiThieu'));
                      return;
                    }
                    const uniqueChars = new Set(clean.toLowerCase().replace(/[\s\-_.,]/g, ''));
                    if (uniqueChars.size < 3) {
                      setLoiLyDo(t('khoa.lyDoThuHoiToiThieu'));
                      return;
                    }
                    setLoiLyDo('');
                    setCanThuHoi(hoatDong);
                  }}
                >
                  {t('khoa.thuHoi')}
                </Button>
              </div>
            </TruongNhap>
          </div>
        </div>

        {/* Phần dưới: Bảng nhật ký hoạt động ký số & khóa thiết bị */}
        <div className="space-y-3 pt-2">
          <h3 className="text-base font-bold text-main">{t('khoa.nhatKyHoatDong')}</h3>
          <div className="overflow-x-auto rounded-lg border border-border-subtle">
            <table className="w-full text-left text-sm border-collapse">
              <thead className="bg-surface-subtle text-xs font-semibold text-secondary uppercase border-b border-border-subtle">
                <tr>
                  <th className="px-4 py-3">{t('khoa.thoiGian')}</th>
                  <th className="px-4 py-3">{t('khoa.hanhDongLog')}</th>
                  <th className="px-4 py-3">{t('khoa.maHoSoLog')}</th>
                  <th className="px-4 py-3">{t('khoa.maKhoaLog')}</th>
                  <th className="px-4 py-3 text-right">{t('khoa.trangThaiLog')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {(ds.duLieu || []).length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted">
                      <div className="flex flex-col items-center justify-center gap-1.5">
                        <i className="fa-solid fa-clock-rotate-left text-2xl text-secondary opacity-60" aria-hidden="true" />
                        <p className="text-sm font-medium">{t('khoa.chuaCoLichSu')}</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  (ds.duLieu || []).map((k) => (
                    <tr key={k.id} className="hover:bg-surface-hover transition-colors">
                      <td className="px-4 py-3 whitespace-nowrap text-secondary font-mono text-xs">
                        {k.created_at ? new Date(k.created_at).toLocaleString('vi-VN') : '-'}
                      </td>
                      <td className="px-4 py-3 font-medium text-main">
                        {k.trang_thai === 'THU_HOI' ? t('khoa.thuHoi') : t('khoa.dangKyKhoaThietBi')}
                      </td>
                      <td className="px-4 py-3 text-secondary font-mono text-xs">-</td>
                      <td className="px-4 py-3 text-secondary font-mono text-xs">
                        #{k.id} ({k.ma_khoa?.slice(0, 8)}...)
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <TrangThaiBadge trangThai={k.trang_thai} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      {/* Modal Crop Chữ Ký Chuẩn 2:1 */}
      <CropChuKyModal
        mo={moCrop}
        onDong={() => {
          setMoCrop(false);
          setTepChon(null);
        }}
        tep={tepChon}
        onLuu={onLuuAnhChuKy}
        dangXuLy={dangLam}
      />

      {canThuHoi && (
        <HopThoai moTieuDe={t('khoa.thuHoi')} mo onDong={() => setCanThuHoi(null)} dangXuLy={dangLam}
          chanDuoi={<>
            <Button variant="secondary" onClick={() => setCanThuHoi(null)}>{t('chung.huyBo')}</Button>
            <Button variant="danger" icon="fa-ban" isLoading={dangLam}
              onClick={async () => {
                await lam(() => signingApi.thuHoiKhoa(canThuHoi.id, lyDo.trim()));
                setCanThuHoi(null);
              }}>{t('khoa.thuHoi')}</Button>
          </>}>
          <p className="text-sm text-main">{t('khoa.xacNhanThuHoi')}</p>
          <p className="text-sm text-secondary">{t('khoa.lyDoThuHoi')}: {lyDo.trim()}</p>
        </HopThoai>
      )}
    </div>
  );
}
