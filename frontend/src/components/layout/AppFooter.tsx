import React from 'react';
import { useTranslation } from '@i18n/translate';
import { Logo } from '@components/common/Logo';

export default function AppFooter() {
  const { t } = useTranslation();

  return (
    <footer className="app-footer px-6 py-3 border-t border-border-subtle bg-surface text-xs text-muted flex flex-wrap justify-between items-center gap-3 select-none">
      <div className="flex items-center gap-2.5">
        <Logo size="xs" className="opacity-75" />
        <div>
          <strong className="text-main">{t('app.name') || 'Hệ Thống Quản Lý Văn Bản & Tài Liệu'}</strong>
        </div>
      </div>
      <div>
        <span>{t('footer.copyright', { year: new Date().getFullYear().toString() })}</span>
      </div>
    </footer>
  );
}


