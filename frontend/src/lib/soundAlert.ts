/**
 * Tiện ích phát âm thanh cảnh báo sử dụng Web Audio API chuẩn trình duyệt.
 * Không phụ thuộc tài nguyên bên ngoài, không tốn băng thông, an toàn 100%.
 */

export class SoundAlertManager {
  private audioCtx: AudioContext | null = null;

  public isUrgentSoundEnabled(): boolean {
    if (typeof window === 'undefined') return false;
    const val = localStorage.getItem('tlbm_notif_sound_urgent');
    return val !== 'false';
  }

  public setUrgentSoundEnabled(enabled: boolean): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem('tlbm_notif_sound_urgent', String(enabled));
    window.dispatchEvent(new Event('tlbm_sound_settings_updated'));
  }

  private getAudioContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    try {
      const AudioCtxClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtxClass) return null;

      if (!this.audioCtx) {
        this.audioCtx = new AudioCtxClass();
      }
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume().catch(() => {});
      }
      return this.audioCtx;
    } catch {
      return null;
    }
  }

  /**
   * Phát chuông cảnh báo hai âm sắc thanh lịch (D5 587.33Hz -> A5 880Hz)
   * @param force Nếu true, phát bất kể toggle có bật hay không (dùng cho nút Nghe thử)
   */
  public playUrgentChime(force: boolean = false): void {
    if (!force && !this.isUrgentSoundEnabled()) {
      return;
    }

    const ctx = this.getAudioContext();
    if (!ctx) return;

    try {
      const now = ctx.currentTime;

      // Nốt 1: D5 (587.33 Hz)
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(587.33, now);
      gain1.gain.setValueAtTime(0, now);
      gain1.gain.linearRampToValueAtTime(0.2, now + 0.02);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start(now);
      osc1.stop(now + 0.25);

      // Nốt 2: A5 (880 Hz) - tạo âm hưởng chuông vang
      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(880, now + 0.12);
      gain2.gain.setValueAtTime(0, now + 0.12);
      gain2.gain.linearRampToValueAtTime(0.25, now + 0.14);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.55);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start(now + 0.12);
      osc2.stop(now + 0.55);
    } catch {
      // Bỏ qua lỗi audio nếu trình duyệt chặn autoplay
    }
  }
}

export const soundAlert = new SoundAlertManager();
export default soundAlert;
