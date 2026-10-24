import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SAMPLE_STREAMS } from '@lib/constants';
import { NotificationStreamType, NotificationItem, StreamData } from '@app-types/notification';
import { useTranslation } from '@i18n/translate';
import DocumentPreviewModal from '@components/dashboard/DocumentPreviewModal';
import { DocumentItem } from '@components/dashboard/ModernDashboardView';

import { apiClient } from '@lib/apiClient';

interface ApiDocumentItem {
  id?: number | string;
  code?: string;
  title?: string;
  sender?: string;
  recipient?: string;
  date?: string;
  scope?: 'NOI_BO' | 'HAN_CHE' | string;
}

interface ApiTaskItem {
  id?: number | string;
  title?: string;
  status?: string;
  statusLabel?: string;
  due?: string;
}

interface DashboardOverviewApiResponse {
  recentIncoming?: ApiDocumentItem[];
  recentOutgoing?: ApiDocumentItem[];
  tasks?: ApiTaskItem[];
}

export default function NotificationStreams() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<NotificationStreamType>('incoming');
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [streams, setStreams] = useState<StreamData[]>(SAMPLE_STREAMS);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Nạp dữ liệu thực tế từ CSDL thông qua API overview
  useEffect(() => {
    const token = localStorage.getItem('tlbm_access_token') || localStorage.getItem('tlbm_token');
    if (!token) return;

    apiClient<DashboardOverviewApiResponse>('/api/dashboard/overview/')
      .then((data) => {
        if (!data) return;
        const recentIncoming = data.recentIncoming || [];
        const recentOutgoing = data.recentOutgoing || [];
        const tasks = data.tasks || [];

        const inItems: NotificationItem[] = recentIncoming
          .filter((d: ApiDocumentItem) => d.scope !== 'HAN_CHE')
          .map((d: ApiDocumentItem) => ({
            id: `in-${d.id}`,
            code: d.code || '',
            title: d.title || '',
            senderOrDept: d.sender || 'Cơ quan ban hành',
            time: d.date || '',
            isRead: false,
            scope: (d.scope === 'HAN_CHE' ? 'HAN_CHE' : 'NOI_BO') as 'NOI_BO' | 'HAN_CHE',
          }));

        const outItems: NotificationItem[] = recentOutgoing
          .filter((d: ApiDocumentItem) => d.scope !== 'HAN_CHE')
          .map((d: ApiDocumentItem) => ({
            id: `out-${d.id}`,
            code: d.code || '',
            title: d.title || '',
            senderOrDept: d.recipient || 'Nơi nhận',
            time: d.date || '',
            isRead: false,
            scope: (d.scope === 'HAN_CHE' ? 'HAN_CHE' : 'NOI_BO') as 'NOI_BO' | 'HAN_CHE',
          }));

        const confItems: NotificationItem[] = [
          ...recentIncoming.filter((d: ApiDocumentItem) => d.scope === 'HAN_CHE'),
          ...recentOutgoing.filter((d: ApiDocumentItem) => d.scope === 'HAN_CHE'),
        ].map((d: ApiDocumentItem) => ({
          id: `conf-${d.id}`,
          code: d.code || '',
          title: d.title || '',
          senderOrDept: d.sender || d.recipient || 'Mật / Hạn chế',
          time: d.date || '',
          isRead: false,
          priority: 'confidential',
          scope: 'HAN_CHE',
        }));

        const approvalItems: NotificationItem[] = tasks
          .filter((t: ApiTaskItem) => t.status === 'pending')
          .map((t: ApiTaskItem) => ({
            id: `task-${t.id}`,
            code: `CV-${t.id}`,
            title: t.title || '',
            senderOrDept: t.statusLabel || 'Chờ duyệt',
            time: t.due || '',
            isRead: false,
          }));

        setStreams([
          {
            type: 'incoming',
            label: 'Văn Bản Đến',
            icon: 'fa-inbox',
            color: 'blue',
            unreadCount: inItems.length,
            items: inItems,
          },
          {
            type: 'outgoing',
            label: 'Văn Bản Đi',
            icon: 'fa-paper-plane',
            color: 'emerald',
            unreadCount: outItems.length,
            items: outItems,
          },
          {
            type: 'confidential',
            label: 'Mật / Hạn Chế',
            icon: 'fa-shield-halved',
            color: 'rose',
            unreadCount: confItems.length,
            items: confItems,
          },
          {
            type: 'approvals',
            label: 'Chờ Duyệt',
            icon: 'fa-signature',
            color: 'amber',
            unreadCount: approvalItems.length,
            items: approvalItems,
          },
        ]);
      })
      .catch(() => {
        // Dự phòng giữ mảng mặc định nếu chưa đăng nhập hoặc lỗi mạng
      });
  }, []);

  const handleOpenDoc = (item: NotificationItem) => {
    setIsOpen(false);
    if (activeTab === 'approvals' || item.id.startsWith('task-')) {
      navigate('/approvals');
      return;
    }
    setPreviewDoc({
      code: item.code,
      title: item.title,
      date: item.time,
      sender: item.senderOrDept,
    });
  };

  const handleMarkAllRead = () => {
    setStreams((prev) =>
      prev.map((s) => ({
        ...s,
        unreadCount: 0,
        items: s.items.map((item) => ({ ...item, isRead: true })),
      }))
    );
  };

  // Close when clicking outside (support both pointerdown and touchstart)
  useEffect(() => {
    function handleClickOutside(event: MouseEvent | TouchEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('pointerdown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    return () => {
      document.removeEventListener('pointerdown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, []);

  const totalUnread = streams.reduce((acc, s) => acc + s.unreadCount, 0);
  const currentStream = streams.find((s) => s.type === activeTab) || streams[0];

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        className="relative w-9 h-9 rounded-lg flex items-center justify-center text-text-secondary hover:text-text-main hover:bg-surface-hover transition-colors duration-fast"
        onClick={() => setIsOpen(!isOpen)}
        title="Thông báo hệ thống"
        aria-label="Thông báo"
      >
        <i className="fa-regular fa-bell text-base" />
        {totalUnread > 0 && (
          <span
            className="absolute top-1.5 right-1.5 w-2.5 h-2.5 rounded-full bg-danger ring-2 ring-header shadow-sm"
            aria-label="Có thông báo mới"
          />
        )}
      </button>

      {isOpen && (
        <div className="dropdown-animate fixed inset-x-3 top-16 sm:absolute sm:inset-x-auto sm:right-0 sm:top-full sm:mt-2 w-auto sm:w-[380px] max-h-[calc(100vh-80px)] sm:max-h-[520px] rounded-xl bg-surface-elevated border border-border-subtle shadow-2xl flex flex-col z-[10001] overflow-hidden">
            <div className="p-3.5 border-b border-subtle flex items-center justify-between bg-surface/40">
              <div>
                <span className="font-bold text-sm text-text-main">{t('notifications.title')}</span>
                <div className="text-xs text-text-muted">
                  {t('notifications.unreadCount', { count: totalUnread.toString() })}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="text-xs text-primary font-semibold hover:underline bg-transparent border-0 cursor-pointer"
                  onClick={handleMarkAllRead}
                >
                  {t('notifications.markAllRead')}
                </button>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="w-6 h-6 rounded-full bg-surface-hover border border-subtle text-text-secondary flex items-center justify-center hover:text-text-main text-xs"
                  title="Đóng bảng thông báo"
                  aria-label="Đóng"
                >
                  <i className="fa-solid fa-xmark" />
                </button>
              </div>
            </div>

            {/* Streams Tab Navigation: Đến, Đi, Mật, Chờ Duyệt (Hiển thị số lượng chi tiết từng mục) */}
            <div className="flex items-center p-1.5 bg-surface border-b border-subtle gap-1 overflow-x-auto">
              {streams.map((stream) => {
                const streamLabelKey = `notifications.${stream.type}`;
                const streamLabel = t(streamLabelKey) !== streamLabelKey ? t(streamLabelKey) : stream.label;
                const isConfidential = stream.type === 'confidential';

                return (
                  <button
                    key={stream.type}
                    type="button"
                    className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-colors duration-fast whitespace-nowrap ${
                      activeTab === stream.type
                        ? isConfidential
                          ? 'bg-danger/10 text-danger border border-danger/25 font-semibold shadow-sm'
                          : 'bg-surface-elevated text-primary font-semibold shadow-sm'
                        : isConfidential
                          ? 'text-danger/80 hover:text-danger hover:bg-danger/5'
                          : 'text-text-muted hover:text-text-main hover:bg-surface-hover'
                    }`}
                    onClick={() => setActiveTab(stream.type)}
                  >
                    <i className={`fa-solid ${stream.icon} text-xs`} />
                    <span>{streamLabel}</span>
                    {stream.unreadCount > 0 && (
                      <span
                        className={`text-[10px] min-w-[18px] h-[18px] px-1 rounded-full font-bold flex items-center justify-center leading-none ${
                          isConfidential
                            ? 'bg-danger text-white'
                            : 'bg-primary text-white'
                        }`}
                      >
                        {stream.unreadCount}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Stream Item List */}
            <div className="flex-1 overflow-y-auto divide-y divide-subtle p-1 max-h-[360px]">
              {currentStream.items.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-8 text-center text-text-muted">
                  <i
                    className={`fa-solid ${currentStream.icon} text-2xl mb-2 ${
                      activeTab === 'confidential' ? 'opacity-40 text-danger' : 'opacity-30'
                    }`}
                  />
                  <span className="text-xs font-medium">
                    {activeTab === 'approvals'
                      ? 'Không có hồ sơ trình ký chờ duyệt'
                      : activeTab === 'confidential'
                        ? (t('notifications.emptyConfidential') || 'Không có văn bản mật mới')
                        : 'Không có thông báo mới'}
                  </span>
                </div>
              ) : (
                currentStream.items.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleOpenDoc(item)}
                    className="p-3 hover:bg-surface-hover rounded-lg transition-colors duration-fast cursor-pointer flex flex-col"
                  >
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-surface border border-subtle text-text-secondary">
                        {item.code}
                      </span>
                      {(item.priority === 'confidential' || item.scope === 'HAN_CHE' || activeTab === 'confidential') && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-danger-subtle text-danger border border-danger/25 flex items-center gap-1">
                          <i className="fa-solid fa-lock text-[9px]" />
                          <span>Mật</span>
                        </span>
                      )}
                      {item.priority === 'urgent' && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-warning-subtle text-warning flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-warning inline-block" />
                          <span>Khẩn</span>
                        </span>
                      )}
                    </div>
                    <div className="font-medium text-xs text-text-main line-clamp-2 leading-relaxed">
                      {item.title}
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-text-muted mt-1.5">
                      <span>{item.senderOrDept}</span>
                      <span>{item.time}</span>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer xem thêm khi ở tab Chờ Duyệt (Trình ký) */}
            {activeTab === 'approvals' && (
              <div className="p-2.5 border-t border-subtle bg-surface/50 text-center select-none">
                <button
                  type="button"
                  onClick={() => {
                    setIsOpen(false);
                    navigate('/approvals');
                  }}
                  className="text-xs text-primary font-semibold hover:underline flex items-center justify-center gap-1.5 mx-auto cursor-pointer"
                >
                  <i className="fa-solid fa-file-signature text-xs" />
                  <span>Xem quy trình trình ký số điện tử »</span>
                </button>
              </div>
            )}
          </div>
      )}

      {/* Modal Xem Trước Văn Bản khi bấm vào thông báo */}
      {previewDoc && (
        <DocumentPreviewModal
          isOpen={!!previewDoc}
          onClose={() => setPreviewDoc(null)}
          document={previewDoc}
          docType={activeTab === 'outgoing' ? 'outgoing' : 'incoming'}
        />
      )}
    </div>
  );
}



