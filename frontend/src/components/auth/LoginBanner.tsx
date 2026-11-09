import React from 'react';
import { useTranslation } from '@i18n/translate';

export const LoginBanner: React.FC = () => {
  const { t } = useTranslation();

  return (
    <div className="w-full md:w-[45%] bg-surface-elevated !rounded-none !shadow-none !border-0 md:!border-r md:!border-solid md:!border-border-subtle relative flex flex-col justify-between p-5 sm:p-6 md:p-8 select-none overflow-hidden min-h-[260px] md:min-h-[440px]">
      {/* 1. Tiêu đề thương hiệu phân hệ */}
      <div className="flex items-center gap-2.5 z-10">
        <div className="w-10 h-10 rounded-lg bg-surface border border-subtle flex items-center justify-center shadow-sm p-1.5 shrink-0">
          <img src="/baolong-icon.png" alt="Bảo Long Icon" className="w-full h-full object-contain" />
        </div>
        <div>
          <div className="text-sm font-extrabold text-main leading-tight">
            {t('auth.brandTitle')}
          </div>
          <div className="text-[11px] font-bold text-primary tracking-wide">
            {t('auth.brandSubtitle')}
          </div>
        </div>
      </div>

      {/* 2. Hình ảnh trung tâm: Banner thương hiệu Bảo Long to hơn, bo nhẹ, có viền tinh tế chống ăn góc */}
      <div className="my-auto py-2 sm:py-4 flex flex-col items-center justify-center text-center z-10 w-full">
        <div className="w-full overflow-hidden rounded-md border border-border-subtle shadow-sm">
          <img
            src="/baolong-banner.jpg"
            alt="Bảo Long Insurance"
            className="w-full h-auto object-cover block"
          />
        </div>
      </div>

      {/* 3. Footer chứng chỉ / cam kết bảo mật */}
      <div className="flex items-center justify-between text-[11px] text-muted border-t border-border-subtle pt-3 z-10">
        <span className="flex items-center gap-1.5">
          <i className="fa-solid fa-shield-halved text-primary" />
          <span>{t('auth.securityBadge')}</span>
        </span>
        <span className="font-semibold text-secondary">v2.0</span>
      </div>
    </div>
  );
};

export default LoginBanner;

