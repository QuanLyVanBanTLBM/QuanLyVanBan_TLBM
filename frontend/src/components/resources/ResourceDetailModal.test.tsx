import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResourceDetailModal } from './ResourceDetailModal';
import { ResourceItem } from '@app-types/resource';

const baseDoc: ResourceItem = {
  id: 10,
  dm_tai_lieu: 1,
  dm_tai_lieu_name: 'Thư mục Quy chế',
  loai_tai_lieu: [1],
  loai_tai_lieu_names: ['Quy chế'],
  ky_hieu: 'QC-2026',
  tieu_de: 'Quy chế văn thư lưu trữ điện tử',
  ngay_dang: '2026-01-01',
  noi_ban_hanh: 'Ban Giám Đốc',
  hieu_luc: 'CON_HIEU_LUC',
  file_dinh_kem: '/media/test.pdf',
  hien_thi: 'TAT_CA',
  nguoi_tao_name: 'Quản trị viên',
};

describe('ResourceDetailModal Component', () => {
  it('renders scheduled expiration notice and active badge when expiration date is in the future', () => {
    const futureDoc: ResourceItem = {
      ...baseDoc,
      hieu_luc: 'HET_HIEU_LUC', // Cài đặt hết hạn trước nhưng ngày ở tương lai
      ngay_het_hieu_luc: '2099-12-31',
    };

    render(
      <ResourceDetailModal
        isOpen={true}
        onClose={vi.fn()}
        item={futureDoc}
      />
    );

    // Vẫn hiển thị Còn hiệu lực kèm ngày hết hạn
    expect(screen.getByText(/Còn hiệu lực/i)).toBeInTheDocument();
    expect(screen.getAllByText(/31\/12\/2099/).length).toBeGreaterThan(0);
    // Hiển thị banner thông báo văn bản đã được lên lịch hết hiệu lực
    expect(
      screen.getByText(/đã được lên lịch hết hiệu lực vào ngày/i)
    ).toBeInTheDocument();
  });

  it('renders expired banner when expiration date has passed', () => {
    const pastDoc: ResourceItem = {
      ...baseDoc,
      hieu_luc: 'CON_HIEU_LUC',
      ngay_het_hieu_luc: '2020-01-01',
    };

    render(
      <ResourceDetailModal
        isOpen={true}
        onClose={vi.fn()}
        item={pastDoc}
      />
    );

    // Đã hết hạn tự động
    expect(screen.getByText(/Văn bản này hiện đã hết hiệu lực thi hành/i)).toBeInTheDocument();
  });
});
