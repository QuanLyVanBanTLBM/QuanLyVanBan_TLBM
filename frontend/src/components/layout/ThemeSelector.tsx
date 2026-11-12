import React from 'react';
import { ThemeMode } from '@app-types/theme';
import { THEME_OPTIONS, isLightThemeMode } from '@lib/constants';

import { useTranslation } from '@i18n/translate';

interface ThemeSelectorProps {
  currentTheme: ThemeMode;
  onSelectTheme: (theme: ThemeMode) => void;
  onToggleTheme?: () => void;
  preferredLightTheme?: ThemeMode;
  preferredDarkTheme?: ThemeMode;
}

export default function ThemeSelector({
  currentTheme,
  onSelectTheme,
  onToggleTheme,
  preferredLightTheme = 'light',
  preferredDarkTheme = 'dark',
}: ThemeSelectorProps) {
  const { t } = useTranslation();
  const isLight = isLightThemeMode(currentTheme);
  const activeOption = THEME_OPTIONS.find((o) => o.id === currentTheme) || THEME_OPTIONS[0];
  const lightOption = THEME_OPTIONS.find((o) => o.id === preferredLightTheme) || THEME_OPTIONS[1];
  const darkOption = THEME_OPTIONS.find((o) => o.id === preferredDarkTheme) || THEME_OPTIONS[0];

  const handleToggle = () => {
    if (onToggleTheme) {
      onToggleTheme();
    } else {
      onSelectTheme(isLight ? preferredDarkTheme : preferredLightTheme);
    }
  };

  const nextModeName = isLight
    ? t('themeSelector.darkMode', { name: darkOption.name })
    : t('themeSelector.lightMode', { name: lightOption.name });

  const titleText = t('themeSelector.title', { active: activeOption.name, next: nextModeName });

  return (
    <div className="relative">
      <button
        type="button"
        className={`relative w-9 h-9 rounded-lg border flex items-center justify-center transition-all duration-fast cursor-pointer ${
          isLight
            ? 'bg-warning-subtle border-warning-border hover:border-warning'
            : 'bg-info-subtle border-info-border hover:border-info'
        }`}
        onClick={handleToggle}
        title={titleText}
        aria-label={titleText}
      >
        <i
          className={`fa-solid ${isLight ? 'fa-sun text-warning-text' : 'fa-moon text-info'} text-base transition-transform duration-300 hover:scale-110`}
        />
        {/* Điểm nhấn chế độ */}
        <span
          className={`absolute bottom-1 right-1 w-1.5 h-1.5 rounded-full ${
            isLight ? 'bg-warning-text' : 'bg-info'
          }`}
        />
      </button>
    </div>
  );
}


