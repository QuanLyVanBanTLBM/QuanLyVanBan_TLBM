/**
 * Xem PDF nhiều trang kèm lớp phủ khung ký (#80 mục D, E): đặt/kéo khung khi tạo hồ sơ; hiển thị ảnh chữ ký
 * (snapshot) hoặc khối "đã ký" trên bản xem trước. Tệp gốc không bị sửa; lớp phủ chỉ là giao diện.
 * Tọa độ khung: tỷ lệ % theo trang, gốc trên-trái (cùng hệ với backend).
 * Inline style chỉ dùng cho tọa độ động lúc chạy (ngoại lệ được phép trong DESIGN_TOKENS_AUDIT mục 2.4).
 */
import { useEffect, useRef, useState } from 'react';
import { laLoiHuyVe, moPdf, veTrang, type TaiLieuPdf } from '@lib/signing/pdf';
import { useSigningT } from '@lib/signing/i18n';
import { kep } from '@lib/signing/viTri';
import { Button } from '@components/common';
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

function khoaLoiPdf(err: unknown): string {
  const name = (err as { name?: string } | null)?.name;
  if (name === 'PasswordException') return 'loi.pdfCanMatKhau';
  if (name === 'InvalidPDFException') return 'loi.pdfKhongHopLe';
  if (name === 'MissingPDFException') return 'loi.pdfKhongTimThay';
  if (name === 'UnexpectedResponseException') return 'loi.pdfPhanHoiKhongHopLe';
  return 'loi.khong_hien_thi_duoc_pdf';
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
      className={`absolute flex flex-col items-center justify-center overflow-hidden rounded-xs border-2 px-1 text-center text-xs font-semibold leading-tight select-none ${mau}`}
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
  const [loiVe, setLoiVe] = useState<string | null>(null);
  const [lanVe, setLanVe] = useState(0);
  useEffect(() => {
    if (!canvas.current || rong <= 0) return undefined;
    setLoiVe(null);
    let huy = false;
    const ve = veTrang(pdf, so, canvas.current, rong);
    ve.xong.then(() => !huy && setLoiVe(null), (err) => {
      if (huy || laLoiHuyVe(err)) return;  // lần vẽ bị thay bằng lần mới (đổi kích thước), không phải lỗi
      console.error('Không vẽ được trang PDF', so, err);
      setLoiVe(khoaLoiPdf(err));
    });
    return () => {
      huy = true;
      ve.huy();
    };
  }, [pdf, so, rong, lanVe]);
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
      {loiVe && <div className="space-y-2">
        <ThongBao>{t(loiVe)}</ThongBao>
        <Button size="sm" variant="secondary" icon="fa-rotate-right" onClick={() => setLanVe((n) => n + 1)}>
          {t('chung.thuLai')}
        </Button>
      </div>}
      <figcaption className="text-center text-xs text-muted">{t('tao.trang', { so })}</figcaption>
    </figure>
  );
}

export default function XemPdf({ duLieu, khung = [], khungDangDat, onDat, onKeo, onSoTrang }: Props) {
  const khungChua = useRef<HTMLDivElement>(null);
  // Kết quả mở PDF gắn với dữ liệu nguồn; đổi tệp hoặc yêu cầu tải lại sẽ bỏ kết quả cũ.
  const [mo, setMo] = useState<{ nguon: ArrayBuffer; pdf: TaiLieuPdf | null; loi: string | null } | null>(null);
  const [rong, setRong] = useState(0);
  const [trang, setTrang] = useState(1);
  const [lanThu, setLanThu] = useState(0);
  const { t } = useSigningT();
  const pdf = mo?.nguon === duLieu ? mo.pdf : null;
  const loi = mo?.nguon === duLieu ? mo.loi : null;

  useEffect(() => {
    let huy = false;
    moPdf(duLieu)
      .then((tai_lieu) => {
        if (huy) return;
        setMo({ nguon: duLieu, pdf: tai_lieu, loi: null });
        setTrang(1);
        onSoTrang?.(tai_lieu.numPages);
      })
      .catch((err) => {
        console.error('Không mở được PDF', err);
        if (!huy) setMo({ nguon: duLieu, pdf: null, loi: khoaLoiPdf(err) });
      });
    return () => {
      huy = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [duLieu, lanThu]);

  useEffect(() => {
    const el = khungChua.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([e]) => setRong(Math.floor(e.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={khungChua} className="mx-auto w-full max-w-3xl space-y-4">
      {loi && <div className="space-y-2">
        <ThongBao>{t(loi)}</ThongBao>
        <Button size="sm" variant="secondary" icon="fa-rotate-right" onClick={() => { setMo(null); setLanThu((n) => n + 1); }}>
          {t('chung.thuLai')}
        </Button>
      </div>}
      {!pdf && !loi && <DangTai />}
      {pdf && <>
        <div className="flex items-center justify-between gap-3 rounded-lg border border-border-subtle bg-surface px-3 py-2">
          <Button size="sm" variant="secondary" icon="fa-chevron-left" disabled={trang <= 1}
            aria-label={t('phanTrang.truoc')} onClick={() => setTrang((n) => Math.max(1, n - 1))}>
            {t('phanTrang.truoc')}
          </Button>
          <span className="text-sm font-semibold text-secondary" aria-live="polite">
            {t('phanTrang.trang', { trang, tong: pdf.numPages })}
          </span>
          <Button size="sm" variant="secondary" icon="fa-chevron-right" disabled={trang >= pdf.numPages}
            aria-label={t('phanTrang.sau')} onClick={() => setTrang((n) => Math.min(pdf.numPages, n + 1))}>
            {t('phanTrang.sau')}
          </Button>
        </div>
        <TrangPdf key={trang} pdf={pdf} so={trang} rong={rong} khung={khung.filter((k) => k.trang === trang)}
          khungDangDat={khungDangDat} onDat={onDat} onKeo={onKeo} />
      </>}
    </div>
  );
}

export type { Props as XemPdfProps };
