import React from 'react';
import { ActivePageId } from '@app-types/navigation';
import { MAIN_MODULES } from '@lib/constants';
import { useTranslation } from '@i18n/translate';

export interface SubNavContentProps {
  activePage: ActivePageId;
  onNavigate?: (page: ActivePageId) => void;
  onScrollToTop?: () => void;
  isCompact?: boolean;
}

export function SubNavContent({
  activePage,
  onNavigate = () => {},
  onScrollToTop,
  isCompact = false,
}: SubNavContentProps) {
  const { t } = useTranslation();

  // Phân hệ cha tương ứng với trang đang hiển thị
  const activeModule =
    MAIN_MODULES.find((mod) => mod.subItems.some((item) => item.id === activePage)) ||
    MAIN_MODULES[0];

  const currentSubItem =
    activeModule.subItems.find((item) => item.id === activePage) || activeModule.subItems[0];

  const getModuleLabel = (modId: string, fallback: string) => {
    const key = modId === 'records_resources' ? 'records' : modId;
    return t(`navigation.${key}`) !== `navigation.${key}` ? t(`navigation.${key}`) : fallback;
  };

  const getSubItemLabel = (subId: string, fallback: string) => {
    const navKey = `navigation.${subId}`;
    const pageTitleKey = `pages.${subId}.title`;
    if (t(navKey) !== navKey) return t(navKey);
    if (t(pageTitleKey) !== pageTitleKey) return t(pageTitleKey);
    return fallback;
  };

  const activeModuleLabel = getModuleLabel(activeModule.id, activeModule.label);
  const activeSubLabel = getSubItemLabel(currentSubItem.id, currentSubItem.label);

  const isAccountPage = activePage === 'password_change' || activePage === 'profile' || activePage === 'settings';
  const accountMeta: Record<string, { icon: string; title: string }> = {
    password_change: { icon: 'fa-key', title: t('passwordChange.title') },
    profile: { icon: 'fa-user-gear', title: t('profile.title') },
    settings: { icon: 'fa-gear', title: t('settings.title') },
  };

  // Trang Dashboard: Nút Home + Thanh tìm kiếm
  if (activePage === 'dashboard') {
    if (isCompact) {
      return (
        <div className="flex items-center gap-2 sm:gap-3 w-full min-w-0">
          <button
            type="button"
            onClick={onScrollToTop || (() => onNavigate('dashboard'))}
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-primary-subtle text-primary hover:bg-primary/15 transition-all cursor-pointer shrink-0 font-semibold text-xs sm:text-sm group shadow-2xs border border-primary/20"
            title={t('navigation.dashboard') || 'Trang Chủ'}
            aria-label={t('navigation.dashboard') || 'Trang Chủ'}
          >
            <div className="w-5 h-5 rounded-lg bg-primary text-white flex items-center justify-center text-[10px] shadow-2xs">
              <i className="fa-solid fa-gauge-high group-hover:scale-110 transition-transform" />
            </div>
            <span className="font-bold text-text-main hidden xs:inline">{t('navigation.dashboard') || 'Home'}</span>
          </button>
          <div id="header-search-slot" className="flex-1 min-w-0" />
        </div>
      );
    }
    return (
      <div className="flex items-center gap-4 w-full min-w-0">
        <div className="flex items-center gap-2.5 shrink-0">
          <div
            className="w-8 h-8 rounded-xl bg-primary-subtle text-primary flex items-center justify-center text-sm shadow-2xs"
            title={`${activeModuleLabel} (${activeModule.teamTag})`}
          >
            <i className={`fa-solid ${activeModule.icon}`} />
          </div>
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <span className="text-text-main font-bold text-sm flex items-center gap-1.5">
              <span>{t('navigation.dashboard') || 'Trang Chủ'}</span>
            </span>
          </div>
        </div>
        <div id="top-subnav-slot" className="flex-1 flex items-center min-w-0" />
      </div>
    );
  }

  // Các trang tài khoản (password_change, profile, settings)
  if (isAccountPage) {
    const meta = accountMeta[activePage];
    return (
      <div className="flex items-center gap-2.5 sm:gap-3 w-full min-w-0">
        <div
          onClick={isCompact && onScrollToTop ? onScrollToTop : undefined}
          className={`${
            isCompact ? 'w-7 h-7 rounded-lg text-xs cursor-pointer hover:opacity-80' : 'w-8 h-8 rounded-xl text-sm'
          } bg-primary-subtle text-primary flex items-center justify-center shadow-2xs shrink-0 transition-opacity`}
          title={isCompact ? 'Bấm để cuộn lên đầu trang' : meta?.title}
        >
          <i className={`fa-solid ${meta?.icon || 'fa-user'}`} />
        </div>
        <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm text-text-secondary min-w-0 truncate">
          <button
            type="button"
            className="hover:text-primary transition-colors cursor-pointer font-medium shrink-0"
            onClick={() => onNavigate('dashboard')}
            title="Về Trang Chủ"
          >
            {t('navigation.dashboard') || 'Trang Chủ'}
          </button>
          <i className="fa-solid fa-angle-right text-[10px] sm:text-xs text-text-muted shrink-0" />
          <span
            onClick={isCompact && onScrollToTop ? onScrollToTop : undefined}
            className={`text-text-main font-bold truncate ${
              isCompact ? 'cursor-pointer hover:text-primary transition-colors' : ''
            }`}
            title={isCompact ? 'Bấm để cuộn lên đầu trang' : meta?.title}
          >
            {meta?.title}
          </span>
        </div>
      </div>
    );
  }

  // Các trang phân hệ nghiệp vụ khác (Đã loại bỏ cụm nút tab con thừa thãi góc phải theo yêu cầu QA)
  return (
    <div className="flex items-center justify-between gap-3 w-full min-w-0">
      <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1">
        <div
          onClick={isCompact && onScrollToTop ? onScrollToTop : () => onNavigate(activeModule.defaultPage)}
          className={`${
            isCompact ? 'w-7 h-7 rounded-lg text-xs cursor-pointer hover:opacity-80' : 'w-8 h-8 rounded-xl text-sm'
          } bg-primary-subtle text-primary flex items-center justify-center shadow-2xs shrink-0 transition-opacity`}
          title={isCompact ? 'Bấm để cuộn lên đầu trang' : `${activeModuleLabel} (${activeModule.teamTag})`}
        >
          <i className={`fa-solid ${activeModule.icon}`} />
        </div>
        <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm text-text-secondary min-w-0 truncate">
          <button
            type="button"
            className="hover:text-primary transition-colors cursor-pointer font-medium shrink-0 hidden sm:inline"
            onClick={() => onNavigate('dashboard')}
            title="Về Trang Chủ"
          >
            {t('navigation.dashboard') || 'Trang Chủ'}
          </button>
          <i className="fa-solid fa-angle-right text-[10px] sm:text-xs text-text-muted shrink-0 hidden sm:inline" />
          <button
            type="button"
            className="hover:text-primary transition-colors cursor-pointer font-medium truncate"
            onClick={() => onNavigate(activeModule.defaultPage)}
            title={`Chuyển tới ${activeModuleLabel}`}
          >
            {activeModuleLabel}
          </button>
          {activeSubLabel !== activeModuleLabel && (
            <>
              <i className="fa-solid fa-angle-right text-[10px] sm:text-xs text-text-muted shrink-0" />
              <span
                onClick={isCompact && onScrollToTop ? onScrollToTop : undefined}
                className={`text-text-main font-bold truncate ${
                  isCompact ? 'cursor-pointer hover:text-primary transition-colors' : ''
                }`}
                title={isCompact ? 'Bấm để cuộn lên đầu trang' : activeSubLabel}
              >
                {activeSubLabel}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export interface TopSubNavProps {
  activePage: ActivePageId;
  isHoveredPreview?: boolean;
  onNavigate: (page: ActivePageId) => void;
  isScrolled?: boolean;
}

export default function TopSubNav({
  activePage,
  onNavigate,
  isScrolled = false,
}: TopSubNavProps) {
  return (
    <nav
      className={`top-subnav px-4 sm:px-6 bg-app flex items-center justify-between shrink-0 select-none transition-all duration-300 ease-in-out ${
        isScrolled
          ? 'lg:h-0 lg:max-h-0 lg:opacity-0 lg:overflow-hidden lg:py-0 lg:border-transparent lg:pointer-events-none'
          : 'h-11 max-h-11 opacity-100 overflow-x-auto border-b border-subtle'
      }`}
      aria-label="Điều hướng phân hệ con"
    >
      <SubNavContent
        activePage={activePage}
        onNavigate={onNavigate}
        isCompact={false}
      />
    </nav>
  );
}
