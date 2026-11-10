import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import DocumentFormModal from './DocumentFormModal';
import apiClient from '@lib/apiClient';
import { resetPermissionsCache } from '@lib/permissions';

vi.mock('@lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
  apiClientBlob: vi.fn(),
  downloadBlob: vi.fn(),
}));

const mockedGet = apiClient.get as unknown as ReturnType<typeof vi.fn>;

function grantPermissions(permissions: string[]) {
  mockedGet.mockImplementation(async (url: string) => {
    if (url.includes('/auth/me/permissions/')) {
      return { is_superuser: false, permissions };
    }
    return [];
  });
}

function restrictedOption(): HTMLOptionElement {
  return screen.getByRole('option', { name: /Hạn chế/ }) as HTMLOptionElement;
}

describe('DocumentFormModal: quyền thêm văn bản hạn chế', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetPermissionsCache();
  });

  it('khóa lựa chọn phạm vi Hạn chế khi chỉ có quyền thêm văn bản', async () => {
    grantPermissions(['view_vanbanden', 'add_vanbanden']);
    render(<DocumentFormModal open={true} onClose={vi.fn()} />);

    await waitFor(() => expect(restrictedOption().disabled).toBe(true));
    expect(restrictedOption().title).toMatch(/chưa được cấp quyền thêm văn bản hạn chế/i);
    expect(screen.getByRole('option', { name: /Nội bộ/ })).not.toBeDisabled();
  });

  it('cho chọn phạm vi Hạn chế khi có add_han_che_vanbanden', async () => {
    grantPermissions(['view_vanbanden', 'add_vanbanden', 'add_han_che_vanbanden']);
    render(<DocumentFormModal open={true} onClose={vi.fn()} />);

    await waitFor(() => expect(restrictedOption().disabled).toBe(false));
  });

  it('quyền của văn bản đến không mở lựa chọn Hạn chế cho văn bản đi', async () => {
    grantPermissions(['view_vanbandi', 'add_vanbandi', 'add_han_che_vanbanden']);
    render(<DocumentFormModal open={true} onClose={vi.fn()} defaultLoai="DI" />);

    await waitFor(() => expect(mockedGet).toHaveBeenCalled());
    await waitFor(() => expect(restrictedOption().disabled).toBe(true));
  });

  it('cho chọn phạm vi Hạn chế của văn bản đi khi có add_han_che_vanbandi', async () => {
    grantPermissions(['view_vanbandi', 'add_vanbandi', 'add_han_che_vanbandi']);
    render(<DocumentFormModal open={true} onClose={vi.fn()} defaultLoai="DI" />);

    await waitFor(() => expect(restrictedOption().disabled).toBe(false));
  });
});
