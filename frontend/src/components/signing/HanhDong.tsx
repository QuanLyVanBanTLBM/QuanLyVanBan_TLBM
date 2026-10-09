/**
 * Hành động trên hồ sơ theo quyền và trạng thái (#80 mục B, C, E): ký duyệt bằng PIN, trả lại để sửa,
 * không đồng ý ban hành, thu hồi chữ ký, hủy, trình lại. Mỗi lần mở hộp thoại dùng một Idempotency-Key;
 * bấm lại hoặc thử lại sau lỗi mạng không tạo thao tác trùng.
 */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@components/common';
import { signingApi } from '@lib/signing/api';
import { LOP_O_NHAP } from '@lib/signing/dinhDang';
import { coQuyen, useKhoaChongTrung, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import { khoaHoatDong, kyBangPin } from '@lib/signing/luongKhoa';
import type { HoSoChiTiet, LuotTrinh } from '@lib/signing/types';
import { HopThoai, ThongBao, TruongNhap } from './ChungUI';

type LoaiHopThoai = 'ky' | 'sua' | 'tu_choi' | 'thu_hoi' | 'huy' | 'trinh_lai' | null;

interface Props {
  hoSo: HoSoChiTiet;
  luot: LuotTrinh | null;
  /** SHA-256 tính lại trên tệp đang hiển thị (null khi chưa tải xong) */
  maBamTepDangXem: string | null;
  onXong: (ho_so?: HoSoChiTiet) => void;
}

export default function HanhDong({ hoSo, luot, maBamTepDangXem, onXong }: Props) {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const navigate = useNavigate();
  const khoa = useKhoaChongTrung();
  const [mo, setMo] = useState<LoaiHopThoai>(null);
  const [o1, setO1] = useState('');
  const [o2, setO2] = useState('');
  const [pin, setPin] = useState('');
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState('');

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
      return null;
    } finally {
      setDangLam(false);
    }
  };

  const ky = () => thucHien(async () => {
    const khoa_ky = khoaHoatDong(await signingApi.khoa());
    if (!khoa_ky) throw new Error('thieu_ban_boc_thiet_bi');
    const chu_ky_so = await kyBangPin(toi.id, khoa_ky, pin, luot.ma_bam_tai_lieu);
    return signingApi.ky(hoSo.id, khoa.lay(), {
      khoa_ky: khoa_ky.id, hash_tai_lieu: luot.ma_bam_tai_lieu, chu_ky_so, ghi_chu_ky: o1,
    });
  });

  const nut = (loai: LoaiHopThoai, nhan: string, icon: string, variant: 'primary' | 'secondary' | 'danger' | 'outline' = 'secondary') => (
    <Button size="sm" variant={variant} icon={icon} onClick={() => setMo(loai)}>{nhan}</Button>
  );

  const nutXacNhan = (ham: () => void, nhan: string, variant: 'primary' | 'danger' = 'primary', tat = false) => (
    <>
      <Button variant="secondary" onClick={dong}>{t('chung.huyBo')}</Button>
      <Button variant={variant} isLoading={dangLam} disabled={tat} onClick={ham}>{nhan}</Button>
    </>
  );

  return (
    <div className="flex flex-wrap gap-2">
      {hoSo.trang_thai === 'NHAP' && laNguoiTao && (
        <Link to={`/approvals/tao-moi?ho_so=${hoSo.id}`}>
          <Button size="sm" icon="fa-paper-plane">{t('tao.buoc2')}</Button>
        </Link>
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

      <HopThoai moTieuDe={t('hanhDong.kyDuyet')} mo={mo === 'ky'} onDong={dong}
        chanDuoi={nutXacNhan(ky, t('hanhDong.kyDuyet'), 'primary', !maBamKhop || pin.length !== 8)}>
        <div className="text-sm text-main">{t('hanhDong.xacNhanTep')} <b>trinh-ky-{hoSo.id}.pdf</b></div>
        <div className="text-xs text-secondary break-all">{t('tao.maBam')}: <code>{luot?.ma_bam_tai_lieu}</code></div>
        {!maBamKhop && <ThongBao>{t('loi.ma_bam_khong_khop')}</ThongBao>}
        <TruongNhap nhan={t('hanhDong.ghiChuKy')}>
          <input className={LOP_O_NHAP} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        <TruongNhap nhan={t('hanhDong.nhapPin')}>
          <input className={LOP_O_NHAP} type="password" inputMode="numeric" autoComplete="off" maxLength={8}
            value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))} />
        </TruongNhap>
        {dangLam && <ThongBao loai="thong_tin">{t('hanhDong.dangKy')}</ThongBao>}
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
        {thongBao === t('loi.thieu_ban_boc_thiet_bi') && (
          <Button size="sm" variant="outline" icon="fa-key" onClick={() => navigate('/approvals/khoa')}>
            {t('nav.khoaCuaToi')}
          </Button>
        )}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.traLaiSua')} mo={mo === 'sua'} onDong={dong}
        chanDuoi={nutXacNhan(() => thucHien(() => signingApi.yeuCauSua(hoSo.id, khoa.lay(), o1, o2)),
          t('hanhDong.traLaiSua'), 'primary', !o1.trim() || !o2.trim())}>
        <TruongNhap nhan={t('hanhDong.tieuDeSua')}>
          <input className={LOP_O_NHAP} maxLength={255} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        <TruongNhap nhan={t('hanhDong.lyDoSua')}>
          <textarea className={LOP_O_NHAP} rows={4} value={o2} onChange={(e) => setO2(e.target.value)} />
        </TruongNhap>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.khongDongY')} mo={mo === 'tu_choi'} onDong={dong}
        chanDuoi={nutXacNhan(() => thucHien(() => signingApi.tuChoi(hoSo.id, khoa.lay(), o1)),
          t('hanhDong.khongDongY'), 'danger', !o1.trim())}>
        <TruongNhap nhan={t('hanhDong.lyDoTuChoi')}>
          <textarea className={LOP_O_NHAP} rows={4} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.thuHoi')} mo={mo === 'thu_hoi'} onDong={dong}
        chanDuoi={nutXacNhan(() => thucHien(() => signingApi.thuHoi(hoSo.id, khoa.lay())), t('hanhDong.thuHoi'))}>
        <p className="text-sm text-main">{t('hanhDong.xacNhanThuHoi')}</p>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.huy')} mo={mo === 'huy'} onDong={dong}
        chanDuoi={nutXacNhan(() => thucHien(() => signingApi.huy(hoSo.id, khoa.lay(), o1)), t('hanhDong.huy'),
          'danger', !laNguoiTao && !o1.trim())}>
        <TruongNhap nhan={t('hanhDong.lyDoHuy')} ghiChu={laNguoiTao ? undefined : t('chung.batBuoc')}>
          <textarea className={LOP_O_NHAP} rows={3} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.trinhLai')} mo={mo === 'trinh_lai'} onDong={dong}
        chanDuoi={nutXacNhan(async () => {
          const moi = await thucHien(() => signingApi.trinhLai(hoSo.id, khoa.lay()));
          if (moi) navigate(`/approvals/tao-moi?ho_so=${moi.id}`);
        }, t('chung.xacNhan'))}>
        <p className="text-sm text-main">{t('hanhDong.xacNhanTrinhLai')}</p>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>
    </div>
  );
}
