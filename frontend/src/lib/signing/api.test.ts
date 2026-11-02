/**
 * `danhBaCanBo`: lỗi 403 (thiếu quyền `view_list_cbnv` ở API CBNV) phải báo thật, không bị nuốt rồi thay bằng
 * một nguồn dữ liệu khác có phạm vi hẹp hơn (Issue #338).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@lib/apiClient';
import { giayChoThuLai, signingApi, thoiDiemThuLai } from './api';

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

describe('signingApi.nguoiKyCoQuyen', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('trả danh sách id tài khoản có quyền ký từ API signing', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(phanHoi(200, { ids: [3, 5] }));

    await expect(signingApi.nguoiKyCoQuyen()).resolves.toEqual([3, 5]);
    expect(String((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0])).toContain('/api/v1/signing/nguoi-ky-co-quyen/');
  });
});

describe('thoiDiemThuLai / giayChoThuLai (HTTP 429)', () => {
  const loi429 = (fields?: Record<string, unknown>) => new ApiError(429, { code: 'x', detail: 'x', fields });

  it('đọc thời điểm thử lại từ fields.thu_lai_sau và tính số giây còn lại', () => {
    const bay_gio = Date.parse('2026-11-02T10:00:00Z');
    const err = loi429({ thu_lai_sau: ['2026-11-02T10:02:00Z'] });
    expect(thoiDiemThuLai(err)?.toISOString()).toBe('2026-11-02T10:02:00.000Z');
    expect(giayChoThuLai(err, bay_gio)).toBe(120);
  });

  it('trả 0 khi thời điểm đã qua, thiếu hoặc sai định dạng', () => {
    const bay_gio = Date.parse('2026-11-02T10:00:00Z');
    expect(giayChoThuLai(loi429({ thu_lai_sau: ['2026-11-02T09:00:00Z'] }), bay_gio)).toBe(0);
    expect(giayChoThuLai(loi429(), bay_gio)).toBe(0);
    expect(thoiDiemThuLai(loi429({ thu_lai_sau: ['khong-phai-ngay'] }))).toBeNull();
  });

  it('bỏ qua phản hồi không phải 429', () => {
    const err = new ApiError(400, { code: 'x', detail: 'x', fields: { thu_lai_sau: ['2099-01-01T00:00:00Z'] } });
    expect(thoiDiemThuLai(err)).toBeNull();
    expect(thoiDiemThuLai(new Error('x'))).toBeNull();
  });
});
