import { Employee } from './employee';

export type TaskStatus =
  | 'CHO_XU_LY'
  | 'DANG_XU_LY'
  | 'CHO_DUYET'
  | 'HOAN_THANH'
  | 'CHUA_HOAN_THANH'
  | 'QUA_HAN';

/** Nhãn dự phòng khi chưa có dữ liệu API; bình thường dùng statusLabel do API trả về. */
export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  CHO_XU_LY: 'Chờ xử lý',
  DANG_XU_LY: 'Đang xử lý',
  CHO_DUYET: 'Chờ duyệt',
  HOAN_THANH: 'Hoàn thành',
  CHUA_HOAN_THANH: 'Chưa hoàn thành',
  QUA_HAN: 'Quá hạn',
};

/** Công việc hết hạn khi chưa nộp bằng chứng thì bị khóa: không sửa, không nộp, không ghi ý kiến. */
export const FROZEN_STATUSES: TaskStatus[] = ['CHUA_HOAN_THANH', 'QUA_HAN'];

export type ParticipantRole = 'NGUOI_TAO' | 'CHU_TRI' | 'CHI_DAO' | 'THAM_GIA';

export type AttachmentKind = 'GIAO_VIEC' | 'BANG_CHUNG';

export interface Attachment {
  id: number;
  kind: AttachmentKind;
  fileName: string;
  size: number;
  uploadedBy: Employee;
  uploadedAt: string;
  /** File bằng chứng luôn thuộc một ý kiến; file giao việc thì null. */
  commentId: number | null;
  downloadUrl: string;
  canDelete: boolean;
  /** Người nộp chưa xóa được file này thì đây là lý do kèm cách xử lý; ngược lại là null. */
  deleteBlockedReason: string | null;
}

export interface TaskComment {
  id: number;
  content: string;
  author: Employee;
  createdAt: string;
  /** File kết quả gửi kèm ý kiến (chính là bằng chứng hoàn thành). */
  attachments: Attachment[];
}

export interface TaskPermissions {
  canEdit: boolean;
  canDelete: boolean;
  canApprove: boolean;
  canUnapprove: boolean;
  /** Được đính kèm file kết quả khi ghi ý kiến (chủ trì, cán bộ tham gia). */
  canSubmitEvidence?: boolean;
  canComment?: boolean;
}

export interface TaskListItem {
  id: number;
  title: string;
  requirement: string;
  createdDate: string;
  dueDate: string;
  status: TaskStatus;
  statusLabel: string;
  isPublic: boolean;
  creator: Employee;
  host: Employee | null;
  directors: Employee[];
  participants: Employee[];
  myRoles: ParticipantRole[];
  permissions: TaskPermissions;
}

/** Loại văn bản của nhóm 2 mà công việc phát sinh từ đó (văn bản mật đã bỏ — issue #83). */
export type DocumentKind = 'vanbanden' | 'vanbandi';

export interface TaskDetail extends TaskListItem {
  firstOpenedAt: string | null;
  firstOpenedBy: Employee | null;
  firstEvidenceAt: string | null;
  approvedAt: string | null;
  approvedBy: Employee | null;
  attachments: Attachment[];
  evidences: Attachment[];
  commentCount: number;
  /** Id các phòng/ban được gắn (organizations_donvi.id). */
  donViIds: number[];
  documentType: DocumentKind | null;
  documentId: number | null;
}

export interface LatestTask {
  id: number;
  title: string;
  createdDate: string;
  dueDate: string;
  status: TaskStatus;
  statusLabel: string;
}

export interface Paginated<T> {
  count: number;
  page: number;
  pageSize: number;
  totalPages: number;
  results: T[];
}

export interface TaskFilters {
  search?: string;
  status?: TaskStatus | '';
  createdFrom?: string;
  createdTo?: string;
  page?: number;
  pageSize?: number;
}

/** Dữ liệu gửi lên khi thêm hoặc sửa công việc. */
export interface TaskFormValues {
  title: string;
  createdDate: string;
  dueDate: string;
  requirement: string;
  hostId: number | null;
  directorIds: number[];
  participantIds: number[];
  isPublic: boolean;
  donViIds: number[];
  attachments: File[];
  removeAttachmentIds: number[];
}
