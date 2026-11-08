import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SoundAlertManager } from './soundAlert';

describe('SoundAlertManager', () => {
  let manager: SoundAlertManager;

  beforeEach(() => {
    localStorage.clear();
    manager = new SoundAlertManager();
  });

  it('defaults to true when no setting is saved in localStorage', () => {
    expect(manager.isUrgentSoundEnabled()).toBe(true);
  });

  it('updates sound enabled state and saves to localStorage', () => {
    manager.setUrgentSoundEnabled(false);
    expect(manager.isUrgentSoundEnabled()).toBe(false);
    expect(localStorage.getItem('tlbm_notif_sound_urgent')).toBe('false');

    manager.setUrgentSoundEnabled(true);
    expect(manager.isUrgentSoundEnabled()).toBe(true);
    expect(localStorage.getItem('tlbm_notif_sound_urgent')).toBe('true');
  });

  it('does not throw when playUrgentChime is called with AudioContext mocked', () => {
    const mockOscillator = {
      type: '',
      frequency: { setValueAtTime: vi.fn() },
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    };
    const mockGain = {
      gain: {
        setValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
    };

    const createOscillatorMock = vi.fn().mockReturnValue(mockOscillator);
    const createGainMock = vi.fn().mockReturnValue(mockGain);

    class MockAudioContext {
      currentTime = 10;
      state = 'running';
      createOscillator = createOscillatorMock;
      createGain = createGainMock;
      destination = {};
      resume = vi.fn().mockResolvedValue(undefined);
    }

    // @ts-expect-error Mocking AudioContext
    window.AudioContext = MockAudioContext;

    expect(() => manager.playUrgentChime()).not.toThrow();
    expect(createOscillatorMock).toHaveBeenCalled();
  });

  it('respects disabled state unless forced', () => {
    manager.setUrgentSoundEnabled(false);
    const createOscillatorMock = vi.fn();

    class MockAudioContext {
      currentTime = 10;
      state = 'running';
      createOscillator = createOscillatorMock;
      createGain = vi.fn().mockReturnValue({
        gain: {
          setValueAtTime: vi.fn(),
          linearRampToValueAtTime: vi.fn(),
          exponentialRampToValueAtTime: vi.fn(),
        },
        connect: vi.fn(),
      });
      destination = {};
    }

    // @ts-expect-error Mocking AudioContext
    window.AudioContext = MockAudioContext;

    manager.playUrgentChime(false);
    expect(createOscillatorMock).not.toHaveBeenCalled();

    manager.playUrgentChime(true);
    expect(createOscillatorMock).toHaveBeenCalled();
  });
});
