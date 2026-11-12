import React from 'react';
import { useTranslation, SupportedLanguage } from '@i18n/translate';

export default function LanguageSwitcher() {
  const { currentLang, setLanguage } = useTranslation();

  const handleToggle = (lang: SupportedLanguage) => {
    setLanguage(lang);
  };

  return (
    <div className="flex items-center p-0.5 rounded-full bg-surface-elevated border border-border-subtle select-none" role="group" aria-label="Language switcher">
      <button
        type="button"
        className={`px-1.5 py-0.5 sm:px-2.5 sm:py-1 rounded-full text-[0.68rem] sm:text-[0.72rem] font-bold transition-all duration-fast cursor-pointer ${
          currentLang === 'vi'
            ? 'bg-primary text-white shadow-sm'
            : 'text-muted hover:text-main bg-transparent'
        }`}
        onClick={() => handleToggle('vi')}
        title="Tiếng Việt (VN)"
        aria-label="Chuyển sang Tiếng Việt"
        aria-pressed={currentLang === 'vi'}
      >
        <span>VN</span>
      </button>

      <button
        type="button"
        className={`px-1.5 py-0.5 sm:px-2.5 sm:py-1 rounded-full text-[0.68rem] sm:text-[0.72rem] font-bold transition-all duration-fast cursor-pointer ${
          currentLang === 'en'
            ? 'bg-primary text-white shadow-sm'
            : 'text-muted hover:text-main bg-transparent'
        }`}
        onClick={() => handleToggle('en')}
        title="English (EN)"
        aria-label="Switch to English"
        aria-pressed={currentLang === 'en'}
      >
        <span>EN</span>
      </button>
    </div>
  );
}
