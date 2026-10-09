import React, { useState, useRef, useEffect } from 'react';
import { ActivePageId } from '@app-types/navigation';
import { useTranslation } from '@i18n/translate';
import authService from '@lib/authService';

interface UserDropdownProps {
  onNavigate?: (page: ActivePageId) => void;
}

interface SessionUser {
  fullName?: string;
  username?: string;
  roleTitle?: string;
  avatar?: string;
  email?: string;
}

export default function UserDropdown({ onNavigate }: UserDropdownProps) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent | TouchEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('pointerdown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    return () => {
      document.removeEventListener('pointerdown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, []);

  const handleItemClick = (pageId: ActivePageId) => {
    setIsOpen(false);
    if (onNavigate) {
      onNavigate(pageId);
    }
  };

  const parseSession = (raw: string | null): SessionUser | null => {
    const getFallbackFromToken = (): SessionUser | null => {
      const token = localStorage.getItem('tlbm_access_token');
      if (!token) return null;
      try {
        const payloadBase64 = token.split('.')[1];
        if (payloadBase64) {
          const decoded = JSON.parse(atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/')));
          const uid = String(decoded.user_id || '');
          if (uid === '2') {
            return {
              username: 'canbo',
              fullName: 'Tấn Lộc Khiêm Nguyễn',
              roleTitle: 'Cán bộ nhân viên',
              email: 'canbo@taphuan.gov.vn',
            };
          } else if (uid === '3') {
            return {
              username: 'canbo2',
              fullName: 'Lê Cán Bộ 2',
              roleTitle: 'Cán bộ nhân viên',
              email: 'canbo2@taphuan.gov.vn',
            };
          }
        }
      } catch {
        // ignore
      }
      return {
        username: 'admin',
        fullName: 'Quản Trị Viên (Admin)',
        roleTitle: 'Quản trị viên tối cao',
        email: 'admin@taphuan.gov.vn',
      };
    };

    if (!raw) return getFallbackFromToken();
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object' && (parsed.fullName || parsed.username)) {
        return parsed;
      }
      return getFallbackFromToken();
    } catch {
      return getFallbackFromToken();
    }
  };

  const [session, setSession] = useState<SessionUser | null>(() => {
    return parseSession(localStorage.getItem('tlbm_session'));
  });

  useEffect(() => {
    const handleAuth = () => {
      setSession(parseSession(localStorage.getItem('tlbm_session')));
    };
    window.addEventListener('tlbm_auth_changed', handleAuth);
    window.addEventListener('storage', handleAuth);
    return () => {
      window.removeEventListener('tlbm_auth_changed', handleAuth);
      window.removeEventListener('storage', handleAuth);
    };
  }, []);

  const displayName = session?.fullName || session?.username;
  const displayRoleOrEmail = session?.roleTitle || session?.email || '';

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        className="flex items-center gap-2 p-1 sm:pr-2.5 rounded-full hover:bg-surface-hover border border-transparent hover:border-subtle transition-all duration-fast"
        onClick={() => setIsOpen(!isOpen)}
        title={session ? 'Hồ sơ người dùng' : 'Tài khoản khách (Chưa đăng nhập)'}
        aria-label={session ? 'Hồ sơ người dùng' : 'Tài khoản khách'}
      >
        {session ? (
          <div className="w-8 h-8 rounded-full bg-primary/20 text-primary font-semibold flex items-center justify-center text-xs">
            {session.avatar ? (
              <img src={session.avatar} alt="Avatar" className="w-full h-full rounded-full object-cover" />
            ) : (
              <i className="fa-solid fa-user" />
            )}
          </div>
        ) : (
          <div className="w-8 h-8 rounded-full bg-surface-elevated border border-subtle text-text-muted flex items-center justify-center text-xs">
            <i className="fa-regular fa-user" />
          </div>
        )}

        <div className="hidden md:flex flex-col text-left">
          <span className="text-xs font-semibold text-text-main leading-tight">
            {displayName || t('userMenu.guest') || 'Chưa đăng nhập'}
          </span>
        </div>
        <i className={`fa-solid fa-chevron-down text-[10px] text-text-muted ml-0.5 transition-transform duration-200 ${isOpen ? 'rotate-180 text-primary' : ''}`} />
      </button>

      {isOpen && (
        <div className="dropdown-animate absolute right-0 top-full mt-2 w-64 rounded-xl bg-surface-elevated border border-border-subtle shadow-2xl p-1.5 z-[10001] flex flex-col backdrop-blur-none">
            <div className="p-2.5 border-b border-subtle mb-1">
              {session ? (
                <>
                  <div className="font-semibold text-sm text-text-main">{displayName}</div>
                  {displayRoleOrEmail && (
                    <div className="text-xs text-text-muted truncate mt-0.5">
                      {displayRoleOrEmail}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="font-semibold text-sm text-text-muted flex items-center gap-1.5">
                    <i className="fa-regular fa-circle-user text-xs" />
                    <span>{t('userMenu.notLoggedIn') || 'Chưa đăng nhập'}</span>
                  </div>
                  <div className="text-xs text-text-muted truncate mt-0.5">
                    {t('userMenu.pleaseLogin') || 'Vui lòng đăng nhập để tiếp tục'}
                  </div>
                </>
              )}
            </div>

            <div className="flex flex-col gap-0.5">
              {session ? (
                <>
                  <button
                    type="button"
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-lg text-text-secondary hover:text-text-main hover:bg-surface-hover transition-colors text-left"
                    onClick={() => handleItemClick('profile')}
                  >
                    <i className="w-4 text-center fa-regular fa-user text-xs" />
                    <span>{t('userMenu.profile')}</span>
                  </button>
                  <button
                    type="button"
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-lg text-text-secondary hover:text-text-main hover:bg-surface-hover transition-colors text-left"
                    onClick={() => handleItemClick('password_change')}
                  >
                    <i className="w-4 text-center fa-solid fa-key text-xs" />
                    <span>{t('userMenu.passwordChange')}</span>
                  </button>
                  <button
                    type="button"
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-lg text-text-secondary hover:text-text-main hover:bg-surface-hover transition-colors text-left"
                    onClick={() => handleItemClick('settings')}
                  >
                    <i className="w-4 text-center fa-solid fa-gear text-xs" />
                    <span>{t('userMenu.settings')}</span>
                  </button>
                  <button
                    type="button"
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-lg text-text-secondary hover:text-text-main hover:bg-surface-hover transition-colors text-left"
                    onClick={() => handleItemClick('login')}
                  >
                    <i className="w-4 text-center fa-solid fa-right-to-bracket text-xs" />
                    <span>{t('userMenu.loginDemo')}</span>
                  </button>
                  <hr className="my-1 border-0 border-t border-subtle" />
                  <button
                    type="button"
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-lg text-danger hover:bg-danger-subtle transition-colors text-left"
                    onClick={async () => {
                      if (confirm(t('userMenu.logoutConfirm'))) {
                        await authService.logout();
                        handleItemClick('login');
                      }
                      setIsOpen(false);
                    }}
                  >
                    <i className="w-4 text-center fa-solid fa-arrow-right-from-bracket text-xs" />
                    <span>{t('userMenu.logout')}</span>
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-lg text-primary font-medium hover:bg-primary/10 transition-colors text-left"
                    onClick={() => handleItemClick('login')}
                  >
                    <i className="w-4 text-center fa-solid fa-right-to-bracket text-xs" />
                    <span>{t('userMenu.login') || 'Đăng nhập'}</span>
                  </button>
                  <button
                    type="button"
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-lg text-text-secondary hover:text-text-main hover:bg-surface-hover transition-colors text-left"
                    onClick={() => handleItemClick('login')}
                  >
                    <i className="w-4 text-center fa-solid fa-user-shield text-xs" />
                    <span>{t('userMenu.loginDemo')}</span>
                  </button>
                  <button
                    type="button"
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-xs rounded-lg text-text-secondary hover:text-text-main hover:bg-surface-hover transition-colors text-left"
                    onClick={() => handleItemClick('settings')}
                  >
                    <i className="w-4 text-center fa-solid fa-gear text-xs" />
                    <span>{t('userMenu.settings')}</span>
                  </button>
                </>
              )}
            </div>
          </div>
      )}
    </div>
  );
}



