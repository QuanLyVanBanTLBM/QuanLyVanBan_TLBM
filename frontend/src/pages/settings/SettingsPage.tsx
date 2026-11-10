import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@i18n/translate';
import { Button } from '@components/common';
import soundAlert from '@lib/soundAlert';

// Component Toggle Switch phong cách Hiện đại (Modern UI)
function ModernToggle({
  checked,
  onChange,
  label,
  description,
  icon,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
  icon?: string;
}) {
  return (
    <div
      className="flex items-center justify-between gap-4 p-3.5 rounded-xl bg-surface-elevated/40 hover:bg-surface-hover/80 border border-border-subtle/70 transition-all cursor-pointer group select-none"
      onClick={() => onChange(!checked)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onChange(!checked);
        }
      }}
    >
      <div className="flex items-start gap-3 flex-1 min-w-0">
        {icon && (
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm shrink-0 transition-colors ${
              checked ? 'bg-primary-subtle text-primary' : 'bg-surface text-text-muted border border-border-subtle'
            }`}
          >
            <i className={`fa-solid ${icon}`} />
          </div>
        )}
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-semibold text-main group-hover:text-primary transition-colors">
            {label}
          </span>
          {description && (
            <span className="text-xs text-muted leading-relaxed">
              {description}
            </span>
          )}
        </div>
      </div>
      <div
        className={`w-11 h-6 rounded-full transition-all duration-200 relative shrink-0 p-0.5 flex items-center ${
          checked
            ? 'bg-primary border border-primary/90 shadow-xs'
            : 'bg-slate-300 dark:bg-slate-700 border border-slate-300/80 dark:border-slate-600/80'
        }`}
      >
        <div
          className={`w-5 h-5 rounded-full bg-white shadow-md border border-black/5 transition-transform duration-200 transform ${
            checked ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  // Trạng thái cấu hình âm thanh & bảo mật phiên làm việc (hoạt động thực tế)
  const [notifUrgent, setNotifUrgent] = useState<boolean>(() => soundAlert.isUrgentSoundEnabled());
  const [secAutoLock, setSecAutoLock] = useState<boolean>(() => {
    return localStorage.getItem('tlbm_sec_auto_lock') !== 'false';
  });
  const [secLockTimeout, setSecLockTimeout] = useState<number>(() => {
    return parseInt(localStorage.getItem('tlbm_sec_lock_timeout') || '15', 10);
  });
  const [showSavedToast, setShowSavedToast] = useState(false);

  const handleSaveSettings = () => {
    localStorage.setItem('tlbm_interface_style', 'modern');
    document.documentElement.setAttribute('data-ui-style', 'modern');
    localStorage.removeItem('tlbm_ai_model');
    localStorage.setItem('tlbm_notif_sound_urgent', String(notifUrgent));
    soundAlert.setUrgentSoundEnabled(notifUrgent);
    localStorage.setItem('tlbm_sec_auto_lock', String(secAutoLock));
    localStorage.setItem('tlbm_sec_lock_timeout', String(secLockTimeout));

    window.dispatchEvent(new Event('tlbm_settings_updated'));
    window.dispatchEvent(new Event('tlbm_sound_settings_updated'));
    setShowSavedToast(true);
    setTimeout(() => setShowSavedToast(false), 3500);
  };

  const handleResetSettings = () => {
    localStorage.setItem('tlbm_interface_style', 'modern');
    document.documentElement.setAttribute('data-ui-style', 'modern');
    localStorage.removeItem('tlbm_ai_model');
    setNotifUrgent(true);
    setSecAutoLock(true);
    setSecLockTimeout(15);

    localStorage.setItem('tlbm_notif_sound_urgent', 'true');
    localStorage.setItem('tlbm_sec_auto_lock', 'true');
    localStorage.setItem('tlbm_sec_lock_timeout', '15');
    soundAlert.setUrgentSoundEnabled(true);

    window.dispatchEvent(new Event('tlbm_settings_updated'));
    window.dispatchEvent(new Event('tlbm_sound_settings_updated'));
    setShowSavedToast(true);
    setTimeout(() => setShowSavedToast(false), 3500);
  };

  return (
    <div className="max-w-4xl mx-auto my-4 sm:my-6 flex flex-col gap-6 animate-in fade-in duration-200">
      {/* Toast thông báo lưu thành công */}
      {showSavedToast && (
        <div className="fixed top-20 right-6 z-50 bg-surface border border-success/30 shadow-lg rounded-xl p-4 flex items-center gap-3 animate-in slide-in-from-top-2">
          <div className="w-8 h-8 rounded-full bg-success/15 text-success flex items-center justify-center shrink-0">
            <i className="fa-solid fa-circle-check" />
          </div>
          <div>
            <div className="text-sm font-bold text-main">{t('settings.saveSuccessAlert')}</div>
            <div className="text-xs text-muted">{t('settings.saveSuccessDetail')}</div>
          </div>
        </div>
      )}

      {/* 1. Header Banner: Giới thiệu & Nút xem trước Trang Chủ */}
      <div className="bg-surface border border-border-subtle rounded-2xl p-6 sm:p-7 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="px-3 py-1 rounded-full bg-primary text-white text-xs font-bold flex items-center gap-1.5 shadow-xs">
              <i className="fa-solid fa-gear text-[11px]" />
              <span>{t('settings.appConfig')}</span>
            </span>
          </div>
          <h1 className="text-2xl font-extrabold text-main mt-2">
            {t('settings.title')}
          </h1>
          <p className="text-sm text-secondary mt-1 max-w-2xl">
            {t('settings.subtitle')}
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button
            type="button"
            variant="outline"
            size="md"
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 shadow-xs"
          >
            <i className="fa-solid fa-eye text-primary" />
            <span>{t('settings.previewDashboard')}</span>
          </Button>
        </div>
      </div>

      {/* 2. Cấu hình thông báo âm thanh & Bảo mật phiên làm việc */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card: Cấu hình thông báo âm thanh */}
        <div className="bg-surface border border-border-subtle rounded-2xl p-6 shadow-xs space-y-4 flex flex-col justify-between">
          <div className="space-y-3.5">
            <div className="flex items-center gap-2.5 pb-2 border-b border-border-subtle">
              <div className="w-8 h-8 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-sm">
                <i className="fa-solid fa-bell" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-main">
                  {t('settings.notificationSectionTitle')}
                </h3>
                <p className="text-xs text-muted">{t('settings.notificationSectionDesc')}</p>
              </div>
            </div>

            <div className="space-y-2.5 pt-1">
              <ModernToggle
                checked={notifUrgent}
                onChange={setNotifUrgent}
                label={t('settings.notifUrgent')}
                description={t('settings.notifUrgentDesc')}
                icon="fa-volume-high"
              />
            </div>
          </div>

          {/* Tiện ích nghe thử âm thanh chuông */}
          <div className="pt-3 mt-1 flex items-center justify-between gap-3 border-t border-border-subtle/70">
            <div className="flex items-center gap-1.5 text-xs text-muted">
              <i className="fa-solid fa-circle-check text-primary text-[11px]" />
              <span>Web Audio Chuông Hỏa Tốc</span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => soundAlert.playUrgentChime(true)}
              className="gap-2 shadow-2xs hover:border-primary/40 font-semibold"
            >
              <i className="fa-solid fa-volume-high text-primary text-xs" />
              <span>{t('settings.testSound')}</span>
            </Button>
          </div>
        </div>

        {/* Card: Bảo mật phiên làm việc */}
        <div className="bg-surface border border-border-subtle rounded-2xl p-6 shadow-xs space-y-4 flex flex-col justify-between">
          <div className="space-y-3.5">
            <div className="flex items-center gap-2.5 pb-2 border-b border-border-subtle">
              <div className="w-8 h-8 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-sm">
                <i className="fa-solid fa-shield-halved" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-main">
                  {t('settings.securitySectionTitle')}
                </h3>
                <p className="text-xs text-muted">{t('settings.securitySectionDesc')}</p>
              </div>
            </div>

            <div className="space-y-2.5 pt-1">
              <ModernToggle
                checked={secAutoLock}
                onChange={setSecAutoLock}
                label={t('settings.secAutoLock')}
                description={t('settings.secAutoLockDesc')}
                icon="fa-lock"
              />
            </div>
          </div>

          {/* Tùy chỉnh thời gian & Nút khóa màn hình ngay để demo */}
          <div className="pt-3 mt-1 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-border-subtle/70">
            <div className="flex items-center gap-2">
              <span className="text-xs text-secondary font-medium whitespace-nowrap">
                {t('settings.lockTimeout')}:
              </span>
              <select
                value={secLockTimeout}
                onChange={(e) => setSecLockTimeout(Number(e.target.value))}
                disabled={!secAutoLock}
                className="text-xs bg-surface border border-border-subtle rounded-lg px-2.5 py-1 text-main font-medium focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value={5}>5 phút</option>
                <option value={15}>15 phút (Chuẩn)</option>
                <option value={30}>30 phút</option>
              </select>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => window.dispatchEvent(new Event('tlbm_lock_screen_now'))}
              className="gap-2 shadow-2xs hover:border-amber-500/40 text-amber-600 dark:text-amber-400 font-semibold"
            >
              <i className="fa-solid fa-lock text-xs" />
              <span>{t('settings.lockNow')}</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 3. Cấu hình mô hình AI phân tích văn bản */}
      <div className="bg-surface border border-border-subtle rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-border-subtle">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary-subtle text-primary flex items-center justify-center text-sm">
              <i className="fa-solid fa-brain" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-main">
                {t('settings.aiModelSectionTitle')}
              </h3>
              <p className="text-xs text-muted">
                {t('settings.aiModelSectionDesc')}
              </p>
            </div>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-primary-subtle text-primary border border-primary/30 flex items-center gap-1.5 shadow-2xs">
            <i className="fa-solid fa-circle-check text-xs" />
            <span>{t('settings.aiModelActive')}OPENAI · GPT-6-LUNA</span>
          </span>
        </div>

        <div className="pt-1">
          {/* Fixed OpenAI model used by the AI system */}
          <div className="p-5 rounded-2xl border-2 border-primary bg-primary-subtle/20 shadow-xs ring-1 ring-primary/40 flex flex-col md:flex-row md:items-center justify-between gap-5 transition-all select-none">
            <div className="flex items-start gap-4 flex-1">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-primary to-indigo-500 text-white flex items-center justify-center text-xl shrink-0 shadow-sm shadow-primary/30">
                <i className="fa-solid fa-wand-magic-sparkles" />
              </div>
              <div className="flex flex-col gap-1.5 flex-1">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="text-base font-bold text-main">
                    {t('settings.aiModelLuna6')}
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-success/15 text-success border border-success/30 flex items-center gap-1">
                    <i className="fa-solid fa-check text-[10px]" />
                    <span>{t('settings.aiModelLuna6Badge')}</span>
                  </span>
                </div>
                <p className="text-xs text-secondary leading-relaxed max-w-2xl">
                  {t('settings.aiModelLuna6Desc')}
                </p>
                <div className="flex items-center gap-2 flex-wrap pt-1">
                  <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-surface text-text-muted border border-border-subtle flex items-center gap-1.5">
                    <i className="fa-solid fa-file-lines text-primary text-[11px]" />
                    <span>{t('settings.aiFeatureSummarize')}</span>
                  </span>
                  <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-surface text-text-muted border border-border-subtle flex items-center gap-1.5">
                    <i className="fa-solid fa-tags text-primary text-[11px]" />
                    <span>{t('settings.aiFeatureEntity')}</span>
                  </span>
                  <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-surface text-text-muted border border-border-subtle flex items-center gap-1.5">
                    <i className="fa-solid fa-shield-halved text-success text-[11px]" />
                    <span>{t('settings.aiFeatureSecurity')}</span>
                  </span>
                </div>
              </div>
            </div>

            <div className="shrink-0 flex items-center md:flex-col md:items-end gap-1.5 text-xs border-t md:border-t-0 md:border-l border-border-subtle/80 pt-3 md:pt-0 md:pl-5">
              <span className="font-semibold text-primary">OpenAI</span>
              <span className="text-[11px] text-muted font-mono">gpt-6-luna</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Khối Lưu & Khôi phục (Footer Actions) */}
      <div className="bg-surface border border-border-subtle rounded-2xl p-4 sm:p-5 shadow-xs flex items-center justify-between gap-4 flex-wrap">
        <p className="text-xs text-muted">
          {t('settings.saveSettingsNote')}
        </p>
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="secondary"
            size="md"
            onClick={handleResetSettings}
          >
            {t('settings.resetDefault')}
          </Button>
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={handleSaveSettings}
          >
            <i className="fa-solid fa-floppy-disk mr-1.5" />
            {t('settings.saveSettings')}
          </Button>
        </div>
      </div>
    </div>
  );
}


