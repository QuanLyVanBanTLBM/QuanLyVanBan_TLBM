import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Region, Unit } from '@app-types/organization';

interface RegionUnitSelectProps {
  regions: Region[];
  units: Unit[];
  regionId: string;
  unitId: string;
  placeholder: string;
  allLabel: string;
  unitsLabel: string;
  onSelectRegion: (regionId: string) => void;
  onSelectUnit: (regionId: string, unitId: string) => void;
}

// Dropdown Khối (cấp 1): rê chuột vào một Khối thì hiện danh sách Đơn vị (cấp 2) của Khối đó,
// bấm vào Khối để lọc theo Khối và mở luôn danh sách Đơn vị của Khối đó (dropdown chưa đóng),
// bấm vào Đơn vị để lọc thẳng theo Đơn vị. Khối không có Đơn vị thì bấm vào là chọn và đóng.
// Màn hình cảm ứng không có hover nên mỗi Khối có thêm nút mũi tên để mở/đóng danh sách Đơn vị.
// Màn hình lớn: danh sách Đơn vị vẽ ra ngoài khung cuộn của danh sách Khối (portal + vị trí cố định) để không bị cắt.
export const RegionUnitSelect: React.FC<RegionUnitSelectProps> = ({
  regions,
  units,
  regionId,
  unitId,
  placeholder,
  allLabel,
  unitsLabel,
  onSelectRegion,
  onSelectUnit,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<string>('');
  const [flyout, setFlyout] = useState<{ left: number; top: number } | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const flyoutRef = useRef<HTMLDivElement>(null);
  const leaveTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!isOpen) return;
    const onDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (rootRef.current?.contains(target) || flyoutRef.current?.contains(target)) return;
      setIsOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [isOpen]);

  const selectedRegion = regions.find((r) => String(r.id) === regionId);
  const unitsOf = (id: string) => units.filter((u) => String(u.khoi) === id);

  const close = () => {
    window.clearTimeout(leaveTimer.current);
    setIsOpen(false);
    setExpandedId('');
  };

  useEffect(() => () => window.clearTimeout(leaveTimer.current), []);

  // Màn hình nhỏ: danh sách Đơn vị mở ngay dưới Khối nên chỉ mở/đóng khi bấm. Nếu mở theo hover,
  // rê chuột qua một Khối làm các dòng bên dưới bị đẩy xuống và cú bấm rơi nhầm vào dòng khác.
  const isWideScreen = () => typeof window.matchMedia !== 'function' || window.matchMedia('(min-width: 768px)').matches;

  // Rê chuột từ Khối sang danh sách Đơn vị phải đi qua khoảng hở nên chờ một chút trước khi đóng
  const keepOpen = () => window.clearTimeout(leaveTimer.current);
  const closeSoon = () => {
    if (!isWideScreen()) return;
    window.clearTimeout(leaveTimer.current);
    leaveTimer.current = window.setTimeout(() => setExpandedId(''), 180);
  };
  const expandRegion = (id: string, row: HTMLElement) => {
    keepOpen();
    const rect = row.getBoundingClientRect();
    const height = Math.min(288, window.innerHeight - 16);
    setFlyout({ left: rect.right + 4, top: Math.max(8, Math.min(rect.top, window.innerHeight - height - 8)) });
    setExpandedId(id);
  };

  const renderUnits = (id: string) => (
    <div role="group" aria-label={unitsLabel}>
      {unitsOf(id).map((u) => (
        <div
          key={u.id}
          role="option"
          aria-selected={String(u.id) === unitId}
          onClick={() => {
            onSelectUnit(id, String(u.id));
            close();
          }}
          className={`px-3 py-2 text-sm rounded-lg cursor-pointer select-none truncate transition-colors ${
            String(u.id) === unitId
              ? 'bg-primary/15 text-primary font-semibold'
              : 'text-main hover:bg-surface-hover hover:text-primary'
          }`}
        >
          {u.ten}
        </div>
      ))}
    </div>
  );

  return (
    <div ref={rootRef} className="relative w-full">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={placeholder}
        onClick={() => setIsOpen((o) => !o)}
        className={`w-full flex items-center justify-between gap-2 bg-surface-elevated border rounded-lg text-left select-none transition-all duration-fast cursor-pointer px-3.5 py-2 text-sm ${
          isOpen ? 'border-primary ring-2 ring-primary/20 shadow-sm' : 'border-border hover:border-primary/50'
        }`}
      >
        <span className="flex items-center gap-2 overflow-hidden flex-1 min-w-0">
          <i className="fa-solid fa-layer-group text-muted shrink-0 text-xs" />
          <span className={`truncate ${selectedRegion ? 'text-main font-medium' : 'text-muted'}`}>
            {selectedRegion ? selectedRegion.ten : placeholder}
          </span>
        </span>
        <i
          className={`fa-solid fa-chevron-down text-[11px] text-muted transition-transform duration-200 ${
            isOpen ? 'rotate-180 text-primary' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div
          role="listbox"
          className="dropdown-animate absolute left-0 right-0 top-full mt-1.5 w-full rounded-xl bg-surface-elevated border border-border-subtle shadow-2xl p-1.5 z-[10002] flex flex-col box-border"
          onMouseLeave={closeSoon}
        >
          <div
            role="option"
            aria-selected={regionId === ''}
            onClick={() => {
              onSelectRegion('');
              close();
            }}
            onMouseEnter={() => {
              keepOpen();
              if (isWideScreen()) setExpandedId('');
            }}
            className={`px-3 py-2 text-sm rounded-lg cursor-pointer select-none transition-colors ${
              regionId === '' ? 'bg-primary/15 text-primary font-semibold' : 'text-main hover:bg-surface-hover hover:text-primary'
            }`}
          >
            {allLabel}
          </div>
          <div className="max-h-72 overflow-y-auto">
            {regions.map((reg) => {
              const id = String(reg.id);
              const children = unitsOf(id);
              const expanded = expandedId === id && children.length > 0;
              return (
                <div key={reg.id} data-region-row className="relative" onMouseEnter={(e) => {
                    if (isWideScreen()) expandRegion(id, e.currentTarget);
                  }}
                >
                  <div
                    className={`flex items-center justify-between rounded-lg transition-colors ${
                      regionId === id ? 'bg-primary/15 text-primary font-semibold' : 'text-main hover:bg-surface-hover hover:text-primary'
                    }`}
                  >
                    <div
                      role="option"
                      aria-selected={regionId === id}
                      onClick={(e) => {
                        onSelectRegion(id);
                        const row = e.currentTarget.closest<HTMLElement>('[data-region-row]');
                        if (children.length > 0 && row) {
                          expandRegion(id, row);
                          // Màn hình nhỏ: cuộn để danh sách Đơn vị vừa mở hiện ra (Khối ở cuối danh sách thì Đơn vị bị khuất)
                          if (!isWideScreen()) window.requestAnimationFrame(() => row.scrollIntoView?.({ block: 'nearest' }));
                        } else close();
                      }}
                      className="flex-1 min-w-0 px-3 py-2 text-sm cursor-pointer select-none truncate"
                    >
                      {reg.ten}
                    </div>
                    {children.length > 0 && (
                      <button
                        type="button"
                        aria-label={`${unitsLabel}: ${reg.ten}`}
                        aria-expanded={expanded}
                        onClick={(e) => {
                          const row = e.currentTarget.closest<HTMLElement>('[data-region-row]');
                          if (expanded || !row) setExpandedId('');
                          else expandRegion(id, row);
                        }}
                        className="px-3 py-2 text-muted hover:text-primary cursor-pointer"
                      >
                        <i className={`fa-solid fa-chevron-right text-[11px] transition-transform ${expanded ? 'rotate-90 md:rotate-0' : ''}`} />
                      </button>
                    )}
                  </div>
                  {expanded && (
                    <>
                      {/* Màn hình nhỏ: danh sách đơn vị mở ngay dưới Khối */}
                      <div className="md:hidden pl-4 pr-1 pb-1">{renderUnits(id)}</div>
                      {/* Màn hình lớn: danh sách đơn vị bung sang phải khi hover */}
                      {flyout &&
                        createPortal(
                          <div
                            ref={flyoutRef}
                            style={{ left: flyout.left, top: flyout.top }}
                            onMouseEnter={keepOpen}
                            onMouseLeave={closeSoon}
                            className="hidden md:block fixed w-64 max-h-72 overflow-y-auto rounded-xl bg-surface-elevated border border-border-subtle shadow-2xl p-1.5 z-[10003]"
                          >
                            {renderUnits(id)}
                          </div>,
                          document.body,
                        )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
