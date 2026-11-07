import { describe, expect, it } from 'vitest';
import { isValidEmployeePhone } from './employeeContactRules';

describe('employeeContactRules', () => {
  it.each(['0912345678', '0387654321', '0587654321', '0712345678', '0812345678'])(
    'nhận số di động 10 chữ số: %s',
    (value) => {
      expect(isValidEmployeePhone(value)).toBe(true);
    }
  );

  it.each([
    '023243423',
    '091234567',
    '09123456789',
    '+84912345678',
    '84912345678',
    '0112345678',
    '0212345678',
    '0412345678',
    '091 234 5678',
    '09123abc78',
    '',
  ])('từ chối số điện thoại không đúng 10 chữ số: %s', (value) => {
    expect(isValidEmployeePhone(value)).toBe(false);
  });
});
