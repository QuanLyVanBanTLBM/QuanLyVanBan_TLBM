import { Permission } from '@app-types/authorization';
import { t } from '@i18n/translate';

const MODULE_KEYS: Record<string, string> = {
  'Đơn vị, phòng ban': 'organizations',
  'Chức vụ': 'positions',
  'Loại tài liệu biểu mẫu': 'templateTypes',
  'CBNV': 'employees',
  'Văn bản đến': 'incomingDocuments',
  'Văn bản đi': 'outgoingDocuments',
  'Hồ sơ': 'records',
  'Tài liệu, biểu mẫu': 'templates',
  'Trình ký': 'signing',
  'Công việc': 'tasks',
  'Phòng họp (danh mục)': 'meetingRooms',
  'Đặt phòng họp': 'meetingBookings',
  'Sinh nhật': 'birthdays',
  'Chatbox AI': 'aiAssistant',
  'Phân quyền': 'authorization',
};

export function getModuleLabel(moduleName: string): string {
  const moduleKey = MODULE_KEYS[moduleName];
  if (!moduleKey) return moduleName;
  const key = `roles.permissionModules.${moduleKey}`;
  const translated = t(key);
  return translated === key ? moduleName : translated;
}

export function getPermissionLabel(permission: Permission): string {
  const key = `roles.permissionNames.${permission.codename}`;
  const translated = t(key);
  return translated === key ? permission.name : translated;
}
