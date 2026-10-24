import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ActivePageId } from '@app-types/navigation';
import { pageIdToPath } from '@lib/routes';
import { apiClient, ApiError } from '@lib/apiClient';
import ModernDashboardView, { DocumentItem, TaskItem, ResourceTemplateItem, SigningRequestItem } from '@components/dashboard/ModernDashboardView';
import { BirthdayEmployee } from '@components/dashboard/BirthdaysWidget';

export interface DashboardMeetingItem {
  id: string;
  room_name: string;
  roomName?: string;
  meeting_title: string;
  topic?: string;
  start_time: string;
  end_time: string;
  time?: string;
  organizer: string;
  status: string;
}

export interface DashboardKpis {
  incomingCount: number;
  outgoingCount: number;
  tasksCount: number;
  signingCount?: number;
}

export interface DashboardOverviewResponse {
  kpis?: DashboardKpis;
  recentIncoming?: DocumentItem[];
  recentOutgoing?: DocumentItem[];
  tasks?: TaskItem[];
  resources?: ResourceTemplateItem[];
  recentSigning?: SigningRequestItem[];
  meetingRooms?: DashboardMeetingItem[];
  birthdays?: BirthdayEmployee[];
  error?: string;
  message?: string;
}

interface DashboardPageProps {
  onNavigate?: (page: string) => void;
}

export default function DashboardPage({ onNavigate }: DashboardPageProps) {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadTrigger, setReloadTrigger] = useState<number>(0);

  const handleNavigate = (pageId: ActivePageId) => {
    if (onNavigate) {
      onNavigate(pageId);
    }
    navigate(pageIdToPath(pageId));
  };

  const handleRetry = () => {
    setIsLoading(true);
    setError(null);
    setReloadTrigger((prev) => prev + 1);
  };

  useEffect(() => {
    let isMounted = true;

    apiClient<DashboardOverviewResponse>('/api/dashboard/overview/')
      .then((res) => {
        if (isMounted) {
          setData(res);
          setIsLoading(false);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          if (err instanceof ApiError) {
            if (err.status === 401 || err.status === 403) {
              localStorage.removeItem('tlbm_access_token');
              localStorage.removeItem('tlbm_token');
              localStorage.removeItem('tlbm_refresh_token');
              localStorage.removeItem('tlbm_session');
              window.dispatchEvent(new Event('tlbm_auth_changed'));
              navigate('/login', { replace: true });
              return;
            } else {
              setError(
                err.data?.error ||
                  err.data?.message ||
                  err.data?.detail ||
                  'Không thể tải dữ liệu Bảng điều khiển từ máy chủ.'
              );
            }
          } else {
            setError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.');
          }
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [reloadTrigger, navigate]);

  // 1. Trạng thái Đang tải (Loading Skeleton)
  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse p-2" data-testid="dashboard-loading">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-surface rounded-2xl border border-border-subtle/40" />
          ))}
        </div>
        <div className="h-12 bg-surface rounded-xl border border-border-subtle/40" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="h-64 bg-surface rounded-2xl border border-border-subtle/40" />
          <div className="h-64 bg-surface rounded-2xl border border-border-subtle/40" />
        </div>
      </div>
    );
  }

  // 2. Trạng thái Lỗi (Error State)
  if (error) {
    return (
      <div
        className="p-8 bg-surface rounded-2xl border border-border-subtle flex flex-col items-center justify-center text-center gap-4 my-8"
        data-testid="dashboard-error"
      >
        <div className="w-14 h-14 rounded-full bg-danger-subtle text-danger flex items-center justify-center text-2xl font-bold">
          !
        </div>
        <div className="max-w-md">
          <h3 className="text-lg font-bold text-main mb-1">Không thể tải dữ liệu Bảng điều khiển</h3>
          <p className="text-sm text-secondary">{error}</p>
        </div>
        <button
          type="button"
          onClick={handleRetry}
          className="px-5 py-2.5 bg-primary hover:bg-primary-hover text-white rounded-xl font-medium text-sm transition-all shadow-sm cursor-pointer"
          data-testid="dashboard-retry-btn"
        >
          Thử lại
        </button>
      </div>
    );
  }

  // 3. Trạng thái Thành công hoặc Dữ liệu rỗng (Empty State tích hợp sẵn trong ModernDashboardView)
  return (
    <ModernDashboardView
      onNavigate={handleNavigate}
      incomingCount={data?.kpis?.incomingCount ?? 0}
      outgoingCount={data?.kpis?.outgoingCount ?? 0}
      tasksCount={data?.kpis?.tasksCount ?? 0}
      signingCount={data?.kpis?.signingCount ?? 0}
      incomingDocuments={data?.recentIncoming ?? []}
      outgoingDocuments={data?.recentOutgoing ?? []}
      tasks={data?.tasks ?? []}
      resources={data?.resources ?? []}
      signingRequests={data?.recentSigning ?? []}
      birthdays={data?.birthdays}
    />
  );
}
