import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from './DashboardPage';
import * as apiClientModule from '@lib/apiClient';

vi.mock('@lib/apiClient', async () => {
  const actual = await vi.importActual<typeof apiClientModule>('@lib/apiClient');
  return {
    ...actual,
    apiClient: vi.fn(),
  };
});

const mockedApiClient = vi.mocked(apiClientModule.apiClient);

describe('DashboardPage Component (Issue #10 Real Data)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton while fetching dashboard data', () => {
    mockedApiClient.mockReturnValue(new Promise(() => {})); // Never resolves during this test

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(screen.getByTestId('dashboard-loading')).toBeInTheDocument();
  });

  it('renders error state when API call fails and allows retry', async () => {
    mockedApiClient.mockRejectedValueOnce(new Error('Network disconnected'));

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('dashboard-error')).toBeInTheDocument();
    });

    expect(
      screen.getByText('Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.')
    ).toBeInTheDocument();

    const retryBtn = screen.getByTestId('dashboard-retry-btn');
    expect(retryBtn).toBeInTheDocument();

    // Setup success for retry
    mockedApiClient.mockResolvedValueOnce({
      kpis: { incomingCount: 10, outgoingCount: 5, tasksCount: 3 },
      recentIncoming: [],
      recentOutgoing: [],
      tasks: [],
      birthdays: [],
    });

    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.queryByTestId('dashboard-error')).not.toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
    });
  });

  it('renders real data returned from backend API', async () => {
    mockedApiClient.mockResolvedValueOnce({
      kpis: {
        incomingCount: 25,
        outgoingCount: 14,
        tasksCount: 7,
      },
      recentIncoming: [
        { id: 1, code: 'VB-001/UBND', title: 'Thông báo triển khai dự án', date: '19/09/2026' },
      ],
      recentOutgoing: [
        { id: 2, code: 'VBD-002/ITC', title: 'Công văn phúc đáp', date: '19/09/2026' },
      ],
      tasks: [],
      birthdays: [
        {
          id: 101,
          name: 'Nguyễn Văn Minh',
          birthdate: '19/09 (Hôm nay)',
          position: 'Chuyên viên CNTT',
          department: 'Văn phòng số hóa',
          isToday: true,
        },
      ],
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('25')).toBeInTheDocument();
      expect(screen.getByText('14')).toBeInTheDocument();
      expect(screen.getByText('7')).toBeInTheDocument();
    });

    expect(screen.getByText('VB-001/UBND')).toBeInTheDocument();
    expect(screen.getByText('Thông báo triển khai dự án')).toBeInTheDocument();
    expect(screen.getByText('VBD-002/ITC')).toBeInTheDocument();
    expect(screen.getByText('Công văn phúc đáp')).toBeInTheDocument();
    expect(screen.getAllByText('Nguyễn Văn Minh')[0]).toBeInTheDocument();
  });

  it('renders clean empty state when backend returns zero data', async () => {
    mockedApiClient.mockResolvedValueOnce({
      kpis: {
        incomingCount: 0,
        outgoingCount: 0,
        tasksCount: 0,
        signingCount: 0,
      },
      recentIncoming: [],
      recentOutgoing: [],
      tasks: [],
      recentSigning: [],
      birthdays: [],
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('0')).toHaveLength(4);
    });

    expect(screen.getByText('Chưa có phát sinh trong ngày')).toBeInTheDocument();
    expect(screen.getByText('Không có hồ sơ chờ ký')).toBeInTheDocument();
  });

  it('triggers onNavigate callback when meeting room button is clicked', async () => {
    mockedApiClient.mockResolvedValueOnce({
      kpis: { incomingCount: 0, outgoingCount: 0, tasksCount: 0 },
      recentIncoming: [],
      recentOutgoing: [],
      tasks: [],
      birthdays: [],
    });

    const handleNavigate = vi.fn();
    render(
      <MemoryRouter>
        <DashboardPage onNavigate={handleNavigate} />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Đặt phòng họp/i })).toBeInTheDocument();
    });

    const bookingBtn = screen.getByRole('button', { name: /Đặt phòng họp/i });
    fireEvent.click(bookingBtn);

    expect(handleNavigate).toHaveBeenCalledWith('meetings');
  });
});
