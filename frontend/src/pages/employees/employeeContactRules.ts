/** Quy tắc số điện thoại CBNV, khớp backend `accounts/models.py`. Email nhận mọi tên miền; backend giới hạn khi có cấu hình. */

// Số di động Việt Nam: đúng 10 chữ số, bắt đầu 03/05/07/08/09.
export const EMPLOYEE_PHONE_PATTERN = /^0[35789][0-9]{8}$/;

export function isValidEmployeePhone(value: string): boolean {
  return EMPLOYEE_PHONE_PATTERN.test(value.trim());
}
