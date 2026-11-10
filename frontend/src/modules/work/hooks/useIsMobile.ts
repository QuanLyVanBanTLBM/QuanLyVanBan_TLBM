import { useSyncExternalStore } from 'react';

/**
 * Trả về true khi viewport có chiều rộng nhỏ hơn `maxWidth` (mặc định 768px,
 * khớp breakpoint md của Tailwind). Dùng cho các chỗ phải chuyển hẳn kiểu
 * render (bảng → card list, modal → full-screen) chứ không chỉ đổi CSS.
 *
 * Dùng useSyncExternalStore để tránh gọi setState trong useEffect (lint rule
 * react-hooks/set-state-in-effect của React 19) và đảm bảo đồng bộ snapshot.
 *
 * jsdom (môi trường test mặc định) không có window.matchMedia nên guard lại
 * để tránh test ném lỗi: trả về desktop (false) khi matchMedia chưa có.
 */
function hasMatchMedia(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function';
}

function subscribe(query: string): (callback: () => void) => () => void {
  return (callback) => {
    if (!hasMatchMedia()) return () => undefined;
    const mql = window.matchMedia(query);
    mql.addEventListener('change', callback);
    return () => mql.removeEventListener('change', callback);
  };
}

function getSnapshot(query: string): () => boolean {
  return () => {
    if (!hasMatchMedia()) return false;
    return window.matchMedia(query).matches;
  };
}

function getServerSnapshot(): boolean {
  return false;
}

export function useIsMobile(maxWidth = 767): boolean {
  const query = `(max-width: ${maxWidth}px)`;
  return useSyncExternalStore(subscribe(query), getSnapshot(query), getServerSnapshot);
}
