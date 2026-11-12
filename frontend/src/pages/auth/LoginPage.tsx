import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import confetti from 'canvas-confetti';
import { ActivePageId } from '@app-types/navigation';
import { TwoFactorChallenge, UserSession } from '@app-types/auth';
import { useTranslation } from '@i18n/translate';
import LanguageSwitcher from '@components/layout/LanguageSwitcher';
import LoginBanner from '@components/auth/LoginBanner';
import LoginForm from '@components/auth/LoginForm';
import TwoFactorStep from '@components/auth/TwoFactorStep';
import authService, { TwoFactorRequiredError } from '@lib/authService';
import { ApiError } from '@lib/apiClient';
import '@styles/login-characters.css';

interface LoginPageProps {
  onNavigate?: (pageId: ActivePageId) => void;
  onLoginSuccess?: (session: UserSession) => void;
}

interface TranslatedErrorState {
  key: string;
  params?: Record<string, string>;
}

export default function LoginPage({ onNavigate, onLoginSuccess }: LoginPageProps) {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [errorState, setErrorState] = useState<TranslatedErrorState | null>(null);
  const [customError, setCustomError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);
  const [twoFactorChallenge, setTwoFactorChallenge] = useState<TwoFactorChallenge | null>(null);

  const completeLoginSuccess = (session: UserSession) => {
    setIsLoading(false);
    setIsSuccess(true);

    try {
      confetti({
        particleCount: 100,
        spread: 75,
        origin: { y: 0.6 },
      });
    } catch {
      // Fallback confetti
    }

    setTimeout(() => {
      if (onLoginSuccess) {
        onLoginSuccess(session);
      }
      if (onNavigate) {
        onNavigate('dashboard');
      }
      navigate('/dashboard', { replace: true });
    }, 700);
  };

  const applyApiError = (err: unknown) => {
    if (err instanceof ApiError) {
      const code = String(err.data?.code || '');
      if (code === 'otp_required') {
        setErrorState({ key: 'auth.twofa.errors.otpRequired' });
        return;
      }
      if (code === 'otp_invalid') {
        const attempts = err.data?.attempts_remaining;
        setErrorState(
          typeof attempts === 'number'
            ? { key: 'auth.twofa.errors.otpInvalid', params: { attempts: String(attempts) } }
            : { key: 'auth.twofa.errors.otpInvalidNoCount' }
        );
        return;
      }
      if (code === 'otp_reused') {
        setErrorState({ key: 'auth.twofa.errors.otpReused' });
        return;
      }
      if (code === 'twofa_locked') {
        const seconds = Number(err.data?.retry_after_seconds || 300);
        setErrorState({
          key: 'auth.twofa.errors.locked',
          params: { seconds: String(seconds) },
        });
        return;
      }
      if (code === 'temp_token_expired') {
        setErrorState({ key: 'auth.twofa.errors.sessionExpired' });
        return;
      }
      if (code === 'temp_token_invalid' || code === 'temp_token_missing') {
        setErrorState({ key: 'auth.twofa.errors.sessionInvalid' });
        return;
      }

      if (err.status === 401 || err.status === 400) {
        const detail = (err.data?.error || err.data?.detail || '').toLowerCase();
        if (detail.includes('không chính xác') || detail.includes('credentials')) {
          setErrorState({ key: 'auth.invalidCredentials' });
        } else if (err.data?.error || err.data?.detail) {
          setCustomError(err.data.error || err.data.detail || '');
        } else {
          setErrorState({ key: 'auth.invalidCredentials' });
        }
      } else if (err.status === 403) {
        setCustomError(
          err.data?.error ||
            err.data?.detail ||
            'Tài khoản đã bị vô hiệu hóa. Vui lòng liên hệ Quản trị viên.'
        );
      } else if (err.status >= 500) {
        const raw = err.data?.error || err.data?.detail || '';
        if (raw.startsWith('<') || raw.includes('<!DOCTYPE')) {
          setCustomError('Máy chủ đang gặp sự cố (500). Vui lòng thử lại sau!');
        } else {
          setCustomError(raw || 'Máy chủ đang gặp sự cố (500). Vui lòng thử lại sau!');
        }
      } else {
        const raw = err.data?.error || err.data?.detail || err.message;
        setCustomError(raw.startsWith('<') ? 'Đã xảy ra lỗi không xác định.' : raw);
      }
    } else {
      setErrorState({ key: 'auth.networkError' });
    }
  };

  const handleLoginSubmit = async ({ username, password }: { username: string; password: string }) => {
    setErrorState(null);
    setCustomError('');
    setIsLoading(true);

    try {
      const session = await authService.login({ username, password });
      completeLoginSuccess(session);
    } catch (err: unknown) {
      setIsLoading(false);
      if (err instanceof TwoFactorRequiredError) {
        setTwoFactorChallenge(err.challenge);
        return;
      }
      applyApiError(err);
    }
  };

  const handleTwoFactorSubmit = async (code: string) => {
    if (!twoFactorChallenge) return;
    setErrorState(null);
    setCustomError('');
    setIsLoading(true);

    try {
      const session = await authService.verifyTwoFactor({
        tempToken: twoFactorChallenge.tempToken,
        code,
        username: twoFactorChallenge.username,
      });
      completeLoginSuccess(session);
    } catch (err: unknown) {
      setIsLoading(false);
      applyApiError(err);
    }
  };

  const handleBackToLogin = () => {
    setTwoFactorChallenge(null);
    setErrorState(null);
    setCustomError('');
    setIsLoading(false);
    setIsSuccess(false);
  };

  const activeError = errorState
    ? (t(errorState.key, errorState.params) as string)
    : customError;

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-start md:justify-center pt-14 pb-8 px-3 sm:px-4 md:p-6 bg-app bg-auth-backdrop relative overflow-y-auto font-sans">
      {/* 1. Nút quay lại Dashboard nếu có onNavigate */}
      {onNavigate && (
        <button
          type="button"
          onClick={() => onNavigate('dashboard')}
          className="absolute top-3 left-3 sm:top-4 sm:left-4 bg-surface-elevated/80 backdrop-blur-md border border-border-subtle px-3 sm:px-4 py-1.5 sm:py-2 rounded-full text-xs font-semibold text-main hover:bg-surface transition-fast flex items-center gap-2 z-20 shadow-sm"
        >
          <i className="fa-solid fa-arrow-left" />
          <span>{t('auth.backToDashboard')}</span>
        </button>
      )}

      {/* 2. Bộ chuyển đổi ngôn ngữ VN/EN ra ngoài trang Login */}
      <div className="absolute top-3 right-3 sm:top-4 sm:right-4 z-20">
        <LanguageSwitcher />
      </div>

      {/* 3. Thẻ chứa Form và Banner thương hiệu Bảo Long */}
      <div className="login-card-container w-full max-w-4xl bg-surface rounded-2xl overflow-hidden shadow-lg flex flex-col md:flex-row relative z-10 md:my-auto border border-border-subtle animate-fade-in">
        {/* Nửa trái: Khung nhận diện thương hiệu Bảo Long */}
        <LoginBanner />

        {/* Nửa phải: Form đăng nhập hoặc bước xác thực 2FA */}
        {twoFactorChallenge ? (
          <TwoFactorStep
            username={twoFactorChallenge.username}
            isLoading={isLoading}
            isSuccess={isSuccess}
            error={activeError}
            onSubmitCode={handleTwoFactorSubmit}
            onBackToLogin={handleBackToLogin}
          />
        ) : (
          <LoginForm
            isLoading={isLoading}
            isSuccess={isSuccess}
            error={activeError}
            onSubmit={handleLoginSubmit}
            onUsernameFocusChange={() => {}}
            onPasswordFocusChange={() => {}}
            onShowPasswordChange={() => {}}
            onTyping={() => {}}
          />
        )}
      </div>
    </div>
  );
}
