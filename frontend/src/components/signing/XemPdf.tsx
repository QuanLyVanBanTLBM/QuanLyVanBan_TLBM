/**
 * Xem PDF nhiều trang kèm lớp phủ khung ký (#80 mục D, E): đặt/kéo khung khi tạo hồ sơ; hiển thị ảnh chữ ký
 * (snapshot) hoặc khối "đã ký" trên bản xem trước. Tệp gốc không bị sửa; lớp phủ chỉ là giao diện.
 * Tọa độ khung: tỷ lệ % theo trang, gốc trên-trái (cùng hệ với backend).
 * Inline style chỉ dùng cho tọa độ động lúc chạy (ngoại lệ được phép trong DESIGN_TOKENS_AUDIT mục 2.4).
 */
import { useEffect, useRef, useState } from 'react';
import { moPdf, veTrang, type TaiLieuPdf } from '@lib/signing/pdf';
import { useSigningT } from '@lib/signing/i18n';
import { kep } from '@lib/signing/viTri';
import { DangTai, ThongBao } from './ChungUI';

export interface KhungHienThi {
  id: string;
  trang: number;
  x: number;
  y: number;
  w: number;
  h: number;
  nhan: string;
  phu?: string;
  anhUrl?: string;
  kieu: 'dat' | 'da_ky' | 'cho';
}

interface Props {
  duLieu: ArrayBuffer;
  khung?: KhungHienThi[];
  /** id khung đang chờ đặt: bấm lên trang để đặt (tâm khung tại điểm bấm) */
  khungDangDat?: string | null;
  onDat?: (id: string, trang: number, x: number, y: number) => void;
  onKeo?: (id: string, x: number, y: number) => void;
  onSoTrang?: (so: number) => void;
}

function KhungKy({ k, onKeo }: { k: KhungHienThi; onKeo?: Props['onKeo'] }) {
  const keo = useRef<{ px: number; py: number; x: number; y: number; rect: DOMRect } | null>(null);
  const coTheKeo = k.kieu === 'dat' && onKeo;
  const mau = {
    dat: 'border-primary bg-primary-subtle text-primary cursor-move',
    da_ky: 'border-success bg-success-subtle text-success',
    cho: 'border-dashed border-warning bg-warning-subtle text-warning-text',
  }[k.kieu];
  return (
    <div
      className={`absolute flex flex-col items-center justify-center overflow-hidden rounded-xs border-2 px-1 text-center text-[0.65rem] leading-tight select-none ${mau}`}
      style={{ left: `${k.x}%`, top: `${k.y}%`, width: `${k.w}%`, height: `${k.h}%` }}
      onPointerDown={(e) => {
        if (!coTheKeo) return;
        e.stopPropagation();
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        const rect = (e.currentTarget.parentElement as HTMLElement).getBoundingClientRect();
        keo.current = { px: e.clientX, py: e.clientY, x: k.x, y: k.y, rect };
      }}
      onPointerMove={(e) => {
        const d = keo.current;
        if (!d || !onKeo) return;
        const x = kep(d.x + ((e.clientX - d.px) / d.rect.width) * 100, 0, 100 - k.w);
        const y = kep(d.y + ((e.clientY - d.py) / d.rect.height) * 100, 0, 100 - k.h);
        onKeo(k.id, Math.round(x * 100) / 100, Math.round(y * 100) / 100);
      }}
      onPointerUp={() => {
        keo.current = null;
      }}
      onClick={(e) => e.stopPropagation()}
      data-testid={`khung-${k.id}`}
    >
      {k.anhUrl && <img src={k.anhUrl} alt="" className="max-h-[70%] max-w-full object-contain" />}
      <span className="font-bold truncate max-w-full">{k.nhan}</span>
      {k.phu && <span className="truncate max-w-full">{k.phu}</span>}
    </div>
  );
}

function TrangPdf({ pdf, so, rong, khung, khungDangDat, onDat, onKeo }: {
  pdf: TaiLieuPdf; so: number; rong: number; khung: KhungHienThi[];
} & Pick<Props, 'khungDangDat' | 'onDat' | 'onKeo'>) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const { t } = useSigningT();
  useEffect(() => {
    if (canvas.current && rong > 0) veTrang(pdf, so, canvas.current, rong).catch(() => undefined);
  }, [pdf, so, rong]);
  return (
    <figure className="space-y-1">
      <div
        className={`relative overflow-hidden rounded-md border border-border-subtle bg-surface shadow-sm ${
          khungDangDat ? 'cursor-crosshair ring-2 ring-primary-subtle' : ''}`}
        onClick={(e) => {
          if (!khungDangDat || !onDat) return;
          const rect = e.currentTarget.getBoundingClientRect();
          onDat(khungDangDat, so, ((e.clientX - rect.left) / rect.width) * 100, ((e.clientY - rect.top) / rect.height) * 100);
        }}
      >
        <canvas ref={canvas} className="block w-full h-auto" aria-label={t('tao.trang', { so })} />
        {khung.map((k) => <KhungKy key={k.id} k={k} onKeo={onKeo} />)}
      </div>
      <figcaption className="text-center text-xs text-muted">{t('tao.trang', { so })}</figcaption>
    </figure>
  );
}

export default function XemPdf({ duLieu, khung = [], khungDangDat, onDat, onKeo, onSoTrang }: Props) {
  const khungChua = useRef<HTMLDivElement>(null);
  // Kết quả mở PDF gắn với dữ liệu nguồn: đổi tệp thì kết quả cũ tự không còn dùng (không reset trong effect)
  const [mo, setMo] = useState<{ nguon: ArrayBuffer; pdf: TaiLieuPdf | null; loi: boolean } | null>(null);
  const [rong, setRong] = useState(0);
  const { t } = useSigningT();
  const pdf = mo?.nguon === duLieu ? mo.pdf : null;
  const loi = mo?.nguon === duLieu && mo.loi;

  useEffect(() => {
    let huy = false;
    moPdf(duLieu)
      .then((tai_lieu) => {
        if (huy) return;
        setMo({ nguon: duLieu, pdf: tai_lieu, loi: false });
        onSoTrang?.(tai_lieu.numPages);
      })
      .catch(() => !huy && setMo({ nguon: duLieu, pdf: null, loi: true }));
    return () => {
      huy = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [duLieu]);

  useEffect(() => {
    const el = khungChua.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([e]) => setRong(Math.floor(e.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={khungChua} className="space-y-4">
      {loi && <ThongBao>{t('loi.tep_khong_phai_pdf')}</ThongBao>}
      {!pdf && !loi && <DangTai />}
      {pdf && Array.from({ length: pdf.numPages }, (_, i) => i + 1).map((so) => (
        <TrangPdf key={so} pdf={pdf} so={so} rong={rong} khung={khung.filter((k) => k.trang === so)}
          khungDangDat={khungDangDat} onDat={onDat} onKeo={onKeo} />
      ))}
    </div>
  );
}

export type { Props as XemPdfProps };
