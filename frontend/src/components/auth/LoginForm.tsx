import React, { useState } from 'react';
import { useTranslation } from '@i18n/translate';
import AlertModal from '@components/common/AlertModal';

export interface LoginFormProps {
  isLoading: boolean;
  isSuccess: boolean;
  error?: string;
  onSubmit: (credentials: { username: string; password: string }) => void;
  onUsernameFocusChange: (focused: boolean) => void;
  onPasswordFocusChange: (focused: boolean) => void;
  onShowPasswordChange: (show: boolean) => void;
  onTyping: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({
  isLoading,
  isSuccess,
  error,
  onSubmit,
  onUsernameFocusChange,
  onPasswordFocusChange,
  onShowPasswordChange,
  onTyping,
}) => {
  const { t } = useTranslation();
  const [username, setUsername] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
   const [alertOpen, setAlertOpen] = useState(false);
   const [alertMsg, setAlertMsg] = useState('');

  const toggleShowPassword = () => {
    const nextShow = !showPassword;
    setShowPassword(nextShow);
    onShowPasswordChange(nextShow);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({ username, password });
  };

  return (
    <div className="w-full md:w-[55%] bg-surface !rounded-none !shadow-none !border-none relative flex flex-col justify-center p-4 sm:p-6 md:p-8">
      <h2 className="text-2xl font-extrabold text-main tracking-tight mb-0.5">
        {t('auth.welcomeBack')}
      </h2>
      <p className="text-xs text-muted mb-4">
        {t('auth.welcomeDesc')}
      </p>

      {error && (
        <div className="bg-danger-subtle border border-danger-border rounded-md p-2.5 text-xs text-danger mb-3 flex items-center gap-2 animate-fade-in">
          <i className="fa-solid fa-triangle-exclamation" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="text-left">
          <label className="block text-xs font-bold text-secondary mb-1">
            {t('auth.usernameLabel')}
          </label>
          <div className="relative flex items-center">
            <input
              type="text"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                onTyping();
              }}
              onFocus={() => onUsernameFocusChange(true)}
              onBlur={() => onUsernameFocusChange(false)}
              placeholder={t('auth.usernamePlaceholder')}
              required
              className="w-full px-3.5 py-2.5 rounded-md border border-border-subtle bg-surface text-main text-sm outline-none transition-fast focus:border-primary focus:ring-2 focus:ring-primary-glow placeholder:text-muted"
            />
          </div>
        </div>

        <div className="text-left">
          <label className="block text-xs font-bold text-secondary mb-1">
            {t('auth.passwordLabel')}
          </label>
          <div className="relative flex items-center">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                onTyping();
              }}
              onFocus={() => onPasswordFocusChange(true)}
              onBlur={() => onPasswordFocusChange(false)}
              placeholder={t('auth.passwordPlaceholder')}
              required
              className="w-full px-3.5 py-2.5 pr-10 rounded-md border border-border-subtle bg-surface text-main text-sm outline-none transition-fast focus:border-primary focus:ring-2 focus:ring-primary-glow placeholder:text-muted"
            />
            <button
              type="button"
              onClick={toggleShowPassword}
              title={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
              className="absolute right-3 text-muted hover:text-primary transition-fast text-sm p-1"
            >
              <i className={`fa-regular ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`} />
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs text-secondary pt-1">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              className="accent-primary cursor-pointer rounded-xs"
            />
            <span>{t('auth.rememberMe')}</span>
          </label>
           <a
             href="#forgot"
             onClick={(e) => {
               e.preventDefault();
               setAlertMsg(t('auth.forgotPasswordAlert'));
               setAlertOpen(true);
             }}
             className="font-semibold text-main hover:text-primary transition-fast hover:underline"
           >
             {t('auth.forgotPassword')}
           </a>
        </div>

        <button
          type="submit"
          disabled={isLoading || isSuccess}
          className="w-full py-2.5 px-4 rounded-md bg-primary hover:bg-primary-hover active:translate-y-0 text-white text-sm font-bold shadow-md hover:shadow-glow transition-normal flex items-center justify-center gap-2 disabled:opacity-60 mt-1"
        >
          {isSuccess && <i className="fa-solid fa-check text-xs" />}
          <span>{isSuccess ? t('auth.loginSuccess') : isLoading ? t('auth.loggingIn') : t('auth.loginBtn')}</span>
          {!isSuccess && <i className="fa-solid fa-arrow-right text-xs" />}
        </button>
      </form>
       <AlertModal open={alertOpen} onClose={()=>setAlertOpen(false)} message={alertMsg} />
    </div>
  );
};

export default LoginForm;


