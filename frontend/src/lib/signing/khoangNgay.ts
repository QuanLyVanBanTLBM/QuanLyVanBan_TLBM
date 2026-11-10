/** Kiểm tra khoảng ngày lọc (YYYY-MM-DD) của phân hệ Trình ký: Từ ngày không được lớn hơn Đến ngày. */
export function khoangNgaySai(tu?: string, den?: string): boolean {
  return !!tu && !!den && tu > den;
}
