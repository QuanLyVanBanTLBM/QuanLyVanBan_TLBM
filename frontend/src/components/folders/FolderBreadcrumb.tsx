import React from 'react';
import { FolderBreadcrumb as BreadcrumbType } from '@app-types/resource';
import { useTranslation } from '@i18n/translate';

interface FolderBreadcrumbProps {
  breadcrumbs: BreadcrumbType[];
  onSelect: (folderId: number | null) => void;
  className?: string;
}

export const FolderBreadcrumb: React.FC<FolderBreadcrumbProps> = ({
  breadcrumbs,
  onSelect,
  className = '',
}) => {
  const { t } = useTranslation();
  return (
    <nav
      aria-label="Breadcrumb"
      className={`flex items-center flex-wrap gap-1.5 px-3 py-2 bg-surface-elevated/40 border border-border-subtle rounded-xl text-xs ${className}`}
    >
      <button
        type="button"
        onClick={() => onSelect(null)}
        className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-secondary hover:text-primary hover:bg-surface-elevated transition-colors font-medium"
        title={t('folders.breadcrumb.rootTitle')}
      >
        <i className="fa-solid fa-house-chimney text-xs text-primary" />
        <span>{t('folders.breadcrumb.root')}</span>
      </button>

      {breadcrumbs.map((item, index) => {
        const isLast = index === breadcrumbs.length - 1;
        return (
          <React.Fragment key={item.id}>
            <i className="fa-solid fa-chevron-right text-[10px] text-muted mx-0.5" />
            <button
              type="button"
              disabled={isLast}
              onClick={() => onSelect(item.id)}
              className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md transition-colors ${
                isLast
                  ? 'text-primary font-bold bg-primary/10 cursor-default'
                  : 'text-secondary hover:text-primary hover:bg-surface-elevated font-medium'
              }`}
              title={t('folders.breadcrumb.levelTitle', { level: item.depth, name: item.name })}
            >
              <i
                className={`fa-solid ${
                  isLast ? 'fa-folder-open text-primary' : 'fa-folder text-amber-500'
                } text-xs`}
              />
              <span className="max-w-[160px] truncate">{item.name}</span>
              <span className="text-[10px] px-1 py-0.2 rounded bg-surface border border-border-subtle text-muted">
                {t('folders.breadcrumb.level', { level: item.depth })}
              </span>
            </button>
          </React.Fragment>
        );
      })}
    </nav>
  );
};

export default FolderBreadcrumb;
