import React from 'react';
import { Button } from '@components/common';

interface PaginationProps {
  page: number;
  pageSize: number;
  count: number;
  onChange: (page: number) => void;
}

export default function Pagination({ page, pageSize, count, onChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const firstItem = count === 0 ? 0 : (page - 1) * pageSize + 1;
  const lastItem = Math.min(page * pageSize, count);

  return (
    <div className="flex flex-col gap-3 border-t border-border-subtle px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="m-0 text-xs text-muted">
        Hiển thị {firstItem}–{lastItem} trong tổng số {count}
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          icon="fa-chevron-left"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label="Trang trước"
        >
          Trước
        </Button>
        <span className="min-w-20 text-center text-xs font-bold text-secondary">
          Trang {page}/{totalPages}
        </span>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          icon="fa-chevron-right"
          iconPosition="right"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          aria-label="Trang sau"
        >
          Sau
        </Button>
      </div>
    </div>
  );
}
