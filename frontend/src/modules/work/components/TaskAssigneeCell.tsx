import React from 'react';
import { useTranslation } from '@i18n/translate';
import { Employee } from '../types/employee';
import { employeeMeta } from './EmployeeSelect';

/** Ô "Người thực hiện" trong bảng danh sách: người chủ trì và các cán bộ tham gia. */

interface TaskAssigneeCellProps {
  host: Employee | null;
  participants: Employee[];
}

/** Dòng phụ "(Chức vụ - Phòng ban)", bỏ qua khi không có dữ liệu để không hiện ngoặc rỗng. */
function MetaLine({ person }: { person: Employee }) {
  const meta = employeeMeta(person);
  if (!meta) return null;
  return <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}> ({meta})</span>;
}

export default function TaskAssigneeCell({ host, participants }: TaskAssigneeCellProps) {
  const { t } = useTranslation();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.84rem', lineHeight: 1.5 }}>
      <div>
        <span style={{ color: 'var(--text-secondary)' }}>{t('work.assigneeCell.host')} </span>
        <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{host ? host.fullName : '—'}</span>
        {host && <MetaLine person={host} />}
      </div>
      {participants.length > 0 && (
        <>
          <div style={{ color: 'var(--text-secondary)' }}>{t('work.assigneeCell.participants')}</div>
          {participants.map((person) => (
            <div key={person.id} style={{ color: 'var(--text-main)' }}>
              - {person.fullName}
              <MetaLine person={person} />
            </div>
          ))}
        </>
      )}
    </div>
  );
}
