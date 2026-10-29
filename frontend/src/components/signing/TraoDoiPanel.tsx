/**
 * Trao đổi về yêu cầu sửa (#80 mục C): người tạo và người yêu cầu sửa nhắn tin; kiểm toán chỉ đọc.
 * Người tạo tải bản sửa để tạo lượt trình mới (mọi cấp ký lại; vị trí ký giữ như lượt trước).
 */
import { useState } from 'react';
import { Button, Card } from '@components/common';
import { signingApi } from '@lib/signing/api';
import { dinhDangNgay, GIOI_HAN, kiemTraTepPdf, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { coQuyen, useKhoaChongTrung, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { HoSoChiTiet } from '@lib/signing/types';
import { DangTai, LoiTai, OChonTep, ThongBao } from './ChungUI';

export default function TraoDoiPanel({ hoSo, onXong }: { hoSo: HoSoChiTiet; onXong: (h?: HoSoChiTiet) => void }) {
  const { t, loi, lang } = useSigningT();
  const { toi } = useToi();
  const khoa = useKhoaChongTrung();
  const td = useTai(() => signingApi.traoDoi(hoSo.id), [hoSo.id, hoSo.luot_trinh.length]);
  const [noiDung, setNoiDung] = useState('');
  const [tep, setTep] = useState<File | null>(null);
  const [loiTep, setLoiTep] = useState('');
  const [dangGui, setDangGui] = useState(false);
  const [thongBao, setThongBao] = useState('');

  const thread = td.duLieu?.thread;
  if (td.dangTai && !td.duLieu) return <DangTai />;
  if (td.loi) return <LoiTai thongBao={loi(td.loi)} onThuLai={td.tai} />;
  if (!thread) return null;

  const dangMo = thread.trang_thai === 'DANG_MO' && hoSo.trang_thai === 'CHO_KY';
  const laBen = toi?.id === hoSo.create_by || toi?.id === thread.nguoi_yeu_cau;
  const laNguoiTao = toi?.id === hoSo.create_by;

  const lam = async (ham: () => Promise<unknown>) => {
    setDangGui(true);
    setThongBao('');
    try {
      await ham();
      return true;
    } catch (err) {
      setThongBao(loi(err));
      return false;
    } finally {
      setDangGui(false);
    }
  };

  const guiTin = async () => {
    if (!noiDung.trim() || dangGui) return;
    if (await lam(() => signingApi.guiTinNhan(hoSo.id, noiDung.trim()))) {
      setNoiDung('');
      td.tai();
    }
  };

  return (
    <Card className="p-4 space-y-3">
      <h3 className="text-lg font-bold text-main">{t('traoDoi.tieuDe')}</h3>
      <div className="rounded-lg border border-purple-border bg-purple-subtle p-3 text-sm">
        <div className="font-bold text-purple break-words">{thread.tieu_de}</div>
        <div className="text-main whitespace-pre-wrap break-words">{thread.ly_do}</div>
      </div>
      <ul className="max-h-72 space-y-2 overflow-y-auto">
        {td.duLieu.tin_nhan.length === 0 && <li className="text-sm text-muted">{t('traoDoi.rong')}</li>}
        {td.duLieu.tin_nhan.map((m) => (
          <li key={m.id} className={`rounded-lg px-3 py-2 text-sm ${
            m.nguoi_viet === toi?.id ? 'ml-8 bg-primary-subtle' : 'mr-8 bg-surface-elevated'}`}>
            <div className="text-xs font-bold text-secondary">
              {m.nguoi_viet === toi?.id ? t('traoDoi.ban') : (m.ten_nguoi_viet || t('traoDoi.nguoiChuaXacDinh'))}
            </div>
            <div className="whitespace-pre-wrap break-words text-main">{m.noi_dung}</div>
            <div className="text-xs text-muted">{dinhDangNgay(m.created_at, lang)}</div>
          </li>
        ))}
      </ul>
      {dangMo && laBen && (
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); guiTin(); }}>
          <input className={LOP_O_NHAP} placeholder={t('traoDoi.nhap')} aria-label={t('traoDoi.nhap')} value={noiDung}
            maxLength={GIOI_HAN.tinNhan} onChange={(e) => setNoiDung(e.target.value)} />
          <Button type="submit" size="sm" icon="fa-paper-plane" isLoading={dangGui} disabled={!noiDung.trim()}>
            {t('traoDoi.gui')}
          </Button>
        </form>
      )}
      {dangMo && !laBen && coQuyen(toi, 'view_signing_audit') && <ThongBao loai="thong_tin">{t('traoDoi.chiDoc')}</ThongBao>}
      {dangMo && laNguoiTao && (
        <div className="space-y-2 border-t border-border-subtle pt-3">
          <div className="text-sm font-bold text-main">{t('traoDoi.taiBanSua')}</div>
          <p className="text-sm text-secondary">{t('traoDoi.ghiChuGiaiQuyet')}</p>
          <label className="block">
            <OChonTep accept="application/pdf" nhan={t('traoDoi.chonTep')} onChon={(f) => {
              const khoaLoi = f ? kiemTraTepPdf(f) : null;
              setLoiTep(khoaLoi ? t(khoaLoi) : '');
              setTep(f && !khoaLoi ? f : null);
            }} />
          </label>
          {loiTep && <ThongBao>{loiTep}</ThongBao>}
          <Button size="sm" icon="fa-upload" isLoading={dangGui} disabled={!tep}
            onClick={async () => {
              let kq: HoSoChiTiet | null = null;
              if (await lam(async () => { kq = await signingApi.giaiQuyet(hoSo.id, khoa.lay(), tep); })) {
                khoa.lamMoi();
                setTep(null);
                onXong(kq);
              }
            }}>{t('traoDoi.taiBanSua')}</Button>
        </div>
      )}
      {thongBao && <ThongBao>{thongBao}</ThongBao>}
    </Card>
  );
}
