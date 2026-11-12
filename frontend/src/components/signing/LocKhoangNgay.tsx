/**
 * Hai ô lọc Từ ngày / Đến ngày dùng chung cho các bộ lọc ngày của Trình ký. Khoảng sai thứ tự (Từ ngày > Đến ngày)
 * chỉ giữ ở ô nhập kèm cảnh báo tại form, không gọi `onDoi` nên không gửi request cho tới khi khoảng hợp lệ.
 */
import { useId, useState } from 'react';
import { TruongLoc } from '@components/signing/BoLocTrinhKy';
import { LOP_O_NHAP } from '@lib/signing/dinhDang';
import { khoangNgaySai } from '@lib/signing/khoangNgay';
import { useSigningT } from '@lib/signing/i18n';

const LOP_O_LOI = 'border-danger focus:border-danger focus:ring-danger-subtle';

interface Props {
  tuNgay?: string;
  denNgay?: string;
  onDoi: (thay_doi: { tu_ngay?: string; den_ngay?: string }) => void;
  /** class của từng ô (lưới của form chứa) */
  lopO?: string;
}

interface Nhap {
  tu: string;
  den: string;
  /** giá trị đã áp dụng lúc nhập: bộ lọc bị đổi/xóa từ nơi khác thì bản nhập sai này không còn dùng */
  gocTu: string;
  gocDen: string;
}

export default function LocKhoangNgay({ tuNgay = '', denNgay = '', onDoi, lopO = '' }: Props) {
  const { t } = useSigningT();
  const idLoi = useId();
  const [nhap, setNhap] = useState<Nhap | null>(null);
  const dangSai = nhap !== null && nhap.gocTu === tuNgay && nhap.gocDen === denNgay;
  const tu = dangSai ? nhap.tu : tuNgay;
  const den = dangSai ? nhap.den : denNgay;
  const loi = khoangNgaySai(tu, den);

  const doi = (truong: 'tu_ngay' | 'den_ngay', gia_tri: string) => {
    const moiTu = truong === 'tu_ngay' ? gia_tri : tu;
    const moiDen = truong === 'den_ngay' ? gia_tri : den;
    if (khoangNgaySai(moiTu, moiDen)) {
      setNhap({ tu: moiTu, den: moiDen, gocTu: tuNgay, gocDen: denNgay });
      return;
    }
    setNhap(null);
    // Đang sửa khoảng sai: ô kia chưa áp dụng, nên gửi cả hai để bộ lọc khớp với hai ô đang hiển thị
    onDoi(dangSai ? { tu_ngay: moiTu, den_ngay: moiDen } : { [truong]: gia_tri });
  };
  const thuocTinh = { 'aria-invalid': loi || undefined, 'aria-describedby': loi ? idLoi : undefined };

  return (
    <>
      <TruongLoc nhan={t('danhSach.tuNgay')} icon="fa-calendar" className={lopO}>
        <input className={`${LOP_O_NHAP} ${loi ? LOP_O_LOI : ''}`} type="date" value={tu} {...thuocTinh}
          onChange={(e) => doi('tu_ngay', e.target.value)} />
      </TruongLoc>
      <TruongLoc nhan={t('danhSach.denNgay')} icon="fa-calendar" className={lopO}>
        <input className={`${LOP_O_NHAP} ${loi ? LOP_O_LOI : ''}`} type="date" value={den} {...thuocTinh}
          onChange={(e) => doi('den_ngay', e.target.value)} />
      </TruongLoc>
      {loi && (
        <p id={idLoi} role="alert" className="col-span-full flex items-center gap-1.5 text-xs font-semibold text-danger">
          <i className="fa-solid fa-circle-exclamation" aria-hidden="true" />{t('danhSach.loiKhoangNgay')}
        </p>
      )}
    </>
  );
}
