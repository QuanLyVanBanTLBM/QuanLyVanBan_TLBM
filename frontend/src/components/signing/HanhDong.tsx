/**
 * Hành động trên hồ sơ theo quyền và trạng thái (#80 mục B, C, E): ký duyệt bằng file khóa (hoặc khóa lưu trên
 * thiết bị) + PIN, trả lại để sửa, không đồng ý ban hành, thu hồi chữ ký, ủy quyền ký, hủy, trình lại. Mỗi lần mở hộp thoại dùng một Idempotency-Key;
 * bấm lại hoặc thử lại sau lỗi mạng không tạo thao tác trùng.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@components/common';
import { signingApi } from '@lib/signing/api';
import { GIOI_HAN, LOP_O_NHAP, moTaVanBan } from '@lib/signing/dinhDang';
import { coQuyen, useKhoaChongTrung, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import { docFileKhoaTuTep, DUOI_FILE_KHOA } from '@lib/signing/fileKhoa';
import type { BanBocKhoa } from '@lib/signing/khoaKy';
import { khoaHoatDong, kyBangPin } from '@lib/signing/luongKhoa';
import type { HoSoChiTiet, LuotTrinh, NguoiDungTim } from '@lib/signing/types';
import { HopThoai, OChonTep, ThongBao, TruongNhap } from './ChungUI';

type LoaiHopThoai = 'ky' | 'sua' | 'tu_choi' | 'thu_hoi' | 'huy' | 'trinh_lai' | 'uy_quyen' | null;

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
  const [fileKhoa, setFileKhoa] = useState<BanBocKhoa | null>(null);
  const [dongUyQuyen, setDongUyQuyen] = useState('');
  const [timNhan, setTimNhan] = useState('');
  const [ungVien, setUngVien] = useState<NguoiDungTim[]>([]);
  const [dangTimNhan, setDangTimNhan] = useState(false);
  const [loiTimNhan, setLoiTimNhan] = useState<unknown>(null);
  const [nguoiNhan, setNguoiNhan] = useState('');
  const tenVanBan = moTaVanBan(hoSo.van_ban, t);

  const laNguoiTao = toi?.id === hoSo.create_by;
  const dangMoChoToi = hoSo.dang_cho.some((d) => d.nguoi_ky === toi?.id);
  const capDangKy = luot?.cap_ky.find((c) => c.trang_thai === 'DANG_KY');
  const daKyTrongCapMo = luot?.trang_thai === 'CHO_KY'
    && capDangKy?.nguoi_ky.some((n) => n.nguoi_ky === toi?.id && n.trang_thai === 'DA_KY');
  const huyDuoc = ['NHAP', 'CHO_KY'].includes(hoSo.trang_thai) && (laNguoiTao || coQuyen(toi, 'cancel_trinhky'));
  const maBamKhop = !luot || maBamTepDangXem === luot.ma_bam_tai_lieu;
  // Người ký còn chờ ký (cấp đang ký hoặc chưa mở) của lượt hiện hành: đối tượng ủy quyền khẩn cấp
  const choUyQuyen = luot?.trang_thai === 'CHO_KY' && coQuyen(toi, 'delegate_trinhky')
    ? luot.cap_ky.filter((c) => c.trang_thai === 'DANG_KY' || c.trang_thai === 'CHUA_MO')
      .flatMap((c) => c.nguoi_ky.filter((n) => n.trang_thai === 'CHO_KY' && n.co_the_uy_quyen === true)
        .map((n) => ({ ...n, ten_cap: `${c.cap_ky}. ${c.ten_cap_ky}` })))
    : [];

  useEffect(() => {
    if (mo !== 'uy_quyen' || !dongUyQuyen) return undefined;
    let huy = false;
    const hen = setTimeout(() => {
      signingApi.timNguoiNhanUyQuyen(timNhan, hoSo.id, Number(dongUyQuyen))
        .then((ds) => { if (!huy) setUngVien(ds); })
        .catch((err) => { if (!huy) { setUngVien([]); setLoiTimNhan(err); } })
        .finally(() => { if (!huy) setDangTimNhan(false); });
    }, 250);
    return () => {
      huy = true;
      clearTimeout(hen);
    };
  }, [mo, timNhan, dongUyQuyen, hoSo.id]);

  const dong = () => {
    setMo(null);
    setO1('');
    setO2('');
    setPin('');
    setThongBao('');
    setFileKhoa(null);
    setDongUyQuyen('');
    setTimNhan('');
    setNguoiNhan('');
    setDangTimNhan(false);
    setUngVien([]);
    setLoiTimNhan(null);
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
    if (!toi || !luot) throw new Error('khong_co_quyen');
    const khoa_ky = khoaHoatDong(await signingApi.khoa());
    if (!khoa_ky) throw new Error('thieu_ban_boc_thiet_bi');
    const chu_ky_so = await kyBangPin(toi.id, khoa_ky, pin, luot.ma_bam_tai_lieu, fileKhoa ?? undefined);
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
      {choUyQuyen.length > 0 && nut('uy_quyen', t('hanhDong.uyQuyen'), 'fa-user-group')}
      {huyDuoc && nut('huy', t('hanhDong.huy'), 'fa-xmark')}
      {hoSo.trang_thai === 'TU_CHOI' && laNguoiTao && coQuyen(toi, 'send_trinhky')
        && nut('trinh_lai', t('hanhDong.trinhLai'), 'fa-repeat')}

      <HopThoai moTieuDe={t('hanhDong.kyDuyet')} mo={mo === 'ky'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={nutXacNhan(ky, t('hanhDong.kyDuyet'), 'primary', !maBamKhop || pin.length !== 8)}>
        <div className="text-sm text-main">{t('hanhDong.xacNhanTep')} <b>{tenVanBan}</b></div>
        {!maBamKhop && <ThongBao>{t('loi.ma_bam_khong_khop')}</ThongBao>}
        <TruongNhap nhan={t('hanhDong.ghiChuKy')}>
          <input className={LOP_O_NHAP} maxLength={GIOI_HAN.ghiChu} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        <TruongNhap nhan={t('hanhDong.fileKhoa')} ghiChu={t('hanhDong.fileKhoaGhiChu')}>
          <OChonTep accept={`${DUOI_FILE_KHOA},application/json`} nhan={t('hanhDong.fileKhoa')}
            onChon={(tep) => {
              setFileKhoa(null);
              setThongBao('');
              if (tep) docFileKhoaTuTep(tep).then(setFileKhoa, (err) => setThongBao(loi(err)));
            }} />
        </TruongNhap>
        {fileKhoa && <ThongBao loai="thong_tin">{t('hanhDong.daChonFile')}</ThongBao>}
        <TruongNhap nhan={t('hanhDong.nhapPin')}>
          <input className={LOP_O_NHAP} type="password" inputMode="numeric" autoComplete="off" maxLength={8}
            value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && pin.length === 8 && maBamKhop && !dangLam) {
                e.preventDefault();
                ky();
              }
            }} />
        </TruongNhap>
        {dangLam && <ThongBao loai="thong_tin">{t('hanhDong.dangKy')}</ThongBao>}
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
        {thongBao === t('loi.thieu_ban_boc_thiet_bi') && (
          <Button size="sm" variant="outline" icon="fa-key" onClick={() => navigate('/approvals/khoa')}>
            {t('nav.khoaCuaToi')}
          </Button>
        )}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.traLaiSua')} mo={mo === 'sua'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={nutXacNhan(() => thucHien(() => signingApi.yeuCauSua(hoSo.id, khoa.lay(), o1, o2)),
          t('hanhDong.traLaiSua'), 'primary', !o1.trim() || !o2.trim())}>
        <TruongNhap nhan={t('hanhDong.tieuDeSua')}>
          <input className={LOP_O_NHAP} maxLength={255} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        <TruongNhap nhan={t('hanhDong.lyDoSua')}>
          <textarea className={LOP_O_NHAP} rows={4} maxLength={GIOI_HAN.lyDo} value={o2} onChange={(e) => setO2(e.target.value)} />
        </TruongNhap>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.khongDongY')} mo={mo === 'tu_choi'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={nutXacNhan(() => thucHien(() => signingApi.tuChoi(hoSo.id, khoa.lay(), o1)),
          t('hanhDong.khongDongY'), 'danger', !o1.trim())}>
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
        chanDuoi={nutXacNhan(() => thucHien(() => signingApi.thuHoi(hoSo.id, khoa.lay())), t('hanhDong.thuHoi'))}>
        <p className="text-sm text-main">{t('hanhDong.xacNhanThuHoi')}</p>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.uyQuyen')} mo={mo === 'uy_quyen'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={nutXacNhan(() => thucHien(() => signingApi.uyQuyen(hoSo.id, khoa.lay(), {
          dong_nguoi_ky: Number(dongUyQuyen), nguoi_nhan: Number(nguoiNhan), ly_do_uy_quyen: o1,
        })), t('hanhDong.uyQuyen'), 'primary', !dongUyQuyen || !nguoiNhan || !o1.trim())}>
        <TruongNhap nhan={t('hanhDong.nguoiDuocUyQuyen')}>
          <select className={LOP_O_NHAP} aria-label={t('hanhDong.nguoiDuocUyQuyen')} value={dongUyQuyen}
            onChange={(e) => { setDongUyQuyen(e.target.value); setDangTimNhan(Boolean(e.target.value)); setNguoiNhan(''); setUngVien([]); setThongBao(''); setLoiTimNhan(null); }}>
            <option value="">{t('chung.chon')}</option>
            {choUyQuyen.map((n) => (
              <option key={n.id} value={n.id}>{n.ten_nguoi_ky} · {n.ten_cap}</option>
            ))}
          </select>
        </TruongNhap>
        <TruongNhap nhan={t('hanhDong.nguoiNhanUyQuyen')}>
          <input className={LOP_O_NHAP} placeholder={t('hanhDong.timNguoiNhan')} aria-label={t('hanhDong.timNguoiNhan')}
            value={timNhan}
            onChange={(e) => { setTimNhan(e.target.value); setDangTimNhan(Boolean(dongUyQuyen)); setNguoiNhan(''); setLoiTimNhan(null); }} />
          {dongUyQuyen && <div className="mt-2 max-h-48 overflow-y-auto rounded-lg border border-border-subtle" role="group" aria-label={t('hanhDong.nguoiNhanUyQuyen')}>
            {dangTimNhan ? <p className="p-3 text-sm text-muted">{t('chung.dangTai')}</p> : ungVien.length === 0 && loiTimNhan == null && <p className="p-3 text-sm text-muted">{t('hanhDong.khongCoNguoiNhan')}</p>}
            {!dangTimNhan && ungVien.map((u) => <button type="button" key={u.id} onClick={() => setNguoiNhan(String(u.id))} aria-pressed={nguoiNhan === String(u.id)}
              className={`block w-full border-b border-border-subtle p-2 text-left ${nguoiNhan === String(u.id) ? 'bg-primary-subtle' : 'hover:bg-surface-hover'}`}>
              <span className="block text-sm font-semibold">{u.chuc_vu || t('hanhDong.chuaCoChucDanh')}</span>
              <span className="block text-xs text-secondary">{[u.ten, u.don_vi].filter(Boolean).join(' · ')}</span>
            </button>)}
          </div>}
        </TruongNhap>
        {loiTimNhan != null && <ThongBao>{loi(loiTimNhan)}</ThongBao>}
        <TruongNhap nhan={t('hanhDong.lyDoUyQuyen')}>
          <textarea className={LOP_O_NHAP} rows={3} maxLength={GIOI_HAN.lyDo} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.huy')} mo={mo === 'huy'} onDong={dong} dangXuLy={dangLam}
        chanDuoi={nutXacNhan(() => thucHien(() => signingApi.huy(hoSo.id, khoa.lay(), o1)), t('hanhDong.huy'),
          'danger', !laNguoiTao && !o1.trim())}>
        <TruongNhap nhan={t('hanhDong.lyDoHuy')} ghiChu={laNguoiTao ? undefined : t('chung.batBuoc')}>
          <textarea className={LOP_O_NHAP} rows={3} maxLength={GIOI_HAN.lyDo} value={o1} onChange={(e) => setO1(e.target.value)} />
        </TruongNhap>
        {thongBao && <ThongBao>{thongBao}</ThongBao>}
      </HopThoai>

      <HopThoai moTieuDe={t('hanhDong.trinhLai')} mo={mo === 'trinh_lai'} onDong={dong} dangXuLy={dangLam}
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
