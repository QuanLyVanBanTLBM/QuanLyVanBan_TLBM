/** Quy tắc email và số điện thoại CBNV (chốt 04/11/2026), khớp backend `accounts/models.py` và `settings.EMPLOYEE_EMAIL_ALLOWED_DOMAINS`. */

export const EMPLOYEE_EMAIL_DOMAINS: readonly string[] = ['baolong.vn'];

// Số di động Việt Nam: đúng 10 chữ số, bắt đầu 03/05/07/08/09.
export const EMPLOYEE_PHONE_PATTERN = /^0[35789][0-9]{8}$/;

export function isCompanyEmail(value: string): boolean {
  const email = value.trim().toLowerCase();
  const at = email.lastIndexOf('@');
  if (at <= 0) return false;
  return EMPLOYEE_EMAIL_DOMAINS.includes(email.slice(at + 1));
}

export function isValidEmployeePhone(value: string): boolean {
  return EMPLOYEE_PHONE_PATTERN.test(value.trim());
}
