import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';

export interface TwoFactorStepProps {
  username: string;
  isLoading: boolean;
  isSuccess: boolean;
  error?: string;
  onSubmitCode: (code: string) => void;
  onBackToLogin: () => void;
}

export const TwoFactorStep: React.FC<TwoFactorStepProps> = ({
  username,
  isLoading,
  isSuccess,
  error,
  onSubmitCode,
  onBackToLogin,
}) => {
  const { t } = useTranslation();
  const [useBackupMode, setUseBackupMode] = useState<boolean>(false);
  const [code, setCode] = useState<string>('');

  const handleModeSwitch = () => {
    setUseBackupMode((prev) => !prev);
    setCode('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmitCode(code);
  };

  return (
    <div className="w-full md:w-[55%] bg-surface !rounded-none !shadow-none !border-none relative flex flex-col justify-center p-4 sm:p-6 md:p-8 animate-fade-in">
      <div className="flex items-center gap-2.5 mb-2">
        <div className="w-9 h-9 rounded-xl bg-primary-subtle text-primary flex items-center justify-center text-base shrink-0">
          <i className="fa-solid fa-shield-halved" />
        </div>
        <div>
          <h2 className="text-xl font-extrabold text-main tracking-tight">
            {t('auth.twofa.title')}
          </h2>
        </div>
      </div>

      <p className="text-xs text-muted mb-4 leading-relaxed">
        {useBackupMode
          ? t('auth.twofa.subtitleBackup')
          : t('auth.twofa.subtitleOtp', { username: username || '—' })}
      </p>

      {error && (
        <div className="bg-danger-subtle border border-danger-border rounded-md p-2.5 text-xs text-danger mb-3 flex items-center gap-2 animate-fade-in">
          <i className="fa-solid fa-triangle-exclamation shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="text-left">
          <label className="block text-xs font-bold text-secondary mb-1.5">
            {useBackupMode ? t('auth.twofa.backupLabel') : t('auth.twofa.otpLabel')}
          </label>
          <input
            type="text"
            inputMode={useBackupMode ? 'text' : 'numeric'}
            autoComplete="one-time-code"
            autoFocus
            value={code}
            onChange={(e) => {
              const raw = e.target.value;
              setCode(useBackupMode ? raw.toUpperCase() : raw.replace(/\D/g, '').slice(0, 6));
            }}
            placeholder={
              useBackupMode ? t('auth.twofa.backupPlaceholder') : t('auth.twofa.otpPlaceholder')
            }
            maxLength={useBackupMode ? 12 : 6}
            required
            className="w-full px-3.5 py-2.5 rounded-md border border-border-subtle bg-surface text-main text-base font-mono tracking-widest text-center outline-none transition-fast focus:border-primary focus:ring-2 focus:ring-primary-glow placeholder:text-muted placeholder:tracking-normal placeholder:font-sans placeholder:text-sm"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || isSuccess || !code.trim()}
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

      <div className="mt-4 pt-3 border-t border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
        <button
          type="button"
          onClick={handleModeSwitch}
          className="text-primary hover:underline font-semibold text-left"
        >
          {useBackupMode ? t('auth.twofa.useAuthenticatorCode') : t('auth.twofa.useBackupCode')}
        </button>

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

