/** Sửa hồ sơ nháp (người tạo, trước khi gửi): hạn chót, ghi chú, số hiệu tham chiếu/trích yếu, thay PDF dự thảo chưa vào sổ. */
import { useState } from 'react';
import { Button } from '@components/common';
import { HopThoai, OChonTep, ThongBao, TruongNhap } from '@components/signing/ChungUI';
import { signingApi } from '@lib/signing/api';
import { GIOI_HAN, hanChotDaQua, kiemTraTepPdf, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { kiemTraPdfCoMatKhau } from '@lib/signing/pdf';
import { useSigningT } from '@lib/signing/i18n';
import type { HoSoChiTiet } from '@lib/signing/types';

/** ISO → giá trị ô datetime-local theo giờ máy người dùng. */
function sangGioDiaPhuong(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export default function SuaNhapDialog({ hoSo, onDong, onXong }: {
  hoSo: HoSoChiTiet; onDong: () => void; onXong: (moi: HoSoChiTiet) => void;
}) {
  const { t, loi } = useSigningT();
  const [hanChot, setHanChot] = useState(sangGioDiaPhuong(hoSo.han_chot));
  const [ghiChu, setGhiChu] = useState(hoSo.ghi_chu ?? '');
  // PDF dự thảo chưa vào sổ (không gắn bản ghi văn bản đi) thì sửa được số hiệu tham chiếu, trích yếu.
  const nhapTay = hoSo.van_ban_id == null;
  const [soHieu, setSoHieu] = useState(hoSo.so_hieu_van_ban ?? '');
  const [trichYeu, setTrichYeu] = useState(hoSo.trich_yeu_van_ban ?? '');
  const [canhBaoTrichYeu, setCanhBaoTrichYeu] = useState('');
  const [tep, setTep] = useState<File | null>(null);
  const [loiTep, setLoiTep] = useState('');
  const [loiHanChot, setLoiHanChot] = useState('');
  const [dangLuu, setDangLuu] = useState(false);
  const [thongBao, setThongBao] = useState('');
  const hanChotGoc = sangGioDiaPhuong(hoSo.han_chot);

  const onDoiTrichYeu = (e: React.ChangeEvent<HTMLInputElement>) => {
    setThongBao('');
    const val = e.target.value;
    if (val.length > GIOI_HAN.trichYeu) {
      setTrichYeu(val.slice(0, GIOI_HAN.trichYeu));
      setCanhBaoTrichYeu(t('tao.canhBaoTrichYeuCatNgan', { max: GIOI_HAN.trichYeu }));
    } else {
      setTrichYeu(val);
      setCanhBaoTrichYeu(val.length === GIOI_HAN.trichYeu ? t('tao.canhBaoDatGioiHan', { max: GIOI_HAN.trichYeu }) : '');
    }
  };

  const onChonTep = async (f: File | undefined) => {
    setThongBao('');
    if (!f) {
      setTep(null);
      setLoiTep('');
      return;
    }
    const khoaLoi = kiemTraTepPdf(f);
    if (khoaLoi) {
      setLoiTep(t(khoaLoi));
      setTep(null);
      return;
    }
    try {
      const buf = await f.arrayBuffer();
      const coMatKhau = await kiemTraPdfCoMatKhau(buf);
      if (coMatKhau) {
        setLoiTep(t('loi.tep_pdf_co_mat_khau'));
        setTep(null);
        return;
      }
      setLoiTep('');
      setTep(f);
    } catch {
      setLoiTep('');
      setTep(f);
    }
  };

  const luu = async () => {
    // Hạn chót chưa đổi mà đã qua thì để máy chủ quyết; chỉ chặn khi người dùng nhập hạn chót mới ở quá khứ
    if (hanChot !== hanChotGoc && hanChotDaQua(hanChot)) {
      setLoiHanChot(t('tao.loiHanChot'));
      return;
    }
    const form = new FormData();
    form.append('han_chot', hanChot ? new Date(hanChot).toISOString() : '');
    form.append('ghi_chu', ghiChu);
    if (nhapTay) {
      form.append('so_hieu_van_ban', soHieu.trim());
      form.append('trich_yeu_van_ban', trichYeu.trim());
    }
    if (tep) form.append('tep', tep);
    setDangLuu(true);
    setThongBao('');
    try {
      onXong(await signingApi.suaNhap(hoSo.id, form));
    } catch (err) {
      setThongBao(loi(err));
    } finally {
      setDangLuu(false);
    }
  };

  return (
    <HopThoai moTieuDe={t('chiTiet.suaHoSo')} mo onDong={onDong} dangXuLy={dangLuu}
      chanDuoi={<>
        <Button variant="secondary" onClick={onDong}>{t('chung.huyBo')}</Button>
        <Button icon="fa-floppy-disk" isLoading={dangLuu}
          disabled={(nhapTay && !trichYeu.trim()) || Boolean(loiTep) || Boolean(loiHanChot)} onClick={luu}>{t('chung.luu')}</Button>
      </>}>
      {nhapTay && (
        <>
          <TruongNhap nhan={t('tao.soHieu')} ghiChu={t('tao.soHieuGhiChu')}>
            <input className={LOP_O_NHAP} maxLength={100} value={soHieu} onChange={(e) => setSoHieu(e.target.value)} />
          </TruongNhap>
          <TruongNhap nhan={t('tao.trichYeu')} batBuoc ghiChu={`${trichYeu.length}/${GIOI_HAN.trichYeu} ${t('chung.kyTu')}`}>
            <input className={LOP_O_NHAP} maxLength={GIOI_HAN.trichYeu} value={trichYeu} onChange={onDoiTrichYeu} />
            {canhBaoTrichYeu && (
              <p className="text-xs text-warning font-medium mt-1">{canhBaoTrichYeu}</p>
            )}
          </TruongNhap>
        </>
      )}
      <TruongNhap nhan={t('danhSach.hanChot')} ghiChu={t('tao.hanChotGhiChu')} loi={loiHanChot}>
        <input className={LOP_O_NHAP} type="datetime-local" value={hanChot} aria-invalid={loiHanChot ? true : undefined}
          onChange={(e) => {
            setHanChot(e.target.value);
            setLoiHanChot(e.target.value !== hanChotGoc && hanChotDaQua(e.target.value) ? t('tao.loiHanChot') : '');
          }} />
      </TruongNhap>
      <TruongNhap nhan={t('chiTiet.ghiChu')} ghiChu={t('tao.ghiChuHuongDan')}>
        <textarea className={LOP_O_NHAP} rows={3} maxLength={GIOI_HAN.ghiChu} value={ghiChu} onChange={(e) => setGhiChu(e.target.value)} />
      </TruongNhap>
      <TruongNhap nhan={t('chiTiet.thayTep')} ghiChu={t('tao.tepGhiChu')} loi={loiTep}>
        <OChonTep accept="application/pdf,.pdf" onChon={onChonTep} />
      </TruongNhap>
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
    </HopThoai>
  );
}
