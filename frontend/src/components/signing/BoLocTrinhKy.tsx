import type { ReactNode } from 'react';
import { Card } from '@components/common';
import { useSigningT } from '@lib/signing/i18n';

const LOP_NHAN = 'mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-secondary';

export function BoLocKhung({ children, hanhDong, className = '' }: {
  children: ReactNode; hanhDong?: ReactNode; className?: string;
}) {
  const { t } = useSigningT();
  const nhan = t('danhSach.tieuDeBoLoc');

  return (
    <Card className={`p-4 sm:p-5 ${className}`}>
      <section aria-label={nhan} className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="m-0 flex items-center gap-2 text-sm font-semibold text-main">
            <i className="fa-solid fa-sliders text-primary" aria-hidden="true" />
            {nhan}
          </h2>
          {hanhDong && <div className="flex flex-wrap items-center gap-2">{hanhDong}</div>}
        </div>
        {children}
      </section>
    </Card>
  );
}

export function TruongLoc({ nhan, icon, children, className = '' }: {
  nhan: string; icon?: string; children: ReactNode; className?: string;
}) {
  return (
    <label className={`block min-w-0 ${className}`}>
      <span className={LOP_NHAN}>
        {icon && <i className={`fa-solid ${icon} text-primary`} aria-hidden="true" />}
        {nhan}
      </span>
      {children}
    </label>
  );
}
