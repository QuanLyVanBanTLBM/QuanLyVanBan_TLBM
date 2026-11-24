import React, { useEffect, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { ForgotPasswordLookupResult, OtpChannel } from '@app-types/auth';
import authService from '@lib/authService';
import { ApiError } from '@lib/apiClient';

export interface ForgotPasswordStepProps {
  onSuccess: (message: string) => void;
  onBackToLogin: () => void;
}

export const ForgotPasswordStep: React.FC<ForgotPasswordStepProps> = ({
  onSuccess,
  onBackToLogin,
}) => {
  const { t } = useTranslation();
  const [step, setStep] = useState<'lookup' | 'reset'>('lookup');
  const [identifier, setIdentifier] = useState('');
  const [lookupResult, setLookupResult] = useState<ForgotPasswordLookupResult | null>(null);
  const [channel, setChannel] = useState<OtpChannel>('email');
  const [resetToken, setResetToken] = useState('');
  const [sentDestination, setSentDestination] = useState('');
  const [cooldown, setCooldown] = useState(0);

  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [sendingOtp, setSendingOtp] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setInterval(() => {
      setCooldown((prev) => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  const extractErrorMessage = (err: unknown): string => {
    if (err instanceof ApiError) {
      const codeVal = String(err.data?.code || '');
      if (codeVal === 'twofa_locked') {
        return t('auth.twofa.errors.locked', {
          seconds: String(err.data?.retry_after_seconds || 300),
        });
      }
      if (codeVal === 'otp_cooldown') {
        return t('auth.twofa.errors.cooldown', {
          seconds: String(err.data?.retry_after_seconds || 60),
        });
      }
      return String(err.data?.detail || err.data?.error || err.message);
    }
    return t('auth.networkError');
  };

  const handleLookupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      const res = await authService.lookupForgotPassword(identifier);
      setLookupResult(res);
      const defaultChannel: OtpChannel = res.channels.email ? 'email' : 'sms';
      setChannel(defaultChannel);
      setStep('reset');
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendOtp = async () => {
    if (sendingOtp || cooldown > 0) return;
    setError('');
    setSendingOtp(true);
    try {
      const res = await authService.sendForgotPasswordOtp({
        identifier,
        channel,
        previousResetToken: resetToken || undefined,
      });
      setResetToken(res.reset_token);
      setSentDestination(res.masked_destination);
      setCooldown(res.cooldown_seconds || 60);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSendingOtp(false);
    }
  };

  const handleConfirmReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword.length < 8) {
      setError(t('auth.forgot.passwordTooShort'));
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t('auth.forgot.passwordMismatch'));
      return;
    }

    setIsLoading(true);
    try {
      await authService.confirmForgotPassword({
        resetToken,
        code,
        newPassword,
        confirmPassword,
      });
      onSuccess(t('auth.forgot.successMsg'));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full md:w-[55%] bg-surface !rounded-none !shadow-none !border-none relative flex flex-col justify-center p-4 sm:p-6 md:p-8 animate-fade-in">
      <div className="flex items-center gap-2.5 mb-3">
        <div className="w-9 h-9 rounded-xl bg-primary-subtle text-primary flex items-center justify-center text-base shrink-0">
          <i className="fa-solid fa-key" />
        </div>
        <h2 className="text-xl font-extrabold text-main tracking-tight">
          {t('auth.forgot.title')}
        </h2>
      </div>

      {error && (
        <div className="bg-danger-subtle border border-danger-border rounded-md p-2.5 text-xs text-danger mb-3 flex items-center gap-2 animate-fade-in">
          <i className="fa-solid fa-triangle-exclamation shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {step === 'lookup' ? (
        <form onSubmit={handleLookupSubmit} className="space-y-3.5">
          <div className="text-left">
            <label className="block text-xs font-bold text-secondary mb-1">
              {t('auth.forgot.identifierLabel')}
            </label>
            <input
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder={t('auth.forgot.identifierPlaceholder')}
              required
              autoFocus
              className="w-full px-3.5 py-2.5 rounded-md border border-border-subtle bg-surface text-main text-sm outline-none transition-fast focus:border-primary focus:ring-2 focus:ring-primary-glow placeholder:text-muted"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !identifier.trim()}
            className="w-full py-2.5 px-4 rounded-md bg-primary hover:bg-primary-hover text-white text-sm font-bold shadow-md transition-normal disabled:opacity-60"
          >
            {isLoading ? t('auth.forgot.checking') : t('auth.forgot.continueBtn')}
          </button>
        </form>
      ) : (
        <form onSubmit={handleConfirmReset} className="space-y-3">
          <div>
            <span className="block text-xs font-bold text-secondary mb-1.5">
              {t('auth.forgot.channelLabel')}
            </span>
            <div className="flex gap-2">
              {lookupResult?.channels.email && (
                <button
                  type="button"
                  onClick={() => {
                    setChannel('email');
                    setResetToken('');
                    setSentDestination('');
                    setCooldown(0);
                  }}
                  className={`flex-1 py-1.5 px-2.5 rounded-md text-xs font-semibold border transition-fast ${
                    channel === 'email'
                      ? 'bg-primary-subtle text-primary border-primary/40'
                      : 'bg-surface-elevated text-secondary border-border-subtle'
                  }`}
                >
                  {t('auth.twofa.channels.email')} ({lookupResult.masked_email})
                </button>
              )}
              {lookupResult?.channels.sms && (
                <button
                  type="button"
                  onClick={() => {
                    setChannel('sms');
                    setResetToken('');
                    setSentDestination('');
                    setCooldown(0);
                  }}
                  className={`flex-1 py-1.5 px-2.5 rounded-md text-xs font-semibold border transition-fast ${
                    channel === 'sms'
                      ? 'bg-primary-subtle text-primary border-primary/40'
                      : 'bg-surface-elevated text-secondary border-border-subtle'
                  }`}
                >
                  {t('auth.twofa.channels.sms')} ({lookupResult.masked_phone})
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 p-2.5 rounded-md bg-surface-elevated border border-border-subtle">
            <span className="text-xs font-mono text-main truncate">
              {channel === 'email' ? lookupResult?.masked_email : lookupResult?.masked_phone}
            </span>
            <button
              type="button"
              disabled={sendingOtp || cooldown > 0}
              onClick={handleSendOtp}
              className="px-3 py-1 rounded bg-primary text-white text-xs font-semibold hover:bg-primary-hover disabled:opacity-50 shrink-0"
            >
              {sendingOtp
                ? t('auth.twofa.sendingCode')
                : cooldown > 0
                  ? t('auth.twofa.resendCode', { seconds: String(cooldown) })
                  : t('auth.twofa.sendCode')}
            </button>
          </div>

          {sentDestination && !error && (
            <div className="bg-success/10 border border-success/30 rounded-md p-2 text-xs text-success flex items-center gap-2">
              <i className="fa-solid fa-circle-check shrink-0" />
              <span>{t('auth.twofa.sentTo', { target: sentDestination })}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-secondary mb-1">
              {t('auth.forgot.otpLabel')}
            </label>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder={t('auth.forgot.otpPlaceholder')}
              required
              className="w-full px-3.5 py-2 rounded-md border border-border-subtle bg-surface text-main text-sm font-mono tracking-widest text-center outline-none focus:border-primary focus:ring-2 focus:ring-primary-glow"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-secondary mb-1">
              {t('auth.forgot.newPasswordLabel')}
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={t('auth.forgot.newPasswordPlaceholder')}
              required
              className="w-full px-3.5 py-2 rounded-md border border-border-subtle bg-surface text-main text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary-glow"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-secondary mb-1">
              {t('auth.forgot.confirmPasswordLabel')}
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t('auth.forgot.confirmPasswordPlaceholder')}
              required
              className="w-full px-3.5 py-2 rounded-md border border-border-subtle bg-surface text-main text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary-glow"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !resetToken || code.length !== 6}
            className="w-full py-2.5 px-4 rounded-md bg-primary hover:bg-primary-hover text-white text-sm font-bold shadow-md transition-normal disabled:opacity-60"
          >
            {isLoading ? t('auth.forgot.submitting') : t('auth.forgot.submitBtn')}
          </button>
        </form>
      )}

      <div className="mt-4 pt-3 border-t border-border-subtle flex items-center justify-end text-xs">
        <button
          type="button"
          onClick={onBackToLogin}
          className="text-secondary hover:text-main font-medium flex items-center gap-1.5"
        >
          <i className="fa-solid fa-arrow-left text-xs" />
          <span>{t('auth.forgot.backToLogin')}</span>
        </button>
      </div>
    </div>
  );
};

export default ForgotPasswordStep;
