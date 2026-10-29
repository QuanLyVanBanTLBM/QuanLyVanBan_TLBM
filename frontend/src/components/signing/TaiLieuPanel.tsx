/**
 * Trang tài liệu của hồ sơ: mọi phiên bản tệp đã trình (mỗi lượt một bản, kèm mã băm), tệp hoàn tất và bằng chứng
 * JSON khi đã hoàn tất. Tệp lưu theo thư mục trinh_ky/<năm>/<tháng>/ ở máy chủ, tải qua API có kiểm quyền.
 */
import { useState } from 'react';
import { Button, Card } from '@components/common';
import { ThongBao } from '@components/signing/ChungUI';
import { signingApi } from '@lib/signing/api';
import { dinhDangNgay, tenBangChungTaiVe, tenTepTaiVe } from '@lib/signing/dinhDang';
import { useSigningT } from '@lib/signing/i18n';
import type { HoSoChiTiet } from '@lib/signing/types';

function luuTep(blob: Blob, ten: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = ten;
  a.click();
  URL.revokeObjectURL(url);
}

export default function TaiLieuPanel({ hoSo }: { hoSo: HoSoChiTiet }) {
  const { t, loi, lang } = useSigningT();
  const [thongBao, setThongBao] = useState('');

  const tai = async (lay: () => Promise<Blob>, ten: string) => {
    setThongBao('');
    try {
      luuTep(await lay(), ten);
    } catch (err) {
      setThongBao(loi(err));
    }
  };
  const taiBangChung = () => tai(async () => new Blob(
    [JSON.stringify(await signingApi.bangChung(hoSo.id), null, 2)], { type: 'application/json' },
  ), tenBangChungTaiVe(hoSo.id));

  const dong = (khoa: string, nhan: string, phu: string, onTai: () => void) => (
    <li key={khoa} className="flex flex-wrap items-center justify-between gap-2 py-2">
      <div className="min-w-0">
        <div className="text-sm font-semibold text-main"><i className="fa-regular fa-file-pdf mr-1.5 text-danger" aria-hidden="true" />{nhan}</div>
        <div className="truncate text-xs text-secondary" title={phu}>{phu}</div>
      </div>
      <Button size="sm" variant="ghost" icon="fa-download" onClick={onTai}>{t('chung.taiVe')}</Button>
    </li>
  );

  return (
    <Card className="p-4 space-y-2">
      <h3 className="text-lg font-bold text-main">{t('chiTiet.danhSachTep')}</h3>
      <ul className="divide-y divide-border-subtle">
        {hoSo.luot_trinh.length === 0 && dong('nhap', t('chiTiet.banDuThao'),
          '',
          () => tai(() => signingApi.tepGoc(hoSo.id), tenTepTaiVe(hoSo.id, 'DU_THAO')))}
        {hoSo.luot_trinh.map((l) => dong(`luot-${l.id}`,
          hoSo.luot_trinh.length > 1 ? `${t('chiTiet.banLuot')} (${t('chiTiet.luot', { so: l.so_luot })})` : t('chiTiet.banLuot'),
          dinhDangNgay(l.thoi_diem_gui, lang),
          () => tai(() => signingApi.tepCuaLuot(hoSo.id, l.id), tenTepTaiVe(hoSo.id, 'LUOT', l.so_luot))))}
        {hoSo.trang_thai === 'HOAN_THANH' && hoSo.luot_trinh[0]?.trang_thai_tep_hoan_tat === 'THANH_CONG' && dong('hoan-tat',
          t('chiTiet.tepHoanTat'), '',
          () => tai(() => signingApi.tepHoanTat(hoSo.id), tenTepTaiVe(hoSo.id, 'HOAN_TAT')))}
      </ul>
      {hoSo.trang_thai === 'HOAN_THANH' && (
        <Button size="sm" variant="secondary" icon="fa-file-code" onClick={taiBangChung}>{t('chiTiet.bangChungJson')}</Button>
      )}
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
    </Card>
  );
}
