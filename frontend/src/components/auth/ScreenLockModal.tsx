import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import authService from '@lib/authService';
import { formatRoleTitle, formatUserName } from '@lib/roleUtils';
import Logo from '@components/common/Logo';
import { Button } from '@components/common';

interface ScreenLockModalProps {
  isLocked: boolean;
  onUnlock: () => void;
}

interface SessionUser {
  fullName?: string;
  username?: string;
  roleTitle?: string;
  avatar?: string;
  email?: string;
}

export default function ScreenLockModal({ isLocked, onUnlock }: ScreenLockModalProps) {
  const { t, currentLang } = useTranslation();
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  if (!isLocked) {
    return null;
  }

  const session: SessionUser | null = (() => {
    try {
      const raw = localStorage.getItem('tlbm_session');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  })();

  const rawName = session?.fullName || session?.username;
  const displayName = rawName ? formatUserName(rawName, currentLang) : 'Cán bộ nhân viên Bảo Long';
  const rawRole = session?.roleTitle;
  const displayRoleOrEmail = rawRole ? formatRoleTitle(rawRole, currentLang) : (session?.email || 'Hệ thống Quản lý Văn bản');

  const handleUnlockSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanPass = password.trim();
    if (!cleanPass) {
      setErrorMsg(t('settings.passwordRequired') || 'Vui lòng nhập mật khẩu để mở khóa.');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    try {
      const isValid = await authService.verifyPassword(cleanPass);
      if (isValid) {
        setPassword('');
        setErrorMsg('');
        onUnlock();
      } else {
        setErrorMsg(t('settings.wrongPassword') || 'Mật khẩu không chính xác. Vui lòng thử lại.');
      }
    } catch {
      setErrorMsg(t('settings.wrongPassword') || 'Mật khẩu không chính xác. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    onUnlock();
    authService.logout();
    window.location.href = '/login';
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Khóa màn hình làm việc"
      className="fixed inset-0 z-[99999] bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 select-none animate-in fade-in duration-200"
    >
      <div className="w-full max-w-md bg-surface border border-border-subtle rounded-3xl p-6 sm:p-8 shadow-2xl flex flex-col items-center text-center relative overflow-hidden">
        {/* Glow decoration */}
        <div className="absolute -top-16 -left-16 w-36 h-36 bg-primary/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-16 -right-16 w-36 h-36 bg-amber-500/15 rounded-full blur-3xl pointer-events-none" />

        {/* Top Logo */}
        <div className="mb-5">
          <Logo size="md" />
        </div>

        {/* Lock Icon */}
        <div className="w-16 h-16 rounded-2xl bg-amber-500/15 border border-amber-500/30 text-amber-500 flex items-center justify-center text-2xl mb-4 shadow-sm shadow-amber-500/20">
          <i className="fa-solid fa-lock" />
        </div>

        {/* Title */}
        <h2 className="text-xl font-extrabold text-main">
          {t('settings.screenLockedTitle') || 'Phiên Làm Việc Đã Tạm Khóa'}
        </h2>
        <p className="text-xs text-muted mt-1.5 max-w-sm">
          {t('settings.screenLockedDesc') ||
            'Màn hình tự động khóa để bảo mật dữ liệu văn bản theo chính sách an toàn thông tin Bảo Long Insurance.'}
        </p>

        {/* User Badge */}
        <div className="w-full bg-surface-hover/60 border border-border-subtle rounded-2xl p-3 my-5 flex items-center gap-3 text-left">
          <div className="w-10 h-10 rounded-full bg-primary/20 text-primary font-bold flex items-center justify-center text-sm shrink-0 border border-primary/30 overflow-hidden">
            {session?.avatar ? (
              <img src={session.avatar} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <i className="fa-solid fa-user" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-main truncate">{displayName}</div>
            <div className="text-xs text-muted truncate">{displayRoleOrEmail}</div>
          </div>
          <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-600 dark:text-amber-400 text-[10px] font-bold border border-amber-500/30 shrink-0">
            Đang khóa
          </span>
        </div>

        {/* Unlock Form */}
        <form onSubmit={handleUnlockSubmit} className="w-full space-y-3.5">
          <div className="relative">
            <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted text-sm">
              <i className="fa-solid fa-key" />
            </span>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (errorMsg) setErrorMsg('');
              }}
              placeholder="Nhập mật khẩu để mở khóa..."
              disabled={loading}
              className="w-full pl-10 pr-10 py-2.5 bg-surface border border-border-subtle rounded-xl text-sm text-main placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all disabled:opacity-50"
              autoFocus
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              tabIndex={-1}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted hover:text-main text-xs transition-colors p-1"
              title={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
            >
              <i className={`fa-solid ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`} />
            </button>
          </div>

          {errorMsg && (
            <div className="text-xs text-danger font-medium text-left flex items-center gap-1.5 animate-in fade-in duration-150">
              <i className="fa-solid fa-circle-exclamation text-[11px]" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="flex flex-col gap-2 pt-1">
            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={loading}
              className="w-full justify-center gap-2 py-2.5 font-bold shadow-sm shadow-primary/25 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <i className="fa-solid fa-circle-notch fa-spin text-xs" />
                  <span>Đang kiểm tra...</span>
                </>
              ) : (
                <>
                  <i className="fa-solid fa-lock-open text-xs" />
                  <span>{t('settings.unlockButton') || 'Mở khóa làm việc'}</span>
                </>
              )}
            </Button>

            <button
              type="button"
              onClick={handleLogout}
              disabled={loading}
              className="text-xs text-muted hover:text-danger transition-colors py-1 flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <i className="fa-solid fa-arrow-right-from-bracket text-[11px]" />
              <span>{t('settings.logoutSwitchUser') || 'Đăng xuất tài khoản khác'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
