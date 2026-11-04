import { SupportedLanguage } from '@i18n/translate';

const ROLE_TRANSLATIONS: Record<SupportedLanguage, Record<string, string>> = {
  vi: {
    admin: 'Quản trị viên',
    administrator: 'Quản trị viên',
    'quản trị viên': 'Quản trị viên',
    'quản trị hệ thống': 'Quản trị hệ thống',
    'quản trị viên tối cao': 'Quản trị viên tối cao',
    'quản trị viên (admin)': 'Quản trị viên (Admin)',
    'cán bộ chuyên viên': 'Cán bộ chuyên viên',
    'cán bộ xử lý văn bản': 'Cán bộ xử lý văn bản',
    'chuyên viên': 'Chuyên viên',
    'trưởng phòng': 'Trưởng phòng',
    'phó phòng': 'Phó phòng',
    'văn thư': 'Văn thư',
    'ban giám đốc': 'Ban Giám đốc',
    'tổng giám đốc': 'Tổng Giám đốc',
    'phó tổng giám đốc điều hành': 'Phó Tổng Giám đốc điều hành',
    'kiểm toán viên': 'Kiểm toán viên',
    'trợ lý tgđ': 'Trợ lý TGĐ',
    'giám đốc': 'Giám đốc',
    'phó giám đốc': 'Phó Giám đốc',
    'nhân viên': 'Nhân viên',
    staff: 'Cán bộ nhân viên',
  },
  en: {
    admin: 'Administrator',
    administrator: 'Administrator',
    'quản trị viên': 'Administrator',
    'quản trị hệ thống': 'System Administrator',
    'quản trị viên tối cao': 'Super Administrator',
    'quản trị viên (admin)': 'System Administrator',
    'cán bộ chuyên viên': 'Specialist / Officer',
    'cán bộ xử lý văn bản': 'Document Processing Officer',
    'chuyên viên': 'Specialist',
    'trưởng phòng': 'Department Head',
    'phó phòng': 'Deputy Department Head',
    'văn thư': 'Archivist / Document Clerk',
    'ban giám đốc': 'Board of Directors',
    'tổng giám đốc': 'General Director',
    'phó tổng giám đốc điều hành': 'Deputy General Director',
    'kiểm toán viên': 'Auditor',
    'trợ lý tgđ': 'CEO Assistant',
    'giám đốc': 'Director',
    'phó giám đốc': 'Deputy Director',
    'nhân viên': 'Staff',
    staff: 'Staff',
  },
};

/**
 * Dịch chức danh / vai trò hệ thống dựa trên ngôn ngữ hiện tại ('vi' | 'en')
 */
export function formatRoleTitle(role?: string, lang: SupportedLanguage = 'vi'): string {
  if (!role) return '';
  const normalized = role.trim().toLowerCase();
  const dict = ROLE_TRANSLATIONS[lang] || ROLE_TRANSLATIONS.vi;
  return dict[normalized] || role;
}

/**
 * Dịch tên hiển thị người dùng (ví dụ: Quản trị hệ thống -> System Administrator khi lang === 'en')
 */
export function formatUserName(name?: string, lang: SupportedLanguage = 'vi'): string {
  if (!name) return '';
  const normalized = name.trim().toLowerCase();
  if (lang === 'en') {
    if (normalized === 'quản trị hệ thống' || normalized === 'admin') {
      return 'System Administrator';
    }
  } else {
    if (normalized === 'admin') {
      return 'Quản trị hệ thống';
    }
  }
  return name;
}

// Tên nhóm quyền chuẩn (auth_group, không đổi tên được) theo ngôn ngữ; nhóm tự tạo giữ nguyên tên.
const GROUP_NAME_EN: Record<string, string> = {
  'văn thư': 'Document Clerk',
  'chuyên viên': 'Specialist',
  'trưởng phòng': 'Department Head',
  'ban giám đốc': 'Board of Directors',
  'quản trị hệ thống': 'System Administrator',
  'trợ lý ban giám đốc': 'Board Assistant',
  'kiểm toán': 'Audit',
};

export function formatGroupName(name?: string, lang: SupportedLanguage = 'vi'): string {
  if (!name) return '';
  if (lang !== 'en') return name;
  return GROUP_NAME_EN[name.trim().toLowerCase()] || name;
}
