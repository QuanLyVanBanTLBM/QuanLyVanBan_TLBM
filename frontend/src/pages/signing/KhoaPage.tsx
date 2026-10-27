/**
 * Khóa ký và PIN cá nhân theo contract #79 (#80 mục E): tạo khóa trên thiết bị (proof-of-possession, đặt PIN,
 * kích hoạt hoặc xoay vòng khóa của thiết bị cũ), xuất/nhập file khóa, đổi PIN, thu hồi. PIN và private key
 * không rời trình duyệt; file khóa chứa private key đã mã hóa, chỉ mở được khi có PIN và máy chủ xác minh PIN.
 */
import { useEffect, useState } from 'react';
import { Button, Card } from '@components/common';
import type { KhoaKy } from '@lib/signing/types';
import { DangTai, HopThoai, LoiTai, OChonTep, ThongBao, TrangThaiBadge, TruongNhap } from '@components/signing/ChungUI';
import { signingApi } from '@lib/signing/api';
import { GIOI_HAN, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { coQuyen, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import { docFileKhoaTuTep, DUOI_FILE_KHOA, taiXuongFileKhoa } from '@lib/signing/fileKhoa';
import { hoTroEd25519, kiemTraPin, layBanBoc } from '@lib/signing/khoaKy';
import { dangKyKhoaThietBi, doiPin, khoaHoatDong, nhapFileKhoa } from '@lib/signing/luongKhoa';

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
  const [canThuHoi, setCanThuHoi] = useState<KhoaKy | null>(null);
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState<{ loai: 'loi' | 'thanh_cong'; noi_dung: string } | null>(null);
  const [lanTaiBanBoc, setLanTaiBanBoc] = useState(0);
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
  }, [hoatDongId, toi, lanTaiBanBoc]);

  const loiPin = pin ? kiemTraPin(pin) : null;
  const pinHopLe = !loiPin && pin.length === 8 && pin === pin2;

  const lam = async (ham: () => Promise<unknown>, thanh_cong = t('hanhDong.thanhCong')) => {
    setDangLam(true);
    setThongBao(null);
    try {
      await ham();
      setPin('');
      setPin2('');
      setPinCu('');
      setLyDo('');
      setThongBao({ loai: 'thanh_cong', noi_dung: thanh_cong });
      setLanTaiBanBoc((n) => n + 1);
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

  const sanSang = hoatDong && coBanBoc;
  const taiFile = () => lam(async () => {
    const ban = hoatDong && await layBanBoc(toi.id, hoatDong.id);
    if (!ban) throw new Error('thieu_ban_boc_thiet_bi');
    taiXuongFileKhoa(ban);
  }, t('khoa.daTaiFile'));
  const nhapFile = (tep: File | undefined) => tep && hoatDong && lam(async () => {
    await nhapFileKhoa(toi.id, hoatDong, await docFileKhoaTuTep(tep));
  }, t('khoa.daNhapFile'));
  return (
    <div className="grid gap-4 lg:grid-cols-2">
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
                taiXuongFileKhoa((await dangKyKhoaThietBi(toi.id, pin, ds.duLieu || [])).banBoc);
              }, t('khoa.daTaoVaTaiFile'))}>{t('khoa.taoKhoa')}</Button>
            {hoatDong && (
              <TruongNhap nhan={t('khoa.nhapFile')} ghiChu={t('khoa.nhapFileGhiChu')}>
                <OChonTep accept={`${DUOI_FILE_KHOA},application/json`} nhan={t('khoa.nhapFile')} onChon={nhapFile} />
              </TruongNhap>
            )}
          </div>
        )}
        {sanSang && (
          <div className="space-y-2">
            <p className="text-sm text-secondary">{t('khoa.fileGhiChu')}</p>
            <Button variant="outline" icon="fa-file-arrow-down" isLoading={dangLam} onClick={taiFile}>
              {t('khoa.taiFile')}
            </Button>
          </div>
        )}
        {sanSang && (
          <div className="space-y-3 border-t border-border-subtle pt-3">
            <h3 className="text-xl font-bold text-main">{t('khoa.doiPin')}</h3>
            <OPin nhan={t('khoa.pinCu')} gia_tri={pinCu} onDoi={setPinCu} />
            <OPin nhan={t('khoa.pin')} gia_tri={pin} onDoi={setPin} />
            <OPin nhan={t('khoa.pinNhapLai')} gia_tri={pin2} onDoi={setPin2} />
            {loiPin && <ThongBao loai="canh_bao">{t(`loi.${loiPin}`)}</ThongBao>}
            <Button variant="secondary" icon="fa-rotate" isLoading={dangLam} disabled={!pinHopLe || pinCu.length !== 8}
              onClick={() => lam(async () => {
                taiXuongFileKhoa(await doiPin(toi.id, hoatDong, pinCu, pin));
              }, t('khoa.daDoiPinTaiFile'))}>{t('khoa.doiPin')}</Button>
          </div>
        )}
        {thongBao && <ThongBao loai={thongBao.loai}>{thongBao.noi_dung}</ThongBao>}
      </Card>
      <Card className="min-w-0 p-4 space-y-3">
        {(ds.duLieu || []).map((k) => (
          <div key={k.id} className="space-y-1 rounded-lg border border-border-subtle p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="min-w-0 text-base font-bold text-main truncate" title={k.ma_khoa}>{k.ma_khoa || `#${k.id}`}</span>
              <TrangThaiBadge trangThai={k.trang_thai} />
            </div>
            <div className="text-xs text-secondary">
              {t('khoa.dauVanTay')}: <code title={k.dau_van_tay}>{k.dau_van_tay.length > 10 ? `${k.dau_van_tay.slice(0, 8)}****` : k.dau_van_tay}</code>
            </div>
            {k.trang_thai === 'HOAT_DONG' && (
              <div className="flex gap-2 pt-1">
                <input className={LOP_O_NHAP} placeholder={t('khoa.lyDoThuHoi')} aria-label={t('khoa.lyDoThuHoi')}
                  maxLength={GIOI_HAN.lyDo} value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
                <Button size="sm" variant="danger" icon="fa-ban" disabled={!lyDo.trim()} isLoading={dangLam}
                  onClick={() => setCanThuHoi(k)}>{t('khoa.thuHoi')}</Button>
              </div>
            )}
          </div>
        ))}
      </Card>
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
          <p className="text-sm text-main">{t('khoa.xacNhanThuHoi', { ma: canThuHoi.ma_khoa || `#${canThuHoi.id}` })}</p>
          <p className="text-sm text-secondary">{t('khoa.lyDoThuHoi')}: {lyDo.trim()}</p>
        </HopThoai>
      )}
    </div>
  );
}
