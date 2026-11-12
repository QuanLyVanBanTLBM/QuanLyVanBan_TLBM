import React from 'react';
import { Button } from '@components/common';
import { useTranslation } from '@i18n/translate';

interface PaginationProps {
  page: number;
  pageSize: number;
  count: number;
  onChange: (page: number) => void;
}

export default function Pagination({ page, pageSize, count, onChange }: PaginationProps) {
  const { t } = useTranslation();
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const firstItem = count === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastItem = Math.min(page * pageSize, count);

  return (
    <div className="flex flex-col gap-3 border-t border-border-subtle px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="m-0 text-xs text-muted">
        {t('records.pagination.summary', {
          first: String(firstItem),
          last: String(lastItem),
          count: String(count),
        })}
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          icon="fa-chevron-left"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label={t('records.pagination.previous')}
        >
          {t('records.pagination.previous')}
        </Button>
        <span className="min-w-20 text-center text-xs font-bold text-secondary">
          {t('records.pagination.page', {
            page: String(page),
            total: String(totalPages),
          })}
        </span>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          icon="fa-chevron-right"
          iconPosition="right"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          aria-label={t('records.pagination.next')}
        >
          {t('records.pagination.next')}
        </Button>
      </div>
    </div>
  );
}
