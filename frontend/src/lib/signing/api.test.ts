/**
 * `danhBaCanBo`: lỗi 403 (thiếu quyền `view_list_cbnv` ở API CBNV) phải báo thật, không bị nuốt rồi thay bằng
 * một nguồn dữ liệu khác có phạm vi hẹp hơn (Issue #338).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@lib/apiClient';
import { signingApi } from './api';

function phanHoi(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
  } as Response;
}

describe('signingApi.danhBaCanBo', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('trả đúng danh sách khi /api/accounts/employees/?all=true thành công', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(phanHoi(200, [
      { id: 1, username: 'u1', ho_ten: 'Cán bộ Một', don_vi_id: null, don_vi_ten: '', chuc_vu_id: null, chuc_vu_ten: '' },
    ]));

    const ds = await signingApi.danhBaCanBo();
    expect(ds).toHaveLength(1);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it('báo lỗi 403 thật, không âm thầm thay bằng /api/accounts/staffs/', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      phanHoi(403, { detail: 'roles.messages.permissionDenied' }),
    );

    await expect(signingApi.danhBaCanBo()).rejects.toMatchObject({ status: 403 } satisfies Partial<ApiError>);
    // Không có lần gọi dự phòng nào khác được thực hiện
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it('lỗi khác 403 (ví dụ 404 do môi trường thiếu endpoint) vẫn dùng /api/accounts/staffs/ dự phòng', async () => {
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce(phanHoi(404, { detail: 'not found' }))
      .mockResolvedValueOnce(phanHoi(200, [
        { id: 2, username: 'u2', ho_ten: 'Cán bộ Hai', don_vi_id: null, don_vi_ten: '', chuc_vu_id: null, chuc_vu_ten: '' },
      ]));

    const ds = await signingApi.danhBaCanBo();
    expect(ds).toHaveLength(1);
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });
});
