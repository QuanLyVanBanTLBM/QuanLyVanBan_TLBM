import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useIdleTimer } from './useIdleTimer';

describe('useIdleTimer hook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    sessionStorage.clear();
    localStorage.setItem('tlbm_session', JSON.stringify({ username: 'testuser' }));
    localStorage.setItem('tlbm_sec_auto_lock', 'true');
    localStorage.setItem('tlbm_sec_lock_timeout', '15');
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts unlocked by default', () => {
    const { result } = renderHook(() => useIdleTimer());
    expect(result.current.isLocked).toBe(false);
  });

  it('locks when lock() is called or tlbm_lock_screen_now event is fired', () => {
    const { result } = renderHook(() => useIdleTimer());

    act(() => {
      result.current.lock();
    });

    expect(result.current.isLocked).toBe(true);
    expect(sessionStorage.getItem('tlbm_screen_locked')).toBe('true');

    act(() => {
      result.current.unlock();
    });
    expect(result.current.isLocked).toBe(false);
  });

  it('triggers lock automatically when idle timeout expires', () => {
    localStorage.setItem('tlbm_sec_lock_timeout', '5'); // 5 minutes
    const { result } = renderHook(() => useIdleTimer());

    expect(result.current.isLocked).toBe(false);

    // Fast-forward 5 minutes (300,000 ms)
    act(() => {
      vi.advanceTimersByTime(5 * 60 * 1000);
    });

    expect(result.current.isLocked).toBe(true);
  });

  it('resets timer when user activity occurs', () => {
    localStorage.setItem('tlbm_sec_lock_timeout', '5');
    const { result } = renderHook(() => useIdleTimer());

    // Advance 4 minutes
    act(() => {
      vi.advanceTimersByTime(4 * 60 * 1000);
    });
    expect(result.current.isLocked).toBe(false);

    // User activity: mousemove
    act(() => {
      window.dispatchEvent(new Event('mousemove'));
    });

    // Advance another 2 minutes (total 6 min, but timer was reset)
    act(() => {
      vi.advanceTimersByTime(2 * 60 * 1000);
    });
    expect(result.current.isLocked).toBe(false);

    // Advance remaining 3 minutes
    act(() => {
      vi.advanceTimersByTime(3 * 60 * 1000);
    });
    expect(result.current.isLocked).toBe(true);
  });
});
