import React, { useEffect, useState } from 'react';
import { useTranslation } from '@i18n/translate';
import { Button } from '@components/common';
import authService from '@lib/authService';
import { ApiError } from '@lib/apiClient';
import { TwoFactorSetupPayload, TwoFactorStatus } from '@app-types/auth';

type ModalMode = 'none' | 'setup' | 'backup_codes' | 'disable' | 'regenerate';

export const TwoFactorSecurityCard: React.FC = () => {
  const { t } = useTranslation();
  const isAuthenticated = authService.isAuthenticated();
  const initialSession = authService.getSession();

  const [statusData, setStatusData] = useState<TwoFactorStatus>({
    enabled: Boolean(initialSession?.is_2fa_enabled),
    backup_codes_remaining: 0,
    has_usable_credential:
      initialSession?.has_usable_credential === undefined
        ? true
        : Boolean(initialSession.has_usable_credential),
  });
  const [statusLoading, setStatusLoading] = useState<boolean>(isAuthenticated);

  const [modalMode, setModalMode] = useState<ModalMode>('none');
  const [setupPayload, setSetupPayload] = useState<TwoFactorSetupPayload | null>(null);
  const [otpInput, setOtpInput] = useState<string>('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [secretCopied, setSecretCopied] = useState<boolean>(false);
  const [codesCopied, setCodesCopied] = useState<boolean>(false);

  const [verifyMethod, setVerifyMethod] = useState<'password' | 'code'>('password');
  const [passwordInput, setPasswordInput] = useState<string>('');
  const [actionOtpInput, setActionOtpInput] = useState<string>('');

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [modalError, setModalError] = useState<string>('');
  const [bannerMessage, setBannerMessage] = useState<string>('');

  useEffect(() => {
    if (!isAuthenticated) return;
    let active = true;
    authService
      .getTwoFactorStatus()
      .then((res) => {
        if (active) {
          setStatusData(res);
        }
      })
      .catch(() => {
        // Giữ trạng thái fallback từ session local nếu offline
      })
      .finally(() => {
        if (active) setStatusLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isAuthenticated]);

  const mapTwoFactorError = (err: unknown): string => {
    if (err instanceof ApiError) {
      const code = String(err.data?.code || '');
      if (code === 'otp_invalid') return t('settings.twofa.errorOtpInvalid');
      if (code === 'setup_token_expired') return t('settings.twofa.errorSetupExpired');
      if (code === 'invalid_credential') return t('settings.twofa.errorCredentialInvalid');
      if (err.data?.detail) return String(err.data.detail);
      if (err.data?.error) return String(err.data.error);
    }
    return t('settings.twofa.errorGeneric');
  };

  const resetModal = () => {
    setModalMode('none');
    setSetupPayload(null);
    setOtpInput('');
    setPasswordInput('');
    setActionOtpInput('');
    setModalError('');
    setSecretCopied(false);
    setCodesCopied(false);
  };

  const handleOpenSetup = async () => {
    setBannerMessage('');
    setModalError('');
    setOtpInput('');
    setSubmitting(true);
    setModalMode('setup');
    try {
      const payload = await authService.setupTwoFactor();
      setSetupPayload(payload);
    } catch (err) {
      setModalError(mapTwoFactorError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!setupPayload) return;
    setModalError('');
    setSubmitting(true);
    try {
      const result = await authService.confirmTwoFactor(setupPayload.setup_token, otpInput);
      setStatusData((prev) => ({
        ...prev,
        enabled: result.enabled,
        backup_codes_remaining: result.backup_codes_remaining,
      }));
      setBackupCodes(result.backup_codes);
      setSetupPayload(null);
      setOtpInput('');
      setModalMode('backup_codes');
      setBannerMessage(t('settings.twofa.setupSuccessMsg'));
    } catch (err) {
      setModalError(mapTwoFactorError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const openVerificationModal = (targetMode: 'disable' | 'regenerate') => {
    setBannerMessage('');
    setModalError('');
    setPasswordInput('');
    setActionOtpInput('');
    setVerifyMethod(statusData.has_usable_credential ? 'password' : 'code');
    setModalMode(targetMode);
  };

  const handleSensitiveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setModalError('');
    setSubmitting(true);

    const payload =
      verifyMethod === 'password'
        ? { password: passwordInput }
        : { code: actionOtpInput };

    try {
      if (modalMode === 'disable') {
        const res = await authService.disableTwoFactor(payload);
        setStatusData((prev) => ({
          ...prev,
          enabled: res.enabled,
          backup_codes_remaining: 0,
        }));
        resetModal();
        setBannerMessage(t('settings.twofa.disableSuccessMsg'));
      } else if (modalMode === 'regenerate') {
        const res = await authService.regenerateBackupCodes(payload);
        setStatusData((prev) => ({
          ...prev,
          backup_codes_remaining: res.backup_codes_remaining,
        }));
        setBackupCodes(res.backup_codes);
        setPasswordInput('');
        setActionOtpInput('');
        setModalMode('backup_codes');
      }
    } catch (err) {
      setModalError(mapTwoFactorError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const copyToClipboard = async (text: string, onDone: () => void) => {
    try {
      await navigator.clipboard.writeText(text);
      onDone();
    } catch {
      // Fallback không làm crash trình duyệt không cấp quyền clipboard
    }
  };

  const handleDownloadBackupTxt = () => {
    const content = [
      'BAO LONG INSURANCE - DOCUMENT MANAGEMENT SYSTEM',
      '2FA RECOVERY BACKUP CODES (SINGLE-USE)',
      '======================================',
      ...backupCodes,
    ].join('\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'baolong-2fa-backup-codes.txt';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-surface border border-border-subtle rounded-2xl p-6 shadow-xs space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-border-subtle">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-sm">
            <i className="fa-solid fa-mobile-screen-button" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-main">
              {t('settings.twofa.sectionTitle')}
            </h3>
            <p className="text-xs text-muted">
              {t('settings.twofa.sectionDesc')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {statusData.enabled ? (
            <>
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-success/15 text-success border border-success/30 flex items-center gap-1.5">
                <i className="fa-solid fa-circle-check text-xs" />
                <span>{t('settings.twofa.statusEnabled')}</span>
              </span>
              <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-surface-elevated text-secondary border border-border-subtle">
                {t('settings.twofa.backupRemainingBadge', {
                  count: String(statusData.backup_codes_remaining),
                })}
              </span>
            </>
          ) : (
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-surface-elevated text-muted border border-border-subtle">
              {t('settings.twofa.statusDisabled')}
            </span>
          )}
        </div>
      </div>

      {bannerMessage && (
        <div className="rounded-xl bg-success/10 border border-success/30 text-success px-4 py-2.5 text-xs font-medium flex items-center gap-2">
          <i className="fa-solid fa-circle-check" />
          <span>{bannerMessage}</span>
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-surface-elevated/40 border border-border-subtle/80">
        <p className="text-xs text-secondary leading-relaxed max-w-2xl">
          {!isAuthenticated
            ? t('settings.twofa.loginRequiredHint')
            : statusData.enabled
              ? t('settings.twofa.cardEnabledInfo')
              : t('settings.twofa.cardDisabledInfo')}
        </p>

        <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
          {!statusData.enabled ? (
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={!isAuthenticated || statusLoading}
              onClick={handleOpenSetup}
              className="gap-2"
            >
              <i className="fa-solid fa-qrcode text-xs" />
              <span>{t('settings.twofa.enableBtn')}</span>
            </Button>
          ) : (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!isAuthenticated || statusLoading}
                onClick={() => openVerificationModal('regenerate')}
                className="gap-1.5"
              >
                <i className="fa-solid fa-rotate text-xs" />
                <span>{t('settings.twofa.regenerateBtn')}</span>
              </Button>
              <Button
                type="button"
                variant="danger"
                size="sm"
                disabled={!isAuthenticated || statusLoading}
                onClick={() => openVerificationModal('disable')}
                className="gap-1.5"
              >
                <i className="fa-solid fa-shield-xmark text-xs" />
                <span>{t('settings.twofa.disableBtn')}</span>
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Modal Wizard Thiết lập / Mã dự phòng / Tắt 2FA */}
      {modalMode !== 'none' && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-md bg-surface border border-border-subtle rounded-2xl shadow-xl p-6 space-y-4 animate-fade-in max-h-[90vh] overflow-y-auto">
            {modalMode === 'setup' && (
              <>
                <div className="flex items-center justify-between gap-2 pb-2 border-b border-border-subtle">
                  <h4 className="text-base font-bold text-main">
                    {t('settings.twofa.setupModalTitle')}
                  </h4>
                  <button
                    type="button"
                    onClick={resetModal}
                    className="text-muted hover:text-main p-1"
                    aria-label={t('settings.twofa.cancelBtn')}
                  >
                    <i className="fa-solid fa-xmark" />
                  </button>
                </div>

                {modalError && (
                  <div className="bg-danger-subtle border border-danger-border rounded-lg p-2.5 text-xs text-danger flex items-center gap-2">
                    <i className="fa-solid fa-triangle-exclamation shrink-0" />
                    <span>{modalError}</span>
                  </div>
                )}

                {setupPayload ? (
                  <form onSubmit={handleConfirmSetup} className="space-y-4">
                    <p className="text-xs text-secondary leading-relaxed">
                      {t('settings.twofa.step1Desc')}
                    </p>

                    <div className="flex justify-center p-4 bg-white rounded-xl border border-border-subtle">
                      <img
                        src={setupPayload.qr_code}
                        alt="2FA QR Code"
                        className="w-44 h-44 object-contain"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <span className="block text-xs font-medium text-muted">
                        {t('settings.twofa.manualSecretLabel')}
                      </span>
                      <div className="flex items-center gap-2 p-2.5 rounded-lg bg-surface-elevated border border-border-subtle">
                        <code className="text-xs font-mono font-bold text-main break-all flex-1">
                          {setupPayload.secret_key}
                        </code>
                        <button
                          type="button"
                          onClick={() =>
                            copyToClipboard(setupPayload.secret_key, () => setSecretCopied(true))
                          }
                          className="text-xs font-semibold text-primary hover:underline shrink-0"
                        >
                          {secretCopied ? t('settings.twofa.copiedToast') : t('settings.twofa.copySecret')}
                        </button>
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-bold text-secondary">
                        {t('settings.twofa.step2Desc')}
                      </label>
                      <input
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        value={otpInput}
                        onChange={(e) => setOtpInput(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        placeholder={t('settings.twofa.otpPlaceholder')}
                        required
                        className="w-full px-3.5 py-2 rounded-lg border border-border-subtle bg-surface text-main text-base font-mono tracking-widest text-center focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-glow"
                      />
                    </div>

                    <div className="flex justify-end gap-2 pt-2">
                      <Button type="button" variant="secondary" size="sm" onClick={resetModal}>
                        {t('settings.twofa.cancelBtn')}
                      </Button>
                      <Button
                        type="submit"
                        variant="primary"
                        size="sm"
                        disabled={submitting || otpInput.length !== 6}
                      >
                        {submitting ? t('settings.twofa.activating') : t('settings.twofa.confirmEnableBtn')}
                      </Button>
                    </div>
                  </form>
                ) : (
                  !modalError && (
                    <div className="py-8 text-center text-xs text-muted">
                      <i className="fa-solid fa-spinner fa-spin mr-2" />
                      <span>{t('settings.twofa.processing')}</span>
                    </div>
                  )
                )}
              </>
            )}

            {modalMode === 'backup_codes' && (
              <>
                <div className="flex items-center gap-2 pb-2 border-b border-border-subtle">
                  <i className="fa-solid fa-key text-primary" />
                  <h4 className="text-base font-bold text-main">
                    {t('settings.twofa.backupTitle')}
                  </h4>
                </div>

                <p className="text-xs text-secondary leading-relaxed">
                  {t('settings.twofa.backupDesc')}
                </p>

                <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-surface-elevated border border-border-subtle">
                  {backupCodes.map((code) => (
                    <div
                      key={code}
                      className="font-mono text-xs font-bold text-main bg-surface px-2.5 py-1.5 rounded-md border border-border-subtle text-center select-all"
                    >
                      {code}
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between gap-2 flex-wrap pt-1">
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        copyToClipboard(backupCodes.join('\n'), () => setCodesCopied(true))
                      }
                    >
                      {codesCopied ? t('settings.twofa.copiedToast') : t('settings.twofa.copyAllCodes')}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleDownloadBackupTxt}
                    >
                      {t('settings.twofa.downloadTxt')}
                    </Button>
                  </div>

                  <Button type="button" variant="primary" size="sm" onClick={resetModal}>
                    {t('settings.twofa.closeBtn')}
                  </Button>
                </div>
              </>
            )}

            {(modalMode === 'disable' || modalMode === 'regenerate') && (
              <>
                <div className="flex items-center justify-between gap-2 pb-2 border-b border-border-subtle">
                  <h4 className="text-base font-bold text-main">
                    {modalMode === 'disable'
                      ? t('settings.twofa.disableModalTitle')
                      : t('settings.twofa.regenModalTitle')}
                  </h4>
                  <button
                    type="button"
                    onClick={resetModal}
                    className="text-muted hover:text-main p-1"
                    aria-label={t('settings.twofa.cancelBtn')}
                  >
                    <i className="fa-solid fa-xmark" />
                  </button>
                </div>

                <p className="text-xs text-secondary leading-relaxed">
                  {modalMode === 'disable'
                    ? t('settings.twofa.disableModalDesc')
                    : t('settings.twofa.regenModalDesc')}
                </p>

                {!statusData.has_usable_credential && (
                  <p className="text-xs text-muted bg-surface-elevated p-2.5 rounded-lg border border-border-subtle">
                    {t('settings.twofa.externalAuthOtpNotice')}
                  </p>
                )}

                {statusData.has_usable_credential && (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setVerifyMethod('password')}
                      className={`flex-1 py-1.5 px-2.5 rounded-lg text-xs font-semibold border transition-colors ${
                        verifyMethod === 'password'
                          ? 'bg-primary-subtle text-primary border-primary/40'
                          : 'bg-surface-elevated text-secondary border-border-subtle'
                      }`}
                    >
                      {t('settings.twofa.verifyByPassword')}
                    </button>
                    <button
                      type="button"
                      onClick={() => setVerifyMethod('code')}
                      className={`flex-1 py-1.5 px-2.5 rounded-lg text-xs font-semibold border transition-colors ${
                        verifyMethod === 'code'
                          ? 'bg-primary-subtle text-primary border-primary/40'
                          : 'bg-surface-elevated text-secondary border-border-subtle'
                      }`}
                    >
                      {t('settings.twofa.verifyByOtp')}
                    </button>
                  </div>
                )}

                {modalError && (
                  <div className="bg-danger-subtle border border-danger-border rounded-lg p-2.5 text-xs text-danger flex items-center gap-2">
                    <i className="fa-solid fa-triangle-exclamation shrink-0" />
                    <span>{modalError}</span>
                  </div>
                )}

                <form onSubmit={handleSensitiveSubmit} className="space-y-4">
                  {verifyMethod === 'password' ? (
                    <input
                      type="password"
                      value={passwordInput}
                      onChange={(e) => setPasswordInput(e.target.value)}
                      placeholder={t('settings.twofa.currentPasswordPlaceholder')}
                      required
                      className="w-full px-3.5 py-2 rounded-lg border border-border-subtle bg-surface text-main text-sm focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-glow"
                    />
                  ) : (
                    <input
                      type="text"
                      value={actionOtpInput}
                      onChange={(e) => setActionOtpInput(e.target.value.toUpperCase())}
                      placeholder={t('settings.twofa.currentOtpPlaceholder')}
                      required
                      className="w-full px-3.5 py-2 rounded-lg border border-border-subtle bg-surface text-main text-sm font-mono tracking-wider focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary-glow"
                    />
                  )}

                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="secondary" size="sm" onClick={resetModal}>
                      {t('settings.twofa.cancelBtn')}
                    </Button>
                    <Button
                      type="submit"
                      variant={modalMode === 'disable' ? 'danger' : 'primary'}
                      size="sm"
                      disabled={submitting}
                    >
                      {submitting
                        ? t('settings.twofa.processing')
                        : modalMode === 'disable'
                          ? t('settings.twofa.confirmDisableBtn')
                          : t('settings.twofa.confirmRegenBtn')}
                    </Button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TwoFactorSecurityCard;

