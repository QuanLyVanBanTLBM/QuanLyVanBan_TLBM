import React from 'react';
import { useTranslation } from '@i18n/translate';
import { Permission } from '@app-types/authorization';

interface PermissionMatrixProps {
  permissions: Permission[];
  selectedIds: Set<number>;
  onToggle: (permId: number) => void;
}

interface ModuleGroup {
  key: string;
  label: string;
  items: Permission[];
}

const ACTION_LABEL_KEYS: Record<string, string> = {
  view: 'roles.actionsColumns.view',
  add: 'roles.actionsColumns.add',
  change: 'roles.actionsColumns.change',
  delete: 'roles.actionsColumns.delete',
};
const ACTION_ORDER = ['view', 'add', 'change', 'delete'];

// Các app thuần kỹ thuật của framework, không có giá trị phân quyền nghiệp vụ thật -> ẩn khỏi ma trận
const EXCLUDED_APPS = new Set(['admin', 'contenttypes', 'sessions', 'token_blacklist']);

// Tên hiển thị tiếng Việt cho các model đã biết - model mới chưa có trong danh sách này
// sẽ tự động fallback về tên bảng viết hoa chữ đầu, không cần sửa code khi có module mới.
const MODEL_LABELS: Record<string, string> = {
  group: 'Nhóm quyền',
  permission: 'Quyền hệ thống',
  user: 'Tài khoản đăng nhập',
  staffprofile: 'Hồ sơ nhân viên',
  donvi: 'Đơn vị',
  khoikhuvuc: 'Khối / Khu vực',
  incomingdocument: 'Văn bản đến',
  outgoingdocument: 'Văn bản đi',
  meetingroom: 'Phòng họp',
};

const formatFallbackLabel = (raw: string) => raw.charAt(0).toUpperCase() + raw.slice(1).replace(/_/g, ' ');

function actionOf(codename: string): string | undefined {
  return ACTION_ORDER.find((key) => codename.startsWith(`${key}_`));
}

function groupByModule(permissions: Permission[]): ModuleGroup[] {
  const map = new Map<string, ModuleGroup>();
  for (const perm of permissions) {
    const { app_label, model } = perm.content_type;
    if (EXCLUDED_APPS.has(app_label)) continue;
    const key = `${app_label}.${model}`;
    if (!map.has(key)) {
      map.set(key, { key, label: MODEL_LABELS[model] || formatFallbackLabel(model), items: [] });
    }
    map.get(key)!.items.push(perm);
  }
  const groups = Array.from(map.values());
  for (const group of groups) {
    group.items.sort((a, b) => {
      const orderA = ACTION_ORDER.indexOf(actionOf(a.codename) || '');
      const orderB = ACTION_ORDER.indexOf(actionOf(b.codename) || '');
      if (orderA === -1 && orderB === -1) return a.name.localeCompare(b.name);
      if (orderA === -1) return 1;
      if (orderB === -1) return -1;
      return orderA - orderB;
    });
  }
  return groups.sort((a, b) => a.label.localeCompare(b.label, 'vi'));
}

export const PermissionMatrix: React.FC<PermissionMatrixProps> = ({ permissions, selectedIds, onToggle }) => {
  const { t } = useTranslation();
  const groups = groupByModule(permissions);

  const formatPermissionLabel = (perm: Permission) => {
    const action = actionOf(perm.codename);
    if (action) return t(ACTION_LABEL_KEYS[action]);
    // Quyền đặc biệt (vd Duyệt/Ký) do nhóm khác tự khai báo - dùng thẳng tên gốc
    return perm.name;
  };

  if (groups.length === 0) {
    return (
      <div className="text-center py-12 text-secondary">
        <i className="fa-solid fa-folder-open text-3xl text-muted mb-2 block" />
        {t('roles.table.empty')}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {groups.map((group, idx) => (
        <div key={group.key}>
          <h4 className="font-bold text-danger mb-2 text-sm">
            {idx + 1}. {group.label}
          </h4>
          <div className="space-y-1 pl-2">
            {group.items.map((perm) => (
              <label
                key={perm.id}
                className="flex items-center justify-between gap-3 py-1 px-2 -mx-2 text-sm text-main cursor-pointer select-none hover:bg-surface-hover rounded-lg transition-colors"
              >
                <span className="flex items-center gap-2">
                  <i className="fa-solid fa-arrow-right-long text-muted text-xs" />
                  {formatPermissionLabel(perm)}
                </span>
                <input
                  type="checkbox"
                  checked={selectedIds.has(perm.id)}
                  onChange={() => onToggle(perm.id)}
                  className="h-4 w-4 rounded border-border-subtle text-primary focus:ring-primary cursor-pointer shrink-0"
                />
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
