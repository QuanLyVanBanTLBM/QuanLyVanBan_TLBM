/**
 * Trao đổi về yêu cầu sửa (#80 mục C): người tạo và người yêu cầu sửa nhắn tin; kiểm toán chỉ đọc.
 * Người tạo tải bản sửa để tạo lượt trình mới (mọi cấp ký lại; vị trí ký giữ như lượt trước).
 */
import { useState } from 'react';
import { Button, Card } from '@components/common';
import { signingApi } from '@lib/signing/api';
import { dinhDangNgay, LOP_O_NHAP } from '@lib/signing/dinhDang';
import { coQuyen, useKhoaChongTrung, useTai, useToi } from '@lib/signing/hooks';
import { useSigningT } from '@lib/signing/i18n';
import type { HoSoChiTiet } from '@lib/signing/types';
import { DangTai, LoiTai, ThongBao } from './ChungUI';

export default function TraoDoiPanel({ hoSo, onXong }: { hoSo: HoSoChiTiet; onXong: (h?: HoSoChiTiet) => void }) {
  const { t, loi, lang } = useSigningT();
  const { toi } = useToi();
  const khoa = useKhoaChongTrung();
  const td = useTai(() => signingApi.traoDoi(hoSo.id), [hoSo.id, hoSo.luot_trinh.length]);
  const [noiDung, setNoiDung] = useState('');
  const [tep, setTep] = useState<File | null>(null);
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

  return (
    <Card className="p-4 space-y-3">
      <h3 className="font-bold text-sm text-main">{t('traoDoi.tieuDe')}</h3>
      <div className="rounded-lg border border-purple-border bg-purple-subtle p-3 text-sm">
        <div className="font-bold text-purple">{thread.tieu_de}</div>
        <div className="text-main whitespace-pre-wrap">{thread.ly_do}</div>
      </div>
      <ul className="max-h-72 space-y-2 overflow-y-auto">
        {td.duLieu.tin_nhan.length === 0 && <li className="text-sm text-muted">{t('traoDoi.rong')}</li>}
        {td.duLieu.tin_nhan.map((m) => (
          <li key={m.id} className={`rounded-lg px-3 py-2 text-sm ${
            m.nguoi_viet === toi?.id ? 'ml-8 bg-primary-subtle' : 'mr-8 bg-surface-elevated'}`}>
            <div className="whitespace-pre-wrap text-main">{m.noi_dung}</div>
            <div className="text-xs text-muted">{dinhDangNgay(m.created_at, lang)}</div>
          </li>
        ))}
      </ul>
      {dangMo && laBen && (
        <div className="flex gap-2">
          <input className={LOP_O_NHAP} placeholder={t('traoDoi.nhap')} value={noiDung}
            onChange={(e) => setNoiDung(e.target.value)} />
          <Button size="sm" icon="fa-paper-plane" isLoading={dangGui} disabled={!noiDung.trim()}
            onClick={async () => {
              if (await lam(() => signingApi.guiTinNhan(hoSo.id, noiDung))) {
                setNoiDung('');
                td.tai();
              }
            }}>{t('traoDoi.gui')}</Button>
        </div>
      )}
      {dangMo && !laBen && coQuyen(toi, 'view_signing_audit') && <ThongBao loai="thong_tin">{t('traoDoi.chiDoc')}</ThongBao>}
      {dangMo && laNguoiTao && (
        <div className="space-y-2 border-t border-border-subtle pt-3">
          <div className="text-sm font-bold text-main">{t('traoDoi.taiBanSua')}</div>
          <p className="text-xs text-secondary">{t('traoDoi.ghiChuGiaiQuyet')}</p>
          <input type="file" accept="application/pdf" aria-label={t('traoDoi.chonTep')} className={LOP_O_NHAP}
            onChange={(e) => setTep(e.target.files?.[0] || null)} />
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
