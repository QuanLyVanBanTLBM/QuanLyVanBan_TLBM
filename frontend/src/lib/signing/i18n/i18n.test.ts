/**
 * Từ điển trình ký: các key dùng chung phải có ở cả vi/en (`chung.loiTai` từng thiếu nên giao diện hiện '—').
 */
import { describe, expect, it } from 'vitest';
import { dich } from './index';

describe('từ điển trình ký: nhóm chung', () => {
  it.each(['loiTai', 'loiMayChu', 'hetPhien', 'khongTimThay', 'quaNhieuYeuCau'])('có chung.%s ở vi và en', (khoa) => {
    for (const lang of ['vi', 'en'] as const) {
      const noi_dung = dich(lang, `chung.${khoa}`);
      expect(noi_dung).not.toBe('—');
      expect(noi_dung.length).toBeGreaterThan(0);
    }
    expect(dich('vi', `chung.${khoa}`)).not.toBe(dich('en', `chung.${khoa}`));
  });
});
