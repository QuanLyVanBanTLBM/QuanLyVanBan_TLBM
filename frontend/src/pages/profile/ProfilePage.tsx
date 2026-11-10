import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ActivePageId } from '@app-types/navigation';
import { useTranslation } from '@i18n/translate';
import { Card, Button } from '@components/common';
import { formatRoleTitle, formatUserName } from '@lib/roleUtils';

interface ProfilePageProps {
  onNavigate?: (page: ActivePageId) => void;
}

export default function ProfilePage({ onNavigate }: ProfilePageProps) {
  const navigate = useNavigate();
  const { t, currentLang } = useTranslation();

  // Lấy thông tin phiên đăng nhập thực tế
  const session = (() => {
    try {
      const raw = localStorage.getItem('tlbm_session');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  })();

  const rawName = session?.fullName || session?.username || '—';
  const displayName = formatUserName(rawName, currentLang);
  const rawRole = session?.roleTitle || session?.role || '—';
  const displayRole = formatRoleTitle(rawRole, currentLang);
  const displayDept = session?.department || (session ? t('profile.sampleDept') : '—');
  const displayEmail = session?.email || (session?.username ? `${session.username}@donvi.gov.vn` : '—');

  return (
    <div className="max-w-4xl mx-auto my-5 flex flex-col gap-5">
      <Card className="p-7 sm:p-8">
        <div className="flex justify-between items-center mb-6 flex-wrap gap-2.5">
          <h2 className="text-xl font-extrabold text-main flex items-center gap-2.5 m-0">
            <i className="fa-solid fa-user text-primary" />
            <span>{t('profile.title')}</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-3.5 px-4.5 bg-surface-elevated border border-border-subtle rounded-lg">
            <span className="text-xs text-muted font-medium">{t('profile.fullName')}:</span>
            <div className="font-bold text-base text-main mt-1">
              {displayName}
            </div>
          </div>

          <div className="p-3.5 px-4.5 bg-surface-elevated border border-border-subtle rounded-lg">
            <span className="text-xs text-muted font-medium">{t('profile.role')}:</span>
            <div className="font-bold text-base text-primary mt-1">
              {displayRole}
            </div>
          </div>

          <div className="p-3.5 px-4.5 bg-surface-elevated border border-border-subtle rounded-lg">
            <span className="text-xs text-muted font-medium">{t('profile.department')}:</span>
            <div className="font-bold text-base text-main mt-1">
              {displayDept}
            </div>
          </div>

          <div className="p-3.5 px-4.5 bg-surface-elevated border border-border-subtle rounded-lg">
            <span className="text-xs text-muted font-medium">{t('profile.email')}:</span>
            <div className="font-bold text-base text-main mt-1">
              {displayEmail}
            </div>
          </div>
        </div>

        <div className="mt-6 flex gap-3 flex-wrap">
          <Button
            variant="primary"
            size="md"
            icon="fa-arrow-left"
            onClick={() => {
              if (onNavigate) onNavigate('dashboard');
              navigate('/dashboard');
            }}
          >
            {t('common.backToDashboard')}
          </Button>
        </div>
      </Card>
    </div>
  );
}



