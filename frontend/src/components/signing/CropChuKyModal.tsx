import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@components/common';
import { HopThoai, ThongBao } from '@components/signing/ChungUI';
import { useSigningT } from '@lib/signing/i18n';

interface CropChuKyModalProps {
  mo: boolean;
  onDong: () => void;
  tep: File | null;
  onLuu: (blob: Blob, dataUrl: string) => Promise<void> | void;
  dangXuLy?: boolean;
}

// Kích thước chuẩn đầu ra của chữ ký: tỉ lệ 2:1 (300 x 150 px)
const CROP_W = 300;
const CROP_H = 150;

// Kích thước vùng nhìn xem trước (Viewport) nằm gọn gàng trong modal 480px
const VIEWPORT_W = 420;
const VIEWPORT_H = 220;

// Vị trí cố định của khung cắt ở chính giữa Viewport
const CROP_X = (VIEWPORT_W - CROP_W) / 2; // 60px
const CROP_Y = (VIEWPORT_H - CROP_H) / 2; // 35px
const CROP_CENTER_X = VIEWPORT_W / 2; // 210px
const CROP_CENTER_Y = VIEWPORT_H / 2; // 110px

function nguongScanChuKy(histogram: Uint32Array, total: number) {
  let tongMucSang = 0;
  for (let muc = 0; muc < histogram.length; muc += 1) tongMucSang += muc * histogram[muc];

  let tongNen = 0;
  let mucNen = 0;
  let doPhanLopTotNhat = 0;
  let nguong = 190;
  for (let muc = 0; muc < histogram.length; muc += 1) {
    tongNen += histogram[muc];
    if (tongNen === 0) continue;
    const tongTienCanh = total - tongNen;
    if (tongTienCanh === 0) break;
    mucNen += muc * histogram[muc];
    const trungBinhNen = mucNen / tongNen;
    const trungBinhTienCanh = (tongMucSang - mucNen) / tongTienCanh;
    const doPhanLop = tongNen * tongTienCanh * (trungBinhNen - trungBinhTienCanh) ** 2;
    if (doPhanLop > doPhanLopTotNhat) {
      doPhanLopTotNhat = doPhanLop;
      nguong = muc;
    }
  }
  return Math.min(240, Math.max(150, nguong));
}

function scanChuKy(ctx: CanvasRenderingContext2D, width: number, height: number) {
  const imageData = ctx.getImageData(0, 0, width, height);
  const pixels = imageData.data;
  const histogram = new Uint32Array(256);
  let total = 0;

  for (let i = 0; i < pixels.length; i += 4) {
    if (pixels[i + 3] === 0) continue;
    const red = pixels[i];
    const green = pixels[i + 1];
    const blue = pixels[i + 2];
    const luminance = (red * 299 + green * 587 + blue * 114) / 1000;
    histogram[Math.round(luminance)] += 1;
    total += 1;
  }

  if (total === 0) return;
  const threshold = nguongScanChuKy(histogram, total);
  const softness = 24;
  for (let i = 0; i < pixels.length; i += 4) {
    if (pixels[i + 3] === 0) continue;
    const luminance = (pixels[i] * 299 + pixels[i + 1] * 587 + pixels[i + 2] * 114) / 1000;
    const inkCoverage = Math.min(1, Math.max(0, (threshold + softness - luminance) / (softness * 2)));
    pixels[i + 3] = Math.round(pixels[i + 3] * inkCoverage);
  }

  ctx.putImageData(imageData, 0, 0);
}

export default function CropChuKyModal({ mo, onDong, tep, onLuu, dangXuLy = false }: CropChuKyModalProps) {
  const { t } = useSigningT();
  const dichRef = useRef(t);
  useEffect(() => {
    dichRef.current = t;
  }, [t]);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [rawImg, setRawImg] = useState<HTMLImageElement | null>(null);

  const [baseScale, setBaseScale] = useState(1);
  const [zoom, setZoom] = useState(1); // 1 = 100% kích thước fit khởi tạo
  const zoomRef = useRef(zoom);
  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

  const [offset, setOffset] = useState({ x: 0, y: 0 }); // Độ lệch tâm so với tâm khung cắt

  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ mouseX: 0, mouseY: 0, startOffsetX: 0, startOffsetY: 0 });

  // Hỗ trợ pinch 2 ngón trên màn hình cảm ứng
  const touchStartDistRef = useRef<number | null>(null);
  const touchStartZoomRef = useRef<number>(1);

  const [loi, setLoi] = useState('');

  // Modal xác nhận kết quả cắt
  const [xacNhan, setXacNhan] = useState<{ blob: Blob; dataUrl: string } | null>(null);

  // 1. Nạp ảnh khi chọn tệp mới và tự động scan nét chữ ký khỏi nền giấy.
  useEffect(() => {
    if (!tep) {
      setRawImg(null);
      setLoi('');
      return undefined;
    }
    let dangHoatDong = true;
    setRawImg(null);
    setLoi('');
    setXacNhan(null);
    const reader = new FileReader();
    reader.onload = (e) => {
      if (!dangHoatDong) return;
      const src = e.target?.result as string;
      const img = new Image();
      img.onload = () => {
        if (!dangHoatDong) return;
        setRawImg(img);
        setLoi('');
        const fitW = CROP_W / img.width;
        const fitH = CROP_H / img.height;
        const initScale = Math.min(fitW, fitH);
        setBaseScale(initScale > 0 ? initScale : 1);
        setZoom(1);
        setOffset({ x: 0, y: 0 });
      };
      img.onerror = () => {
        if (dangHoatDong) setLoi(dichRef.current('pin.chuaChonAnh'));
      };
      img.src = src;
    };
    reader.onerror = () => {
      if (dangHoatDong) setLoi(dichRef.current('pin.chuaChonAnh'));
    };
    reader.readAsDataURL(tep);
    return () => {
      dangHoatDong = false;
      if (reader.readyState === FileReader.LOADING) reader.abort();
    };
  }, [tep]);

  const gioiHanViTriKeo = useCallback((x: number, y: number) => {
    if (!rawImg) return { x, y };
    const currentScale = baseScale * zoom;
    const imgW = rawImg.width * currentScale;
    const imgH = rawImg.height * currentScale;
    const maxDistX = Math.max(imgW / 2 + CROP_W / 2 - 20, CROP_W / 2);
    const maxDistY = Math.max(imgH / 2 + CROP_H / 2 - 20, CROP_H / 2);
    return {
      x: Math.max(-maxDistX, Math.min(maxDistX, x)),
      y: Math.max(-maxDistY, Math.min(maxDistY, y)),
    };
  }, [baseScale, rawImg, zoom]);

  const keoAnhDen = useCallback((clientX: number, clientY: number) => {
    const dx = clientX - dragStartRef.current.mouseX;
    const dy = clientY - dragStartRef.current.mouseY;
    setOffset(gioiHanViTriKeo(
      dragStartRef.current.startOffsetX + dx,
      dragStartRef.current.startOffsetY + dy,
    ));
  }, [gioiHanViTriKeo]);

  // 2. Kéo ảnh bằng pointer capture; touch giữ luồng pinch hiện có.
  useEffect(() => {
    if (!isDragging) return;

    const handleTouchMove = (e: TouchEvent) => {
      if (!rawImg) return;
      if (e.touches.length === 1) {
        const touch = e.touches[0];
        keoAnhDen(touch.clientX, touch.clientY);
      } else if (e.touches.length === 2 && touchStartDistRef.current) {
        // Pinch-to-zoom 2 ngón tay trên màn hình cảm ứng
        const dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY,
        );
        const scaleRatio = dist / touchStartDistRef.current;
        const nextZoom = Math.min(Math.max(Number((touchStartZoomRef.current * scaleRatio).toFixed(2)), 0.2), 6.0);
        setZoom(nextZoom);
      }
    };

    const handleTouchEnd = () => {
      setIsDragging(false);
      touchStartDistRef.current = null;
    };

    window.addEventListener('touchmove', handleTouchMove);
    window.addEventListener('touchend', handleTouchEnd);

    return () => {
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [isDragging, keoAnhDen, rawImg]);

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === 'touch' || (e.button !== 0 && e.button !== 2)) return;
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    setIsDragging(true);
    dragStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      startOffsetX: offset.x,
      startOffsetY: offset.y,
    };
  };

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === 'touch' || !e.currentTarget.hasPointerCapture(e.pointerId)) return;
    e.preventDefault();
    keoAnhDen(e.clientX, e.clientY);
  };

  const onPointerEnd = (e: React.PointerEvent<HTMLDivElement>) => {
    if (e.pointerType === 'touch') return;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    setIsDragging(false);
  };

  const onTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      setIsDragging(true);
      dragStartRef.current = {
        mouseX: e.touches[0].clientX,
        mouseY: e.touches[0].clientY,
        startOffsetX: offset.x,
        startOffsetY: offset.y,
      };
    } else if (e.touches.length === 2) {
      touchStartDistRef.current = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY,
      );
      touchStartZoomRef.current = zoom;
    }
  };

  // 3. Thu phóng toàn diện: Trackpad Pinch (Windows Precision Touchpad & Mac), 2-finger swipe, Mouse Wheel
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    let isHovered = false;
    const onEnter = () => { isHovered = true; };
    const onLeave = () => { isHovered = false; };

    el.addEventListener('mouseenter', onEnter);
    el.addEventListener('mouseleave', onLeave);

    const onWheelHandler = (e: WheelEvent) => {
      // Kích hoạt khi con trỏ chuột nằm trong hoặc trên khung vẽ
      if (!isHovered && !el.contains(e.target as Node)) return;

      e.preventDefault();
      e.stopPropagation();

      let delta = 0;
      if (e.ctrlKey) {
        // Trackpad 2-ngón tay pinch-to-zoom (Windows Precision Touchpad / Chrome MacOS)
        delta = -e.deltaY * 0.015;
      } else if (Math.abs(e.deltaY) < 50) {
        // Trackpad 2-ngón tay vuốt cuộn (2-finger swipe trên bàn rê chuột)
        delta = -e.deltaY * 0.008;
      } else {
        // Con lăn chuột vật lý thông thường
        delta = e.deltaY < 0 ? 0.08 : -0.08;
      }

      setZoom((z) => {
        const next = z + delta;
        return Math.min(Math.max(Number(next.toFixed(3)), 0.2), 6.0);
      });
    };

    // Hỗ trợ Safari Mac gesture pinch
    let initialZoom = 1;
    const onGestureStart = (e: Event) => {
      e.preventDefault();
      initialZoom = zoomRef.current;
    };
    const onGestureChange = (e: Event) => {
      e.preventDefault();
      const ge = e as unknown as { scale: number };
      if (ge.scale) {
        const next = initialZoom * ge.scale;
        setZoom(Math.min(Math.max(Number(next.toFixed(3)), 0.2), 6.0));
      }
    };

    // Gắn listener trên window với passive: false để chặn triệt để Browser Page Zoom của Windows khi pinch
    window.addEventListener('wheel', onWheelHandler, { passive: false });
    el.addEventListener('gesturestart', onGestureStart as EventListener, { passive: false });
    el.addEventListener('gesturechange', onGestureChange as EventListener, { passive: false });

    return () => {
      el.removeEventListener('mouseenter', onEnter);
      el.removeEventListener('mouseleave', onLeave);
      window.removeEventListener('wheel', onWheelHandler);
      el.removeEventListener('gesturestart', onGestureStart as EventListener);
      el.removeEventListener('gesturechange', onGestureChange as EventListener);
    };
  }, []);

  // 4. Vẽ ảnh vào viewport rồi tự động tách nét chữ ký khỏi nền giấy.
  const veCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !rawImg) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, VIEWPORT_W, VIEWPORT_H);

    const currentScale = baseScale * zoom;
    const drawW = rawImg.width * currentScale;
    const drawH = rawImg.height * currentScale;
    const drawX = CROP_CENTER_X + offset.x - drawW / 2;
    const drawY = CROP_CENTER_Y + offset.y - drawH / 2;

    ctx.drawImage(rawImg, drawX, drawY, drawW, drawH);
    scanChuKy(ctx, VIEWPORT_W, VIEWPORT_H);
  }, [baseScale, offset.x, offset.y, rawImg, zoom]);

  useEffect(() => {
    veCanvas();
  }, [veCanvas, mo, xacNhan]);

  // 5. Cắt ảnh và mở modal xác nhận trước khi lưu
  const xuatAnh = () => {
    if (!rawImg) return;
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = CROP_W;
    exportCanvas.height = CROP_H;
    const exportCtx = exportCanvas.getContext('2d');
    if (!exportCtx) return;

    const currentScale = baseScale * zoom;
    const drawW = rawImg.width * currentScale;
    const drawH = rawImg.height * currentScale;
    const drawX = CROP_CENTER_X + offset.x - drawW / 2;
    const drawY = CROP_CENTER_Y + offset.y - drawH / 2;

    const expX = drawX - CROP_X;
    const expY = drawY - CROP_Y;

    exportCtx.drawImage(rawImg, expX, expY, drawW, drawH);
    scanChuKy(exportCtx, CROP_W, CROP_H);

    exportCanvas.toBlob((blob) => {
      if (!blob) return;
      const dataUrl = exportCanvas.toDataURL('image/png');
      setXacNhan({ blob, dataUrl });
    }, 'image/png');
  };

  // 6. Người dùng xác nhận lưu ảnh chữ ký
  const onDongYApDung = () => {
    if (!xacNhan) return;
    onLuu(xacNhan.blob, xacNhan.dataUrl);
    setXacNhan(null);
  };

  const onHuyXacNhan = () => {
    setXacNhan(null);
  };

  return (
    <>
      {/* Modal cắt ảnh chữ ký (tối giản, không tiêu đề, không text thừa, gọn gàng 480px) */}
      <HopThoai
        mo={mo}
        moTieuDe=""
        onDong={onDong}
        dangXuLy={dangXuLy}
        chieuRong="480px"
        chanDuoi={
          <>
            <Button variant="secondary" onClick={onDong} disabled={dangXuLy}>
              {t('chung.huyBo')}
            </Button>
            <Button
              variant="primary"
              icon="fa-crop-simple"
              isLoading={dangXuLy}
              disabled={!rawImg || Boolean(loi)}
              onClick={xuatAnh}
            >
              {t('pin.xacNhanCat')}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          {loi && <ThongBao loai="loi">{loi}</ThongBao>}

          {/* Khung Viewport xem trước chứa Khung Cắt 300x150 cố định ở giữa */}
          <div className="flex justify-center">
            <div
              ref={containerRef}
              className={`relative overflow-hidden rounded-xl border border-border-subtle shadow-inner select-none touch-none ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
              style={{
                width: `${VIEWPORT_W}px`,
                height: `${VIEWPORT_H}px`,
                backgroundImage:
                  'linear-gradient(45deg, #e5e5e5 25%, transparent 25%), linear-gradient(-45deg, #e5e5e5 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #e5e5e5 75%), linear-gradient(-45deg, transparent 75%, #e5e5e5 75%)',
                backgroundSize: '16px 16px',
                backgroundPosition: '0 0, 0 8px, 8px -8px, -8px 0px',
              }}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerEnd}
              onPointerCancel={onPointerEnd}
              onLostPointerCapture={() => setIsDragging(false)}
              onTouchStart={onTouchStart}
              onContextMenu={(e) => e.preventDefault()}
            >
              {/* Canvas vẽ ảnh di chuyển bên dưới */}
              <canvas
                ref={canvasRef}
                width={VIEWPORT_W}
                height={VIEWPORT_H}
                className="w-full h-full block"
              />

              {/* Khung cắt 300x150 nằm cố định ở giữa với lớp phủ tối mờ bên ngoài */}
              <div
                className="absolute pointer-events-none rounded border-2 border-primary"
                style={{
                  left: `${CROP_X}px`,
                  top: `${CROP_Y}px`,
                  width: `${CROP_W}px`,
                  height: `${CROP_H}px`,
                  boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.45)',
                }}
              >
                {/* 4 góc chỉ báo viền cắt màu trắng */}
                <div className="absolute -top-1 -left-1 w-3 h-3 border-t-2 border-l-2 border-white shadow-sm" />
                <div className="absolute -top-1 -right-1 w-3 h-3 border-t-2 border-r-2 border-white shadow-sm" />
                <div className="absolute -bottom-1 -left-1 w-3 h-3 border-b-2 border-l-2 border-white shadow-sm" />
                <div className="absolute -bottom-1 -right-1 w-3 h-3 border-b-2 border-r-2 border-white shadow-sm" />
              </div>
            </div>
          </div>
          {rawImg && (
            <label className="block space-y-1.5">
              <span className="flex items-center justify-between gap-2 text-sm font-medium text-main">
                <span>{t('pin.thuPhong')}</span>
                <span className="text-secondary tabular-nums">{Math.round(zoom * 100)}%</span>
              </span>
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={Math.round(((zoom - 0.2) / (6 - 0.2)) * 100)}
                onChange={(e) => setZoom(0.2 + (Number(e.target.value) / 100) * (6 - 0.2))}
                aria-label={t('pin.thuPhong')}
                aria-valuetext={`${Math.round(zoom * 100)}%`}
                className="w-full cursor-pointer accent-primary"
              />
            </label>
          )}
        </div>
      </HopThoai>

      {/* Modal xác nhận kết quả cắt chữ ký (chiều rộng nhỏ gọn 400px) */}
      {xacNhan && (
        <HopThoai
          mo={Boolean(xacNhan)}
          moTieuDe={t('pin.xacNhanChuKyTieuDe')}
          onDong={onHuyXacNhan}
          dangXuLy={dangXuLy}
          chieuRong="400px"
          chanDuoi={
            <>
              <Button variant="secondary" onClick={onHuyXacNhan} disabled={dangXuLy}>
                {t('pin.chinhSuaLai')}
              </Button>
              <Button
                variant="primary"
                icon="fa-check"
                isLoading={dangXuLy}
                onClick={onDongYApDung}
              >
                {t('pin.dongYApDung')}
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <ThongBao loai="canh_bao">
              {t('pin.xacNhanChuKyNoiDung')}
            </ThongBao>

            <div className="flex flex-col items-center justify-center space-y-2">
              <span className="text-xs text-secondary font-medium">
                {t('pin.ketQuaCat')}
              </span>
              <div
                className="flex items-center justify-center p-3 rounded-lg border-2 border-primary shadow-sm"
                style={{
                  width: `${CROP_W}px`,
                  height: `${CROP_H}px`,
                  backgroundImage:
                    'linear-gradient(45deg, #e5e5e5 25%, transparent 25%), linear-gradient(-45deg, #e5e5e5 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #e5e5e5 75%), linear-gradient(-45deg, transparent 75%, #e5e5e5 75%)',
                  backgroundSize: '16px 16px',
                  backgroundPosition: '0 0, 0 8px, 8px -8px, -8px 0px',
                }}
              >
                <img
                  src={xacNhan.dataUrl}
                  alt={t('pin.chuKyCaNhan')}
                  className="w-full h-full object-contain"
                />
              </div>
            </div>
          </div>
        </HopThoai>
      )}
    </>
  );
}
