# Quy trình Phân nhánh Git & Đóng góp Mã nguồn

Tài liệu này hướng dẫn 8 nhóm làm việc song song trên kho mã nguồn mà không gây xung đột.

---

## 1. Mô hình Phân nhánh (Git Branching Model)

- `main`: Nhánh sản phẩm chính thức (Production). Chỉ merge khi đã nghiệm thu hoàn tất.
- `staging`: Nhánh tích hợp và kiểm thử chung của toàn bộ dự án.
- **8 Nhánh tính năng chuyên trách:**
  1. `1_layout_home`
  2. `2_documents`
  3. `3_dossiers_documents`
  4. `4_documents_templates`
  5. `5_signing_workflow`
  6. `6_tasks`
  7. `7_meeting_rooms_birthdays_system`
  8. `8_ai_chatbox`

---

## 2. Quy trình làm việc của từng nhóm

1. **Khởi tạo và làm việc trên nhánh của nhóm:**
   ```bash
   git checkout <branch_name>
   git pull origin staging
   ```
2. **Cam kết mã nguồn (Commit):**
   - Tuân thủ quy chuẩn Conventional Commits:
     - `feat(<module>): ...` cho tính năng mới.
     - `fix(<module>): ...` cho sửa lỗi.
     - `docs(<module>): ...` cho cập nhật tài liệu.
   - Luôn kiểm tra `git status` trước khi commit, không dùng `git add .` bừa bãi.
3. **Đẩy mã nguồn và tạo Pull Request (PR):**
   - Đẩy nhánh lên remote: `git push origin <branch_name>`.
   - Tạo PR trỏ vào nhánh `staging`.
   - Điền đầy đủ thông tin theo mẫu PR Template được cấu hình sẵn.
   - Chờ DevOps/PM duyệt và kiểm thử trước khi merge vào `staging`.
