import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResourceFormModal } from './ResourceFormModal';
import { ResourceItem, ResourceCategory, ResourceType } from '@app-types/resource';

const mockCategories: ResourceCategory[] = [
  { id: 1, stt_uu_tien: 1, ten_tai_lieu: 'Thư mục 1' },
];

const mockTypes: ResourceType[] = [
  { id: 1, dm_tai_lieu: 1, ten_loai: 'Loại 1', is_public: true },
];

describe('ResourceFormModal Component', () => {
  it('renders default Active badge and optional expiration date input in Add Mode', () => {
    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        categories={mockCategories}
        types={mockTypes}
      />
    );

    // Không hiển thị 4 nút chọn trạng thái khi thêm mới
    expect(screen.queryByRole('button', { name: /^Còn hiệu lực$/i })).not.toBeInTheDocument();
    // Hiển thị badge Còn hiệu lực mặc định
    expect(screen.getByText(/Còn hiệu lực \(Mặc định khi tạo mới\)/i)).toBeInTheDocument();
    // Hiển thị nhãn Hẹn ngày tự động hết hiệu lực (Tùy chọn)
    expect(screen.getByText(/Hẹn ngày tự động hết hiệu lực \(Tùy chọn\)/i)).toBeInTheDocument();
    // Hiển thị gợi ý tự động hết hiệu lực
    expect(screen.getByText(/tự động chuyển sang Hết hiệu lực khi tới ngày/i)).toBeInTheDocument();
    // Ô chọn ngày hết hiệu lực có min attribute để không cho chọn ngày trước ngày tạo
    const expDateInput = document.getElementById('field-ngay_het_hieu_luc') as HTMLInputElement;
    expect(expDateInput).toBeInTheDocument();
    expect(expDateInput.min).toBeTruthy();
  });

  it('renders status selector buttons in Edit Mode', () => {
    const editItem: ResourceItem = {
      id: 5,
      dm_tai_lieu: 1,
      loai_tai_lieu: [1],
      tieu_de: 'Tài liệu đang sửa',
      ngay_dang: '2026-01-01',
      hieu_luc: 'CON_HIEU_LUC',
      file_dinh_kem: '/media/test.pdf',
      hien_thi: 'TAT_CA',
    };

    render(
      <ResourceFormModal
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
        initialData={editItem}
        categories={mockCategories}
        types={mockTypes}
      />
    );

    // Ở chế độ chỉnh sửa, hiển thị 4 nút chọn trạng thái
    expect(screen.getByRole('button', { name: /^Còn hiệu lực$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Còn hiệu lực 1 phần$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Hết hiệu lực$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Hết hiệu lực và thay thế$/i })).toBeInTheDocument();
  });
});
