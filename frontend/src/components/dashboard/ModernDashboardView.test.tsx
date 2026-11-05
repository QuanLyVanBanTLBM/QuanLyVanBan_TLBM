import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { setLanguage } from '@i18n/translate';
import ModernDashboardView, { DocumentItem, TaskItem } from './ModernDashboardView';

describe('ModernDashboardView Component (Zero Mock Data)', () => {
  it('renders clean empty states by default with zero mock data', () => {
    render(
      <MemoryRouter>
        <ModernDashboardView />
      </MemoryRouter>
    );

    // 4 KPI cards show 0 by default (Incoming, Outgoing, Tasks, Signing)
    expect(screen.getAllByText('0')).toHaveLength(4);
    expect(screen.getByText('Chưa có phát sinh trong ngày')).toBeInTheDocument();
    expect(screen.getByText('Chưa có phát hành hôm nay')).toBeInTheDocument();
    expect(screen.getByText('Không có nhiệm vụ cần xử lý')).toBeInTheDocument();
    expect(screen.getByText('Không có hồ sơ chờ ký')).toBeInTheDocument();

    // Tables show empty states
    expect(screen.getByText('Chưa có dữ liệu văn bản đến')).toBeInTheDocument();
    expect(screen.getByText('Chưa có dữ liệu văn bản đi')).toBeInTheDocument();
    expect(screen.getByText('Chưa có nhiệm vụ nào cần xử lý')).toBeInTheDocument();
    expect(screen.getByText('Chưa có dữ liệu tài liệu & biểu mẫu')).toBeInTheDocument();
    expect(screen.getByText('Không có phiếu trình ký nào cần xử lý')).toBeInTheDocument();

    // No mock text
    expect(screen.queryByText(/Mock Filter/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Xin chào, Châu Tuấn Kiệt/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Nguyễn Văn Hiếu/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Phòng Họp A201/i)).not.toBeInTheDocument();
    expect(screen.queryByText('128/QĐ-BGDĐT')).not.toBeInTheDocument();
    expect(screen.queryByText('210/TB-BL')).not.toBeInTheDocument();
  });

  it('renders simplified quick search input bar', () => {
    render(
      <MemoryRouter>
        <ModernDashboardView />
      </MemoryRouter>
    );

    expect(screen.getByPlaceholderText(/Nhập số ký hiệu/i)).toBeInTheDocument();
  });

  it('renders custom values and documents when provided', () => {
    const mockIncoming: DocumentItem[] = [
      { code: '99/CV-ITC', title: 'Công văn thử nghiệm', date: '17/09/2026' },
    ];
    const mockTasks: TaskItem[] = [
      { id: '1', title: 'Nhiệm vụ kiểm thử', due: '18/09/2026', status: 'processing', statusLabel: 'Đang làm', variant: 'warning' },
    ];

    render(
      <MemoryRouter>
        <ModernDashboardView
          incomingCount={10}
          outgoingCount={5}
          tasksCount={1}
          incomingDocuments={mockIncoming}
          tasks={mockTasks}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('99/CV-ITC')).toBeInTheDocument();
    expect(screen.getByText('Công văn thử nghiệm')).toBeInTheDocument();
    expect(screen.getByText('Nhiệm vụ kiểm thử')).toBeInTheDocument();
  });

  it('filters incoming documents when search term is entered', () => {
    const mockIncoming: DocumentItem[] = [
      { code: '10/CV-ITC', title: 'Công văn A', date: '17/09/2026' },
      { code: '20/CV-ITC', title: 'Báo cáo B', date: '17/09/2026' },
    ];

    render(
      <MemoryRouter>
        <ModernDashboardView incomingDocuments={mockIncoming} />
      </MemoryRouter>
    );

    expect(screen.getByText('10/CV-ITC')).toBeInTheDocument();
    expect(screen.getByText('20/CV-ITC')).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText(/Nhập số ký hiệu/i);
    fireEvent.change(searchInput, { target: { value: 'Báo cáo' } });

    expect(screen.getByText('20/CV-ITC')).toBeInTheDocument();
    expect(screen.queryByText('10/CV-ITC')).not.toBeInTheDocument();
  });

  it('triggers navigation when clicking action buttons', () => {
    const mockNavigate = vi.fn();

    render(
      <MemoryRouter>
        <ModernDashboardView onNavigate={mockNavigate} />
      </MemoryRouter>
    );

    const bookBtn = screen.getByRole('button', { name: /Đặt phòng họp/i });
    fireEvent.click(bookBtn);

    expect(mockNavigate).toHaveBeenCalledWith('meetings');
  });

  it('opens TaskDetailModal when clicking on a task item', () => {
    const mockTasks: TaskItem[] = [
      { id: '1', title: 'Hoàn thiện báo cáo quý III', due: '15/10/2026', status: 'processing', statusLabel: 'Đang xử lý', variant: 'info' },
    ];

    render(
      <MemoryRouter>
        <ModernDashboardView tasks={mockTasks} />
      </MemoryRouter>
    );

    const taskRow = screen.getByText('Hoàn thiện báo cáo quý III');
    fireEvent.click(taskRow);
    expect(screen.getByText('Chi Tiết Nhiệm Vụ Được Giao')).toBeInTheDocument();
    expect(screen.getByText('Mã công việc: #CV-01 · Phân hệ Quản lý công việc (Nhóm 6)')).toBeInTheDocument();
  });

  it('renders compact search bar into top-subnav-slot and syncs search term', () => {
    // Setup portal slot in DOM
    const slot = document.createElement('div');
    slot.id = 'top-subnav-slot';
    document.body.appendChild(slot);

    const mockIncoming: DocumentItem[] = [
      { code: '10/CV-ITC', title: 'Công văn A', date: '17/09/2026' },
      { code: '20/CV-ITC', title: 'Báo cáo B', date: '17/09/2026' },
    ];

    render(
      <MemoryRouter>
        <ModernDashboardView incomingDocuments={mockIncoming} />
      </MemoryRouter>
    );

    const compactInput = screen.getByPlaceholderText(/Tìm nhanh văn bản, công việc/i);
    expect(compactInput).toBeInTheDocument();
    expect(slot).toContainElement(compactInput);

    // Typing in compact search bar filters the documents
    fireEvent.change(compactInput, { target: { value: 'Báo cáo' } });
    expect(screen.getByText('20/CV-ITC')).toBeInTheDocument();
    expect(screen.queryByText('10/CV-ITC')).not.toBeInTheDocument();

    // Clear button appears and clicking it clears search
    const clearBtn = screen.getByTitle('Xóa tìm kiếm nhanh');
    fireEvent.click(clearBtn);
    expect(screen.getByText('10/CV-ITC')).toBeInTheDocument();
    expect(screen.getByText('20/CV-ITC')).toBeInTheDocument();

    // Clean up DOM slot
    document.body.removeChild(slot);
  });
  it('translates domain task status in the row and detail modal when language changes', () => {
    render(
      <MemoryRouter>
        <ModernDashboardView tasks={[{
          id: 'status-task', title: 'Status translation', due: '18/10/2026',
          status: 'pending', workStatus: 'CHO_DUYET', statusLabel: 'Chờ duyệt', variant: 'warning',
        }]} />
      </MemoryRouter>
    );
    try {
      act(() => setLanguage('en'));
      fireEvent.click(screen.getByRole('button', { name: 'Pending Approval' }));
      expect(screen.getByText('Pending approval')).toBeInTheDocument();
      expect(screen.queryByText('Chờ duyệt')).not.toBeInTheDocument();
      fireEvent.click(screen.getByText('Status translation'));
      expect(screen.getAllByText('Pending approval').length).toBeGreaterThan(1);
      act(() => setLanguage('vi'));
      expect(screen.getAllByText('Chờ duyệt').length).toBeGreaterThan(1);
    } finally {
      act(() => setLanguage('vi'));
    }
  });

  it('renders signing requests table and handles navigation', () => {
    const mockNavigate = vi.fn();
    const mockSigning = [
      {
        id: '1',
        ma_trinh_ky: '15/TTr-VP',
        tieu_de: 'Tờ trình phê duyệt mua sắm máy quét tài liệu',
        nguoi_trinh: 'Lê Thanh Hậu',
        ngay_gui: '23/10/2026',
        trang_thai: 'CHO_KY',
        nhan_trang_thai: 'Ký ngay',
        can_toi_ky: true,
      },
      {
        id: '2',
        ma_trinh_ky: '16/TTr-VP',
        tieu_de: 'Tờ trình phê duyệt dự toán',
        nguoi_trinh: 'Trần Văn B',
        ngay_gui: '24/10/2026',
        trang_thai: 'CHO_KY',
        nhan_trang_thai: 'Đang chờ ký',
        can_toi_ky: false,
      },
    ];

    render(
      <MemoryRouter>
        <ModernDashboardView
          onNavigate={mockNavigate}
          signingCount={2}
          signingRequests={mockSigning}
        />
      </MemoryRouter>
    );

    expect(screen.getByText('15/TTr-VP')).toBeInTheDocument();
    expect(screen.getByText('Tờ trình phê duyệt mua sắm máy quét tài liệu')).toBeInTheDocument();
    expect(screen.getByText('Lê Thanh Hậu')).toBeInTheDocument();
    expect(screen.getByText('Đang chờ ký')).toBeInTheDocument();

    const signBtn = screen.getByRole('button', { name: /ký ngay/i });
    fireEvent.click(signBtn);

    const viewAllBtn = screen.getByText('Xem tất cả hồ sơ trình ký');
    fireEvent.click(viewAllBtn);
    expect(mockNavigate).toHaveBeenCalledWith('approvals');
  });

  it('correctly maps signing request and current attempt statuses', () => {
    const multiStatusSigning = [
      { id: '1', ma_trinh_ky: 'TK-01', tieu_de: 'Phieu 1', trang_thai: 'CHO_KY' },
      { id: '2', ma_trinh_ky: 'TK-02', tieu_de: 'Phieu 2', trang_thai: 'DANG_XU_LY' },
      { id: '3', ma_trinh_ky: 'TK-03', tieu_de: 'Phieu 3', trang_thai: 'DA_KY' },
      { id: '4', ma_trinh_ky: 'TK-04', tieu_de: 'Phieu 4', trang_thai: 'HOAN_THANH' },
      { id: '5', ma_trinh_ky: 'TK-05', tieu_de: 'Phieu 5', trang_thai: 'TU_CHOI' },
    ];

    const { rerender } = render(
      <MemoryRouter>
        <ModernDashboardView signingRequests={multiStatusSigning} />
      </MemoryRouter>
    );

    expect(screen.getAllByText('Đang chờ ký').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Đang xử lý').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Đã ký').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Hoàn tất duyệt nội bộ').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Đã từ chối').length).toBeGreaterThan(0);

    rerender(
      <MemoryRouter>
        <ModernDashboardView signingRequests={[
          { id: '8', ma_trinh_ky: 'TK-08', tieu_de: 'Phiếu trả sửa', trang_thai: 'CHO_KY', trang_thai_luot: 'YEU_CAU_SUA' },
        ]} />
      </MemoryRouter>
    );
    expect(screen.getByText('Chờ người trình sửa')).toBeInTheDocument();

    // Rerender with cancelled and draft
    const secondaryStatusSigning = [
      { id: '6', ma_trinh_ky: 'TK-06', tieu_de: 'Phieu 6', trang_thai: 'HUY' },
      { id: '7', ma_trinh_ky: 'TK-07', tieu_de: 'Phieu 7', trang_thai: 'NHAP' },
    ];

    rerender(
      <MemoryRouter>
        <ModernDashboardView signingRequests={secondaryStatusSigning} />
      </MemoryRouter>
    );

    expect(screen.getAllByText('Đã hủy').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Nháp').length).toBeGreaterThan(0);
  });
});


