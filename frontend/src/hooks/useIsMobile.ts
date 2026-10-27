import { useSyncExternalStore } from 'react';

/**
 * Trả về true khi viewport có chiều rộng nhỏ hơn `maxWidth` (mặc định 767px,
 * khớp breakpoint md của Tailwind). Dùng cho các chỗ chuyển đổi giữa Desktop Table và Mobile Card View.
 * jsdom (môi trường test) không có matchMedia nên trả về desktop (false) an toàn.
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

export default useIsMobile;
