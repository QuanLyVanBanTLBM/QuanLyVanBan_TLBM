-- =====================================================================
-- HỆ THỐNG QUẢN LÝ VĂN BẢN VÀ TÀI LIỆU (QLVB&TL) — PostgreSQL DDL
-- Sinh tự động & đồng bộ từ đặc tả: CSDL QLVB&TL.md
-- Quy mô: 54 bảng vật lý | 22 kiểu ENUM | 66 quyền thao tác | 5 nhóm quyền chuẩn | 178 lượt phân quyền
-- =====================================================================
-- GHI CHÚ VỀ CÁC QUYẾT ĐỊNH THIẾT KẾ & ĐỒNG BỘ KIẾN TRÚC:
--
-- 1) [CẬP NHẬT] Cơ cấu tổ chức dùng 2 BẢNG RIÊNG theo đặc tả mới nhất
--    (tab "Đvị, phòngban"): organizations_khoi (Khối/Khu vực - cấp 1) và
--    organizations_donvi (Đơn vị/phòng ban - cấp 2, FK khoi_id -> Khối).
--    Không dùng self-reference — mọi FK nghiệp vụ (don_vi_nhan,
--    accounts_employee.don_vi_id...) chỉ trỏ tới organizations_donvi,
--    tránh trường hợp trỏ nhầm vào một hàng Khối như thiết kế tự tham
--    chiếu cũ có thể gặp phải.
-- 2) Mục 14 "accounts_employee" là bản đặc tả cuối cùng, dùng làm bảng
--    người dùng chính (thay auth_user mặc định của Django, vì có sẵn
--    username/password) — mọi FK "ForeignKey (auth_user)" trong tài
--    liệu được trỏ về accounts_employee(id).
-- 3) "Văn bản liên quan" ở signing_request và task (Công việc) tham
--    chiếu đa hình tới 1-trong-3 bảng văn bản -> dùng cặp cột
--    (document_type, document_id) thay vì FK cứng (generic relation
--    kiểu Django ContentType), có CHECK ràng buộc giá trị hợp lệ.
-- 4) Cột "kyhieu" trùng lặp với "so_hieu" ở documents_vanbandi /
--    documents_vanbanmat (tài liệu gốc tự ghi chú "trùng với 7") ->
--    bỏ, chỉ giữ so_hieu.
-- 5) Thống nhất ENUM: Đúng 22 kiểu ENUM chuẩn. Hợp nhất hieu_luc_status
--    ('CON_HIEU_LUC', 'HET_HIEU_LUC', 'HET_VA_THAY_THE') dùng chung cho
--    cả 4 bảng văn bản và chi tiết tài liệu; xóa bỏ hieu_luc_status_v2.
-- 6) [Tô Thanh Tân] Hệ thống phân quyền RBAC độc lập, kế thừa quy ước và tên bảng
--    chuẩn của Django Auth (auth_group, auth_permission, auth_group_permissions),
--    mở rộng cột module_ten phục vụ trực tiếp giao diện phân nhóm quyền, không phụ
--    thuộc cứng vào bảng nội bộ django_content_type để đảm bảo tính độc lập DDL.
--    Cột content_type_id để NULL để chạy DDL trực tiếp trên PostgreSQL;
--    Seed 66 quyền chi tiết, 5 nhóm quyền chuẩn và 178 lượt mapping idempotent.
-- 7) [Tô Thanh Tân] accounts_employee bổ sung is_active (khóa tài khoản nhân viên nghỉ
--    việc theo chuẩn Django User), is_staff, is_superuser; thống nhất mô hình
--    Custom User Model hoặc Profile 1-1 không bị dư thừa dữ liệu.
-- 8) [Lê Thanh Hậu — Issue #25] Bảo toàn bằng chứng ký số điện tử:
--    - FK signing_attempt -> request, signing_signature, signing_manifest đổi sang
--      ON DELETE RESTRICT.
--    - Trigger chặn xóa cứng attempt đã kích hoạt, chữ ký số và manifest đã chốt.
--    - Kiến trúc Zero-Knowledge: Backend TUYỆT ĐỐI KHÔNG lưu encrypted_private_key.
-- 9) [Phan Tạ Hữu Đức] Bổ sung quyền approve_congviec (kiểm tra 3 lớp độc lập)
--    tách biệt với change_congviec; approved_at/approved_by đóng vai trò audit log.
-- 10) [Trần Vũ Giang Anh] Quyền use_aiassistant có ranh giới an ninh chặt chẽ:
--     chỉ cấp quyền UI, tầng ứng dụng / RAG bắt buộc kiểm tra quyền xem (view_*)
--     và ACL trước khi cung cấp ngữ cảnh cho mô hình ngôn ngữ lớn (LLM).
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS public;

SET search_path TO public;

BEGIN;

-- ---------------------------------------------------------------------
-- 0. HÀM DÙNG CHUNG: tự cập nhật updated_at (tương đương auto_now=True)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 0.1 ENUM TYPES
-- ---------------------------------------------------------------------
-- Hiệu lực văn bản / tài liệu: thống nhất 1 ENUM duy nhất dùng chung cho cả Văn bản và Tài liệu lưu trữ
CREATE TYPE hieu_luc_status       AS ENUM ('CON_HIEU_LUC', 'HET_HIEU_LUC', 'HET_VA_THAY_THE');
-- [REMOVED] hoso_status ENUM — đã xóa theo yêu cầu Nhóm 3 (Thịnh Trương): cột trang_thai chưa được duyệt.
CREATE TYPE chitiettailieu_hienthi AS ENUM ('TAT_CA','NOI_BO_PHONG_BAN');

CREATE TYPE signing_process_status AS ENUM ('DRAFT','HOAT_DONG','NGUNG');

CREATE TYPE signing_scope          AS ENUM ('DEPARTMENT','COMPANY');

CREATE TYPE signing_kieuky         AS ENUM ('TUAN_TU','SONG_SONG');

CREATE TYPE signing_request_status AS ENUM ('NHAP','CHO_KY','HOAN_THANH','TU_CHOI','HUY','QUA_HAN');

CREATE TYPE signing_attempt_status AS ENUM ('DRAFT','CHO_KY','YEU_CAU_SUA','HOAN_THANH','TU_CHOI','HUY','QUA_HAN');

CREATE TYPE signing_step_status    AS ENUM ('CHO_KY','DA_KY','TU_CHOI','BO_QUA','YEU_CAU_SUA','THU_HOI');

CREATE TYPE signing_key_status     AS ENUM ('PENDING','HOAT_DONG','ROTATED','THU_HOI','HET_HAN');

CREATE TYPE signing_verify_status  AS ENUM ('CHUA_XAC_MINH','HOP_LE','KHONG_HOP_LE');

CREATE TYPE signing_manifest_status AS ENUM ('DRAFT','FINAL');

CREATE TYPE signing_thread_status  AS ENUM ('OPEN','RELEASED','RESOLVED');

CREATE TYPE signing_notify_channel AS ENUM ('IN_APP','EMAIL');

CREATE TYPE signing_notify_status  AS ENUM ('CHO_GUI','DA_GUI','THAT_BAI');

CREATE TYPE task_vaitro            AS ENUM ('CHU_TRI','CHI_DAO','THAM_GIA');

CREATE TYPE task_attachment_loai   AS ENUM ('GIAO_VIEC','BANG_CHUNG');

CREATE TYPE meetingroom_status     AS ENUM ('AVAILABLE','MAINTENANCE','UNAVAILABLE');

CREATE TYPE meetingbooking_status  AS ENUM ('CONFIRMED','CANCELLED','COMPLETED');

CREATE TYPE birthdaywish_status    AS ENUM ('PENDING','APPROVED','REJECTED');

CREATE TYPE emaillog_status        AS ENUM ('PENDING','SENDING','SUCCESS','FAILED','RETRY');

CREATE TYPE employee_work_status   AS ENUM ('LAM_VIEC','NGHI_VIEC');
-- dùng chung cho generic relation "văn bản liên quan"
CREATE TYPE document_kind          AS ENUM ('vanbanden','vanbandi','vanbanmat');

-- =====================================================================
-- 12. DANH MỤC CHỨC VỤ (accounts_position)
-- =====================================================================
CREATE TABLE accounts_position (
    id BIGSERIAL PRIMARY KEY,
    display_order INTEGER NOT NULL UNIQUE, -- STT ưu tiên hiển thị, tự động = MAX+1
    name VARCHAR(255) NOT NULL, -- Tên chức vụ
    is_public BOOLEAN NOT NULL DEFAULT TRUE, -- Hiển thị (isPublic)
    note TEXT
);

-- =====================================================================
-- 11. CƠ CẤU TỔ CHỨC: KHỐI/KHU VỰC (Cấp 1) + ĐƠN VỊ, PHÒNG BAN (Cấp 2)
-- =====================================================================
CREATE TABLE organizations_khoi (
    id BIGSERIAL PRIMARY KEY,
    ten VARCHAR(255) NOT NULL, -- Tên khối/khu vực
    thu_tu_hien_thi INTEGER NOT NULL DEFAULT 0 -- Thứ tự hiển thị
);

CREATE TABLE organizations_donvi (
    id BIGSERIAL PRIMARY KEY,
    khoi_id BIGINT NOT NULL REFERENCES organizations_khoi (id) ON DELETE RESTRICT,
    stt_uu_tien INTEGER NOT NULL UNIQUE, -- tự động = MAX + 1
    ten VARCHAR(255) NOT NULL, -- Tên đơn vị/phòng ban
    dia_chi VARCHAR(255),
    dien_thoai VARCHAR(20),
    email VARCHAR(254),
    is_public BOOLEAN NOT NULL DEFAULT TRUE, -- isPublic
    ghi_chu TEXT
);

CREATE INDEX idx_donvi_khoi ON organizations_donvi (khoi_id);

-- =====================================================================
-- 15. NHÓM QUYỀN & QUYỀN THAO TÁC (auth_group / auth_permission)
-- RBAC độc lập, kế thừa quy ước Django Auth và mở rộng module_ten phục vụ quản trị/phân nhóm quyền
-- =====================================================================
CREATE TABLE auth_group (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    ma_nhom_quyen VARCHAR(50) UNIQUE -- vd: TP -> Trưởng phòng (mã nhóm mở rộng)
);

CREATE TABLE auth_permission (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL, -- vd: Xem chi tiết văn bản đến
    content_type_id BIGINT, -- Tương thích quy ước Django Auth; để NULL trong DDL vì hệ thống dùng RBAC độc lập, không phụ thuộc django_content_type
    codename VARCHAR(100) NOT NULL UNIQUE, -- vd: view_vanbanden
    module_ten VARCHAR(150) NOT NULL -- Module áp dụng phục vụ gom nhóm trực tiếp trên UI
);

CREATE TABLE auth_group_permissions (
    id BIGSERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL REFERENCES auth_group (id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES auth_permission (id) ON DELETE CASCADE,
    CONSTRAINT uq_auth_group_permission UNIQUE (group_id, permission_id)
);

-- =====================================================================
-- 14. CÁN BỘ NHÂN VIÊN (accounts_employee) — kiêm Custom User Model Django
-- Đã bổ sung is_active, is_staff, is_superuser theo góp ý của Tô Thanh Tân
-- =====================================================================
CREATE TABLE accounts_employee (
    id BIGSERIAL PRIMARY KEY,
    ho_ten VARCHAR(150) NOT NULL, -- Họ và tên
    ngay_sinh DATE NOT NULL, -- UI ẩn năm sinh trừ Admin
    chuc_vu_id BIGINT NOT NULL REFERENCES accounts_position (id) ON DELETE RESTRICT,
    chuc_danh VARCHAR(150), -- Chức danh (tự do, khác Chức vụ)
    email VARCHAR(254) UNIQUE,
    sdt VARCHAR(20), -- SĐT cá nhân / SĐT bàn
    don_vi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    username VARCHAR(150) NOT NULL UNIQUE, -- auto = local-part email
    password VARCHAR(255) NOT NULL, -- lưu hash (vd pbkdf2/argon2), KHÔNG lưu plaintext
    is_active BOOLEAN NOT NULL DEFAULT TRUE, -- Cờ khóa tài khoản nhân viên nghỉ việc (chuẩn Django)
    is_staff BOOLEAN NOT NULL DEFAULT FALSE, -- Quyền đăng nhập trang quản trị
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE, -- Quyền quản trị tối cao
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    trang_thai employee_work_status NOT NULL DEFAULT 'LAM_VIEC',
    ghi_chu TEXT,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_employee_updated_at BEFORE UPDATE ON accounts_employee
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_employee_donvi ON accounts_employee (don_vi_id);

CREATE INDEX idx_employee_chucvu ON accounts_employee (chuc_vu_id);

CREATE INDEX idx_employee_is_active ON accounts_employee (is_active);

-- Nhóm quyền của CBNV (FK/M2M -> auth_group, tương đương auth_user_groups trong Django)
CREATE TABLE accounts_employee_groups (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES auth_group (id) ON DELETE CASCADE,
    CONSTRAINT uq_employee_group UNIQUE (employee_id, group_id)
);

-- Ghi chú: spec mới (tab "Đvị, phòngban") không có trường "Trưởng đơn vị"
-- trên organizations_donvi -> không tạo cột manager_id.

-- =====================================================================
-- 4. DANH MỤC HỒ SƠ (records_hoso)
-- Đã tinh gọn & nâng cấp theo review của Nhóm 3 (Thịnh Trương):
--   - Xóa 6 trường chưa duyệt: don_vi, trang_thai, thoi_han_bao_quan,
--     ngay_dong, ngay_nop_luu, is_default.
--   - FK nguoi_lap_id → settings.AUTH_USER_MODEL (ON DELETE RESTRICT
--     tương đương on_delete=PROTECT trong Django).
--   - stt_uu_tien: số nguyên dương, UNIQUE, tự động MAX+1 qua trigger,
--     có xử lý chống trùng đồng thời (advisory lock).
--   - is_he_thong: cờ nhận diện Hồ sơ chung / bản ghi hệ thống, có trigger
--     BEFORE DELETE chống xóa.
--   - Partial unique index: đảm bảo duy nhất 1 Hồ sơ hệ thống (Hồ sơ chung).
--   - Bổ sung chỉ mục tìm kiếm: so_ky_hieu, ten_ho_so, ngay_lap, nguoi_lap_id.
-- =====================================================================
CREATE TABLE records_hoso (
    id BIGSERIAL PRIMARY KEY,
    stt_uu_tien INTEGER NOT NULL UNIQUE CHECK (stt_uu_tien > 0),
    so_ky_hieu VARCHAR(255) NOT NULL UNIQUE CHECK (BTRIM (so_ky_hieu) <> ''),
    ten_ho_so VARCHAR(255) NOT NULL CHECK (BTRIM (ten_ho_so) <> ''),
    nguoi_lap_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    ngay_lap TIMESTAMPTZ,
    ghi_chu TEXT,
    is_he_thong BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Partial index: đảm bảo duy nhất 1 bản ghi Hồ sơ hệ thống (Hồ sơ chung)
CREATE UNIQUE INDEX uq_records_hoso_he_thong ON records_hoso (is_he_thong)
WHERE
    is_he_thong = TRUE;

-- Chỉ mục tìm kiếm cho records_hoso (Đã loại bỏ idx_hoso_so_ky_hieu thừa do trùng với UNIQUE constraint)
CREATE INDEX idx_hoso_ten ON records_hoso (ten_ho_so);

CREATE INDEX idx_hoso_ngay_lap ON records_hoso (ngay_lap);

CREATE INDEX idx_hoso_nguoi_lap ON records_hoso (nguoi_lap_id);

CREATE TRIGGER trg_hoso_updated_at BEFORE UPDATE ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Trigger tự động gán stt_uu_tien = MAX + 1 khi INSERT (nếu chưa cung cấp hoặc = 0)
-- Sử dụng advisory lock để chống race condition khi nhiều request đồng thời.
CREATE OR REPLACE FUNCTION auto_stt_uu_tien_hoso()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.stt_uu_tien IS NULL OR NEW.stt_uu_tien = 0 THEN
    -- Advisory lock trên OID của bảng để serialize việc tính MAX
    PERFORM pg_advisory_xact_lock('records_hoso'::regclass::oid::bigint);
    NEW.stt_uu_tien := COALESCE(
      (SELECT MAX(stt_uu_tien) FROM records_hoso), 0
    ) + 1;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_hoso_auto_stt BEFORE INSERT ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION auto_stt_uu_tien_hoso();

-- Trigger chống xóa Hồ sơ chung / bản ghi hệ thống
CREATE OR REPLACE FUNCTION prevent_delete_he_thong_hoso()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.is_he_thong = TRUE THEN
    RAISE EXCEPTION 'Không thể xóa Hồ sơ chung / bản ghi hệ thống (records_hoso id=%).', OLD.id;
  END IF;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_hoso_prevent_delete BEFORE DELETE ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION prevent_delete_he_thong_hoso();

-- Trigger bảo vệ tuyệt đối Hồ sơ chung: Chặn lách luật tắt cờ is_he_thong từ TRUE sang FALSE
CREATE OR REPLACE FUNCTION prevent_update_he_thong_hoso()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.is_he_thong = TRUE AND NEW.is_he_thong = FALSE THEN
    RAISE EXCEPTION 'Bảo toàn Hồ sơ hệ thống: Không thể gỡ bỏ cờ is_he_thong từ TRUE sang FALSE (records_hoso id=%).', OLD.id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_hoso_prevent_update_he_thong BEFORE UPDATE ON records_hoso
  FOR EACH ROW EXECUTE FUNCTION prevent_update_he_thong_hoso();

-- =====================================================================
-- 5. LOẠI VĂN BẢN (records_loaivanban)
-- Giữ đúng 7 trường đã duyệt bởi Nhóm 3 (Thịnh Trương).
-- Không thêm stt_uu_tien — STT hiển thị trên UI là forloop.counter.
-- FK ho_so_id theo chuẩn Django _id convention.
-- Ràng buộc chống trùng tên Loại văn bản trong cùng một Hồ sơ (không phân biệt hoa/thường, khoảng trắng thừa).
-- Bổ sung CHECK (BTRIM(ten_loai) <> '') chống chuỗi rỗng và khoảng trắng thừa.
-- =====================================================================
CREATE TABLE records_loaivanban (
    id BIGSERIAL PRIMARY KEY,
    ho_so_id BIGINT NOT NULL REFERENCES records_hoso (id) ON DELETE RESTRICT,
    ten_loai VARCHAR(255) NOT NULL CHECK (BTRIM (ten_loai) <> ''),
    ngay_lap TIMESTAMPTZ,
    ghi_chu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_loaivanban_updated_at BEFORE UPDATE ON records_loaivanban
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Ràng buộc không cho trùng tên Loại văn bản trong cùng một Hồ sơ (xử lý chữ hoa/thường và khoảng trắng thừa)
CREATE UNIQUE INDEX uq_records_loaivanban_hoso_ten ON records_loaivanban (
    ho_so_id,
    LOWER(TRIM(ten_loai))
);

-- Chỉ mục tìm kiếm cho records_loaivanban
CREATE INDEX idx_loaivanban_hoso ON records_loaivanban (ho_so_id);

CREATE INDEX idx_loaivanban_ten ON records_loaivanban (ten_loai);

CREATE INDEX idx_loaivanban_ngay_lap ON records_loaivanban (ngay_lap);

-- =====================================================================
-- 6. DANH MỤC TÀI LIỆU CẤP 1 (records_tailieu)
-- =====================================================================
CREATE TABLE records_tailieu (
    id BIGSERIAL PRIMARY KEY,
    stt_uu_tien SMALLINT NOT NULL UNIQUE,
    ky_hieu VARCHAR(255),
    ten_tai_lieu VARCHAR(255) NOT NULL,
    nguoi_lap_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    ngay_lap DATE,
    ghi_chu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_tailieu_updated_at BEFORE UPDATE ON records_tailieu
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =====================================================================
-- 7. LOẠI TÀI LIỆU CẤP 2 (records_loaitailieu)
-- =====================================================================
CREATE TABLE records_loaitailieu (
    id BIGSERIAL PRIMARY KEY,
    dm_tai_lieu BIGINT NOT NULL REFERENCES records_tailieu (id) ON DELETE RESTRICT,
    ten_loai VARCHAR(255) NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT TRUE,
    ngay_lap TIMESTAMPTZ,
    ghi_chu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_loaitailieu_updated_at BEFORE UPDATE ON records_loaitailieu
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =====================================================================
-- 8. CHI TIẾT TÀI LIỆU (records_chitiettailieu)
-- =====================================================================
CREATE TABLE records_chitiettailieu (
    id BIGSERIAL PRIMARY KEY,
    dm_tai_lieu BIGINT NOT NULL REFERENCES records_tailieu (id) ON DELETE RESTRICT,
    ky_hieu VARCHAR(255),
    tieu_de VARCHAR(255) NOT NULL,
    ngay_dang DATE NOT NULL,
    noi_ban_hanh VARCHAR(255),
    hieu_luc hieu_luc_status NOT NULL,
    ngay_het_hieu_luc DATE,
    link_thay_the VARCHAR(500),
    ghi_chu TEXT,
    file_dinh_kem VARCHAR(500) NOT NULL, -- đường dẫn/khoá lưu trữ file (PDF/DOC/JPG/PNG/ZIP/RAR, <=20MB - validate ở tầng app)
    hien_thi chitiettailieu_hienthi NOT NULL,
    nguoi_tao BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_chitiettailieu_updated_at BEFORE UPDATE ON records_chitiettailieu
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Loại tài liệu cấp 2 áp dụng cho chi tiết tài liệu (M2M, lọc theo dm_tai_lieu đã chọn)
CREATE TABLE records_chitiettailieu_loaitailieu (
    chitiettailieu_id BIGINT NOT NULL REFERENCES records_chitiettailieu (id) ON DELETE CASCADE,
    loaitailieu_id BIGINT NOT NULL REFERENCES records_loaitailieu (id) ON DELETE RESTRICT,
    PRIMARY KEY (
        chitiettailieu_id,
        loaitailieu_id
    )
);

-- =====================================================================
-- 1. VĂN BẢN ĐẾN (documents_vanbanden)
-- =====================================================================
CREATE TABLE documents_vanbanden (
    id BIGSERIAL PRIMARY KEY,
    nam SMALLINT NOT NULL,
    so_hieu VARCHAR(255) NOT NULL,
    so_thu_tu INTEGER NOT NULL, -- Số đến (auto increment theo nghiệp vụ, xử lý ở tầng app)
    ngay_den TIMESTAMPTZ NOT NULL,
    trich_yeu TEXT NOT NULL,
    noi_ban_hanh VARCHAR(500),
    ngay_van_ban TIMESTAMPTZ,
    nguoi_ky VARCHAR(255),
    chuc_vu VARCHAR(255),
    hieu_luc hieu_luc_status NOT NULL,
    ngay_het_hieu_luc TIMESTAMPTZ,
    link_thay_the VARCHAR(500),
    ghi_chu TEXT,
    file_dinh_kem VARCHAR(500) NOT NULL, -- PDF/DOC/DOCX/JPG/JPEG/PNG
    hien_thi BOOLEAN NOT NULL DEFAULT TRUE,
    gui_mail_toan_he_thong BOOLEAN NOT NULL DEFAULT FALSE,
    nguoi_tao BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_vanbanden_updated_at BEFORE UPDATE ON documents_vanbanden
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_vanbanden_sohieu ON documents_vanbanden (so_hieu);

CREATE INDEX idx_vanbanden_nam ON documents_vanbanden (nam);

CREATE TABLE documents_vanbanden_hoso (
    vanbanden_id BIGINT NOT NULL REFERENCES documents_vanbanden (id) ON DELETE CASCADE,
    hoso_id BIGINT NOT NULL REFERENCES records_hoso (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanden_id, hoso_id)
);

CREATE INDEX idx_vanbanden_hoso_hoso ON documents_vanbanden_hoso (hoso_id);

CREATE TABLE documents_vanbanden_danhmuc (
    vanbanden_id BIGINT NOT NULL REFERENCES documents_vanbanden (id) ON DELETE CASCADE,
    loaivanban_id BIGINT NOT NULL REFERENCES records_loaivanban (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanden_id, loaivanban_id)
);

CREATE INDEX idx_vanbanden_danhmuc_loai ON documents_vanbanden_danhmuc (loaivanban_id);

-- Toàn vẹn tham chiếu chéo giữa Hồ sơ và Loại văn bản cho Văn bản đến:
-- 1) Khi thêm Loại văn bản, nếu văn bản đã liên kết hồ sơ thì Loại văn bản phải thuộc đúng Hồ sơ đó
CREATE OR REPLACE FUNCTION check_vanbanden_cross_reference()
RETURNS TRIGGER AS $$
DECLARE
  v_hoso_id BIGINT;
BEGIN
  SELECT ho_so_id INTO v_hoso_id FROM records_loaivanban WHERE id = NEW.loaivanban_id;
  IF EXISTS (SELECT 1 FROM documents_vanbanden_hoso WHERE vanbanden_id = NEW.vanbanden_id) THEN
    IF NOT EXISTS (
      SELECT 1 FROM documents_vanbanden_hoso
      WHERE vanbanden_id = NEW.vanbanden_id AND hoso_id = v_hoso_id
    ) THEN
      RAISE EXCEPTION 'Vi phạm toàn vẹn tham chiếu chéo: Loại văn bản (id=%) thuộc Hồ sơ (id=%), nhưng Văn bản đến (id=%) không liên kết với Hồ sơ này.',
        NEW.loaivanban_id, v_hoso_id, NEW.vanbanden_id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vanbanden_danhmuc_cross_ref
  BEFORE INSERT OR UPDATE ON documents_vanbanden_danhmuc
  FOR EACH ROW EXECUTE FUNCTION check_vanbanden_cross_reference();

-- 2) Khi xóa liên kết hồ sơ, không cho xóa nếu văn bản vẫn còn chứa loại văn bản thuộc hồ sơ đó
-- An toàn khi xóa văn bản cha (ON DELETE CASCADE): bỏ qua kiểm tra nếu văn bản cha không còn tồn tại
CREATE OR REPLACE FUNCTION check_vanbanden_hoso_delete_cross_ref()
RETURNS TRIGGER AS $$
BEGIN
  -- Nếu văn bản cha không còn tồn tại (đang trong luồng ON DELETE CASCADE của documents_vanbanden), bỏ qua không chặn
  IF NOT EXISTS (SELECT 1 FROM documents_vanbanden WHERE id = OLD.vanbanden_id) THEN
    RETURN OLD;
  END IF;

  IF EXISTS (
    SELECT 1 FROM documents_vanbanden_danhmuc dm
    JOIN records_loaivanban lvb ON dm.loaivanban_id = lvb.id
    WHERE dm.vanbanden_id = OLD.vanbanden_id AND lvb.ho_so_id = OLD.hoso_id
  ) THEN
    RAISE EXCEPTION 'Không thể gỡ Hồ sơ (id=%) khỏi Văn bản đến (id=%): văn bản vẫn còn chứa Loại văn bản thuộc Hồ sơ này.',
      OLD.hoso_id, OLD.vanbanden_id;
  END IF;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_vanbanden_hoso_del_cross_ref
  AFTER DELETE ON documents_vanbanden_hoso
  DEFERRABLE INITIALLY IMMEDIATE
  FOR EACH ROW EXECUTE FUNCTION check_vanbanden_hoso_delete_cross_ref();

CREATE TABLE documents_vanbanden_donvinhan (
    vanbanden_id BIGINT NOT NULL REFERENCES documents_vanbanden (id) ON DELETE CASCADE,
    donvi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanden_id, donvi_id)
);

CREATE TABLE documents_vanbanden_nguoinhan (
    vanbanden_id BIGINT NOT NULL REFERENCES documents_vanbanden (id) ON DELETE CASCADE,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanden_id, employee_id)
);

-- =====================================================================
-- 2. VĂN BẢN ĐI (documents_vanbandi)
-- Đã đổi tên cột 'so' thành 'so_thu_tu' theo góp ý của Lê Trí Kiệt (Nhóm 2)
-- Đã bỏ cột 'noi_ban_hanh' và chuyển sang bảng M2M documents_vanbandi_noibanhanh
-- =====================================================================
CREATE TABLE documents_vanbandi (
    id BIGSERIAL PRIMARY KEY,
    nam SMALLINT NOT NULL,
    so_hieu VARCHAR(255) NOT NULL, -- (bỏ cột 'kyhieu' trùng lặp — xem ghi chú đầu file)
    so_thu_tu INTEGER NOT NULL, -- Số thứ tự văn bản đi trong năm
    ngay_ban_hanh TIMESTAMPTZ NOT NULL,
    trich_yeu TEXT NOT NULL,
    ngay_van_ban TIMESTAMPTZ NOT NULL,
    nguoi_ky VARCHAR(255),
    chuc_vu VARCHAR(255),
    hieu_luc hieu_luc_status NOT NULL,
    ngay_het_hieu_luc TIMESTAMPTZ,
    link_thay_the VARCHAR(500),
    ghi_chu TEXT,
    file_dinh_kem VARCHAR(500) NOT NULL,
    hien_thi BOOLEAN NOT NULL DEFAULT TRUE,
    gui_mail_toan_he_thong BOOLEAN NOT NULL DEFAULT FALSE,
    nguoi_tao BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_vanbandi_updated_at BEFORE UPDATE ON documents_vanbandi
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_vanbandi_sohieu ON documents_vanbandi (so_hieu);

CREATE INDEX idx_vanbandi_nam ON documents_vanbandi (nam);

CREATE TABLE documents_vanbandi_hoso (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    hoso_id BIGINT NOT NULL REFERENCES records_hoso (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, hoso_id)
);

CREATE INDEX idx_vanbandi_hoso_hoso ON documents_vanbandi_hoso (hoso_id);

CREATE TABLE documents_vanbandi_danhmuc (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    loaivanban_id BIGINT NOT NULL REFERENCES records_loaivanban (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, loaivanban_id)
);

CREATE INDEX idx_vanbandi_danhmuc_loai ON documents_vanbandi_danhmuc (loaivanban_id);

-- Toàn vẹn tham chiếu chéo giữa Hồ sơ và Loại văn bản cho Văn bản đi:
-- 1) Khi thêm Loại văn bản, nếu văn bản đã liên kết hồ sơ thì Loại văn bản phải thuộc đúng Hồ sơ đó
CREATE OR REPLACE FUNCTION check_vanbandi_cross_reference()
RETURNS TRIGGER AS $$
DECLARE
  v_hoso_id BIGINT;
BEGIN
  SELECT ho_so_id INTO v_hoso_id FROM records_loaivanban WHERE id = NEW.loaivanban_id;
  IF EXISTS (SELECT 1 FROM documents_vanbandi_hoso WHERE vanbandi_id = NEW.vanbandi_id) THEN
    IF NOT EXISTS (
      SELECT 1 FROM documents_vanbandi_hoso
      WHERE vanbandi_id = NEW.vanbandi_id AND hoso_id = v_hoso_id
    ) THEN
      RAISE EXCEPTION 'Vi phạm toàn vẹn tham chiếu chéo: Loại văn bản (id=%) thuộc Hồ sơ (id=%), nhưng Văn bản đi (id=%) không liên kết với Hồ sơ này.',
        NEW.loaivanban_id, v_hoso_id, NEW.vanbandi_id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vanbandi_danhmuc_cross_ref
  BEFORE INSERT OR UPDATE ON documents_vanbandi_danhmuc
  FOR EACH ROW EXECUTE FUNCTION check_vanbandi_cross_reference();

-- 2) Khi xóa liên kết hồ sơ, không cho xóa nếu văn bản vẫn còn chứa loại văn bản thuộc hồ sơ đó
-- An toàn khi xóa văn bản cha (ON DELETE CASCADE): bỏ qua kiểm tra nếu văn bản cha không còn tồn tại
CREATE OR REPLACE FUNCTION check_vanbandi_hoso_delete_cross_ref()
RETURNS TRIGGER AS $$
BEGIN
  -- Nếu văn bản cha không còn tồn tại (đang trong luồng ON DELETE CASCADE của documents_vanbandi), bỏ qua không chặn
  IF NOT EXISTS (SELECT 1 FROM documents_vanbandi WHERE id = OLD.vanbandi_id) THEN
    RETURN OLD;
  END IF;

  IF EXISTS (
    SELECT 1 FROM documents_vanbandi_danhmuc dm
    JOIN records_loaivanban lvb ON dm.loaivanban_id = lvb.id
    WHERE dm.vanbandi_id = OLD.vanbandi_id AND lvb.ho_so_id = OLD.hoso_id
  ) THEN
    RAISE EXCEPTION 'Không thể gỡ Hồ sơ (id=%) khỏi Văn bản đi (id=%): văn bản vẫn còn chứa Loại văn bản thuộc Hồ sơ này.',
      OLD.hoso_id, OLD.vanbandi_id;
  END IF;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_vanbandi_hoso_del_cross_ref
  AFTER DELETE ON documents_vanbandi_hoso
  DEFERRABLE INITIALLY IMMEDIATE
  FOR EACH ROW EXECUTE FUNCTION check_vanbandi_hoso_delete_cross_ref();

-- Bảng trung gian M2M Nơi ban hành cho Văn bản đi
CREATE TABLE documents_vanbandi_noibanhanh (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    donvi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, donvi_id)
);

CREATE INDEX idx_vanbandi_noibanhanh_donvi ON documents_vanbandi_noibanhanh (donvi_id);

CREATE TABLE documents_vanbandi_donvinhan (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    donvi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, donvi_id)
);

CREATE TABLE documents_vanbandi_nguoinhan (
    vanbandi_id BIGINT NOT NULL REFERENCES documents_vanbandi (id) ON DELETE CASCADE,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbandi_id, employee_id)
);

-- =====================================================================
-- 3. VĂN BẢN MẬT (documents_vanbanmat)
-- Người nhận: CHỈ đích danh CBNV được liệt kê mới xem được (áp dụng ở tầng app/permission)
-- =====================================================================
CREATE TABLE documents_vanbanmat (
    id BIGSERIAL PRIMARY KEY,
    nam SMALLINT NOT NULL,
    so_hieu VARCHAR(255) NOT NULL,
    trich_yeu TEXT NOT NULL,
    ngay_ban_hanh TIMESTAMPTZ,
    ngay_van_ban TIMESTAMPTZ,
    nguoi_ky VARCHAR(255),
    chuc_vu VARCHAR(255),
    hieu_luc hieu_luc_status NOT NULL,
    ngay_het_hieu_luc TIMESTAMPTZ,
    link_thay_the VARCHAR(500),
    ghi_chu TEXT,
    file_dinh_kem VARCHAR(500) NOT NULL,
    hien_thi BOOLEAN NOT NULL DEFAULT TRUE,
    gui_mail_toan_he_thong BOOLEAN NOT NULL DEFAULT FALSE,
    nguoi_tao BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_vanbanmat_updated_at BEFORE UPDATE ON documents_vanbanmat
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_vanbanmat_sohieu ON documents_vanbanmat (so_hieu);

CREATE TABLE documents_vanbanmat_hoso (
    vanbanmat_id BIGINT NOT NULL REFERENCES documents_vanbanmat (id) ON DELETE CASCADE,
    hoso_id BIGINT NOT NULL REFERENCES records_hoso (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanmat_id, hoso_id)
);

CREATE INDEX idx_vanbanmat_hoso_hoso ON documents_vanbanmat_hoso (hoso_id);

CREATE TABLE documents_vanbanmat_danhmuc (
    vanbanmat_id BIGINT NOT NULL REFERENCES documents_vanbanmat (id) ON DELETE CASCADE,
    loaivanban_id BIGINT NOT NULL REFERENCES records_loaivanban (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanmat_id, loaivanban_id)
);

CREATE INDEX idx_vanbanmat_danhmuc_loai ON documents_vanbanmat_danhmuc (loaivanban_id);

-- Toàn vẹn tham chiếu chéo giữa Hồ sơ và Loại văn bản cho Văn bản mật:
-- 1) Khi thêm Loại văn bản, nếu văn bản đã liên kết hồ sơ thì Loại văn bản phải thuộc đúng Hồ sơ đó
CREATE OR REPLACE FUNCTION check_vanbanmat_cross_reference()
RETURNS TRIGGER AS $$
DECLARE
  v_hoso_id BIGINT;
BEGIN
  SELECT ho_so_id INTO v_hoso_id FROM records_loaivanban WHERE id = NEW.loaivanban_id;
  IF EXISTS (SELECT 1 FROM documents_vanbanmat_hoso WHERE vanbanmat_id = NEW.vanbanmat_id) THEN
    IF NOT EXISTS (
      SELECT 1 FROM documents_vanbanmat_hoso
      WHERE vanbanmat_id = NEW.vanbanmat_id AND hoso_id = v_hoso_id
    ) THEN
      RAISE EXCEPTION 'Vi phạm toàn vẹn tham chiếu chéo: Loại văn bản (id=%) thuộc Hồ sơ (id=%), nhưng Văn bản mật (id=%) không liên kết với Hồ sơ này.',
        NEW.loaivanban_id, v_hoso_id, NEW.vanbanmat_id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vanbanmat_danhmuc_cross_ref
  BEFORE INSERT OR UPDATE ON documents_vanbanmat_danhmuc
  FOR EACH ROW EXECUTE FUNCTION check_vanbanmat_cross_reference();

-- 2) Khi xóa liên kết hồ sơ, không cho xóa nếu văn bản vẫn còn chứa loại văn bản thuộc hồ sơ đó
-- An toàn khi xóa văn bản cha (ON DELETE CASCADE): bỏ qua kiểm tra nếu văn bản cha không còn tồn tại
CREATE OR REPLACE FUNCTION check_vanbanmat_hoso_delete_cross_ref()
RETURNS TRIGGER AS $$
BEGIN
  -- Nếu văn bản cha không còn tồn tại (đang trong luồng ON DELETE CASCADE của documents_vanbanmat), bỏ qua không chặn
  IF NOT EXISTS (SELECT 1 FROM documents_vanbanmat WHERE id = OLD.vanbanmat_id) THEN
    RETURN OLD;
  END IF;

  IF EXISTS (
    SELECT 1 FROM documents_vanbanmat_danhmuc dm
    JOIN records_loaivanban lvb ON dm.loaivanban_id = lvb.id
    WHERE dm.vanbanmat_id = OLD.vanbanmat_id AND lvb.ho_so_id = OLD.hoso_id
  ) THEN
    RAISE EXCEPTION 'Không thể gỡ Hồ sơ (id=%) khỏi Văn bản mật (id=%): văn bản vẫn còn chứa Loại văn bản thuộc Hồ sơ này.',
      OLD.hoso_id, OLD.vanbanmat_id;
  END IF;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_vanbanmat_hoso_del_cross_ref
  AFTER DELETE ON documents_vanbanmat_hoso
  DEFERRABLE INITIALLY IMMEDIATE
  FOR EACH ROW EXECUTE FUNCTION check_vanbanmat_hoso_delete_cross_ref();

-- Bảng trung gian M2M Nơi ban hành cho Văn bản mật
CREATE TABLE documents_vanbanmat_noibanhanh (
    vanbanmat_id BIGINT NOT NULL REFERENCES documents_vanbanmat (id) ON DELETE CASCADE,
    donvi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanmat_id, donvi_id)
);

CREATE INDEX idx_vanbanmat_noibanhanh_donvi ON documents_vanbanmat_noibanhanh (donvi_id);

-- Đơn vị nhận: xem được cả đơn vị
CREATE TABLE documents_vanbanmat_donvinhan (
    vanbanmat_id BIGINT NOT NULL REFERENCES documents_vanbanmat (id) ON DELETE CASCADE,
    donvi_id BIGINT NOT NULL REFERENCES organizations_donvi (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanmat_id, donvi_id)
);
-- Người nhận: chỉ đích danh CBNV được xem
CREATE TABLE documents_vanbanmat_nguoinhan (
    vanbanmat_id BIGINT NOT NULL REFERENCES documents_vanbanmat (id) ON DELETE CASCADE,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    PRIMARY KEY (vanbanmat_id, employee_id)
);

-- =====================================================================
-- BẢNG PHỤ: LỊCH SỬ NGƯỜI XEM (documents_view_log)
-- Dùng chung cho cả 3 bảng văn bản (Đến/Đi/Mật) qua cặp document_type +
-- document_id (generic relation, cùng cơ chế với signing_request/task_congviec).
-- unique_together(document_type, document_id, user_id) -> mỗi user chỉ giữ
-- 1 bản ghi mới nhất trên 1 văn bản (upsert ở tầng app bằng
-- INSERT ... ON CONFLICT (document_type, document_id, user_id)
-- DO UPDATE SET viewed_at = EXCLUDED.viewed_at).
-- =====================================================================
CREATE TABLE documents_view_log (
    id BIGSERIAL PRIMARY KEY,
    document_type document_kind NOT NULL,
    document_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    viewed_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_viewlog_doc_user UNIQUE (
        document_type,
        document_id,
        user_id
    )
);

CREATE INDEX idx_viewlog_document ON documents_view_log (document_type, document_id);

-- =====================================================================
-- =====================================================================
-- 9. PHÂN HỆ TRÌNH KÝ (signing_*) — ĐÃ SỬA theo báo cáo bug (commit 8200604,
-- nhánh 5_signing_workflow). Các thay đổi so với bản trước:
--   [FIX-P1] updated_at/updated_by thay update_at/update_by -> khớp đúng
--            cột mà set_updated_at() ghi (trước đây trigger lỗi runtime
--            vì NEW.updated_at không tồn tại trên bảng dùng update_at).
--   [FIX-P1] Multi-signer: bỏ so_nguoi_ky/nguoi_ky đơn lẻ khỏi
--            signing_process_step & signing_request_step; nguồn sự thật
--            chuyển sang 2 bảng con signing_process_step_signer (danh sách
--            người ký cấu hình theo quy trình) và signing_request_step_signer
--            (snapshot signer slot theo từng request, mỗi dòng 1 người ký
--            với trạng thái riêng — đúng cho cả TUAN_TU lẫn SONG_SONG).
--   [FIX-P1] signing_attempt: mỗi lần gửi/gửi lại/reconsider tạo 1 attempt
--            mới, khoá cứng document_version/document_hash/storage_key tại
--            thời điểm đó; signing_request_step nay thuộc về 1 attempt cụ
--            thể (không còn thuộc thẳng signing_request) để tách bạch lịch
--            sử các lần gửi, không ghi đè lên nhau.
--   [FIX-P2] UNIQUE(ma_quy_trinh, phien_ban) thay UNIQUE(ma_quy_trinh) ->
--            cho phép clone phiên bản mới cùng mã quy trình.
--   [FIX-P2] signing_key: UNIQUE(key_id); thêm unique index key đang
--            HOAT_DONG theo (nguoi_so_huu, thuat_toan) -> 1 người chỉ có
--            1 khoá active cho mỗi thuật toán tại 1 thời điểm.
--   [FIX-P2] signing_signature.buoc_ky trỏ tới 1 signer slot cụ thể + UNIQUE
--            (1 slot chỉ ký 1 lần; ký lại sau reject phải qua attempt mới =
--            slot mới). Thêm CHECK định dạng hash SHA-256 hex cho cả
--            signing_attempt.document_hash và signing_signature.hash_tai_lieu.
--   [FIX-P2] signing_audit_log: đổi ON DELETE CASCADE -> RESTRICT trên
--            trinh_ky, không cho xoá signing_request khi vẫn còn audit
--            (đúng yêu cầu bảo toàn lịch sử).
--   [FIX-P2] signing_notification: thêm dedupe_key UNIQUE cho idempotency
--            khi retry (giữ ON DELETE CASCADE vì notification không phải
--            audit trail bắt buộc lưu vĩnh viễn).
--
-- [NEEDS DECISION — CHƯA TỰ QUYẾT, giữ nguyên chờ xác nhận]:
--   - Contract văn bản: tạm giữ document_type/document_id (polymorphic,
--     validate tồn tại ở tầng service) thay vì FK cứng tới 1 bảng document
--     registry chung, vì 3 bảng văn bản (đến/đi/mật) hiện đã tách riêng và
--     documents_view_log/task_congviec cũng đang dùng chung cơ chế này ->
--     đổi sang FK thật sẽ phải tái cấu trúc cả 3 bảng, vượt phạm vi issue.
--     Nếu team quyết định làm document registry chung, cần một issue riêng.
--   - Trạng thái DRAFT cho signing_process và các field deadline
--     (final_due_at, due_at, reminder policy): CHƯA thêm vì phụ thuộc
--     phạm vi MVP — báo lại nếu cần để bổ sung.
-- =====================================================================
-- =====================================================================
-- 9. PHÂN HỆ TRÌNH KÝ (signing_*) — ĐÁP ỨNG 100% THIẾT KẾ BACKEND (commit 8200604)
-- =====================================================================
CREATE TABLE signing_process (
    id BIGSERIAL PRIMARY KEY,
    ma_quy_trinh VARCHAR(50) NOT NULL,
    ten_quy_trinh VARCHAR(255) NOT NULL,
    mo_ta TEXT,
    phien_ban SMALLINT NOT NULL DEFAULT 1,
    trang_thai signing_process_status NOT NULL DEFAULT 'HOAT_DONG',
    pham_vi signing_scope NOT NULL DEFAULT 'COMPANY',
    kieu_ky_mac_dinh signing_kieuky NOT NULL DEFAULT 'TUAN_TU',
    reminder_policy JSONB, -- Cấu hình nhắc hạn (mặc định due - 24h và due)
    nguoi_tao BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    CONSTRAINT uq_signing_process_ma_phienban UNIQUE (ma_quy_trinh, phien_ban)
);

CREATE TRIGGER trg_signing_process_updated_at BEFORE UPDATE ON signing_process
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE signing_process_step (
    id BIGSERIAL PRIMARY KEY,
    quy_trinh BIGINT NOT NULL REFERENCES signing_process (id) ON DELETE CASCADE,
    cap_ky SMALLINT NOT NULL,
    ten_cap_ky VARCHAR(255) NOT NULL,
    thu_tu SMALLINT NOT NULL,
    chuc_vu_id BIGINT REFERENCES accounts_position (id) ON DELETE SET NULL, -- gợi ý vai trò mặc định
    don_vi_id BIGINT REFERENCES organizations_donvi (id) ON DELETE SET NULL,
    sla_hours INTEGER, -- Thời hạn ký từng cấp (giờ)
    bat_buoc BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ghi_chu TEXT,
    CONSTRAINT uq_process_step_thutu UNIQUE (quy_trinh, thu_tu)
);

CREATE INDEX idx_process_step_quytrinh ON signing_process_step (quy_trinh);

-- Danh sách người ký cấu hình sẵn cho từng cấp ký của quy trình
CREATE TABLE signing_process_step_signer (
    id BIGSERIAL PRIMARY KEY,
    process_step_id BIGINT NOT NULL REFERENCES signing_process_step (id) ON DELETE CASCADE,
    nguoi_ky BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    bat_buoc BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_process_step_signer UNIQUE (process_step_id, nguoi_ky)
);

CREATE TABLE signing_request (
    id BIGSERIAL PRIMARY KEY,
    document_type document_kind NOT NULL, -- văn bản liên quan (generic relation kiểu Django)
    document_id BIGINT NOT NULL,
    document_storage_key VARCHAR(500),
    document_hash VARCHAR(64),
    quy_trinh BIGINT NOT NULL REFERENCES signing_process (id) ON DELETE RESTRICT,
    phien_ban_quy_trinh SMALLINT NOT NULL,
    muc_do VARCHAR(20) NOT NULL,
    kieu_ky signing_kieuky NOT NULL,
    create_by BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    trang_thai signing_request_status NOT NULL DEFAULT 'NHAP',
    final_due_at TIMESTAMPTZ, -- Hạn chót toàn bộ yêu cầu trình ký
    ngay_gui TIMESTAMPTZ,
    ngay_hoan_thanh TIMESTAMPTZ,
    ngay_tu_choi TIMESTAMPTZ,
    ly_do_tu_choi TEXT,
    ngay_huy TIMESTAMPTZ,
    ly_do_huy TEXT,
    ghi_chu TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL
);

CREATE TRIGGER trg_signing_request_updated_at BEFORE UPDATE ON signing_request
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_signing_request_document ON signing_request (document_type, document_id);

-- Lịch sử mỗi lần gửi/gửi lại/reconsider — khoá version/hash/storage_key tài liệu
CREATE TABLE signing_attempt (
    id BIGSERIAL PRIMARY KEY,
    trinh_ky BIGINT NOT NULL REFERENCES signing_request (id) ON DELETE RESTRICT, -- RESTRICT: Bảo toàn bằng chứng, không cascade xóa từ request
    parent_attempt_id BIGINT REFERENCES signing_attempt (id) ON DELETE SET NULL, -- vết lần gửi trước
    attempt_no SMALLINT NOT NULL,
    document_version VARCHAR(50),
    document_hash VARCHAR(64) NOT NULL, -- SHA-256 hex
    storage_key VARCHAR(500) NOT NULL,
    trang_thai signing_attempt_status NOT NULL DEFAULT 'CHO_KY',
    ly_do TEXT, -- lý do resend/reconsider, NULL cho attempt đầu tiên
    idempotency_key VARCHAR(255) UNIQUE, -- Idempotency key tránh submit trùng
    submitted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ,
    created_by BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_signing_attempt UNIQUE (trinh_ky, attempt_no),
    CONSTRAINT chk_attempt_hash_sha256 CHECK (
        document_hash ~ '^[0-9a-f]{64}$'
    )
);

CREATE INDEX idx_attempt_trinhky ON signing_attempt (trinh_ky);

-- Trigger bảo vệ bằng chứng: Chặn xóa cứng signing_attempt đã kích hoạt hoặc đã có chữ ký/manifest
CREATE OR REPLACE FUNCTION prevent_delete_signing_attempt()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.trang_thai <> 'DRAFT' THEN
    RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Không thể xóa lượt trình ký (signing_attempt id=%) đã kích hoạt (trạng thái: %).',
      OLD.id, OLD.trang_thai;
  END IF;
  IF EXISTS (SELECT 1 FROM signing_manifest WHERE signing_attempt_id = OLD.id) THEN
    RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Lượt trình ký (id=%) đã có manifest số, không thể xóa.', OLD.id;
  END IF;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_signing_attempt_prevent_delete
  BEFORE DELETE ON signing_attempt
  FOR EACH ROW EXECUTE FUNCTION prevent_delete_signing_attempt();

-- Mỗi cấp ký trong 1 attempt cụ thể
CREATE TABLE signing_request_step (
    id BIGSERIAL PRIMARY KEY,
    attempt_id BIGINT NOT NULL REFERENCES signing_attempt (id) ON DELETE CASCADE,
    buoc_quy_trinh BIGINT NOT NULL REFERENCES signing_process_step (id) ON DELETE RESTRICT,
    cap_ky SMALLINT NOT NULL,
    ten_cap_ky VARCHAR(255) NOT NULL,
    thu_tu SMALLINT NOT NULL,
    trang_thai signing_step_status NOT NULL DEFAULT 'CHO_KY',
    due_at TIMESTAMPTZ, -- Hạn xử lý cấp này
    opened_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    ghi_chu TEXT,
    CONSTRAINT uq_request_step_thutu UNIQUE (attempt_id, thu_tu)
);

CREATE INDEX idx_request_step_attempt ON signing_request_step (attempt_id);

-- Signer slot: mỗi dòng = 1 người ký trong 1 cấp ký của attempt
CREATE TABLE signing_request_step_signer (
    id BIGSERIAL PRIMARY KEY,
    request_step_id BIGINT NOT NULL REFERENCES signing_request_step (id) ON DELETE CASCADE,
    nguoi_ky BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    bat_buoc BOOLEAN NOT NULL DEFAULT TRUE,
    trang_thai signing_step_status NOT NULL DEFAULT 'CHO_KY',
    opened_at TIMESTAMPTZ,
    signed_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    ly_do_tu_choi TEXT,
    last_action_idempotency_key VARCHAR(255),
    CONSTRAINT uq_request_step_signer UNIQUE (request_step_id, nguoi_ky)
);

CREATE INDEX idx_request_step_signer_step ON signing_request_step_signer (request_step_id);

-- Quản lý khóa ký công khai Ed25519 của người dùng
CREATE TABLE signing_key (
    id BIGSERIAL PRIMARY KEY,
    nguoi_so_huu BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    key_id VARCHAR(100) NOT NULL UNIQUE,
    fingerprint VARCHAR(64) UNIQUE, -- Fingerprint định danh public key
    thuat_toan VARCHAR(50) NOT NULL DEFAULT 'Ed25519',
    public_key TEXT NOT NULL, -- Không lưu private key
    trang_thai signing_key_status NOT NULL DEFAULT 'HOAT_DONG',
    challenge_verified_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    ngay_hieu_luc TIMESTAMPTZ NOT NULL DEFAULT now(),
    ngay_thu_hoi TIMESTAMPTZ,
    replaced_by_id BIGINT REFERENCES signing_key (id) ON DELETE SET NULL, -- Xoay vòng khóa
    ghi_chu TEXT
);

CREATE UNIQUE INDEX uq_signing_key_active_owner ON signing_key (nguoi_so_huu, thuat_toan)
WHERE
    trang_thai = 'HOAT_DONG';

-- Chữ ký số điện tử của từng signer slot
CREATE TABLE signing_signature (
    id BIGSERIAL PRIMARY KEY,
    buoc_ky BIGINT NOT NULL UNIQUE REFERENCES signing_request_step_signer (id) ON DELETE RESTRICT, -- RESTRICT: Chữ ký số không thể bị cascade xóa
    khoa_ky BIGINT NOT NULL REFERENCES signing_key (id) ON DELETE RESTRICT,
    hash_tai_lieu VARCHAR(64) NOT NULL, -- SHA-256 hex, phải khớp signing_attempt.document_hash
    thuat_toan VARCHAR(50) NOT NULL,
    chu_ky_so TEXT NOT NULL, -- Raw bytes / Base64 chữ ký số
    ngay_ky TIMESTAMPTZ NOT NULL DEFAULT now(),
    trang_thai_xac_minh signing_verify_status NOT NULL DEFAULT 'CHUA_XAC_MINH',
    file_da_ky VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_signature_hash_sha256 CHECK (
        hash_tai_lieu ~ '^[0-9a-f]{64}$'
    )
);

-- Trigger bảo vệ chữ ký số: Chặn tuyệt đối hành vi xóa chữ ký đã sinh ra
CREATE OR REPLACE FUNCTION prevent_delete_signing_signature()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Chữ ký số điện tử (signing_signature id=%) là bất biến và không thể xóa khỏi CSDL.', OLD.id;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_signing_signature_prevent_delete
  BEFORE DELETE ON signing_signature
  FOR EACH ROW EXECUTE FUNCTION prevent_delete_signing_signature();

-- Bằng chứng số tổng hợp (Manifest Canonical) của attempt sau khi hoàn tất ký
CREATE TABLE signing_manifest (
    id BIGSERIAL PRIMARY KEY,
    signing_attempt_id BIGINT NOT NULL REFERENCES signing_attempt (id) ON DELETE RESTRICT, -- RESTRICT: Manifest không thể bị cascade xóa
    manifest_version SMALLINT NOT NULL DEFAULT 1,
    canonical_json JSONB NOT NULL, -- Chứa snapshot document hash, signers, keys, signatures
    manifest_hash VARCHAR(64) NOT NULL, -- SHA-256 của canonical_json
    storage_key VARCHAR(500),
    status signing_manifest_status NOT NULL DEFAULT 'DRAFT',
    finalized_at TIMESTAMPTZ,
    created_by BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_manifest_attempt_version UNIQUE (
        signing_attempt_id,
        manifest_version
    ),
    CONSTRAINT chk_manifest_hash_sha256 CHECK (
        manifest_hash ~ '^[0-9a-f]{64}$'
    )
);

CREATE TRIGGER trg_signing_manifest_updated_at BEFORE UPDATE ON signing_manifest
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_manifest_attempt ON signing_manifest (signing_attempt_id);

-- Trigger bảo vệ bằng chứng: Chặn xóa manifest đã chốt (FINAL)
CREATE OR REPLACE FUNCTION prevent_delete_final_manifest()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.status = 'FINAL' THEN
    RAISE EXCEPTION 'Bảo toàn bằng chứng pháp lý: Không thể xóa manifest số đã chốt (signing_manifest id=%, version=%).',
      OLD.id, OLD.manifest_version;
  END IF;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_signing_manifest_prevent_delete
  BEFORE DELETE ON signing_manifest
  FOR EACH ROW EXECUTE FUNCTION prevent_delete_final_manifest();

-- Luồng yêu cầu chỉnh sửa (Request Changes) dạng thread thảo luận giữa người ký & người tạo
CREATE TABLE signing_change_thread (
    id BIGSERIAL PRIMARY KEY,
    signing_attempt_id BIGINT NOT NULL REFERENCES signing_attempt (id) ON DELETE CASCADE,
    requested_by BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    status signing_thread_status NOT NULL DEFAULT 'OPEN',
    tieu_de VARCHAR(255) NOT NULL,
    ly_do TEXT NOT NULL,
    released_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_signing_change_thread_updated_at BEFORE UPDATE ON signing_change_thread
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_change_thread_attempt ON signing_change_thread (signing_attempt_id);

-- Chi tiết các tin nhắn thảo luận bên trong thread chỉnh sửa
CREATE TABLE signing_change_message (
    id BIGSERIAL PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES signing_change_thread (id) ON DELETE CASCADE,
    author_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_change_message_thread ON signing_change_message (thread_id);

-- Nhật ký kiểm toán bảo toàn pháp lý (Append-only)
CREATE TABLE signing_audit_log (
    id BIGSERIAL PRIMARY KEY,
    trinh_ky BIGINT NOT NULL REFERENCES signing_request (id) ON DELETE RESTRICT, -- KHÔNG cascade: giữ audit vĩnh viễn
    buoc_ky BIGINT REFERENCES signing_request_step_signer (id) ON DELETE SET NULL,
    nguoi_thuc_hien BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    hanh_dong VARCHAR(50) NOT NULL,
    chi_tiet TEXT,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_log_trinhky ON signing_audit_log (trinh_ky);

-- Hệ thống thông báo và nhắc hạn tích hợp Outbox/Celery Worker
CREATE TABLE signing_notification (
    id BIGSERIAL PRIMARY KEY,
    trinh_ky BIGINT NOT NULL REFERENCES signing_request (id) ON DELETE CASCADE,
    buoc_ky BIGINT REFERENCES signing_request_step_signer (id) ON DELETE SET NULL,
    nguoi_nhan BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    kenh signing_notify_channel NOT NULL,
    loai_thong_bao VARCHAR(50) NOT NULL,
    trang_thai signing_notify_status NOT NULL DEFAULT 'CHO_GUI',
    retry_count INTEGER NOT NULL DEFAULT 0,
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    dedupe_key VARCHAR(255) UNIQUE, -- idempotency key chống gửi trùng lặp
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notification_nguoinhan ON signing_notification (nguoi_nhan);

-- =====================================================================
-- 10. QUẢN LÝ CÔNG VIỆC (task_*)
-- =====================================================================
CREATE TABLE task_congviec (
    id BIGSERIAL PRIMARY KEY,
    noi_dung TEXT NOT NULL,
    ngay_tao_cv DATE NOT NULL,
    ngay_xu_ly DATE NOT NULL, -- hạn xử lý
    yeu_cau_xu_ly TEXT NOT NULL,
    nguoi_tao BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    document_type document_kind, -- văn bản liên quan (có thể trống)
    document_id BIGINT,
    hien_thi BOOLEAN NOT NULL DEFAULT TRUE,
    opened_at TIMESTAMPTZ,
    opened_by BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    approved_at TIMESTAMPTZ,
    approved_by BIGINT REFERENCES accounts_employee (id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_task_document CHECK (
        (
            document_type IS NULL
            AND document_id IS NULL
        )
        OR (
            document_type IS NOT NULL
            AND document_id IS NOT NULL
        )
    )
);

CREATE TRIGGER trg_congviec_updated_at BEFORE UPDATE ON task_congviec
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Chỉ mục phức hợp hỗ trợ tra cứu công việc theo quan hệ đa hình với văn bản liên quan
CREATE INDEX IF NOT EXISTS idx_task_congviec_document ON task_congviec (document_type, document_id);
-- Trạng thái (Chờ xử lý/Đang xử lý/Chờ duyệt/Hoàn thành/Chưa hoàn thành/Quá hạn)
-- là giá trị TÍNH TOÁN ở tầng ứng dụng dựa trên ngay_xu_ly/opened_at/approved_at,
-- KHÔNG lưu cột riêng — đúng theo ghi chú gốc trong tài liệu.

CREATE TABLE task_participant (
    id BIGSERIAL PRIMARY KEY,
    cong_viec BIGINT NOT NULL REFERENCES task_congviec (id) ON DELETE CASCADE,
    can_bo BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    vai_tro task_vaitro NOT NULL,
    CONSTRAINT uq_task_participant UNIQUE (cong_viec, can_bo),
    CONSTRAINT chk_task_participant_role CHECK (
        vai_tro IN (
            'CHU_TRI',
            'CHI_DAO',
            'THAM_GIA'
        )
    )
);

CREATE INDEX idx_participant_congviec ON task_participant (cong_viec);

CREATE TABLE task_comment (
    id BIGSERIAL PRIMARY KEY,
    cong_viec BIGINT NOT NULL REFERENCES task_congviec (id) ON DELETE CASCADE,
    nguoi_ghi BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    noi_dung TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_comment_congviec ON task_comment (cong_viec);

-- File bằng chứng hoàn thành và file trong ý kiến dùng CHUNG bảng này
CREATE TABLE task_attachment (
    id BIGSERIAL PRIMARY KEY,
    cong_viec BIGINT NOT NULL REFERENCES task_congviec (id) ON DELETE CASCADE,
    y_kien BIGINT REFERENCES task_comment (id) ON DELETE CASCADE, -- trống nếu là file giao việc
    tep VARCHAR(500) NOT NULL, -- PDF/DOC/DOCX/JPG/JPEG/PNG, <20MB
    loai task_attachment_loai NOT NULL,
    nguoi_tai BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_attachment_congviec ON task_attachment (cong_viec);

-- =====================================================================
-- 13. PHÒNG HỌP, SINH NHẬT & NHẬT KÝ EMAIL (meetings_*, birthdays_*)
-- =====================================================================
CREATE TABLE meetings_meetingroom (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    location VARCHAR(200) NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    amenities TEXT,
    is_public BOOLEAN NOT NULL DEFAULT TRUE, -- Hiển thị công khai cho CBNV đặt (nếu False chỉ Admin/Lễ tân thấy)
    status meetingroom_status NOT NULL DEFAULT 'AVAILABLE',
    ghi_chu TEXT, -- Ghi chú thiết bị, hướng dẫn sử dụng
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_meetingroom_updated_at BEFORE UPDATE ON meetings_meetingroom
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE meetings_meetingbooking (
    id BIGSERIAL PRIMARY KEY,
    room_id BIGINT NOT NULL REFERENCES meetings_meetingroom (id) ON DELETE RESTRICT,
    organizer_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE RESTRICT,
    department_id BIGINT REFERENCES organizations_donvi (id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    attendees_count INTEGER NOT NULL DEFAULT 1 CHECK (attendees_count > 0),
    purpose TEXT,
    status meetingbooking_status NOT NULL DEFAULT 'CONFIRMED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_booking_time CHECK (end_time > start_time)
);

CREATE INDEX idx_booking_room_date ON meetings_meetingbooking (room_id, date);
-- Chống trùng lịch cùng phòng cùng khung giờ ở tầng DB (yêu cầu extension btree_gist,
-- có sẵn trong contrib của PostgreSQL — hầu hết managed DB đều cho phép CREATE EXTENSION này).
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE meetings_meetingbooking
ADD CONSTRAINT excl_room_time EXCLUDE USING gist (
    room_id
    WITH
        =,
        tsrange (
            date + start_time,
            date + end_time
        )
    WITH
        &&
)
WHERE (status <> 'CANCELLED');

CREATE TABLE birthdays_birthdaywish (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    sender_name VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    card_template VARCHAR(50) NOT NULL DEFAULT 'GOLDEN',
    is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    status birthdaywish_status NOT NULL DEFAULT 'APPROVED',
    sticker_url VARCHAR(500),
    likes_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_birthdaywish_updated_at BEFORE UPDATE ON birthdays_birthdaywish
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX idx_birthdaywish_employee ON birthdays_birthdaywish (employee_id);

CREATE TABLE birthdays_birthdayemaillog (
    id BIGSERIAL PRIMARY KEY,
    employee_id BIGINT NOT NULL REFERENCES accounts_employee (id) ON DELETE CASCADE,
    sent_date DATE NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL,
    recipient_email VARCHAR(254) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    card_template VARCHAR(50) NOT NULL DEFAULT 'GOLDEN',
    status emaillog_status NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ, -- Hẹn thời điểm thử lại tiếp theo cho Celery worker
    smtp_response_code VARCHAR(50),
    opened_at TIMESTAMPTZ,
    clicked_count INTEGER NOT NULL DEFAULT 0,
    email_provider VARCHAR(50),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_emaillog_employee_date UNIQUE (employee_id, sent_date)
);

CREATE TRIGGER trg_emaillog_updated_at BEFORE UPDATE ON birthdays_birthdayemaillog
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;

-- =====================================================================
-- SEED DATA: Cơ cấu tổ chức thực tế (Khối/Khu vực cấp 1 + Đơn vị cấp 2)
-- Nguồn: Mục 11 tài liệu đặc tả — đây là dữ liệu danh mục tổ chức thật
-- của doanh nghiệp, không phải dữ liệu cá nhân/mock, phù hợp để seed.
-- =====================================================================
BEGIN;

-- 1) Chèn các Khối/Khu vực (Cấp 1) — không trùng lặp (Idempotent)
INSERT INTO
    organizations_khoi (ten, thu_tu_hien_thi)
SELECT DISTINCT
    khoi,
    ROW_NUMBER() OVER (
        ORDER BY khoi
    )
FROM (
        VALUES ('HỘI ĐỒNG QUẢN TRỊ'), ('VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ'), ('BAN TỔNG GIÁM ĐỐC'), (
                'VĂN PHÒNG BAN ĐIỀU HÀNH TẠI TP.HCM & HÀ NỘI'
            ), ('KHỐI KINH DOANH'), ('KHỐI NGHIỆP VỤ'), ('KHỐI HỖ TRỢ'), ('KHỐI QUẢN LÝ RỦI RO'), ('KHỐI TÀI CHÍNH'), ('KHỐI KẾ TOÁN'), ('VĂN PHÒNG 2'), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH'
            ), ('KHU VỰC MIỀN BẮC'), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN'
            ), ('KHU VỰC ĐÔNG NAM BỘ'), ('GIÁM ĐỊNH VÙNG')
    ) AS t (khoi)
WHERE
    NOT EXISTS (
        SELECT 1
        FROM organizations_khoi
    );

-- 2) Chèn Đơn vị/phòng ban (Cấp 2), gán khoi_id theo tên Khối tương ứng
INSERT INTO
    organizations_donvi (khoi_id, ten, stt_uu_tien)
SELECT k.id, x.don_vi, ROW_NUMBER() OVER (
        ORDER BY x.khoi, x.don_vi
    )
FROM (
        VALUES (
                'HỘI ĐỒNG QUẢN TRỊ', 'Hội đồng quản trị'
            ), (
                'HỘI ĐỒNG QUẢN TRỊ', 'Ban kiểm toán nội bộ'
            ), (
                'VĂN PHÒNG HỘI ĐỒNG QUẢN TRỊ', 'Văn phòng hội đồng quản trị'
            ), (
                'BAN TỔNG GIÁM ĐỐC', 'Ban tổng giám đốc'
            ), (
                'BAN TỔNG GIÁM ĐỐC', 'Giám đốc vùng'
            ), (
                'VĂN PHÒNG BAN ĐIỀU HÀNH TẠI TP.HCM & HÀ NỘI', 'Văn phòng ban điều hành'
            ), (
                'KHỐI KINH DOANH', 'Ban khách hàng doanh nghiệp'
            ), (
                'KHỐI KINH DOANH', 'Ban khách hàng qua môi giới'
            ), (
                'KHỐI KINH DOANH', 'Ban Bancassurance'
            ), (
                'KHỐI KINH DOANH', 'Ban khách hàng cá nhân'
            ), (
                'KHỐI KINH DOANH', 'Ban chăm sóc khách hàng ĐT'
            ), (
                'KHỐI KINH DOANH', 'Ban dự án phát triển sản phẩm liên kết với các công ty dịch vụ viễn thông'
            ), (
                'KHỐI KINH DOANH', 'Ban dự án lớn'
            ), (
                'KHỐI KINH DOANH', 'Ban dự án khách hàng qua đại lý'
            ), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm con người'
            ), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm tài sản kỹ thuật'
            ), (
                'KHỐI NGHIỆP VỤ', 'Ban tái bảo hiểm'
            ), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm xe cơ giới'
            ), (
                'KHỐI NGHIỆP VỤ', 'Ban bảo hiểm hàng hải, hàng không, dầu khí, năng lượng'
            ), (
                'KHỐI HỖ TRỢ', 'Lãnh đạo khối'
            ), (
                'KHỐI HỖ TRỢ', 'Ban hành chính quản trị'
            ), ('KHỐI HỖ TRỢ', 'Ban nhân sự'), ('KHỐI HỖ TRỢ', 'Ban pháp chế'), (
                'KHỐI HỖ TRỢ', 'Ban công nghệ thông tin'
            ), (
                'KHỐI HỖ TRỢ', 'Ban truyền thông và marketing'
            ), (
                'KHỐI QUẢN LÝ RỦI RO', 'Ban quản lý rủi ro và tuân thủ'
            ), (
                'KHỐI TÀI CHÍNH', 'Ban đầu tư'
            ), (
                'KHỐI TÀI CHÍNH', 'Ban tài chính kế hoạch'
            ), (
                'KHỐI TÀI CHÍNH', 'Ban dự án MIS'
            ), (
                'KHỐI KẾ TOÁN', 'Lãnh đạo khối'
            ), ('KHỐI KẾ TOÁN', 'Ban kế toán'), ('VĂN PHÒNG 2', 'Văn phòng 2'), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Sở giao dịch Bảo Long'
            ), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long TP.HCM'
            ), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Sài Gòn'
            ), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Gia Định'
            ), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Bến Thành'
            ), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Nam Sài Gòn'
            ), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Tân Sơn Nhất'
            ), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Đông Sài Gòn'
            ), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Bảo Long Đông Phương'
            ), (
                'KHU VỰC THÀNH PHỐ HỒ CHÍ MINH', 'Trung tâm kinh doanh Thủ Thiêm'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Hà Nội'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thủ Đô'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thăng Long'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thái Nguyên'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Quảng Ninh'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Hải Phòng'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Phú Thọ'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Bắc Ninh'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Hải Dương'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Nam Định'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Vĩnh Phúc'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Đông Hải'
            ), (
                'KHU VỰC MIỀN BẮC', 'Sở giao dịch miền Bắc'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Ninh Bình'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thái Bình'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Đông Đô'
            ), (
                'KHU VỰC MIỀN BẮC', 'Bảo Long Thanh Hóa'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long KV Tây Nguyên (Daklak)'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Phú Yên'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Đà Nẵng'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Trung Bộ (Huế)'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Bắc Trung Bộ (Nghệ An)'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Khánh Hòa'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Bình Định'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Bình Thuận'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Quảng Ngãi'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Gia Lai'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Lâm Đồng'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Bảo Long Quảng Bình'
            ), (
                'KHU VỰC MIỀN TRUNG TÂY NGUYÊN', 'Trung tâm kinh doanh Sông Hàn'
            ), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Bình Dương'
            ), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Vũng Tàu'
            ), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Đồng Nai'
            ), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Tây Ninh'
            ), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Long An'
            ), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Cần Thơ'
            ), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Cà Mau'
            ), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Kiên Giang'
            ), (
                'KHU VỰC ĐÔNG NAM BỘ', 'Bảo Long Đồng Tháp'
            ), (
                'GIÁM ĐỊNH VÙNG', 'Giám định vùng'
            )
    ) AS x (khoi, don_vi)
    JOIN organizations_khoi k ON k.ten = x.khoi
WHERE
    NOT EXISTS (
        SELECT 1
        FROM organizations_donvi
    );

-- 3) Seed Chức vụ và Tài khoản quản trị hệ thống mẫu (Idempotent, không hard-code ID)
INSERT INTO
    accounts_position (
        display_order,
        name,
        is_public
    )
SELECT 1, 'Quản trị viên', TRUE
WHERE
    NOT EXISTS (
        SELECT 1
        FROM accounts_position
        WHERE
            name = 'Quản trị viên'
    );

-- Đảm bảo có tài khoản quản trị hệ thống mẫu làm nguoi_lap_id nếu chưa có (truy vấn động ID)
INSERT INTO
    accounts_employee (
        username,
        email,
        password,
        ho_ten,
        ngay_sinh,
        chuc_vu_id,
        don_vi_id,
        is_staff,
        is_superuser,
        is_active
    )
SELECT 'admin', 'admin@baolong.vn', 'pbkdf2_sha256$system_seed_placeholder', 'Quản trị hệ thống', '1990-01-01', (
        SELECT id
        FROM accounts_position
        WHERE
            name = 'Quản trị viên'
        LIMIT 1
    ), COALESCE(
        (
            SELECT id
            FROM organizations_donvi
            WHERE
                ten = 'Ban công nghệ thông tin'
            LIMIT 1
        ), (
            SELECT id
            FROM organizations_donvi
            ORDER BY id
            LIMIT 1
        )
    ), TRUE, TRUE, TRUE
WHERE
    NOT EXISTS (
        SELECT 1
        FROM accounts_employee
        WHERE
            username = 'admin'
    ) ON CONFLICT (username) DO NOTHING;

-- Chèn hoặc cập nhật Hồ sơ chung an toàn, idempotent 100% (không cố định stt_uu_tien = 1 nếu đã bị chiếm)
UPDATE records_hoso
SET
    is_he_thong = TRUE
WHERE
    so_ky_hieu = 'HSC'
    AND is_he_thong = FALSE
    AND NOT EXISTS (
        SELECT 1
        FROM records_hoso
        WHERE
            is_he_thong = TRUE
    );

INSERT INTO
    records_hoso (
        stt_uu_tien,
        so_ky_hieu,
        ten_ho_so,
        nguoi_lap_id,
        is_he_thong,
        ghi_chu
    )
SELECT
    CASE
        WHEN NOT EXISTS (
            SELECT 1
            FROM records_hoso
            WHERE
                stt_uu_tien = 1
        ) THEN 1
        ELSE (
            SELECT COALESCE(MAX(stt_uu_tien), 0) + 1
            FROM records_hoso
        )
    END,
    'HSC',
    'Hồ sơ chung',
    (
        SELECT id
        FROM accounts_employee
        WHERE
            username = 'admin'
        LIMIT 1
    ),
    TRUE,
    'Hồ sơ chung mặc định của hệ thống - không được xóa'
WHERE
    NOT EXISTS (
        SELECT 1
        FROM records_hoso
        WHERE
            is_he_thong = TRUE
            OR so_ky_hieu = 'HSC'
    ) ON CONFLICT (so_ky_hieu) DO
UPDATE
SET
    is_he_thong = TRUE;

-- ---------------------------------------------------------------------
-- 4) Seed 5 Nhóm quyền chuẩn (auth_group)
-- ---------------------------------------------------------------------
INSERT INTO
    auth_group (name, ma_nhom_quyen)
VALUES ('Văn thư', 'VT'),
    ('Chuyên viên', 'CV'),
    ('Trưởng phòng', 'TP'),
    ('Ban Giám đốc', 'BGD'),
    ('Quản trị hệ thống', 'ADMIN') ON CONFLICT (name) DO
UPDATE
SET
    ma_nhom_quyen = EXCLUDED.ma_nhom_quyen;

-- ---------------------------------------------------------------------
-- 5) Seed 66 Quyền thao tác chi tiết (auth_permission)
-- ---------------------------------------------------------------------
INSERT INTO
    auth_permission (name, codename, module_ten)
VALUES
    -- Đơn vị, phòng ban (Nhóm 7)
    (
        'Xem danh sách đơn vị/phòng ban',
        'view_donvi',
        'Đơn vị, phòng ban'
    ),
    (
        'Thêm đơn vị/phòng ban',
        'add_donvi',
        'Đơn vị, phòng ban'
    ),
    (
        'Sửa đơn vị/phòng ban',
        'change_donvi',
        'Đơn vị, phòng ban'
    ),
    (
        'Xóa đơn vị/phòng ban',
        'delete_donvi',
        'Đơn vị, phòng ban'
    ),
    (
        'Xuất Excel đơn vị/phòng ban',
        'export_donvi',
        'Đơn vị, phòng ban'
    ),
    -- Chức vụ (Nhóm 7)
    (
        'Xem danh sách chức vụ',
        'view_chucvu',
        'Chức vụ'
    ),
    (
        'Thêm chức vụ',
        'add_chucvu',
        'Chức vụ'
    ),
    (
        'Sửa chức vụ',
        'change_chucvu',
        'Chức vụ'
    ),
    (
        'Xóa chức vụ',
        'delete_chucvu',
        'Chức vụ'
    ),
    -- Loại tài liệu biểu mẫu (Nhóm 7)
    (
        'Xem danh sách loại tài liệu',
        'view_loaitailieubieumau',
        'Loại tài liệu biểu mẫu'
    ),
    (
        'Thêm loại tài liệu',
        'add_loaitailieubieumau',
        'Loại tài liệu biểu mẫu'
    ),
    (
        'Sửa loại tài liệu',
        'change_loaitailieubieumau',
        'Loại tài liệu biểu mẫu'
    ),
    (
        'Xóa loại tài liệu',
        'delete_loaitailieubieumau',
        'Loại tài liệu biểu mẫu'
    ),
    -- Cán bộ nhân viên (Nhóm 7)
    (
        'Xem toàn bộ thông tin CBNV (kể cả năm sinh, Nhóm quyền, mật khẩu)',
        'view_full_cbnv',
        'CBNV'
    ),
    (
        'Xem danh sách CBNV (ẩn field nhạy cảm)',
        'view_list_cbnv',
        'CBNV'
    ),
    (
        'Thêm CBNV',
        'add_cbnv',
        'CBNV'
    ),
    (
        'Sửa CBNV (đầy đủ field)',
        'change_full_cbnv',
        'CBNV'
    ),
    (
        'Sửa thông tin cá nhân của chính mình',
        'change_self_cbnv',
        'CBNV'
    ),
    (
        'Xóa CBNV',
        'delete_cbnv',
        'CBNV'
    ),
    (
        'Duyệt yêu cầu đổi mật khẩu',
        'approve_password_reset_cbnv',
        'CBNV'
    ),
    (
        'Import file CBNV',
        'import_cbnv',
        'CBNV'
    ),
    -- Văn bản đến (Nhóm 2)
    (
        'Xem danh sách/chi tiết văn bản đến',
        'view_vanbanden',
        'Văn bản đến'
    ),
    (
        'Thêm văn bản đến',
        'add_vanbanden',
        'Văn bản đến'
    ),
    (
        'Sửa văn bản đến',
        'change_vanbanden',
        'Văn bản đến'
    ),
    (
        'Xóa văn bản đến',
        'delete_vanbanden',
        'Văn bản đến'
    ),
    (
        'Import file văn bản đến',
        'import_vanbanden',
        'Văn bản đến'
    ),
    (
        'Xuất Excel văn bản đến',
        'export_vanbanden',
        'Văn bản đến'
    ),
    (
        'Xem log user đã xem văn bản đến',
        'view_read_log_vanbanden',
        'Văn bản đến'
    ),
    (
        'Gửi mail toàn hệ thống (văn bản đến)',
        'send_mail_all_vanbanden',
        'Văn bản đến'
    ),
    -- Văn bản đi (Nhóm 2)
    (
        'Xem danh sách/chi tiết văn bản đi',
        'view_vanbandi',
        'Văn bản đi'
    ),
    (
        'Thêm văn bản đi',
        'add_vanbandi',
        'Văn bản đi'
    ),
    (
        'Sửa văn bản đi',
        'change_vanbandi',
        'Văn bản đi'
    ),
    (
        'Xóa văn bản đi',
        'delete_vanbandi',
        'Văn bản đi'
    ),
    (
        'Import file văn bản đi',
        'import_vanbandi',
        'Văn bản đi'
    ),
    (
        'Xuất Excel văn bản đi',
        'export_vanbandi',
        'Văn bản đi'
    ),
    (
        'Xem log user đã xem văn bản đi',
        'view_read_log_vanbandi',
        'Văn bản đi'
    ),
    (
        'Gửi mail toàn hệ thống (văn bản đi)',
        'send_mail_all_vanbandi',
        'Văn bản đi'
    ),
    -- Văn bản mật (Nhóm 2)
    (
        'Xem văn bản mật (chỉ người được liệt kê đích danh)',
        'view_vanbanmat',
        'Văn bản mật'
    ),
    (
        'Thêm văn bản mật',
        'add_vanbanmat',
        'Văn bản mật'
    ),
    (
        'Sửa văn bản mật',
        'change_vanbanmat',
        'Văn bản mật'
    ),
    (
        'Xóa văn bản mật',
        'delete_vanbanmat',
        'Văn bản mật'
    ),
    -- Hồ sơ lưu trữ (Nhóm 3)
    (
        'Xem danh mục hồ sơ',
        'view_hoso',
        'Hồ sơ'
    ),
    (
        'Lập/Thêm hồ sơ',
        'add_hoso',
        'Hồ sơ'
    ),
    (
        'Sửa hồ sơ',
        'change_hoso',
        'Hồ sơ'
    ),
    (
        'Xóa hồ sơ',
        'delete_hoso',
        'Hồ sơ'
    ),
    (
        'Mở/Đóng danh mục hồ sơ',
        'toggle_status_hoso',
        'Hồ sơ'
    ),
    (
        'Đưa văn bản vào / loại ra khỏi hồ sơ điện tử',
        'manage_documents_hoso',
        'Hồ sơ'
    ),
    -- Tài liệu, biểu mẫu (Nhóm 4)
    (
        'Xem tài liệu, biểu mẫu',
        'view_tailieu',
        'Tài liệu, biểu mẫu'
    ),
    (
        'Thêm tài liệu, biểu mẫu',
        'add_tailieu',
        'Tài liệu, biểu mẫu'
    ),
    (
        'Sửa tài liệu, biểu mẫu',
        'change_tailieu',
        'Tài liệu, biểu mẫu'
    ),
    (
        'Xóa tài liệu, biểu mẫu',
        'delete_tailieu',
        'Tài liệu, biểu mẫu'
    ),
    -- Trình ký (Nhóm 5)
    (
        'Xem văn bản trình ký',
        'view_trinhky',
        'Trình ký'
    ),
    (
        'Tạo trình ký',
        'add_trinhky',
        'Trình ký'
    ),
    (
        'Ký (đúng lượt trong sơ đồ)',
        'sign_trinhky',
        'Trình ký'
    ),
    -- Quản lý Công việc (Nhóm 6)
    (
        'Xem công việc',
        'view_congviec',
        'Công việc'
    ),
    (
        'Thêm/Giao việc',
        'add_congviec',
        'Công việc'
    ),
    (
        'Sửa công việc',
        'change_congviec',
        'Công việc'
    ),
    (
        'Xóa công việc',
        'delete_congviec',
        'Công việc'
    ),
    (
        'Duyệt / Hủy duyệt công việc',
        'approve_congviec',
        'Công việc'
    ),
    -- Phòng họp (Nhóm 7)
    (
        'Xem lịch phòng họp',
        'view_schedule_phonghop',
        'Phòng họp (danh mục)'
    ),
    (
        'Đặt phòng họp',
        'add_datphonghop',
        'Đặt phòng họp'
    ),
    (
        'Sửa/Hủy lịch do chính mình đặt',
        'change_own_datphonghop',
        'Đặt phòng họp'
    ),
    (
        'Sửa/Hủy mọi lịch đặt phòng (QT)',
        'change_any_datphonghop',
        'Đặt phòng họp'
    ),
    -- Sinh nhật (Nhóm 7)
    (
        'Xem danh sách sinh nhật',
        'view_sinhnhat',
        'Sinh nhật'
    ),
    (
        'Gửi lời chúc (thủ công)',
        'send_wish_sinhnhat',
        'Sinh nhật'
    ),
    -- Chatbox AI (Nhóm 8)
    (
        'Sử dụng chatbot (chỉ trả lời nội dung người hỏi có quyền Xem)',
        'use_aiassistant',
        'Chatbox AI'
    ) ON CONFLICT (codename) DO
UPDATE
SET
    name = EXCLUDED.name,
    module_ten = EXCLUDED.module_ten;

-- ---------------------------------------------------------------------
-- 6) Seed Mapping Quyền vào Nhóm (auth_group_permissions)
-- Truy vấn động theo codename và ma_nhom_quyen (không hard-code ID)
-- ---------------------------------------------------------------------

-- Nhóm ADMIN: Toàn bộ quyền trong hệ thống
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g
    CROSS JOIN auth_permission p
WHERE
    g.ma_nhom_quyen = 'ADMIN' ON CONFLICT (group_id, permission_id) DO NOTHING;

-- Nhóm BGD (Ban Giám đốc): Toàn quyền xem, ký số, duyệt việc, quản lý lịch họp, sinh nhật, AI
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'BGD'
    AND p.codename IN (
        'view_donvi',
        'view_chucvu',
        'view_loaitailieubieumau',
        'view_list_cbnv',
        'change_self_cbnv',
        'view_vanbanden',
        'view_vanbandi',
        'view_vanbanmat',
        'view_read_log_vanbanden',
        'view_read_log_vanbandi',
        'view_hoso',
        'view_tailieu',
        'view_trinhky',
        'add_trinhky',
        'sign_trinhky',
        'view_congviec',
        'add_congviec',
        'approve_congviec',
        'view_schedule_phonghop',
        'add_datphonghop',
        'change_own_datphonghop',
        'view_sinhnhat',
        'send_wish_sinhnhat',
        'use_aiassistant'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;

-- Nhóm TP (Trưởng phòng): Quyền xem, ký duyệt phòng ban, giao việc, DUYỆT VIỆC, xem log đọc VB đến, đặt phòng họp, AI
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'TP'
    AND p.codename IN (
        'view_donvi',
        'view_chucvu',
        'view_loaitailieubieumau',
        'view_list_cbnv',
        'change_self_cbnv',
        'view_vanbanden',
        'view_vanbandi',
        'view_vanbanmat',
        'view_read_log_vanbanden',
        'view_hoso',
        'view_tailieu',
        'view_trinhky',
        'add_trinhky',
        'sign_trinhky',
        'view_congviec',
        'add_congviec',
        'change_congviec',
        'approve_congviec',
        'view_schedule_phonghop',
        'add_datphonghop',
        'change_own_datphonghop',
        'view_sinhnhat',
        'send_wish_sinhnhat',
        'use_aiassistant'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;

-- Nhóm CV (Chuyên viên): Xử lý nghiệp vụ chuyên môn, TUYỆT ĐỐI KHÔNG CÓ approve_congviec
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'CV'
    AND p.codename IN (
        'view_donvi',
        'view_chucvu',
        'view_loaitailieubieumau',
        'view_list_cbnv',
        'change_self_cbnv',
        'view_vanbanden',
        'view_vanbandi',
        'view_vanbanmat',
        'view_hoso',
        'view_tailieu',
        'view_trinhky',
        'add_trinhky',
        'view_congviec',
        'add_congviec',
        'change_congviec',
        'view_schedule_phonghop',
        'add_datphonghop',
        'change_own_datphonghop',
        'view_sinhnhat',
        'send_wish_sinhnhat',
        'use_aiassistant'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;

-- Nhóm VT (Văn thư): Nghiệp vụ văn thư lưu trữ, văn bản đến/đi/mật, quản lý hồ sơ, tài liệu biểu mẫu
INSERT INTO
    auth_group_permissions (group_id, permission_id)
SELECT g.id, p.id
FROM auth_group g, auth_permission p
WHERE
    g.ma_nhom_quyen = 'VT'
    AND p.codename IN (
        'view_donvi',
        'view_chucvu',
        'view_loaitailieubieumau',
        'view_list_cbnv',
        'change_self_cbnv',
        'view_vanbanden',
        'add_vanbanden',
        'change_vanbanden',
        'delete_vanbanden',
        'import_vanbanden',
        'export_vanbanden',
        'view_read_log_vanbanden',
        'send_mail_all_vanbanden',
        'view_vanbandi',
        'add_vanbandi',
        'change_vanbandi',
        'delete_vanbandi',
        'import_vanbandi',
        'export_vanbandi',
        'view_read_log_vanbandi',
        'send_mail_all_vanbandi',
        'view_vanbanmat',
        'add_vanbanmat',
        'change_vanbanmat',
        'view_hoso',
        'add_hoso',
        'change_hoso',
        'manage_documents_hoso',
        'toggle_status_hoso',
        'view_tailieu',
        'add_tailieu',
        'change_tailieu',
        'view_trinhky',
        'add_trinhky',
        'view_congviec',
        'add_congviec',
        'change_congviec',
        'view_schedule_phonghop',
        'add_datphonghop',
        'change_own_datphonghop',
        'view_sinhnhat',
        'send_wish_sinhnhat',
        'use_aiassistant'
    ) ON CONFLICT (group_id, permission_id) DO NOTHING;

COMMIT;

-- =====================================================================
-- BỔ SUNG CHO DJANGO AUTH VÀ BẢO ĐẢM TƯƠNG THÍCH 100%
-- =====================================================================
CREATE TABLE IF NOT EXISTS auth_user (
    id SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMPTZ,
    is_superuser BOOLEAN NOT NULL,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL,
    is_staff BOOLEAN NOT NULL,
    is_active BOOLEAN NOT NULL,
    date_joined TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_user_groups (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    group_id BIGINT NOT NULL REFERENCES auth_group(id) ON DELETE CASCADE,
    CONSTRAINT auth_user_groups_user_id_group_id_uniq UNIQUE (user_id, group_id)
);

CREATE TABLE IF NOT EXISTS auth_user_user_permissions (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES auth_permission(id) ON DELETE CASCADE,
    CONSTRAINT auth_user_user_permissions_user_id_permission_id_uniq UNIQUE (user_id, permission_id)
);

-- Bỏ bắt buộc NOT NULL để Django đăng ký quyền không bị lỗi
ALTER TABLE auth_permission ALTER COLUMN module_ten SET DEFAULT 'He thong';
ALTER TABLE auth_permission ALTER COLUMN module_ten DROP NOT NULL;

-- Tạo sẵn tài khoản Admin (Username: admin | Mật khẩu: Admin@123)
INSERT INTO auth_user (id, password, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined)
VALUES (1, 'pbkdf2_sha256$870000$Wv9aQd7yZ1kL$h4s7J9mK2pL8xN3qR5tV7wY1zB3cD5eF7gH9jK1mN3p=', TRUE, 'admin', 'Quản Trị Viên', 'Hệ Thống', 'admin@itc.edu.vn', TRUE, TRUE, NOW())
ON CONFLICT (username) DO NOTHING;
