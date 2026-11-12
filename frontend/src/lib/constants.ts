import { NavGroup, MainModule } from '@app-types/navigation';
import { ThemeOption, ThemeMode } from '@app-types/theme';
import { StreamData } from '@app-types/notification';

// [DEVOPS AUDIT NOTE]:
// previewGradient và borderPreview dưới đây là các ô màu mẫu tĩnh (swatches)
// dùng riêng cho bộ chọn theme (ThemeSelector) để người dùng xem trước màu sắc
// trước khi áp dụng, không phải là style của UI components.
export const THEME_OPTIONS: ThemeOption[] = [
  // 1. Chế độ Tối Hiện Đại (Cyber Midnight Dark)
  {
    id: 'dark',
    name: 'Sleek Dark',
    icon: 'fa-moon',
    category: 'modern',
    categoryLabel: 'Chế độ Tối',
    description: 'Nền đen sâu thẳm #0a0d14, thẻ tối cao cấp #121824 cùng điểm nhấn Indigo hiện đại',
    previewGradient: 'linear-gradient(135deg, #0a0d14 0%, #121824 100%)',
    borderPreview: 'rgba(85, 80, 233, 0.45)',
  },
  // 2. Chế độ Sáng Hiện Đại (Clean Light)
  {
    id: 'light',
    name: 'Clean Light',
    icon: 'fa-sun',
    category: 'modern',
    categoryLabel: 'Chế độ Sáng',
    description: 'Văn phòng trang nhã, tương phản chuẩn mực, sáng sủa, thanh lịch và chuyên nghiệp',
    previewGradient: 'linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%)',
    borderPreview: 'rgba(59, 130, 246, 0.35)',
  },
];

export const LIGHT_THEMES: ThemeMode[] = ['light'];

export const DARK_THEMES: ThemeMode[] = ['dark'];

export const isLightThemeMode = (theme: ThemeMode): boolean => {
  return theme === 'light';
};

export const NAV_GROUPS: NavGroup[] = [
  {
    id: 'nhom_1',
    groupTitle: 'Bàn Làm Việc & Tổng Quan',
    teamTag: 'Nhóm 1',
    items: [
      {
        id: 'dashboard',
        label: 'Trang Chủ Dashboard',
        icon: 'fa-gauge-high',
      },
    ],
  },
  {
    id: 'nhom_2',
    groupTitle: 'Quản Lý Văn Bản',
    teamTag: 'Nhóm 2',
    items: [
      {
        id: 'documents_incoming',
        label: 'Văn Bản Đến',
        icon: 'fa-inbox',
      },
      {
        id: 'documents_outgoing',
        label: 'Văn Bản Đi',
        icon: 'fa-paper-plane',
      },
    ],
  },
  {
    id: 'nhom_3',
    groupTitle: 'Hồ Sơ & Lưu Trữ',
    teamTag: 'Nhóm 3',
    items: [
      {
        id: 'records',
        label: 'Danh Mục Hồ Sơ',
        icon: 'fa-folder-tree',
      },
      { id: 'record_types', label: 'Loại văn bản', icon: 'fa-tags' },
    ],
  },
  {
    id: 'nhom_4',
    groupTitle: 'Tài Liệu & Biểu Mẫu',
    teamTag: 'Nhóm 4',
    items: [
      {
        id: 'resources',
        label: 'Kho Tài Liệu Chung',
        icon: 'fa-file-lines',
      },
    ],
  },
  {
    id: 'nhom_5',
    groupTitle: 'Trình Ký Số',
    teamTag: 'Nhóm 5',
    items: [
      {
        id: 'approvals',
        label: 'Trình Ký',
        icon: 'fa-file-signature',
      },
    ],
  },
  {
    id: 'nhom_6',
    groupTitle: 'Giao Việc & Tiến Độ',
    teamTag: 'Nhóm 6',
    items: [
      {
        id: 'tasks',
        label: 'Quản Lý Công Việc',
        icon: 'fa-list-check',
      },
    ],
  },
  {
    id: 'nhom_7',
    groupTitle: 'Tiện Ích & Quản Trị',
    teamTag: 'Nhóm 7',
    items: [
      {
        id: 'birthdays',
        label: 'Sinh Nhật CBNV',
        icon: 'fa-cake-candles',
      },
      {
        id: 'meetings',
        label: 'Đặt Phòng Họp',
        icon: 'fa-calendar-days',
      },
      {
        id: 'organizations',
        label: 'Đơn Vị & Phòng Ban',
        icon: 'fa-sitemap',
      },
      {
        id: 'positions',
        label: 'Danh Mục Chức Vụ',
        icon: 'fa-id-badge',
      },
      {
        id: 'employees',
        label: 'Hồ Sơ Cán Bộ NV',
        icon: 'fa-users',
      },
      {
        id: 'roles',
        label: 'Phân Quyền Nhóm Quyền',
        icon: 'fa-user-shield',
      },
    ],
  },
  {
    id: 'nhom_8',
    groupTitle: 'Trợ Lý AI',
    teamTag: 'Nhóm 8',
    items: [
      {
        id: 'ai_assistant',
        label: 'AI Chat Tra Cứu',
        icon: 'fa-robot',
      },
    ],
  },
];

// ==========================================
// 6 PHÂN HỆ LỚN CHO SIDEBAR DỌC (TẦNG 1)
// Cùng danh mục các trang con cho thanh Tab ngang (Tầng 2)
// ==========================================
export const MAIN_MODULES: MainModule[] = [
  {
    id: 'dashboard',
    label: 'Trang Chủ',
    shortLabel: 'Trang Chủ',
    icon: 'fa-gauge-high',
    teamTag: 'Nhóm 1',
    defaultPage: 'dashboard',
    subItems: [
      {
        id: 'dashboard',
        label: 'Trang Chủ',
        icon: 'fa-chart-pie',
        description: 'Bàn làm việc tổng quan, thống kê số liệu năm',
      },
    ],
  },
  {
    id: 'documents',
    label: 'Quản Lý Văn Bản',
    shortLabel: 'Văn Bản',
    icon: 'fa-folder-open',
    teamTag: 'Nhóm 2',
    defaultPage: 'documents_incoming',
    subItems: [
      {
        id: 'documents_incoming',
        label: 'Văn Bản Đến',
        icon: 'fa-inbox',
        description: 'Công văn, văn bản ngoài gửi đến đơn vị',
      },
      {
        id: 'documents_outgoing',
        label: 'Văn Bản Đi',
        icon: 'fa-paper-plane',
        description: 'Văn bản phát hành nội bộ công ty',
      },
    ],
  },
  {
    id: 'records_resources',
    label: 'Hồ Sơ & Tài Liệu',
    shortLabel: 'Hồ Sơ & TL',
    icon: 'fa-box-archive',
    teamTag: 'Nhóm 3 & 4',
    defaultPage: 'records',
    subItems: [
      {
        id: 'records',
        label: 'Danh Mục Hồ Sơ',
        icon: 'fa-folder-tree',
        description: 'Quản lý hồ sơ Cấp 1 và phân loại văn bản Cấp 2',
      },
      { id: 'record_types', label: 'Loại văn bản', icon: 'fa-tags' },
      {
        id: 'resources',
        label: 'Kho Tài Liệu & Biểu Mẫu',
        icon: 'fa-file-lines',
        description: 'Biểu mẫu quy định dùng chung toàn hệ thống',
      },
    ],
  },
  {
    id: 'workflow',
    label: 'Công Việc & Ký Số',
    shortLabel: 'Giao Việc & Ký',
    icon: 'fa-list-check',
    teamTag: 'Nhóm 5 & 6',
    defaultPage: 'tasks',
    subItems: [
      {
        id: 'tasks',
        label: 'Quản Lý Công Việc',
        icon: 'fa-tasks',
        description: 'Theo dõi tiến độ, hạn xử lý và phân công',
      },
      {
        id: 'approvals',
        label: 'Trình Ký',
        icon: 'fa-file-signature',
        description: 'Sơ đồ ký số điện tử và phê duyệt văn bản',
      },
    ],
  },
  {
    id: 'system',
    label: 'Tiện Ích & Hệ Thống',
    shortLabel: 'Hệ Thống',
    icon: 'fa-building-columns',
    teamTag: 'Nhóm 7',
    defaultPage: 'birthdays',
    subItems: [
      {
        id: 'birthdays',
        label: 'Sinh Nhật CBNV',
        icon: 'fa-cake-candles',
        description: 'Lịch sinh nhật cán bộ nhân viên ngày T & T+1',
      },
      {
        id: 'meetings',
        label: 'Đặt Phòng Họp',
        icon: 'fa-calendar-days',
        description: 'Lịch hội nghị, họp trực tuyến các phòng ban',
      },
      {
        id: 'organizations',
        label: 'Đơn Vị & Phòng Ban',
        icon: 'fa-sitemap',
        description: 'Cơ cấu khối, ban và chi nhánh Bảo Long',
      },
      {
        id: 'positions',
        label: 'Danh Mục Chức Vụ',
        icon: 'fa-id-badge',
        description: 'Quản lý chức vụ, chức vị và thứ tự ưu tiên',
      },
      {
        id: 'employees',
        label: 'Hồ Sơ Cán Bộ NV',
        icon: 'fa-users',
        description: 'Danh sách và thông tin nhân sự toàn công ty',
      },
      {
        id: 'roles',
        label: 'Phân Quyền & Vai Trò',
        icon: 'fa-user-shield',
        description: 'Ma trận nhóm quyền và phân quyền người dùng',
      },
    ],
  },
  {
    id: 'ai',
    label: 'Trợ Lý AI Tra Cứu',
    shortLabel: 'Trợ Lý AI',
    icon: 'fa-robot',
    teamTag: 'Nhóm 8',
    defaultPage: 'ai_assistant',
    subItems: [
      {
        id: 'ai_assistant',
        label: 'AI Chatbox Tra Cứu',
        icon: 'fa-comments',
        description: 'Trợ lý AI thông minh hỏi đáp quy trình và văn bản',
      },
    ],
  },
];

export const SAMPLE_STREAMS: StreamData[] = [
  {
    type: 'incoming',
    label: 'Văn Bản Đến',
    icon: 'fa-inbox',
    color: 'blue',
    unreadCount: 0,
    items: [],
  },
  {
    type: 'outgoing',
    label: 'Văn Bản Đi',
    icon: 'fa-paper-plane',
    color: 'emerald',
    unreadCount: 0,
    items: [],
  },
  {
    type: 'confidential',
    label: 'Mật / Hạn Chế',
    icon: 'fa-shield-halved',
    color: 'rose',
    unreadCount: 0,
    items: [],
  },
  {
    type: 'approvals',
    label: 'Chờ Duyệt',
    icon: 'fa-signature',
    color: 'amber',
    unreadCount: 0,
    items: [],
  },
];


