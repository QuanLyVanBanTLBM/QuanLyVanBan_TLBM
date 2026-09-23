import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OrganizationsPage from './OrganizationsPage';
import { apiClient } from '@lib/apiClient';

describe('OrganizationsPage Component (Module 7.3 - Nhóm 7)', () => {
  const mockRegions = [
    {
      id: 1,
      ten: 'KHU VỰC MIỀN NAM',
      thu_tu_hien_thi: 1,
      don_vi_count: 2,
      created_at: '2026-09-23T00:00:00Z',
      updated_at: '2026-09-23T00:00:00Z',
    },
    {
      id: 2,
      ten: 'KHU VỰC MIỀN BẮC',
      thu_tu_hien_thi: 2,
      don_vi_count: 0,
      created_at: '2026-09-23T00:00:00Z',
      updated_at: '2026-09-23T00:00:00Z',
    },
  ];

  const mockUnits = {
    count: 2,
    next: null,
    previous: null,
    results: [
      {
        id: 101,
        khoi_id: 1,
        khoi_ten: 'KHU VỰC MIỀN NAM',
        stt_uu_tien: 1,
        ten: 'Bảo Long Sài Gòn',
        dia_chi: '123 Nguyễn Thị Minh Khai, Q.1',
        dien_thoai: '0901234567',
        email: 'saigon@baolong.vn',
        is_public: true,
        ghi_chu: 'Trụ sở chính',
        created_at: '2026-09-23T00:00:00Z',
        updated_at: '2026-09-23T00:00:00Z',
      },
      {
        id: 102,
        khoi_id: 1,
        khoi_ten: 'KHU VỰC MIỀN NAM',
        stt_uu_tien: 2,
        ten: 'Bảo Long Chợ Lớn',
        dia_chi: '456 Hồng Bàng, Q.5',
        dien_thoai: '0909876543',
        email: 'cholon@baolong.vn',
        is_public: false,
        ghi_chu: 'Nội bộ',
        created_at: '2026-09-23T00:00:00Z',
        updated_at: '2026-09-23T00:00:00Z',
      },
    ],
  };

  beforeEach(() => {
    vi.restoreAllMocks();

    vi.spyOn(apiClient, 'get').mockImplementation((url: string) => {
      if (url.includes('/api/organizations/regions/')) {
        return Promise.resolve(mockRegions);
      }
      if (url.includes('/api/organizations/units/')) {
        return Promise.resolve(mockUnits);
      }
      return Promise.resolve([]);
    });
  });

  it('renders page header and tabs properly', async () => {
    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );

    expect(screen.getByText('Cơ cấu Tổ chức & Đơn vị')).toBeInTheDocument();
    expect(screen.getByText('Đơn vị / Phòng ban (Cấp 2)')).toBeInTheDocument();
    expect(screen.getByText('Khối / Khu vực (Cấp 1)')).toBeInTheDocument();
  });

  it('loads and renders units list in table', async () => {
    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Bảo Long Sài Gòn')).toBeInTheDocument();
      expect(screen.getByText('Bảo Long Chợ Lớn')).toBeInTheDocument();
    });

    // Check status badges
    expect(screen.getAllByText('Công khai').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Nội bộ (Ẩn)').length).toBeGreaterThanOrEqual(1);
  });

  it('switches to Regions tab and displays regions list', async () => {
    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );

    const regionsTabBtn = screen.getByText('Khối / Khu vực (Cấp 1)');
    fireEvent.click(regionsTabBtn);

    await waitFor(() => {
      expect(screen.getByText('KHU VỰC MIỀN NAM')).toBeInTheDocument();
      expect(screen.getByText('KHU VỰC MIỀN BẮC')).toBeInTheDocument();
    });
  });

  it('opens Add Unit modal when button is clicked', async () => {
    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );

    const addUnitBtn = screen.getByText('Thêm Đơn vị / Phòng ban');
    fireEvent.click(addUnitBtn);

    await waitFor(() => {
      expect(screen.getByText('Thêm Đơn vị / Phòng ban', { selector: 'h2' })).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Ví dụ: Phòng Hành chính Tổng hợp')).toBeInTheDocument();
    });
  });

  it('opens Add Region modal when button is clicked in regions tab', async () => {
    render(
      <MemoryRouter>
        <OrganizationsPage />
      </MemoryRouter>
    );

    const regionsTabBtn = screen.getByText('Khối / Khu vực (Cấp 1)');
    fireEvent.click(regionsTabBtn);

    const addRegionBtn = screen.getByText('Thêm Khối / Khu vực');
    fireEvent.click(addRegionBtn);

    await waitFor(() => {
      expect(screen.getByText('Thêm Khối / Khu vực', { selector: 'h2' })).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Ví dụ: KHU VỰC MIỀN NAM')).toBeInTheDocument();
    });
  });
});
