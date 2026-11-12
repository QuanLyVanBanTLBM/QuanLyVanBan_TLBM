/**
 * Thay người ký (#500, phân vùng 3 của #447): người tạo hoặc quản trị viên thay người ký đang chờ có quyền ký bị khóa.
 * Danh sách ứng viên do máy chủ lọc (quyền ký, khóa quyền ký, trùng cấp, thứ bậc chức vụ); lý do bắt buộc.
 */
import { useEffect, useState } from 'react';
import { Button } from '@components/common';
import { signingApi } from '@lib/signing/api';
import { GIOI_HAN, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { useTai } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { HoSoChiTiet, NguoiKyLuot } from '@lib/signing/types';
import { DangTai, HopThoai, LoiTai, ThongBao, TruongNhap } from './ChungUI';

interface Props {
  hoSo: HoSoChiTiet;
  /** Các người ký máy chủ báo có thể thay (cờ `co_the_thay`). */
  nguoiKyThayDuoc: NguoiKyLuot[];
  onDong: () => void;
  onXong: (hoSo: HoSoChiTiet) => void;
}

export default function ThayNguoiKyDialog({ hoSo, nguoiKyThayDuoc, onDong, onXong }: Props) {
  const { t, loi } = useSigningT();
  const [nguoiKyId, setNguoiKyId] = useState(nguoiKyThayDuoc[0]?.id ?? 0);
  const [q, setQ] = useState('');
  const [qTim, setQTim] = useState('');
  const [nguoiMoiId, setNguoiMoiId] = useState('');
  const [lyDo, setLyDo] = useState('');
  const [dangLam, setDangLam] = useState(false);
  const [loiGui, setLoiGui] = useState<unknown>(null);

  useEffect(() => {
    const hen = setTimeout(() => setQTim(q.trim()), 300);
    return () => clearTimeout(hen);
  }, [q]);

  const ungVien = useTai(() => signingApi.ungVienThayNguoiKy(hoSo.id, nguoiKyId, qTim), [hoSo.id, nguoiKyId, qTim]);
  const danhSach = ungVien.duLieu ?? [];
  const chonHopLe = danhSach.some((u) => String(u.id) === nguoiMoiId);

  const gui = async () => {
    if (!chonHopLe || !lyDo.trim() || dangLam) return;
    setDangLam(true);
    setLoiGui(null);
    try {
      onXong(await signingApi.thayNguoiKy(hoSo.id, {
        nguoi_ky_id: nguoiKyId, nguoi_ky_moi_id: Number(nguoiMoiId), ly_do: lyDo.trim(),
      }));
    } catch (err) {
      setLoiGui(err);
    } finally {
      setDangLam(false);
    }
  };

  return (
    <HopThoai moTieuDe={t('thayNguoiKy.tieuDe')} mo onDong={onDong} dangXuLy={dangLam}
      chanDuoi={<>
        <Button variant="secondary" size="sm" disabled={dangLam} onClick={onDong}>{t('chung.huyBo')}</Button>
        <Button size="sm" icon="fa-user-pen" isLoading={dangLam} disabled={!chonHopLe || !lyDo.trim()} onClick={gui}>
          {t('thayNguoiKy.xacNhan')}
        </Button>
      </>}>
      <p className="text-sm text-secondary">{t('thayNguoiKy.goiY')}</p>
      <TruongNhap nhan={t('thayNguoiKy.nguoiCanThay')}>
        <select className={LOP_O_NHAP} value={nguoiKyId} disabled={dangLam}
          onChange={(e) => { setNguoiKyId(Number(e.target.value)); setNguoiMoiId(''); }}>
          {nguoiKyThayDuoc.map((n) => (
            <option key={n.id} value={n.id}>{n.ten_nguoi_ky}{n.ten_chuc_vu ? ` · ${n.ten_chuc_vu}` : ''}</option>
          ))}
        </select>
      </TruongNhap>
      <TruongNhap nhan={t('thayNguoiKy.nguoiThay')} batBuoc>
        <input className={LOP_O_NHAP} placeholder={t('thayNguoiKy.timNguoi')} aria-label={t('thayNguoiKy.timNguoi')}
          value={q} disabled={dangLam} onChange={(e) => { setQ(e.target.value); setNguoiMoiId(''); }} />
      </TruongNhap>
      {ungVien.dangTai && !ungVien.duLieu ? <DangTai /> : ungVien.loi ? (
        <LoiTai thongBao={loi(ungVien.loi)} onThuLai={ungVien.tai} />
      ) : danhSach.length === 0 ? (
        <p className="text-xs text-muted">{t('thayNguoiKy.khongCoUngVien')}</p>
      ) : (
        <select className={LOP_O_NHAP} aria-label={t('thayNguoiKy.chonNguoi')} value={nguoiMoiId} disabled={dangLam}
          onChange={(e) => setNguoiMoiId(e.target.value)}>
          <option value="">{t('thayNguoiKy.chonNguoi')}</option>
          {danhSach.map((u) => (
            <option key={u.id} value={u.id}>
              {[u.ten, u.chuc_vu, u.don_vi].filter(Boolean).join(' · ')}
            </option>
          ))}
        </select>
      )}
      <TruongNhap nhan={t('thayNguoiKy.lyDo')} batBuoc>
        <textarea className={LOP_O_NHAP} rows={3} maxLength={GIOI_HAN.lyDo} value={lyDo} disabled={dangLam}
          onChange={(e) => setLyDo(e.target.value)} />
      </TruongNhap>
      {loiGui != null && <ThongBao>{loi(loiGui)}</ThongBao>}
    </HopThoai>
  );
}
