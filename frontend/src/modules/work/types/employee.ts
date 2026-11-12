// Cán bộ nhân viên lấy từ Custom User Model accounts.Employee.
// position = tên chức vụ (accounts_position.name); department = tên phòng ban (organizations.DonVi.ten).
// Cả hai có thể rỗng nếu record seed cũ thiếu FK → chỗ hiển thị phải xử lý chuỗi rỗng.

export interface Employee {
  id: number;
  fullName: string;
  position: string;
  department: string;
  username?: string;
}

export interface CurrentUser extends Employee {
  isAdmin: boolean;
}
