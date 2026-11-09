import React, { useState, useEffect, useRef } from 'react';
import { ActivePageId } from '@app-types/navigation';
import { ThemeMode } from '@app-types/theme';
import { useVisibleModules } from '@lib/navPermissions';

interface MobileAssistiveTouchProps {
  activePage: ActivePageId;
  onNavigate: (pageId: ActivePageId) => void;
  currentTheme: ThemeMode;
  onSelectTheme: (theme: ThemeMode) => void;
  onToggleTheme?: () => void;
}

export default function MobileAssistiveTouch({
  activePage,
  onNavigate,
  currentTheme,
  onSelectTheme,
  onToggleTheme,
}: MobileAssistiveTouchProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isDimmed, setIsDimmed] = useState(false);

  // Vị trí tọa độ kéo thả tự do của nút Home ảo (lưu vào localStorage)
  const [position, setPosition] = useState<{ x: number; y: number } | null>(() => {
    try {
      const saved = localStorage.getItem('tlbm_assistive_pos');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (typeof parsed.x === 'number' && typeof parsed.y === 'number') {
          return parsed;
        }
      }
    } catch {
      // ignore
    }
    return null;
  });

  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{
    startX: number;
    startY: number;
    initialPosX: number;
    initialPosY: number;
    hasMoved: boolean;
  }>({
    startX: 0,
    startY: 0,
    initialPosX: 0,
    initialPosY: 0,
    hasMoved: false,
  });

  const visibleModules = useVisibleModules();

  // Xác định phân hệ cha đang chứa trang hiện tại
  const activeModule =
    visibleModules.find((mod) => mod.subItems.some((item) => item.id === activePage)) ||
    visibleModules[0];

  // Cơ chế tự động mờ phím Home ảo sau 3.5s nếu không tương tác
  useEffect(() => {
    if (isOpen || isDragging) {
      return;
    }

    const timer = window.setTimeout(() => {
      setIsDimmed(true);
    }, 3500);

    const handleUserActivity = () => {
      setIsDimmed(false);
    };

    window.addEventListener('scroll', handleUserActivity, { passive: true });
    window.addEventListener('touchstart', handleUserActivity, { passive: true });

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('scroll', handleUserActivity);
      window.removeEventListener('touchstart', handleUserActivity);
    };
  }, [isOpen, isDragging]);

  // Xử lý kéo thả nút Home ảo tự do trên màn hình (Touch & Mouse)
  useEffect(() => {
    if (!isDragging) return;

    const handlePointerMove = (e: MouseEvent | TouchEvent) => {
      const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
      const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
      const deltaX = clientX - dragRef.current.startX;
      const deltaY = clientY - dragRef.current.startY;

      if (Math.abs(deltaX) > 4 || Math.abs(deltaY) > 4) {
        dragRef.current.hasMoved = true;
      }

      const newX = Math.min(Math.max(8, dragRef.current.initialPosX + deltaX), window.innerWidth - 64);
      const newY = Math.min(Math.max(8, dragRef.current.initialPosY + deltaY), window.innerHeight - 64);
      setPosition({ x: newX, y: newY });
    };

    const handlePointerUp = () => {
      setIsDragging(false);
      if (dragRef.current.hasMoved) {
        setPosition((currentPos) => {
          if (currentPos) {
            localStorage.setItem('tlbm_assistive_pos', JSON.stringify(currentPos));
          }
          return currentPos;
        });
      }
    };

    window.addEventListener('mousemove', handlePointerMove);
    window.addEventListener('mouseup', handlePointerUp);
    window.addEventListener('touchmove', handlePointerMove, { passive: false });
    window.addEventListener('touchend', handlePointerUp);

    return () => {
      window.removeEventListener('mousemove', handlePointerMove);
      window.removeEventListener('mouseup', handlePointerUp);
      window.removeEventListener('touchmove', handlePointerMove);
      window.removeEventListener('touchend', handlePointerUp);
    };
  }, [isDragging]);

  // Giữ vị trí nằm trong khung hình khi đổi kích thước cửa sổ
  useEffect(() => {
    const handleResize = () => {
      setPosition((prev) => {
        if (!prev) return null;
        return {
          x: Math.min(prev.x, window.innerWidth - 64),
          y: Math.min(prev.y, window.innerHeight - 64),
        };
      });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleToggleTheme = () => {
    if (onToggleTheme) {
      onToggleTheme();
    } else {
      const nextTheme: ThemeMode = currentTheme === 'dark' ? 'light' : 'dark';
      onSelectTheme(nextTheme);
    }
  };

  return (
    <aside aria-label="Phím Home ảo AssistiveTouch">
      {/* 1. NÚT HOME ẢO (AssistiveTouch FAB - Kéo thả tự do như iOS) */}
      <button
        type="button"
        className={`w-14 h-14 rounded-full bg-neutral-900/90 border border-white/20 shadow-glass flex items-center justify-center select-none backdrop-blur-md transition-opacity duration-300 ${
          isDimmed && !isDragging && !isOpen ? 'opacity-40 hover:opacity-100' : 'opacity-100'
        } ${isOpen ? 'ring-2 ring-primary' : ''}`}
        style={
          position
            ? {
                position: 'fixed',
                left: `${position.x}px`,
                top: `${position.y}px`,
                bottom: 'auto',
                right: 'auto',
                touchAction: 'none',
                cursor: isDragging ? 'grabbing' : 'grab',
                zIndex: 10000,
              }
            : {
                position: 'fixed',
                bottom: '24px',
                right: '18px',
                touchAction: 'none',
                cursor: isDragging ? 'grabbing' : 'grab',
                zIndex: 10000,
              }
        }
        onMouseDown={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          dragRef.current = {
            startX: e.clientX,
            startY: e.clientY,
            initialPosX: rect.left,
            initialPosY: rect.top,
            hasMoved: false,
          };
          setIsDragging(true);
          setIsDimmed(false);
        }}
        onTouchStart={(e) => {
          const touch = e.touches[0];
          const rect = e.currentTarget.getBoundingClientRect();
          dragRef.current = {
            startX: touch.clientX,
            startY: touch.clientY,
            initialPosX: rect.left,
            initialPosY: rect.top,
            hasMoved: false,
          };
          setIsDragging(true);
          setIsDimmed(false);
        }}
        onClick={() => {
          if (!dragRef.current.hasMoved) {
            setIsOpen((prev) => !prev);
            setIsDimmed(false);
          }
        }}
        title="Mở menu hệ thống (AssistiveTouch) · Nhấn để mở, giữ để kéo thả"
        aria-label="Phím Home ảo"
      >
        <span className="w-10 h-10 rounded-full border border-white/40 flex items-center justify-center pointer-events-none">
          <span className="w-6 h-6 rounded-full bg-white/70 flex items-center justify-center shadow-xs">
            <span className="w-2.5 h-2.5 rounded-full bg-neutral-900" />
          </span>
        </span>
      </button>

      {/* 2. BẢNG ĐIỀU KHIỂN MODAL DẠNG KÍNH MỜ (Khi bung ra) */}
      {isOpen && (
        <div
          className="fixed inset-0 z-[10002] bg-backdrop backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setIsOpen(false)}
          aria-label="Đóng menu"
        >
          <div
            className="w-full max-w-sm rounded-2xl bg-surface-elevated border border-subtle shadow-glass p-4 flex flex-col gap-4 z-[10003]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header nhỏ thông tin hệ thống */}
            <div className="flex items-center justify-between pb-3 border-b border-subtle">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-sm shadow-xs">
                  <i className="fa-solid fa-file-shield" />
                </div>
                <div className="flex flex-col">
                  <span className="font-bold text-sm text-text-main leading-tight">TLBM Mobile</span>
                  <span className="text-[11px] text-text-muted leading-tight">Menu Hệ Thống</span>
                </div>
              </div>

              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-success-subtle text-success text-[11px] font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                <span>Trực tuyến</span>
              </div>
            </div>

            {/* Lưới 6 Phân hệ biểu tượng phong cách Apple */}
            <div className="grid grid-cols-3 gap-2.5">
              {visibleModules.map((mod) => {
                const isSelected = activeModule.id === mod.id;
                const numericBadges = mod.subItems
                  .map((s) => (typeof s.badge === 'number' ? s.badge : 0))
                  .reduce((a, b) => a + b, 0);

                return (
                  <button
                    key={mod.id}
                    type="button"
                    className={`flex flex-col items-center justify-center p-2.5 rounded-xl border transition-all text-center cursor-pointer relative ${
                      isSelected
                        ? 'bg-primary-subtle/40 border-primary-border shadow-xs'
                        : 'border-transparent hover:border-subtle hover:bg-surface-hover'
                    }`}
                    onClick={() => {
                      onNavigate(mod.defaultPage);
                      setIsOpen(false);
                    }}
                  >
                    <div className="w-11 h-11 rounded-xl bg-surface border border-subtle flex items-center justify-center text-lg text-primary mb-1.5 relative shadow-xs">
                      <i className={`fa-solid ${mod.icon}`} />
                      {numericBadges > 0 && (
                        <span className="absolute -top-1.5 -right-1.5 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-danger text-white ring-2 ring-surface">
                          {numericBadges}
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-medium text-text-main truncate w-full">{mod.label}</span>
                    <span className="text-[10px] text-text-muted font-mono">{mod.teamTag}</span>
                  </button>
                );
              })}
            </div>

            {/* Thanh thao tác nhanh ở đáy: Đổi Theme & Đóng nhanh */}
            <div className="flex items-center justify-between pt-3 border-t border-subtle gap-2">
              <button
                type="button"
                className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-surface border border-subtle text-xs font-medium text-text-main hover:bg-surface-hover transition-colors"
                onClick={handleToggleTheme}
                title="Chuyển đổi giao diện Sáng / Tối"
              >
                <i className={`fa-solid ${currentTheme === 'dark' ? 'fa-sun' : 'fa-moon'}`} />
                <span>{currentTheme === 'dark' ? 'Chế độ Sáng' : 'Chế độ Tối'}</span>
              </button>

              <button
                type="button"
                className="w-9 h-9 rounded-full bg-surface border border-subtle text-text-muted hover:text-text-main hover:bg-surface-hover flex items-center justify-center text-sm transition-colors"
                onClick={() => setIsOpen(false)}
                title="Đóng bảng AssistiveTouch"
                aria-label="Đóng bảng"
              >
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}


