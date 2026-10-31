/**
 * Hành động trên hồ sơ theo quyền và trạng thái (#80 mục B, C, E): ký duyệt bằng file khóa (hoặc khóa lưu trên
 * thiết bị) + PIN, trả lại để sửa, không đồng ý ban hành, thu hồi chữ ký, hủy, trình lại. Mỗi lần mở hộp thoại dùng một Idempotency-Key;
 * bấm lại hoặc thử lại sau lỗi mạng không tạo thao tác trùng.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@components/common';
import { signingApi } from '@lib/signing/api';
import { GIOI_HAN, LOP_O_NHAP, moTaVanBan } from '@lib/signing/dinhDang';
import { coQuyen, useKhoaChongTrung, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import { docFileKhoaTuTep, DUOI_FILE_KHOA } from '@lib/signing/fileKhoa';
import type { BanBocKhoa } from '@lib/signing/khoaKy';
import { khoaHoatDong, kyBangPin } from '@lib/signing/luongKhoa';
import type { HoSoChiTiet, LuotTrinh } from '@lib/signing/types';
import { HopThoai, OChonFileKhoa, ThongBao, TruongNhap } from './ChungUI';

const docAnhChuKy = (id: number): string | null => {
  try {
    return localStorage.getItem(`tlbm_user_sig_${id}`);
  } catch {
    return null;
  }
};

const coAnhChuKy = (toi: { id: number; co_anh_chu_ky?: boolean } | null): boolean => {
  return Boolean(toi?.co_anh_chu_ky || (toi ? docAnhChuKy(toi.id) : null));
};

const layAnhChuKyUrl = (toi: { id: number; co_anh_chu_ky?: boolean } | null): string | null => {
  if (!toi) return null;
  if (toi.co_anh_chu_ky) return `/api/signing/anh-chu-ky-ca-nhan/tep/?v=${toi.id}`;
  return docAnhChuKy(toi.id);
};

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
  const [fileKhoaRaw, setFileKhoaRaw] = useState<File | null>(null);
  const [coFileTrenManHinh, setCoFileTrenManHinh] = useState(false);
  const [vaoPhamViModal, setVaoPhamViModal] = useState(false);
  const modalDragCountRef = useRef(0);
  // Điều kiện ký: ảnh chữ ký cá nhân (trình duyệt) và khóa ký hoạt động (máy chủ). Kiểm lại mỗi lần mở hộp thoại ký.
  const [lanKiem, setLanKiem] = useState(0);
  const [ketQuaKiem, setKetQuaKiem] = useState<{ khoa: string; coKhoa: boolean; loi: unknown } | null>(null);
  const canhBaoThieuRef = useRef<HTMLDivElement>(null);
  const khoaKiem = `${toi?.id ?? ''}#${lanKiem}`;
  const dangKiem = !ketQuaKiem || ketQuaKiem.khoa !== khoaKiem;
  const loiKiem = !dangKiem ? ketQuaKiem.loi : null;
  const anhChuKy = layAnhChuKyUrl(toi);
  const thieuAnh = !anhChuKy;
  const thieuKhoa = !dangKiem && !loiKiem && !ketQuaKiem.coKhoa;
  const hienThieu = !dangKiem && !loiKiem && (thieuAnh || thieuKhoa);
  const khoaNhap = dangKiem || Boolean(loiKiem) || thieuAnh || thieuKhoa;

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

  // Lắng nghe thao tác kéo tệp trên toàn màn hình để modal phản ứng hứng file
  useEffect(() => {
    if (mo !== 'ky' || khoaNhap) return undefined;

    let dragCount = 0;

    const onWindowDragEnter = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes('Files')) {
        dragCount++;
        if (dragCount === 1) setCoFileTrenManHinh(true);
      }
    };

    const onWindowDragLeave = () => {
      dragCount--;
      if (dragCount <= 0) {
        dragCount = 0;
        setCoFileTrenManHinh(false);
        setVaoPhamViModal(false);
      }
    };

    const onWindowDragOver = (e: DragEvent) => {
      if (e.dataTransfer?.types?.includes('Files')) {
        e.preventDefault();
      }
    };

    const onWindowDrop = () => {
      dragCount = 0;
      setCoFileTrenManHinh(false);
      setVaoPhamViModal(false);
    };

    window.addEventListener('dragenter', onWindowDragEnter);
    window.addEventListener('dragleave', onWindowDragLeave);
    window.addEventListener('dragover', onWindowDragOver);
    window.addEventListener('drop', onWindowDrop);

    return () => {
      window.removeEventListener('dragenter', onWindowDragEnter);
      window.removeEventListener('dragleave', onWindowDragLeave);
      window.removeEventListener('dragover', onWindowDragOver);
      window.removeEventListener('drop', onWindowDrop);
    };
  }, [mo, khoaNhap]);
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
    setThongBao('');
    setFileKhoa(null);
    setFileKhoaRaw(null);
    setCoFileTrenManHinh(false);
    setVaoPhamViModal(false);
    modalDragCountRef.current = 0;
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

    // 1. Kiểm tra ảnh chữ ký cá nhân (Issue #424)
    if (!coAnhChuKy(toi)) {
      throw new Error('chua_co_anh_chu_ky');
    }

    // 2. Kiểm tra khóa ký đang hoạt động
    const dsKhoa = await signingApi.khoa();
    const khoa_ky = khoaHoatDong(dsKhoa);
    if (!khoa_ky) {
      throw new Error('chua_co_khoa_ky');
    }

    // 3. Kiểm tra mã PIN 8 chữ số
    if (!pin || pin.length !== 8) {
      throw new Error('pin_khong_hop_le');
    }

    // 4. Ký số bằng private key từ PIN và bản bọc (hoặc file khóa)
    const chu_ky_so = await kyBangPin(toi.id, khoa_ky, pin, luot.ma_bam_tai_lieu, fileKhoa ?? undefined);
    return signingApi.ky(hoSo.id, khoa.lay(), {
      khoa_ky: khoa_ky.id, hash_tai_lieu: luot.ma_bam_tai_lieu, chu_ky_so, ghi_chu_ky: o1,
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
        lopKhung={`w-full max-w-2xl rounded-2xl bg-surface-elevated transition-all relative overflow-hidden ${
          coFileTrenManHinh
            ? 'border-2 border-dashed border-primary shadow-2xl ring-4 ring-primary/20'
            : 'border border-border-subtle shadow-xl'
        }`}
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
        <div
          className="relative"
          onDragEnter={(e) => {
            e.preventDefault();
            e.stopPropagation();
            if (khoaNhap) return;
            modalDragCountRef.current++;
            if (modalDragCountRef.current === 1) setVaoPhamViModal(true);
          }}
          onDragOver={(e) => {
            e.preventDefault();
            e.stopPropagation();
            if (khoaNhap) return;
            if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
            if (!vaoPhamViModal) setVaoPhamViModal(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            e.stopPropagation();
            modalDragCountRef.current--;
            if (modalDragCountRef.current <= 0) {
              modalDragCountRef.current = 0;
              setVaoPhamViModal(false);
            }
          }}
          onDrop={(e) => {
            e.preventDefault();
            e.stopPropagation();
            modalDragCountRef.current = 0;
            setCoFileTrenManHinh(false);
            setVaoPhamViModal(false);
            if (khoaNhap) return;
            const tep = e.dataTransfer.files?.[0];
            if (tep) {
              setFileKhoa(null);
              setFileKhoaRaw(tep);
              setThongBao('');
              docFileKhoaTuTep(tep).then(setFileKhoa, (err) => setThongBao(loi(err)));
            }
          }}
        >
          {/* Trạng thái 2: File nằm trong phạm vi modal -> Lớp phủ chuyển sang màu xanh dương nhạt (không có text mô tả) */}
          {vaoPhamViModal && (
            <div className="pointer-events-none absolute -inset-4 z-50 bg-primary-subtle/80 dark:bg-primary/25 backdrop-blur-xs transition-colors animate-in fade-in duration-150" />
          )}

          <div className={coFileTrenManHinh ? "space-y-4 opacity-30 transition-opacity pointer-events-none" : "space-y-4 transition-opacity"}>
            {!maBamKhop && <ThongBao>{t('loi.ma_bam_khong_khop')}</ThongBao>}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 items-start">
            <TruongNhap nhan={t('hanhDong.fileKhoa')} batBuoc>
              <OChonFileKhoa
                accept={`${DUOI_FILE_KHOA},application/json`}
                nhan={t('hanhDong.fileKhoa')}
                tepDaChon={fileKhoaRaw}
                disabled={khoaNhap}
                onChon={(tep) => {
                  setFileKhoa(null);
                  setFileKhoaRaw(tep ?? null);
                  setThongBao('');
                  if (tep) docFileKhoaTuTep(tep).then(setFileKhoa, (err) => setThongBao(loi(err)));
                }}
              />
            </TruongNhap>

            <TruongNhap nhan={t('hanhDong.nhapPin')} batBuoc>
              <input
                className={LOP_O_NHAP}
                type="password"
                inputMode="numeric"
                autoComplete="off"
                maxLength={8}
                disabled={khoaNhap}
                placeholder="••••••••"
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
          </div>
          {fileKhoa && <ThongBao loai="thong_tin">{t('hanhDong.daChonFile')}</ThongBao>}

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

          {/* Hiển thị ảnh chữ ký cá nhân áp dụng nếu đã có */}
          {anhChuKy && (
              <div className="flex items-center justify-between p-3 rounded-lg border border-border-subtle bg-surface-subtle">
                <span className="text-xs text-secondary font-medium">{t('hanhDong.anhChuKySeDung')}</span>
                <div
                  className="px-2 py-1 rounded border border-border-subtle bg-white"
                  style={{
                    backgroundImage:
                      'linear-gradient(45deg, #f0f0f0 25%, transparent 25%), linear-gradient(-45deg, #f0f0f0 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #f0f0f0 75%), linear-gradient(-45deg, transparent 75%, #f0f0f0 75%)',
                    backgroundSize: '8px 8px',
                  }}
                >
                  <img src={anhChuKy} alt="Chữ ký cá nhân" className="h-8 max-w-[120px] object-contain" />
                </div>
              </div>
            )}

          {dangLam && <ThongBao loai="thong_tin">{t('hanhDong.dangKy')}</ThongBao>}
          {thongBao && <ThongBao>{thongBao}</ThongBao>}
          {thongBao && (
            thongBao === t('loi.thieu_ban_boc_thiet_bi') ||
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
    </div>
  );
}
