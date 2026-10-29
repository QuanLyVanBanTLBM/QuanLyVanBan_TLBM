/**
 * Kết quả hồ sơ hoàn tất (#80 mục D, E): nhận diện "Hoàn tất duyệt nội bộ, chưa phát hành"; trạng thái tạo tệp
 * đang xử lý/lỗi/thành công; chỉ cho tải khi tạo tệp thành công; thử lại khi lỗi; xác minh bằng chứng.
 */
import { useEffect, useState } from 'react';
import { Button, Card } from '@components/common';
import { signingApi } from '@lib/signing/api';
import { loiTepHoanTatHienThi, taiXuong, tenTepTaiVe } from '@lib/signing/dinhDang';
import { coQuyen, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { BangChung, HoSoChiTiet, LuotTrinh } from '@lib/signing/types';
import { ThongBao } from './ChungUI';

const CHU_KY_HOI = 3000;

export default function KetQuaPanel({ hoSo, luot, onTaiLai }: {
  hoSo: HoSoChiTiet; luot: LuotTrinh; onTaiLai: (h?: HoSoChiTiet) => void;
}) {
  const { t, loi } = useSigningT();
  const { toi } = useToi();
  const [dangLam, setDangLam] = useState(false);
  const [thongBao, setThongBao] = useState('');
  const [bangChung, setBangChung] = useState<BangChung | null>(null);
  const trangThai = luot.trang_thai_tep_hoan_tat;
  const lyDoLoiTep = luot.loi_tep_hoan_tat
    ? loiTepHoanTatHienThi(luot.loi_tep_hoan_tat, t)
    : t('chiTiet.loiTaoTepKhongRo');

  useEffect(() => {
    if (trangThai !== 'DANG_XU_LY') return undefined;
    const hen = setTimeout(() => onTaiLai(), CHU_KY_HOI);
    return () => clearTimeout(hen);
  }, [trangThai, onTaiLai]);

  const lam = async (ham: () => Promise<void>) => {
    setDangLam(true);
    setThongBao('');
    try {
      await ham();
    } catch (err) {
      setThongBao(loi(err));
    } finally {
      setDangLam(false);
    }
  };

  const thuLaiDuoc = toi?.id === hoSo.create_by || coQuyen(toi, 'view_signing_audit');

  return (
    <Card className="p-4 space-y-3">
      <h3 className="text-lg font-bold text-main">{t('chiTiet.ketQua')}</h3>
      <div className="rounded-lg border border-success-border bg-success-subtle px-3 py-2 text-sm font-bold text-success">
        <i className="fa-solid fa-stamp mr-2" aria-hidden="true" />{t('chiTiet.nhanDien')}
      </div>
      {trangThai === 'DANG_XU_LY' && <ThongBao loai="thong_tin">{t('chiTiet.dangTaoTep')}</ThongBao>}
      {trangThai === 'LOI' && (
        <>
          <ThongBao loai="canh_bao">
            {t('chiTiet.loiTaoTep')}
            <span className="mt-1 block">{lyDoLoiTep}</span>
          </ThongBao>
          {thuLaiDuoc && (
            <Button size="sm" variant="secondary" icon="fa-rotate-right" isLoading={dangLam}
              onClick={() => lam(async () => onTaiLai(await signingApi.taoLaiTepHoanTat(hoSo.id)))}>
              {t('chiTiet.taoLaiTep')}
            </Button>
          )}
        </>
      )}
      {trangThai === 'THANH_CONG' && (
        <div className="space-y-2">
          <div className="text-sm text-secondary">{t('chiTiet.tepHoanTat')}</div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" icon="fa-download" isLoading={dangLam}
              onClick={() => lam(async () => taiXuong(await signingApi.tepHoanTat(hoSo.id),
                tenTepTaiVe(hoSo.id, 'HOAN_TAT')))}>{t('chiTiet.taiTepHoanTat')}</Button>
            <Button size="sm" variant="secondary" icon="fa-shield-halved"
              onClick={() => lam(async () => setBangChung(await signingApi.bangChung(hoSo.id)))}>
              {t('chiTiet.xacMinh')}
            </Button>
          </div>
        </div>
      )}
      {bangChung && (
        <div className="space-y-1 text-sm">
          <ThongBao loai={bangChung.xac_minh.hop_le ? 'thanh_cong' : 'loi'}>
            {t(bangChung.xac_minh.hop_le ? 'chiTiet.bangChungHopLe' : 'chiTiet.bangChungKhongHopLe')}
          </ThongBao>
          <ul className="text-sm text-secondary">
            {bangChung.xac_minh.chu_ky.map((c) => (
              <li key={c.ten_nguoi_ky}>
                <i className={`fa-solid ${c.hop_le ? 'fa-check text-success' : 'fa-xmark text-danger'} mr-1`} aria-hidden="true" />
                {c.ten_nguoi_ky}
              </li>
            ))}
          </ul>
        </div>
      )}
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
    </Card>
  );
}
