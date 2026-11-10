import { LatestTask, Paginated, TaskDetail, TaskFilters, TaskFormValues, TaskListItem } from '../types/task';
import { request } from './client';

export function listTasks(filters: TaskFilters, signal?: AbortSignal): Promise<Paginated<TaskListItem>> {
  return request<Paginated<TaskListItem>>('work/tasks/', {
    params: {
      search: filters.search?.trim(),
      status: filters.status,
      createdFrom: filters.createdFrom,
      createdTo: filters.createdTo,
      page: filters.page,
      pageSize: filters.pageSize,
    },
    signal,
  });
}

/** Chỉ đọc chi tiết, không ghi nhận "đã mở". Việc ghi nhận mở dùng openTask trong taskActions.ts. */
export function getTask(taskId: number, signal?: AbortSignal): Promise<TaskDetail> {
  return request<TaskDetail>(`work/tasks/${taskId}/`, { signal });
}

function buildTaskFormData(values: TaskFormValues, isEdit: boolean): FormData {
  const data = new FormData();
  data.append('title', values.title.trim());
  data.append('createdDate', values.createdDate);
  data.append('dueDate', values.dueDate);
  data.append('requirement', values.requirement.trim());
  if (values.hostId !== null) data.append('hostId', String(values.hostId));
  values.directorIds.forEach((id) => data.append('directorIds', String(id)));
  values.participantIds.forEach((id) => data.append('participantIds', String(id)));
  data.append('isPublic', values.isPublic ? 'true' : 'false');
  values.donViIds.forEach((id) => data.append('donViIds', String(id)));
  values.attachments.forEach((file) => data.append('attachments', file));
  if (isEdit) {
    values.removeAttachmentIds.forEach((id) => data.append('removeAttachmentIds', String(id)));
  }
  return data;
}

export function createTask(values: TaskFormValues): Promise<TaskDetail> {
  return request<TaskDetail>('work/tasks/', { method: 'POST', body: buildTaskFormData(values, false) });
}

export function updateTask(taskId: number, values: TaskFormValues): Promise<TaskDetail> {
  return request<TaskDetail>(`work/tasks/${taskId}/`, { method: 'PATCH', body: buildTaskFormData(values, true) });
}

/** Xóa hẳn công việc cùng toàn bộ file và ý kiến; không hoàn tác được. */
export function deleteTask(taskId: number): Promise<void> {
  return request<void>(`work/tasks/${taskId}/`, { method: 'DELETE' });
}

/** Các công việc mới nhất người dùng được xem, dành cho trang chủ (nhóm 1). */
export function listLatestTasks(limit = 5, signal?: AbortSignal): Promise<LatestTask[]> {
  return request<LatestTask[]>('work/tasks/latest/', { params: { limit }, signal });
}
