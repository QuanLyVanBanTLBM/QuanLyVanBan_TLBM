import { describe, it, expect } from 'vitest';
import { computeEffectiveStatus, getTodayLocalDateString } from './resourceValidity';

describe('computeEffectiveStatus', () => {
  const mockToday = '2026-10-24';

  it('keeps document active if expiration date is in the future', () => {
    // Trường hợp người dùng góp ý: đặt ngày hết hạn là 31/10/2026
    const res = computeEffectiveStatus('HET_HIEU_LUC', '2026-10-31', '', mockToday);
    expect(res.status).toBe('CON_HIEU_LUC');
    expect(res.isExpired).toBe(false);
    expect(res.isScheduled).toBe(true);
    expect(res.expirationDate).toBe('2026-10-31');
  });

  it('keeps partial validity active if expiration date is in the future', () => {
    const res = computeEffectiveStatus('CON_HIEU_LUC_1_PHAN', '2026-11-15', '', mockToday);
    expect(res.status).toBe('CON_HIEU_LUC_1_PHAN');
    expect(res.isExpired).toBe(false);
    expect(res.isScheduled).toBe(true);
  });

  it('marks document as expired if expiration date has passed', () => {
    const res = computeEffectiveStatus('CON_HIEU_LUC', '2026-10-20', '', mockToday);
    expect(res.status).toBe('HET_HIEU_LUC');
    expect(res.isExpired).toBe(true);
    expect(res.isScheduled).toBe(false);
  });

  it('marks document as expired if expiration date is today', () => {
    const res = computeEffectiveStatus('CON_HIEU_LUC', '2026-10-24', '', mockToday);
    expect(res.status).toBe('HET_HIEU_LUC');
    expect(res.isExpired).toBe(true);
    expect(res.isScheduled).toBe(false);
  });

  it('marks document as HET_VA_THAY_THE if expired and replacement link exists', () => {
    const res = computeEffectiveStatus(
      'HET_VA_THAY_THE',
      '2026-10-01',
      'https://example.com/doc/new',
      mockToday
    );
    expect(res.status).toBe('HET_VA_THAY_THE');
    expect(res.isExpired).toBe(true);
    expect(res.isScheduled).toBe(false);
  });

  it('handles documents with no expiration date correctly', () => {
    const activeRes = computeEffectiveStatus('CON_HIEU_LUC', null, null, mockToday);
    expect(activeRes.status).toBe('CON_HIEU_LUC');
    expect(activeRes.isExpired).toBe(false);
    expect(activeRes.isScheduled).toBe(false);

    const expiredRes = computeEffectiveStatus('HET_HIEU_LUC', '', '', mockToday);
    expect(expiredRes.status).toBe('HET_HIEU_LUC');
    expect(expiredRes.isExpired).toBe(true);
    expect(expiredRes.isScheduled).toBe(false);
  });

  it('returns valid local date string for getTodayLocalDateString', () => {
    const today = getTodayLocalDateString();
    expect(today).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
