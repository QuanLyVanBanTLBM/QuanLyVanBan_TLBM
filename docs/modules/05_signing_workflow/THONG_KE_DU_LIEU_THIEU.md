# THỐNG KÊ DỮ LIỆU CÒN THIẾU — PHÂN HỆ TRÌNH KÝ (NHÓM 5)

> Đối chiếu **file CSDL chung** `csdl_qlvbtl_schema_final.sql` (mục 9, 14 bảng `signing_*`)
> với **plan của nhóm** [`signing-backend-plan.md`](signing-backend-plan.md) (mục 3 – 8).
> Mục đích: để nhóm trưởng (Lê Thanh Hậu) và DA (Tô Thanh Tân) chốt bổ sung vào file CSDL chính thức.
>
> Nguồn chuẩn: workbook đề bài (`ITC - Django - QLVB&TL.xlsx`, dòng Nhóm 5) không liệt kê trường —
> chỉ ghi *"Các bạn chọn các trường rồi báo thầy duyệt"*. Vì vậy **plan là nguồn chuẩn duy nhất** cho CSDL Nhóm 5.
>
> Ký hiệu: ❌ thiếu hẳn · ⚠️ có nhưng lệch plan · ℹ️ lệch tên, cùng ý nghĩa

---

## A. Thiếu cột so với plan (ảnh hưởng trực tiếp nghiệp vụ)

### A1. `signing_process_step_signer` — người ký cấu hình sẵn (plan 5.2)
| Cột theo plan | Ý nghĩa | File SQL |
|---|---|:-:|
| `position_id` | Chọn người ký theo **chức vụ** (không chỉ đích danh) | ❌ |
| `signer_role` (`INITIAL` / `PRIMARY`) | Phân biệt **ký nháy** và **ký chính** | ❌ |
| `is_blocking` | Ký nháy xong mới mở ký chính (gating trong cấp) | ❌ |
| `sort_order` | Thứ tự người ký trong cấp | ❌ |

### A2. `signing_request_step_signer` — người ký của từng lượt trình (plan 3.2, 3.5, 5.2)
| Cột theo plan | Ý nghĩa | File SQL |
|---|---|:-:|
| `position_id` | Snapshot chức vụ | ❌ |
| `signer_role`, `is_blocking` | Ký nháy / ký chính + gating | ❌ |
| `delegated_from_user_id`, `delegation_reason`, `delegated_at` | **Chuyển quyền ký khẩn cấp** | ❌ |
| `page_number`, `coord_x`, `coord_y`, `box_width`, `box_height` | **Tọa độ chỗ ký** trên PDF | ❌ |
| `current_signature_id` | Chữ ký hiện hành của slot (cho phép thu hồi & ký lại) | ❌ |
| Snapshot tên hiển thị / chức vụ | Giữ lịch sử khi cơ cấu tổ chức đổi | ❌ |

### A3. `signing_signature` — chữ ký số (plan 3.3, 3.5, 5.2)
| Cột theo plan | Ý nghĩa | File SQL |
|---|---|:-:|
| `signing_attempt_id` | Chữ ký thuộc lượt trình nào | ❌ |
| `sign_note` | **Ký kèm ghi chú bảo lưu** (lỗi nhỏ, không chặn luồng) | ❌ |
| `is_late`, `late_duration_seconds` | **Ký trễ hạn** vẫn được, gắn cờ | ❌ |
| `verified_at` | Thời điểm xác minh | ❌ |
| `key_fingerprint` | Dấu vân tay khóa lúc ký | ❌ (chỉ có FK `khoa_ky`) |

### A4. `signing_audit_log` — nhật ký (plan 5.2)
| Cột theo plan | File SQL |
|---|:-:|
| `attempt_id` | ❌ |
| `entity_type`, `entity_id` | ❌ |
| `from_status`, `to_status` | ❌ |
| `metadata_json` | ❌ |
| (`reason` ≈ `chi_tiet`, `occurred_at` ≈ `created_at`) | ℹ️ |

### A5. `signing_notification` — thông báo (plan 5.2, 9.1)
| Cột theo plan | Ý nghĩa | File SQL |
|---|---|:-:|
| `scheduled_at` | Hẹn giờ gửi — cần cho **nhắc trước hạn 24 giờ** | ❌ |
| `entity_type`, `entity_id` | Thông báo về đối tượng nào | ❌ |
| (Cho giao diện) nội dung, đã đọc/chưa đọc | Chuông thông báo trong hệ thống — **plan cũng chưa có** | ❌ |

### A6. `signing_request`
| Cột theo plan | File SQL |
|---|:-:|
| `document_version` | ❌ (chỉ có ở `signing_attempt`) |

### A7. Ảnh chữ ký cá nhân (plan 3.4, 7.4)
- Plan: ảnh chữ ký PNG nền trong suốt lưu trong **Profile** người dùng.
- File SQL: `accounts_employee` (Nhóm 7) **không có cột ảnh chữ ký** ❌.

### A8. Khóa ký — proof-of-possession (plan 3.4, 7.5)
- Plan: đăng ký khóa qua **challenge** rồi mới kích hoạt.
- File SQL: không có chỗ lưu challenge (nonce, hạn dùng) ❌ — có thể dùng cache nếu nhóm chốt vậy.

---

## B. Có nhưng lệch plan (cần chốt theo bên nào)

| # | Bảng / cột | Plan | File SQL |
|---|---|---|---|
| B1 | `signing_request.trang_thai` | `DRAFT, IN_PROGRESS, COMPLETED, REJECTED, CANCELLED` — **quá hạn không phải trạng thái** | Có thêm `QUA_HAN` ⚠️ |
| B2 | `signing_attempt.trang_thai`, `expired_at` | Không có trạng thái quá hạn, không có `expired_at` | Có `QUA_HAN` và `expired_at` ⚠️ |
| B3 | `signing_request_step.trang_thai` | Enum riêng `LOCKED, PENDING, COMPLETED, BLOCKED` — **không dùng chung với signer** | Dùng chung `signing_step_status` với signer; không có `LOCKED` (chưa tới lượt) ⚠️ |
| B4 | `signing_request_step_signer.trang_thai` | `PENDING, SIGNED, REJECTED, CHANGE_REQUESTED`; thu hồi là sự kiện audit, không phải trạng thái | Có `THU_HOI`, `BO_QUA` ⚠️ |
| B5 | `signing_signature.buoc_ky` | **Không** UNIQUE (ký lại sau thu hồi tạo dòng mới) + con trỏ chữ ký hiện hành | UNIQUE → không ký lại được sau thu hồi ⚠️ |
| B6 | `signing_key.trang_thai` mặc định | `PENDING` (chỉ `ACTIVE` sau khi verify challenge) | Mặc định `HOAT_DONG` ⚠️ |
| B7 | Khóa `ACTIVE` duy nhất | Mỗi người **1 khóa active, không phân biệt thuật toán** | Unique theo (người, **thuật toán**) ⚠️ |
| B8 | `signing_process_step_signer.bat_buoc` | Không cần (mọi người ký đều bắt buộc); nếu giữ thì DB phải ép luôn `true` | Có cột, không ép ⚠️ |
| B9 | Chức vụ / đơn vị | Gắn ở **người ký** (`position_id`) | Gắn ở **cấp ký** (`chuc_vu_id`, `don_vi_id` của step) ⚠️ |
| B10 | Quy ước cột người tạo/cập nhật (plan 5.1) | `create_by, created_at, update_by, update_at` thống nhất | Lẫn lộn `nguoi_tao`, `create_by`, `created_by`, `updated_by`, `updated_at` ℹ️ |
| B11 | Tên trạng thái quy trình | `DRAFT, ACTIVE, INACTIVE` | `DRAFT, HOAT_DONG, NGUNG` ℹ️ |
| B12 | Tên cột cấp ký | `cap_so, ten_cap, mo_ta` | `cap_ky, ten_cap_ky, thu_tu, ghi_chu` (vừa `cap_ky` vừa `thu_tu`) ℹ️ |
| B13 | Cột chữ không bắt buộc (skill `django-models` của nhóm) | `blank=True, default=""` — tránh NULL | `TEXT` cho phép NULL (`mo_ta`, `ghi_chu`, `ly_do_*`...) ℹ️ |
| B14 | Quy trình đang có yêu cầu chạy (plan 3.1) | Không sửa trực tiếp — clone phiên bản mới | Không có cột/ràng buộc thể hiện ⚠️ |
| B15 | Người tạo sửa danh sách người ký (plan 3.1) | **Không được** — người ký lấy đúng cấu hình quy trình | (nghiệp vụ, không thuộc schema) |

---

## C. Phân quyền (plan mục 8)

| Quyền theo plan | File SQL |
|---|:-:|
| `view_signing` | ✔ (`view_trinhky`) |
| `create_signing_request` | ✔ (`add_trinhky`) |
| `sign_signing_request` | ✔ (`sign_trinhky`) |
| `manage_signing_process` (tạo/kích hoạt/clone quy trình) | ❌ |
| `submit_signing_request` | ❌ |
| `delegate_signing_request` (chuyển quyền ký) | ❌ |
| `cancel_signing_request` | ❌ |
| `view_signing_audit` | ❌ |

---

## D. Nghiệp vụ plan chưa định nghĩa rõ (cần nhóm trưởng chốt)

1. **Thread `RELEASED`** — file có trạng thái `OPEN / RELEASED / RESOLVED` nhưng plan không nói `RELEASED` dùng khi nào.
   Theo plan 6.1: lượt trình đã yêu cầu sửa **không bao giờ quay lại ký tiếp**; chỉ có hai đường:
   thống nhất sửa → `RESOLVED` → tạo lượt trình mới; hoặc người tạo/admin **hủy** hồ sơ.
2. **Kích thước ảnh chữ ký** `pixel x pixel` — plan ghi `[CHƯA CHỐT]`.
3. **Khôi phục khóa đa thiết bị** — plan ghi `[CHƯA CHỐT]`.

---

## E. Phụ thuộc nhóm khác (chưa có code trong repo)

| Bảng | Nhóm | Nhóm 5 cần để |
|---|---|---|
| `accounts_employee` (và đặt làm `AUTH_USER_MODEL`) | 7 | Người tạo / người ký / người nhận thông báo |
| `accounts_position`, `organizations_donvi` | 7 | Chọn người ký theo chức vụ, lọc theo phòng ban |
| `documents_vanbanden/di/mat` (cột `file_dinh_kem`) | 2 | Văn bản cần trình ký và **file để khóa SHA-256** |

---

## F. Dữ liệu mẫu
- File SQL **không có dòng dữ liệu nào** cho 14 bảng `signing_*` (0 câu `INSERT`).
- Cần: quy trình mẫu (kèm cấp ký, người ký), dữ liệu demo cho trình bày.
