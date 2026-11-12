import React, { useState } from 'react';
import ConfirmDialog from '../components/ConfirmDialog';
import DateInput, { todayIso } from '../components/DateInput';
import EmployeeMultiSelect from '../components/EmployeeMultiSelect';
import EmployeeSelect from '../components/EmployeeSelect';
import FilePicker from '../components/FilePicker';
import TaskStatusBadge from '../components/TaskStatusBadge';
import WorkAlert from '../components/WorkAlert';
import WorkModal from '../components/WorkModal';
import { TaskStatus } from '../types/task';

/** Trang xem thử component nền của module Công việc (chỉ dùng khi phát triển). */

const ALL_STATUSES: TaskStatus[] = [
  'CHO_XU_LY',
  'DANG_XU_LY',
  'CHO_DUYET',
  'HOAN_THANH',
  'CHUA_HOAN_THANH',
  'QUA_HAN',
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: '16px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)' }}>{title}</h3>
      {children}
    </section>
  );
}

export default function WorkComponentsPreviewPage() {
  const [date, setDate] = useState(todayIso());
  const [dueDate, setDueDate] = useState('');
  const [hostId, setHostId] = useState<number | null>(null);
  const [memberIds, setMemberIds] = useState<number[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '900px' }}>
      <Section title="TaskStatusBadge">
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {ALL_STATUSES.map((status) => (
            <TaskStatusBadge key={status} status={status} />
          ))}
        </div>
      </Section>

      <Section title="WorkAlert">
        <WorkAlert variant="success" message="Đã lưu công việc." />
        <WorkAlert
          variant="danger"
          title="Không xóa được file"
          message="Công việc đã quá hạn, không thể xóa file bằng chứng cuối cùng. Hãy nộp file mới trước rồi xóa file cũ sau."
          onClose={() => undefined}
        />
        <WorkAlert variant="warning" message="Công việc sắp tới hạn xử lý." />
        <WorkAlert variant="info" message="Ý kiến đã gửi không thể sửa hoặc xóa." />
      </Section>

      <Section title="DateInput">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>Ngày tạo</div>
            <DateInput value={date} onChange={setDate} min={todayIso()} />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Ngày xử lý (không nhỏ hơn ngày tạo)
            </div>
            <DateInput value={dueDate} onChange={setDueDate} min={date} invalid={!dueDate} />
          </div>
          <div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>Khóa</div>
            <DateInput value={date} onChange={setDate} disabled />
          </div>
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          Giá trị gửi lên API: {date || '(trống)'} - {dueDate || '(trống)'}
        </div>
      </Section>

      <Section title="EmployeeSelect và EmployeeMultiSelect">
        <EmployeeSelect value={hostId} onChange={setHostId} placeholder="Chọn người chủ trì" />
        <EmployeeMultiSelect
          value={memberIds}
          onChange={setMemberIds}
          excludeIds={hostId ? [hostId] : []}
          placeholder="Chọn cán bộ tham gia"
        />
      </Section>

      <Section title="FilePicker">
        <FilePicker files={files} onChange={setFiles} label="Tệp đính kèm" />
      </Section>

      <Section title="WorkModal và ConfirmDialog">
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button type="button" onClick={() => setModalOpen(true)} style={{ padding: '8px 14px' }}>
            Mở WorkModal
          </button>
          <button type="button" onClick={() => setConfirmOpen(true)} style={{ padding: '8px 14px' }}>
            Mở ConfirmDialog
          </button>
        </div>
      </Section>

      <WorkModal
        open={modalOpen}
        title="Cập nhật thông tin công việc"
        subtitle="Thử bố cục modal và ô ngày nằm trong modal"
        onClose={() => setModalOpen(false)}
        footer={
          <>
            <button type="button" onClick={() => setModalOpen(false)} style={{ padding: '8px 14px' }}>
              Hủy bỏ
            </button>
            <button type="button" onClick={() => setModalOpen(false)} style={{ padding: '8px 14px' }}>
              Lưu công việc
            </button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <DateInput value={dueDate} onChange={setDueDate} min={todayIso()} />
          <EmployeeSelect value={hostId} onChange={setHostId} />
          <FilePicker files={files} onChange={setFiles} />
        </div>
      </WorkModal>

      <ConfirmDialog
        open={confirmOpen}
        danger
        loading={confirmLoading}
        title="Xóa công việc"
        message="Bạn có chắc muốn xóa công việc này? Toàn bộ file và ý kiến kèm theo sẽ mất, thao tác này không hoàn tác được."
        confirmLabel="Xóa công việc"
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmLoading(true);
          window.setTimeout(() => {
            setConfirmLoading(false);
            setConfirmOpen(false);
          }, 1200);
        }}
      />
    </div>
  );
}
