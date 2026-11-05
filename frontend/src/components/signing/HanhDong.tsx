/**
 * Hành động trên hồ sơ theo quyền và trạng thái (#80 mục B, C, E): ký duyệt bằng PIN trên máy chủ, trả lại để sửa,
 * không đồng ý ban hành, thu hồi chữ ký, hủy, trình lại. Mỗi lần mở hộp thoại dùng một Idempotency-Key;
 * bấm lại hoặc thử lại sau lỗi mạng không tạo thao tác trùng.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@components/common';
import { docLoi, signingApi } from '@lib/signing/api';
import { GIOI_HAN, LOP_O_NHAP, moTaVanBan } from '@lib/signing/dinhDang';
import { coQuyen, useKhoaChongTrung, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import { khoaHoatDong } from '@lib/signing/luongKhoa';
import type { HoSoChiTiet, LuotTrinh } from '@lib/signing/types';
import { HopThoai, ThongBao, TruongNhap } from './ChungUI';
import DatLaiPinDialog from './DatLaiPinDialog';
import MfaKyBuoc from './MfaKyBuoc';

const URL_ANH_CHU_KY = '/api/signing/anh-chu-ky-ca-nhan/tep/';

type NguoiKy = { id: number; co_anh_chu_ky?: boolean } | null;

// Ảnh chữ ký chỉ lấy từ máy chủ (cờ co_anh_chu_ky của /toi/); không còn nguồn localStorage.
const layAnhChuKyUrl = (toi: NguoiKy): string | null =>
  toi?.co_anh_chu_ky ? `${URL_ANH_CHU_KY}?v=${toi.id}` : null;

type LoaiHopThoai = 'ky' | 'sua' | 'tu_choi' | 'thu_hoi' | 'huy' | 'trinh_lai' | null;

interface Props {
  hoSo: HoSoChiTiet;
  luot: LuotTrinh | null;
  /** SHA-256 tính lại trên tệp đang hiển thị (null khi chưa tải xong) */
  maBamTepDangXem: string | null;
  onXong: (ho_so?: HoSoChiTiet) => void;
}

function NutXacNhan({
  onXacNhan,
  nhan,
  variant = 'primary',
  disabled = false,
  dangLam,
  onDong,
  nhanHuy,
}: {
  onXacNhan: () => void;
  nhan: string;
  variant?: 'primary' | 'danger';
  disabled?: boolean;
  dangLam: boolean;
  onDong: () => void;
  nhanHuy: string;
}) {
  return (
    <>
      <Button variant="secondary" size="sm" onClick={onDong}>{nhanHuy}</Button>
      <Button variant={variant} size="sm" isLoading={dangLam} disabled={disabled} onClick={onXacNhan}>{nhan}</Button>
    </>
  );
}

export default function HanhDong({ hoSo, luot, maBamTepDangXem, onXong }: Props) {
  const { t, loi } = useSigningT();
  const { toi, taiLaiToi } = useToi();
  const navigate = useNavigate();
  const khoa = useKhoaChongTrung();
  const [mo, setMo] = useState<LoaiHopThoai>(null);
  const [o1, setO1] = useState('');
  const [o2, setO2] = useState('');
  const [pin, setPin] = useState('');
  const [moDatLaiPin, setMoDatLaiPin] = useState(false);
  const [datLaiPinThanhCong, setDatLaiPinThanhCong] = useState(false);
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState('');
  // Điều kiện ký: ảnh chữ ký cá nhân (trình duyệt) và khóa ký hoạt động (máy chủ). Kiểm lại mỗi lần mở hộp thoại ký.
  const [lanKiem, setLanKiem] = useState(0);
  const [ketQuaKiem, setKetQuaKiem] = useState<{ khoa: string; coKhoa: boolean; loi: unknown } | null>(null);
  const canhBaoThieuRef = useRef<HTMLDivElement>(null);
  const khoaKiem = `${toi?.id ?? ''}#${lanKiem}`;
  const dangKiem = !ketQuaKiem || ketQuaKiem.khoa !== khoaKiem;
  const loiKiem = !dangKiem ? ketQuaKiem.loi : null;
  const thieuAnh = !layAnhChuKyUrl(toi);
  const thieuKhoa = !dangKiem && !loiKiem && !ketQuaKiem.coKhoa;
  const hienThieu = !dangKiem && !loiKiem && (thieuAnh || thieuKhoa);
  // MFA qua email (#510): máy chủ bật cờ và access token hiện tại chưa xác thực thì phải nhập mã trước khi ký.
  const canMfa = Boolean(toi?.mfa_ky?.bat && !toi.mfa_ky.da_xac_thuc);
  const khoaNhap = dangKiem || Boolean(loiKiem) || thieuAnh || thieuKhoa || canMfa;

  useEffect(() => {
    if (mo !== 'ky' || !toi) return undefined;
    let huy = false;
    signingApi.khoa().then(
      (ds) => !huy && setKetQuaKiem({ khoa: khoaKiem, coKhoa: Boolean(khoaHoatDong(ds)), loi: null }),
      (err) => !huy && setKetQuaKiem({ khoa: khoaKiem, coKhoa: false, loi: err ?? new Error('loi_mang') }),
    );
    return () => {
      huy = true;
    };
  }, [mo, toi, khoaKiem]);

  useEffect(() => {
    if (hienThieu) canhBaoThieuRef.current?.querySelector('button')?.focus();
  }, [hienThieu]);

  const tenVanBan = moTaVanBan(hoSo.van_ban, t);

  const laNguoiTao = toi?.id === hoSo.create_by;
  const dangMoChoToi = hoSo.dang_cho.some((d) => d.nguoi_ky === toi?.id);
  const capDangKy = luot?.cap_ky.find((c) => c.trang_thai === 'DANG_KY');
  const daKyTrongCapMo = luot?.trang_thai === 'CHO_KY'
    && capDangKy?.nguoi_ky.some((n) => n.nguoi_ky === toi?.id && n.trang_thai === 'DA_KY');
  const huyDuoc = ['NHAP', 'CHO_KY'].includes(hoSo.trang_thai) && (laNguoiTao || coQuyen(toi, 'cancel_trinhky'));
  const maBamKhop = !luot || maBamTepDangXem === luot.ma_bam_tai_lieu;
  const dong = () => {
    setMo(null);
    setO1('');
    setO2('');
    setPin('');
    setDatLaiPinThanhCong(false);
    setThongBao('');
    khoa.lamMoi();
  };

  const thucHien = async (ham: () => Promise<HoSoChiTiet>) => {
    setDangLam(true);
    setThongBao('');
    try {
      const kq = await ham();
      dong();
      onXong(kq);
      return kq;
    } catch (err) {
      setThongBao(loi(err));
      // Token đã đổi (làm mới/đăng nhập lại) nên phiên mất xác thực: tải lại trạng thái để hiện bước nhập mã
      if (docLoi(err).code === 'mfa_chua_xac_thuc') taiLaiToi();
      return null;
    } finally {
      setDangLam(false);
    }
  };

  const ky = () => thucHien(async () => {
    if (!toi || !luot) throw new Error('khong_co_quyen');

    // 1. Kiểm tra ảnh chữ ký cá nhân (máy chủ cũng kiểm lại khi ký)
    if (!toi.co_anh_chu_ky) {
      throw new Error('chua_co_anh_chu_ky');
    }

    // 2. Kiểm tra khóa ký đang hoạt động
    const dsKhoa = await signingApi.khoa();
    const khoa_ky = khoaHoatDong(dsKhoa);
    if (!khoa_ky) {
      throw new Error('chua_co_khoa_ky');
    }

    // 3. PIN được gửi qua HTTPS; server giải mã khóa đã lưu và tạo chữ ký.
    if (!/^\d{6}$/.test(pin)) {
      throw new Error('pin_khong_hop_le');
    }

    return signingApi.ky(hoSo.id, khoa.lay(), {
      khoa_ky: khoa_ky.id, hash_tai_lieu: luot.ma_bam_tai_lieu, pin, ghi_chu_ky: o1,
    });
  });

  const nut = (loai: LoaiHopThoai, nhan: string, icon: string, variant: 'primary' | 'secondary' | 'danger' | 'outline' = 'secondary') => (
    <Button size="sm" variant={variant} icon={icon} onClick={() => {
      if (loai === 'ky') setLanKiem((n) => n + 1);
      setMo(loai);
    }}>{nhan}</Button>
  );



  return (
    <div className="flex flex-wrap gap-2">
      {hoSo.trang_thai === 'NHAP' && laNguoiTao && (
        <Button size="sm" icon="fa-paper-plane" onClick={() => navigate(`/approvals/tao-moi?ho_so=${hoSo.id}`)}>
          {t('tao.buoc2')}
        </Button>
      )}
      {dangMoChoToi && luot?.trang_thai === 'CHO_KY' && <>
        {nut('ky', t('hanhDong.kyDuyet'), 'fa-signature', 'primary')}
        {nut('sua', t('hanhDong.traLaiSua'), 'fa-rotate-left', 'outline')}
        {nut('tu_choi', t('hanhDong.khongDongY'), 'fa-ban', 'danger')}
      </>}
      {daKyTrongCapMo && nut('thu_hoi', t('hanhDong.thuHoi'), 'fa-eraser')}
      {huyDuoc && nut('huy', t('hanhDong.huy'), 'fa-xmark')}
      {hoSo.trang_thai === 'TU_CHOI' && laNguoiTao && coQuyen(toi, 'send_trinhky')
        && nut('trinh_lai', t('hanhDong.trinhLai'), 'fa-repeat')}

      <HopThoai
        moTieuDe={`${t('hanhDong.xacNhanTep')} ${tenVanBan}`}
        mo={mo === 'ky'}
        onDong={dong}
        dangXuLy={dangLam}
        chieuRong="620px"
        lopKhung="w-full max-w-2xl rounded-2xl border border-border-subtle bg-surface-elevated shadow-xl"
        chanDuoi={
          <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center">
            <div ref={canhBaoThieuRef} className="min-w-0 flex-1 text-xs" role={dangKiem || loiKiem || hienThieu ? 'status' : undefined}>
              {dangKiem && (
                <span className="flex items-center gap-1.5 text-secondary">
                  <i className="fa-solid fa-spinner fa-spin" aria-hidden="true" />{t('hanhDong.dangKiemDieuKien')}
                </span>
              )}
              {Boolean(loiKiem) && (
                <span className="flex flex-wrap items-center gap-x-2 text-danger">
                  <span className="flex items-center gap-1.5">
                    <i className="fa-solid fa-circle-exclamation" aria-hidden="true" />{loi(loiKiem)}
                  </span>
                  <button type="button" className="font-semibold text-primary hover:underline"
                    onClick={() => setLanKiem((n) => n + 1)}>{t('chung.thuLai')}</button>
                </span>
              )}
              {hienThieu && (
                <span className="flex flex-wrap items-center gap-x-2 text-warning-text">
                  <span className="flex items-start gap-1.5">
                    <i className="fa-solid fa-triangle-exclamation mt-0.5" aria-hidden="true" />
                    <span>
                      <span className="font-semibold">{t('hanhDong.thieuChuKyTieuDe')}</span>
                      {': '}
                      {thieuAnh && <span>{t('hanhDong.thieuAnhChuKy')}</span>}
                      {thieuAnh && thieuKhoa && '; '}
                      {thieuKhoa && <span>{t('hanhDong.thieuKhoaKy')}</span>}
                    </span>
                  </span>
                  <button type="button" className="font-semibold text-primary hover:underline" onClick={() => {
                    dong();
                    navigate('/approvals/khoa');
                  }}>
                    {t('hanhDong.diToiCauHinh', { muc: t('nav.khoaCuaToi') })}
                  </button>
                </span>
              )}
            </div>
            <div className="flex items-center justify-end gap-2.5">
          <NutXacNhan
            onXacNhan={ky}
            nhan={t('hanhDong.kyDuyet')}
            variant="primary"
            disabled={!maBamKhop || khoaNhap}
            dangLam={dangLam}
            onDong={dong}
            nhanHuy={t('chung.huyBo')}
          />
            </div>
          </div>
        }
      >
        <div className="space-y-4">
            {datLaiPinThanhCong && <ThongBao loai="thanh_cong">{t('khoa.datLaiPinXong')}</ThongBao>}
            {!maBamKhop && <ThongBao>{t('loi.ma_bam_khong_khop')}</ThongBao>}
            {canMfa && !dangKiem && !loiKiem && !hienThieu && <MfaKyBuoc onXacThuc={taiLaiToi} />}

          <TruongNhap nhan={t('hanhDong.nhapPin')} batBuoc>
              <input
                className={LOP_O_NHAP}
                type="password"
                inputMode="numeric"
                autoComplete="off"
                maxLength={6}
                disabled={khoaNhap}
                placeholder="••••••"
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && maBamKhop && !dangLam) {
                    e.preventDefault();
                    ky();
                  }
                }}
              />
          </TruongNhap>
          <div className="text-right">
            <button
              type="button"
              className="text-xs font-semibold text-primary hover:underline"
              disabled={dangLam}
              onClick={() => {
                dong();
                setMoDatLaiPin(true);
              }}
            >
              {t('khoa.quenPin')}
            </button>
          </div>
          <TruongNhap nhan={t('hanhDong.ghiChuKy')}>
            <input
              className={LOP_O_NHAP}
              maxLength={GIOI_HAN.ghiChu}
              disabled={khoaNhap}
              value={o1}
              onChange={(e) => setO1(e.target.value)}
              placeholder={t('hanhDong.ghiChuKy')}
            />
          </TruongNhap>


          {dangLam && <ThongBao loai="thong_tin">{t('hanhDong.dangKy')}</ThongBao>}
          {thongBao && <ThongBao>{thongBao}</ThongBao>}
          {thongBao && (
            thongBao === t('loi.chua_co_khoa_ky') ||
            thongBao === t('loi.chua_co_anh_chu_ky')
          ) && (
            <div className="pt-1">
              <Button size="sm" variant="outline" icon="fa-arrow-right" onClick={() => navigate('/approvals/khoa')}>
                {t('hanhDong.caiDatKhoaVaChuKy')}
              </Button>
            </div>
          )}
        </div>
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.traLaiSua')} mo={mo === 'sua'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={
          <NutXacNhan
            onXacNhan={() => thucHien(() => signingApi.yeuCauSua(hoSo.id, khoa.lay(), o1, o2))}
            nhan={t('hanhDong.traLaiSua')}
            variant="primary"
            disabled={!o1.trim() || !o2.trim()}
            dangLam={dangLam}
            onDong={dong}
            nhanHuy={t('chung.huyBo')}
          />
        }>
        <TruongNhap nhan={t('hanhDong.tieuDeSua')}>
          <input className={LOP_O_NHAP} maxLength={255} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        <TruongNhap nhan={t('hanhDong.lyDoSua')}>
          <textarea className={LOP_O_NHAP} rows={4} maxLength={GIOI_HAN.lyDo} value={o2} onChange={(e) => setO2(e.target.value)} />
        </TruongNhap>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.khongDongY')} mo={mo === 'tu_choi'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={
          <NutXacNhan
            onXacNhan={() => thucHien(() => signingApi.tuChoi(hoSo.id, khoa.lay(), o1))}
            nhan={t('hanhDong.khongDongY')}
            variant="danger"
            disabled={!o1.trim()}
            dangLam={dangLam}
            onDong={dong}
            nhanHuy={t('chung.huyBo')}
          />
        }>
        <div className="rounded-lg border border-warning bg-warning-subtle/30 p-3 text-xs text-warning-text space-y-2">
          <div className="flex items-start gap-2">
            <i className="fa-solid fa-triangle-exclamation mt-0.5 shrink-0 text-warning" aria-hidden="true" />
            <p className="leading-relaxed">{t('hanhDong.canhBaoTuChoi')}</p>
          </div>
          <button
            type="button"
            className="text-primary hover:underline font-semibold flex items-center gap-1.5 pt-1"
            onClick={() => {
              setMo('sua');
              setO1('');
              setO2('');
              setThongBao('');
            }}
          >
            <i className="fa-solid fa-arrow-right-arrow-left text-xs" aria-hidden="true" />
            <span>{t('hanhDong.chuyenSangTraSua')}</span>
          </button>
        </div>
        <TruongNhap nhan={t('hanhDong.lyDoTuChoi')}>
          <textarea className={LOP_O_NHAP} rows={4} maxLength={GIOI_HAN.lyDo} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.thuHoi')} mo={mo === 'thu_hoi'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={
          <NutXacNhan
            onXacNhan={() => thucHien(() => signingApi.thuHoi(hoSo.id, khoa.lay()))}
            nhan={t('hanhDong.thuHoi')}
            dangLam={dangLam}
            onDong={dong}
            nhanHuy={t('chung.huyBo')}
          />
        }>
        <p className="text-sm text-main">{t('hanhDong.xacNhanThuHoi')}</p>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.huy')} mo={mo === 'huy'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={
          <NutXacNhan
            onXacNhan={() => thucHien(() => signingApi.huy(hoSo.id, khoa.lay(), o1))}
            nhan={t('hanhDong.huy')}
            variant="danger"
            disabled={!laNguoiTao && !o1.trim()}
            dangLam={dangLam}
            onDong={dong}
            nhanHuy={t('chung.huyBo')}
          />
        }>
        <TruongNhap nhan={t('hanhDong.lyDoHuy')} ghiChu={laNguoiTao ? undefined : t('chung.batBuoc')}>
          <textarea className={LOP_O_NHAP} rows={3} maxLength={GIOI_HAN.lyDo} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.trinhLai')} mo={mo === 'trinh_lai'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={
          <NutXacNhan
            onXacNhan={async () => {
              const moi = await thucHien(() => signingApi.trinhLai(hoSo.id, khoa.lay()));
              if (moi) navigate(`/approvals/tao-moi?ho_so=${moi.id}`);
            }}
            nhan={t('chung.xacNhan')}
            dangLam={dangLam}
            onDong={dong}
            nhanHuy={t('chung.huyBo')}
          />
        }>
        <p className="text-sm text-main">{t('hanhDong.xacNhanTrinhLai')}</p>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>
      <DatLaiPinDialog
        mo={moDatLaiPin}
        onDong={() => setMoDatLaiPin(false)}
        onXong={(pin_moi) => {
          setMoDatLaiPin(false);
          setPin(pin_moi);
          setThongBao('');
          setDatLaiPinThanhCong(true);
          setMo('ky');
        }}
      />
    </div>
  );
}
