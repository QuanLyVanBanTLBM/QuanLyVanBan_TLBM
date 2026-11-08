import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Hook theo dõi thời gian bất động của người dùng (Idle Timer)
 * Tự động khóa màn hình làm việc sau khoảng thời gian không có thao tác chuột/phím
 */
export function useIdleTimer() {
  const [isLocked, setIsLocked] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    const hasSession = Boolean(
      localStorage.getItem('tlbm_session') ||
        localStorage.getItem('tlbm_access_token') ||
        localStorage.getItem('tlbm_token')
    );
    return hasSession && sessionStorage.getItem('tlbm_screen_locked') === 'true';
  });

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const lock = useCallback(() => {
    const hasSession = Boolean(
      localStorage.getItem('tlbm_session') ||
        localStorage.getItem('tlbm_access_token') ||
        localStorage.getItem('tlbm_token')
    );
    if (!hasSession) return;

    sessionStorage.setItem('tlbm_screen_locked', 'true');
    setIsLocked(true);
    window.dispatchEvent(new CustomEvent('tlbm_screen_locked_changed', { detail: { isLocked: true } }));
  }, []);

  const unlock = useCallback(() => {
    sessionStorage.removeItem('tlbm_screen_locked');
    setIsLocked(false);
    window.dispatchEvent(new CustomEvent('tlbm_screen_locked_changed', { detail: { isLocked: false } }));
  }, []);

  useEffect(() => {
    const checkEnabled = () => {
      const isEnabled = localStorage.getItem('tlbm_sec_auto_lock') !== 'false';
      const timeoutMinutes = parseInt(localStorage.getItem('tlbm_sec_lock_timeout') || '15', 10);
      return { isEnabled, timeoutMs: Math.max(1, timeoutMinutes) * 60 * 1000 };
    };

    const resetTimer = () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }

      const { isEnabled, timeoutMs } = checkEnabled();
      const hasSession = Boolean(
        localStorage.getItem('tlbm_session') ||
          localStorage.getItem('tlbm_access_token') ||
          localStorage.getItem('tlbm_token')
      );

      if (!isEnabled || !hasSession || isLocked) {
        return;
      }

      timerRef.current = setTimeout(() => {
        lock();
      }, timeoutMs);
    };

    const activityEvents = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'];

    let lastActivityTime = 0;
    const handleUserActivity = () => {
      const now = Date.now();
      // Throttle lại sự kiện kiểm tra mỗi 1 giây để tối ưu hiệu năng
      if (now - lastActivityTime > 1000) {
        lastActivityTime = now;
        resetTimer();
      }
    };

    activityEvents.forEach((evt) => {
      window.addEventListener(evt, handleUserActivity, { passive: true });
    });

    const handleLockNow = () => lock();
    const handleUnlockNow = () => unlock();
    const handleSettingsChanged = () => resetTimer();

    window.addEventListener('tlbm_lock_screen_now', handleLockNow);
    window.addEventListener('tlbm_unlock_screen', handleUnlockNow);
    window.addEventListener('tlbm_settings_updated', handleSettingsChanged);

    resetTimer();

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      activityEvents.forEach((evt) => {
        window.removeEventListener(evt, handleUserActivity);
      });
      window.removeEventListener('tlbm_lock_screen_now', handleLockNow);
      window.removeEventListener('tlbm_unlock_screen', handleUnlockNow);
      window.removeEventListener('tlbm_settings_updated', handleSettingsChanged);
    };
  }, [isLocked, lock, unlock]);

  return { isLocked, lock, unlock };
}

export default useIdleTimer;
