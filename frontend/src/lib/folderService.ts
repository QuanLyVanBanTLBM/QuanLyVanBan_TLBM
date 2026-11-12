/**
 * Service giao tiếp với API Thư mục nhiều cấp (Nested / Hierarchical Folders).
 * Cung cấp đầy đủ các thao tác: Cây thư mục, Breadcrumb, CRUD, Di chuyển và Quản lý File.
 */

import apiClient from './apiClient';
import { FolderItem, FolderFileItem, FolderBreadcrumb } from '../types/resource';

export const folderService = {
  /**
   * Lấy toàn bộ cây thư mục đệ quy (hỗ trợ hiển thị Tree View đa cấp).
   * @param rootId Tùy chọn lọc cây từ một nút gốc cụ thể.
   */
  getTree: async (rootId?: number): Promise<FolderItem[]> => {
    const url = rootId ? `/api/folders/tree/?root_id=${rootId}` : '/api/folders/tree/';
    return apiClient<FolderItem[]>(url);
  },

  /**
   * Lấy danh sách thư mục (có thể lọc theo parent).
   */
  getAll: async (parentId?: number | null | 'root'): Promise<FolderItem[]> => {
    let url = '/api/folders/';
    if (parentId !== undefined) {
      url += `?parent=${parentId === null || parentId === 'root' ? 'root' : parentId}`;
    }
    return apiClient<FolderItem[]>(url);
  },

  /**
   * Lấy thông tin chi tiết một thư mục.
   */
  getById: async (id: number): Promise<FolderItem> => {
    return apiClient<FolderItem>(`/api/folders/${id}/`);
  },

  /**
   * Lấy breadcrumb từ gốc đến thư mục hiện tại.
   */
  getBreadcrumb: async (id: number): Promise<FolderBreadcrumb[]> => {
    return apiClient<FolderBreadcrumb[]>(`/api/folders/${id}/breadcrumb/`);
  },

  /**
   * Tạo thư mục mới (gốc hoặc con thông qua parent_id).
   */
  create: async (data: {
    name: string;
    parent_id?: number | null;
    order?: number;
    description?: string;
  }): Promise<FolderItem> => {
    return apiClient.post<FolderItem>('/api/folders/', data);
  },

  /**
   * Tạo thư mục con trực tiếp bên trong thư mục cha.
   */
  createChild: async (
    parentId: number,
    data: { name: string; order?: number; description?: string }
  ): Promise<FolderItem> => {
    return apiClient.post<FolderItem>(`/api/folders/${parentId}/children/`, data);
  },

  /**
   * Cập nhật thông tin thư mục (đổi tên, sửa mô tả, thứ tự sắp xếp).
   */
  update: async (id: number, data: Partial<FolderItem>): Promise<FolderItem> => {
    return apiClient.patch<FolderItem>(`/api/folders/${id}/`, data);
  },

  /**
   * Di chuyển thư mục đến vị trí cha mới (targetParentId = null để chuyển về gốc).
   * Backend tự động kiểm tra chống vòng lặp (circular reference).
   */
  move: async (id: number, targetParentId: number | null): Promise<FolderItem> => {
    return apiClient.patch<FolderItem>(`/api/folders/${id}/move/`, {
      target_parent_id: targetParentId,
    });
  },

  /**
   * Xóa thư mục (cascade xóa toàn bộ con cháu và tệp liên quan).
   */
  delete: async (id: number): Promise<void> => {
    return apiClient.delete<void>(`/api/folders/${id}/`);
  },

  /**
   * Lấy danh sách tệp/tài liệu bên trong một thư mục.
   */
  getFiles: async (folderId: number): Promise<FolderFileItem[]> => {
    return apiClient<FolderFileItem[]>(`/api/folders/${folderId}/files/`);
  },

  /**
   * Thêm metadata tệp vào thư mục.
   */
  addFile: async (
    folderId: number,
    data: {
      file_name: string;
      file_size?: number;
      file_type?: string;
      file_path?: string;
      description?: string;
    }
  ): Promise<FolderFileItem> => {
    return apiClient.post<FolderFileItem>(`/api/folders/${folderId}/files/`, data);
  },

  /**
   * Xóa tệp khỏi thư mục.
   */
  deleteFile: async (fileId: number): Promise<void> => {
    return apiClient.delete<void>(`/api/folder-files/${fileId}/`);
  },

  /**
   * Quét thư mục máy tính cục bộ (Local Directory) và đồng bộ vào hệ thống.
   * @param folderPath Đường dẫn thư mục (tùy chọn, để trống sẽ dùng thư mục 'Folder' mặc định của dự án)
   * @param parentId ID thư mục cha nếu muốn đồng bộ vào bên trong thư mục khác
   */
  scanLocal: async (data?: {
    folder_path?: string;
    parent_id?: number | null;
  }): Promise<{
    status: string;
    message: string;
    base_folder: string;
    root_folder_id: number;
    folder_count: number;
    file_count: number;
  }> => {
    return apiClient.post('/api/folders/scan-local/', data || {});
  },

  /**
   * Lấy URL để tải hoặc xem tệp (hỗ trợ cả tệp local và tệp media server).
   */
  getDownloadUrl: (fileId: number, inline: boolean = false): string => {
    return `/api/folder-files/${fileId}/download/${inline ? '?inline=1' : ''}`;
  },
};

export default folderService;
