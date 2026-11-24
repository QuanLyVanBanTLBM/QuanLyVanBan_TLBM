import React, { useEffect, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { OtpChannel, TwoFactorChallenge, TwoFactorSendOtpResult } from '@app-types/auth';

type VerifyMode = 'totp' | 'email' | 'sms' | 'backup';

export interface TwoFactorStepProps {
  username: string;
  availableChannels?: TwoFactorChallenge['availableChannels'];
  maskedEmail?: string;
  maskedPhone?: string;
  isLoading: boolean;
  isSuccess: boolean;
  error?: string;
  onSendOtp?: (channel: OtpChannel, previousOtpToken?: string) => Promise<TwoFactorSendOtpResult>;
  onSubmitCode: (payload: { code: string; otpToken?: string; trustDevice: boolean }) => void;
  onBackToLogin: () => void;
}

export const TwoFactorStep: React.FC<TwoFactorStepProps> = ({
  username,
  availableChannels,
  maskedEmail,
  maskedPhone,
  isLoading,
  isSuccess,
  error,
  onSendOtp,
  onSubmitCode,
  onBackToLogin,
}) => {
  const { t } = useTranslation();
  const [mode, setMode] = useState<VerifyMode>('totp');
  const [code, setCode] = useState<string>('');
  const [trustDevice, setTrustDevice] = useState<boolean>(true);

  const [otpToken, setOtpToken] = useState<string>('');
  const [sentDestination, setSentDestination] = useState<string>('');
  const [sendingOtp, setSendingOtp] = useState<boolean>(false);
  const [cooldown, setCooldown] = useState<number>(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setInterval(() => {
      setCooldown((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  const handleTriggerSendOtp = async (channel: OtpChannel) => {
    if (!onSendOtp || sendingOtp || cooldown > 0) return;
    setSendingOtp(true);
    try {
      const res = await onSendOtp(channel, otpToken || undefined);
      setOtpToken(res.otp_token);
      setSentDestination(res.masked_destination);
      setCooldown(res.cooldown_seconds || 60);
    } catch {
      // Lỗi đã được xử lý và hiển thị qua prop error từ LoginPage
    } finally {
      setSendingOtp(false);
    }
  };

  const handleModeChange = (nextMode: VerifyMode) => {
    setMode(nextMode);
    setCode('');
    if (nextMode === 'email' || nextMode === 'sms') {
      setOtpToken('');
      setSentDestination('');
      setCooldown(0);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmitCode({
      code,
      otpToken: mode === 'email' || mode === 'sms' ? otpToken : undefined,
      trustDevice,
    });
  };

  const isOtpChannel = mode === 'email' || mode === 'sms';
  const targetLabel = mode === 'email' ? maskedEmail : maskedPhone;

  const modes: Array<{ id: VerifyMode; label: string; visible: boolean }> = [
    { id: 'totp', label: t('auth.twofa.channels.totp'), visible: true },
    { id: 'email', label: t('auth.twofa.channels.email'), visible: Boolean(availableChannels?.email) },
    { id: 'sms', label: t('auth.twofa.channels.sms'), visible: Boolean(availableChannels?.sms) },
    { id: 'backup', label: t('auth.twofa.channels.backup'), visible: true },
  ];

  return (
    <div className="w-full md:w-[55%] bg-surface !rounded-none !shadow-none !border-none relative flex flex-col justify-center p-4 sm:p-6 md:p-8 animate-fade-in">
      <div className="flex items-center gap-2.5 mb-2">
        <div className="w-9 h-9 rounded-xl bg-primary-subtle text-primary flex items-center justify-center text-base shrink-0">
          <i className="fa-solid fa-shield-halved" />
        </div>
        <h2 className="text-xl font-extrabold text-main tracking-tight">
          {t('auth.twofa.title')}
        </h2>
      </div>

      {mode === 'totp' && (
        <p className="text-xs text-muted mb-3">
          {t('auth.twofa.subtitleOtp', { username: username || '—' })}
        </p>
      )}

      <div className="flex flex-wrap gap-1.5 mb-3">
        {modes
          .filter((item) => item.visible)
          .map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => handleModeChange(item.id)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold border transition-fast ${
                mode === item.id
                  ? 'bg-primary-subtle text-primary border-primary/40'
                  : 'bg-surface-elevated text-secondary border-border-subtle hover:text-main'
              }`}
            >
              {item.label}
            </button>
          ))}
      </div>

      {error && (
        <div className="bg-danger-subtle border border-danger-border rounded-md p-2.5 text-xs text-danger mb-3 flex items-center gap-2 animate-fade-in">
          <i className="fa-solid fa-triangle-exclamation shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {isOtpChannel && sentDestination && !error && (
        <div className="bg-success/10 border border-success/30 rounded-md p-2 text-xs text-success mb-3 flex items-center gap-2">
          <i className="fa-solid fa-circle-check shrink-0" />
          <span>{t('auth.twofa.sentTo', { target: sentDestination })}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3.5">
        {isOtpChannel && (
          <div className="flex items-center justify-between gap-2 p-2.5 rounded-md bg-surface-elevated border border-border-subtle">
            <span className="text-xs font-mono text-main truncate">
              {targetLabel || '—'}
            </span>
            <button
              type="button"
              disabled={sendingOtp || cooldown > 0}
              onClick={() => handleTriggerSendOtp(mode)}
              className="px-3 py-1 rounded bg-primary text-white text-xs font-semibold hover:bg-primary-hover disabled:opacity-50 shrink-0"
            >
              {sendingOtp
                ? t('auth.twofa.sendingCode')
                : cooldown > 0
                  ? t('auth.twofa.resendCode', { seconds: String(cooldown) })
                  : t('auth.twofa.sendCode')}
            </button>
          </div>
        )}

        <div className="text-left">
          <label className="block text-xs font-bold text-secondary mb-1.5">
            {mode === 'backup' ? t('auth.twofa.backupLabel') : t('auth.twofa.otpLabel')}
          </label>
          <input
            type="text"
            inputMode={mode === 'backup' ? 'text' : 'numeric'}
            autoComplete="one-time-code"
            autoFocus
            value={code}
            onChange={(e) => {
              const raw = e.target.value;
              setCode(mode === 'backup' ? raw.toUpperCase() : raw.replace(/\D/g, '').slice(0, 6));
            }}
            placeholder={
              mode === 'backup' ? t('auth.twofa.backupPlaceholder') : t('auth.twofa.otpPlaceholder')
            }
            maxLength={mode === 'backup' ? 12 : 6}
            required
            className="w-full px-3.5 py-2.5 rounded-md border border-border-subtle bg-surface text-main text-base font-mono tracking-widest text-center outline-none transition-fast focus:border-primary focus:ring-2 focus:ring-primary-glow placeholder:text-muted placeholder:tracking-normal placeholder:font-sans placeholder:text-sm"
          />
        </div>

        <label className="flex items-center gap-2 text-xs text-secondary cursor-pointer select-none">
          <input
            type="checkbox"
            checked={trustDevice}
            onChange={(e) => setTrustDevice(e.target.checked)}
            className="accent-primary cursor-pointer rounded-xs"
          />
          <span>{t('auth.twofa.trustDevice')}</span>
        </label>

        <button
          type="submit"
          disabled={isLoading || isSuccess || !code.trim() || (isOtpChannel && !otpToken)}
          className="w-full py-2.5 px-4 rounded-md bg-primary hover:bg-primary-hover text-white text-sm font-bold shadow-md hover:shadow-glow transition-normal flex items-center justify-center gap-2 disabled:opacity-60"
        >
          {isSuccess && <i className="fa-solid fa-check text-xs" />}
          <span>
            {isSuccess
              ? t('auth.twofa.verifiedSuccess')
              : isLoading
                ? t('auth.twofa.verifying')
                : t('auth.twofa.verifyBtn')}
          </span>
          {!isSuccess && <i className="fa-solid fa-arrow-right text-xs" />}
        </button>
      </form>

      <div className="mt-4 pt-3 border-t border-border-subtle flex items-center justify-end text-xs">
        <button
          type="button"
          onClick={onBackToLogin}
          className="text-secondary hover:text-main font-medium flex items-center gap-1.5"
        >
          <i className="fa-solid fa-arrow-left text-xs" />
          <span>{t('auth.twofa.backToLogin')}</span>
        </button>
      </div>
    </div>
  );
};

export default TwoFactorStep;
