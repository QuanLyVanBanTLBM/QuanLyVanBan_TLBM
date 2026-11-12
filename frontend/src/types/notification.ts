export type NotificationStreamType = 'incoming' | 'outgoing' | 'confidential' | 'approvals' | 'meetings';

export interface NotificationItem {
  id: string;
  code: string; // Số ký hiệu văn bản
  title: string;
  senderOrDept: string;
  time: string;
  isRead: boolean;
  priority?: 'normal' | 'urgent' | 'confidential';
  scope?: 'NOI_BO' | 'HAN_CHE';
}

export interface StreamData {
  type: NotificationStreamType;
  label: string;
  icon: string;
  color: string;
  unreadCount: number;
  items: NotificationItem[];
}
