# Dữ liệu mẫu và tình trạng nghiệp vụ Trình ký (Nhóm 5)

> **Phạm vi:** mọi người ký trong một cấp có cùng một vai trò (ký chính). Ký nháy, ủy quyền ký và ký thay chưa có.

Cập nhật 23/10/2026, nhánh `feat/5-hoan-thien-nghiep-vu`. Đối chiếu với [`signing-backend-plan.md`](signing-backend-plan.md). Tổng quan module: [`README.md`](README.md).

## 1. Tình trạng các flow nghiệp vụ

| # | Flow | Trước | Sau | Ghi chú |
|---|---|---|---|---|
| 1 | Quy trình mẫu: tạo nháp, sửa, xóa nháp, kích hoạt, ngừng, nhân bản phiên bản; phạm vi công ty/phòng ban | Xong | Xong | `QuyTrinhPage`, `/quy-trinh/` |
| 2 | Tạo hồ sơ nháp (văn bản đi, quy trình, PDF, hạn chót), sửa nháp | Xong | Xong | |
| 3 | Trình ký: khóa tệp và mã băm, chọn người ký theo chức vụ, đặt vị trí ký | Xong | Xong | |
| 4 | Ký tuần tự theo cấp, song song trong cấp | Xong | Xong | |
| 5 | Khóa ký Ed25519 + PIN 8 số (Argon2id + salt, `k_srv`), proof-of-possession, xoay vòng, thu hồi, đổi PIN | Xong | Xong | |
| 6 | Xuất private key đã mã hóa ra file khóa; ký bằng tải file khóa + nhập PIN | Chưa có (chỉ lưu IndexedDB) | Xong | `lib/signing/fileKhoa.ts`, mục 3 |
| 7 | Không đồng ý ban hành (từ chối, kết thúc hồ sơ) | Xong | Xong | |
| 8 | Trả lại để sửa → trao đổi → tải bản sửa → lượt trình mới, ký lại toàn bộ | Xong | Xong | Thêm thông báo tin nhắn |
| 9 | Trình lại sau từ chối (hồ sơ mới, `ho_so_goc`) | Xong | Xong | |
| 10 | Hủy hồ sơ (người tạo; quản trị hủy thay có lý do) | Dở | Xong | Trước: người tạo không được báo khi bị hủy thay, người đã ký không được báo |
| 11 | Thu hồi chữ ký khi cấp còn mở | Xong | Xong | |
| 12 | Hoàn tất: bằng chứng tổng hợp, PDF hoàn tất, xác minh lại | Xong | Xong | |
| 13 | Lịch sử / nhật ký hồ sơ | Dở | Xong | Thêm tên người thực hiện |
| 14 | Thông báo qua email + outbox (gửi lại khi lỗi: `gui_thong_bao_trinh_ky`); không còn trang xem trong ứng dụng | Dở | Xong | Thêm loại `TIN_NHAN`, `NHAC_HAN`, `QUA_HAN`; tab Thông báo đã bỏ (#355) |
| 16 | Nhắc hạn, quá hạn | Chưa có | Xong (MVP) | Lệnh `nhac_han_trinh_ky`; chưa leo thang cấp trên |
| 17 | Ký nháy, ủy quyền ký, thể thức ký thay (KT./TL./TUQ.) | Chưa có | Chưa có | Cần chốt chính sách nghiệp vụ và PR đổi schema riêng |
| 18 | Leo thang quá hạn cho cấp trên trực tiếp | Chưa có | Chưa có | Nhóm 7 chưa có dữ liệu cấp trên trực tiếp |

## 2. Phân quyền theo vai trò (nhóm quyền chuẩn của DDL)

| Nhóm | Trình ký |
|---|---|
| Văn thư (VT) | xem, tạo, gửi trình ký |
| Chuyên viên (CV) | xem, tạo nháp, gửi trình ký (đã cấp `send_trinhky` theo PR #254) |
| Trưởng phòng (TP) | xem, tạo, gửi, ký, hủy thay, quản lý quy trình phòng ban |
| Ban Giám đốc (BGD) | xem, tạo, gửi, ký, hủy thay, xem nhật ký mọi hồ sơ |
| Quản trị (ADMIN) | toàn quyền, quản lý quy trình công ty |

Server kiểm quyền ở từng API; giao diện chỉ ẩn/hiện thao tác.

## 3. File khóa ký

- Tạo khóa ở trang **Cấu hình khóa ký**: trình duyệt sinh cặp khóa Ed25519, đăng ký khóa công khai (chứng minh sở hữu),
  đặt PIN 8 số. Private key được bọc AES-GCM bằng khóa dẫn xuất `HKDF(Argon2id(PIN, salt), k_srv, "wrap")`, lưu trên
  thiết bị và tự tải về file `<mã khóa>.tlbmkey`.
- Ký: hộp thoại ký nhận file khóa và PIN. Trình duyệt kiểm file đúng tài khoản và đúng khóa đang hoạt động, gửi
  verifier của PIN để máy chủ trả `k_srv` (sai 5 lần khóa 15 phút), mở bản bọc và ký SHA-256 của tệp. Bỏ trống file
  thì dùng bản lưu trên thiết bị.
- File khóa chỉ đọc trong trình duyệt, không gửi lên máy chủ. Đổi PIN xoay vòng `k_srv` nên file cũ không còn mở
  được; trang tự tải file mới. Có thể nhập file khóa vào thiết bị khác ở cùng trang.

## 4. Lệnh dữ liệu mẫu `seed_signing_demo`

Tên lệnh theo đề xuất trong [`danh-gia-plan-va-tich-hop.md`](danh-gia-plan-va-tich-hop.md) (`seed_signing_demo` trong
`management/commands`). Đường dẫn này không bị `.gitignore` bỏ qua (`git check-ignore` không khớp; `.gitignore` chỉ bỏ
qua `seed_data.py`, `migrations/*seed*.py`, `seed_accounts.py`).

Đây là lệnh dữ liệu mẫu duy nhất của phân hệ: lệnh cũ `seed_demo_signing` đã gỡ vì trùng chức năng, ghi cứng mật khẩu
trong mã nguồn (trái AGENTS.md mục 6) và sinh khóa bí mật Ed25519 từ chuỗi cố định.

Lệnh tự đủ trên DB vừa `migrate`: đơn vị, chức vụ, nhóm quyền chuẩn có sẵn từ migration; thiếu đơn vị thì tạo.

### 4.1. Dữ liệu tạo ra

- **Tài khoản**: `admin` (Quản trị), `vanthu` (Văn thư, tạo và trình), `chuyenvien` (Chuyên viên, soạn nháp),
  `truongphong` (Trưởng phòng, ký cấp 1), `giamdoc` (Giám đốc, ký cấp 2). Gán đơn vị "Ban công nghệ thông tin"
  (giám đốc: "Ban tổng giám đốc"), chức vụ và nhóm quyền chuẩn. Đơn vị, chức vụ, nhóm quyền dùng dữ liệu nền có sẵn
  (`seed_db`, migration RBAC); văn bản đi tạo qua model `documents.VanBanDi` của Nhóm 2.
- **Quy trình**: `QT-TK-HAI-CAP` (hai cấp tuần tự), `QT-TK-MOT-CAP` (một cấp ký chính), `QT-TK-SONG-SONG`
  (hai người ký song song rồi Giám đốc), `QT-TK-NHAP` (nháp).
- **Hồ sơ** (ghi chú bắt đầu bằng "Dữ liệu mẫu M..:"):

| Mã | Trạng thái | Người cần thao tác |
|---|---|---|
| M01 | Nháp | chuyenvien |
| M02 | Đang ký cấp 1 | truongphong |
| M03 | Đang ký cấp 2 (cấp 1 đã ký kèm ghi chú) | giamdoc |
| M04 | Hoàn thành, có bằng chứng và PDF hoàn tất | — |
| M05 | Không đồng ý ban hành; có hồ sơ trình lại ở trạng thái nháp | vanthu |
| M06 | Trả lại để sửa, đang trao đổi | vanthu, truongphong |
| M07 | Đã sửa, lượt 2 đang ký cấp 2 | giamdoc |
| M08 | Đã hủy | — |
| M09 | Quá hạn ở cấp 1 | truongphong |
| M10 | Hai người ký song song, một người đã ký, một người chờ ký  | truongphong |

Lịch sử và thông báo (`CAN_KY`, `HOAN_THANH`, `TU_CHOI`, `YEU_CAU_SUA`, `HUY`, `TIN_NHAN`, `NHAC_HAN`,
`QUA_HAN`) sinh từ chính các thao tác trên vì lệnh gọi service nghiệp vụ, không ghi bảng trực tiếp.

### 4.2. Mật khẩu và khóa ký

- Mật khẩu tài khoản mẫu đọc từ biến môi trường `DEMO_PASSWORD`; không ghi trong mã nguồn. Tài khoản chưa có mà
  thiếu biến thì lệnh dừng. Tài khoản đã có giữ mật khẩu, trừ khi chạy với `--dat-lai-mat-khau`. Tài khoản `admin`
  chỉ được đặt mật khẩu khi còn mật khẩu không dùng được (sentinel của DDL, DB vừa `migrate`); admin đã khởi tạo bằng
  `seed_db`/`ADMIN_PASSWORD` thì giữ nguyên.
- `--reset`: làm mới bộ hồ sơ mẫu. Lượt trình, chữ ký, nhật ký, bằng chứng tổng hợp bất biến theo trigger của DDL nên
  không xóa được: hồ sơ mẫu cũ còn mở được hủy (có nhật ký), ghi chú đổi sang "Dữ liệu mẫu cũ", ngày tạo và ngày trình
  lùi 30 ngày (không chen vào 5 phiếu gần nhất của Dashboard và đầu danh sách), sau đó tạo bộ mới.
- Ngày trình của các hồ sơ cách nhau 24 giờ để danh sách và Dashboard có ngày khác nhau.
- Chữ ký mẫu dùng khóa Ed25519 tạm sinh trong bộ nhớ, thu hồi ngay sau khi ký; khóa bí mật không lưu. Khi lệnh cần
  ký (lần chạy đầu), khóa đang hoạt động của `truongphong`, `giamdoc`, `admin` được xoay vòng sang khóa tạm rồi thu
  hồi. Sau đó mỗi người tự tạo khóa ký ở trang **Cấu hình khóa ký** để ký tiếp các hồ sơ đang chờ.
- `--email-domain <miền>`: gán email `<username>@<miền>` cho tài khoản mẫu chưa có email. Cần tùy chọn này thì tài
  khoản mẫu mới có email và thông báo mới có kênh email; không có thì thông báo chỉ ghi vào outbox, không có email.

### 4.3. Mật khẩu chung của tài khoản demo

- Cả 5 tài khoản demo (`admin`, `vanthu`, `chuyenvien`, `truongphong`, `giamdoc`) dùng chung **mật khẩu demo của
  lớp**: đặt `ADMIN_PASSWORD` và `DEMO_PASSWORD` cùng một giá trị trong `.env`. Không ghi giá trị mật khẩu vào repo.
- `admin` đã tồn tại với mật khẩu khác: `python manage.py changepassword admin` (hoặc `pnpm manage changepassword
  admin`). Bốn tài khoản còn lại: `python manage.py seed_signing_demo --dat-lai-mat-khau`.
- Windows: không dùng được cú pháp `DEMO_PASSWORD='...' python ...`; ghi vào `backend/.env`:

  ```dotenv
  ADMIN_PASSWORD=<mật khẩu demo của lớp>
  DEMO_PASSWORD=<mật khẩu demo của lớp>
  ```

  rồi chạy `pnpm manage seed_signing_demo --email-domain <miền email>`.

### 4.4. Thử gửi mail thật

- Ghi vào `backend/.env`: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD=<mật khẩu SMTP>`, `DEFAULT_FROM_EMAIL="Hệ thống QLVB <qlvb@baohiembaolong.vn>"`;
  `SIGNING_EMAIL_BACKEND` để trống. `DEFAULT_FROM_EMAIL` trống thì mọi thư SMTP lỗi `Invalid address ''`
  (`manage.py check` báo `signing.W003`).
- Kiểm tra: `pnpm manage check`, rồi `pnpm manage sendtestemail <email nhận>`.
- Chạy `seed_signing_demo --email-domain <miền>` để tài khoản mẫu có email. Email lỗi ghi `THAT_BAI`; sửa cấu hình
  rồi chạy `gui_thong_bao_trinh_ky` để gửi lại.

### 4.5. Chạy local

```bash
pnpm db:setup                                   # hoặc: python scripts/build_db.py --seed
cd backend
DEMO_PASSWORD='<mật khẩu demo của lớp>' python manage.py seed_signing_demo --email-domain <miền email>
python manage.py seed_signing_demo        # chạy lại: không tạo thêm bản ghi
python manage.py nhac_han_trinh_ky               # nhắc hạn/quá hạn (chạy định kỳ)
python manage.py gui_thong_bao_trinh_ky          # gửi lại email lỗi (chạy định kỳ)
```

Cần `SIGNING_DOCUMENT_ROOT` (thư mục lưu tệp PDF) như khi chạy ứng dụng.

### 4.6. Chạy trên máy chủ staging

Deploy staging (`deploy/deploy.sh`, CI) chỉ nâng cấp DB bằng migration, không có bước chạy lệnh dữ liệu mẫu, và
`deploy/` thuộc phần vận hành chung nên PR tính năng không sửa. Sau khi PR vào `staging` được merge và job deploy
xong, người có quyền SSH chạy một lần:

```bash
cd /srv/qlvb/current/backend
set -a; . /etc/qlvb/backend.env; set +a          # cấu hình DB, SIGNING_DOCUMENT_ROOT của staging
DEMO_PASSWORD='<mật khẩu demo của lớp>' /srv/qlvb/current/venv/bin/python manage.py seed_signing_demo \
  --email-domain <miền email>
```

Nếu `backend.env` đã có `DEMO_PASSWORD` thì bỏ phần gán biến trước lệnh. Lệnh chạy lại an toàn. Nên đặt lịch
`nhac_han_trinh_ky` và `gui_thong_bao_trinh_ky` (ví dụ mỗi 15 phút) bằng cron/systemd timer trên máy chủ.

## 5. Dữ liệu cho Dashboard (Nhóm 1)

### 5.1. Selector (gọi trong backend)

`signing.selectors.tong_quan_dashboard(user, gioi_han=5)` trả cùng cấu trúc với API dưới đây. Dashboard gọi selector
này, không truy vấn bảng `signing_*` trực tiếp (AGENTS.md mục 6).

### 5.2. API

`GET /api/v1/signing/dashboard/` — yêu cầu đăng nhập (JWT `Authorization: Bearer <token>`), không tham số; chưa đăng
nhập trả 401. Chỉ dữ liệu của người đang đăng nhập (người tạo hoặc người có tên trong luồng ký); quyền kiểm toán không mở rộng danh sách này.

| Trường | Ý nghĩa |
|---|---|
| `so_cho_ky` | Số hồ sơ đang chờ chính người dùng ký (cùng điều kiện tab "Cần tôi ký duyệt"); dùng cho KPI và thông báo Header |
| `gan_day[]` | Tối đa 5 phiếu liên quan, mới nhất trước theo ngày trình |
| `gan_day[].id` | Mã hồ sơ; trang chi tiết `/approvals/<id>` |
| `gan_day[].tieu_de` | "Số hiệu — trích yếu" của văn bản đi |
| `gan_day[].nguoi_trinh` | Họ tên người trình |
| `gan_day[].ngay_trinh` | ISO 8601 giờ Việt Nam; ngày gửi, hồ sơ nháp dùng ngày tạo |
| `gan_day[].trang_thai` | `NHAP`, `CHO_KY`, `HOAN_THANH`, `TU_CHOI`, `HUY` |
| `gan_day[].nhan_trang_thai` | Nháp, Chờ ký, Đã ký, Từ chối, Đã hủy |
| `gan_day[].can_toi_ky` | `true` khi phiếu đang chờ chính người dùng ký |

Response thật của tài khoản `truongphong` sau khi chạy `seed_signing_demo` trên DB vừa `migrate`:

```json
{
  "so_cho_ky": 2,
  "gan_day": [
    {
      "id": 11,
      "tieu_de": "110/BC-CNTT — Báo cáo đánh giá rủi ro hệ thống thanh toán phí bảo hiểm",
      "nguoi_trinh": "Văn thư Ban CNTT",
      "ngay_trinh": "2026-10-23T15:29:43.256419+07:00",
      "trang_thai": "CHO_KY",
      "nhan_trang_thai": "Chờ ký",
      "can_toi_ky": false
    },
    {
      "id": 4,
      "tieu_de": "104/BC-CNTT — Báo cáo tổng kết công tác an toàn thông tin quý III",
      "nguoi_trinh": "Văn thư Ban CNTT",
      "ngay_trinh": "2026-10-22T15:29:42.189461+07:00",
      "trang_thai": "HOAN_THANH",
      "nhan_trang_thai": "Đã ký",
      "can_toi_ky": false
    },
    {
      "id": 2,
      "tieu_de": "102/TTr-CNTT — Tờ trình mua sắm thiết bị mạng cho văn phòng khu vực",
      "nguoi_trinh": "Văn thư Ban CNTT",
      "ngay_trinh": "2026-10-21T15:29:41.935258+07:00",
      "trang_thai": "CHO_KY",
      "nhan_trang_thai": "Chờ ký",
      "can_toi_ky": true
    },
    {
      "id": 5,
      "tieu_de": "105/ĐX-CNTT — Đề xuất thuê dịch vụ trung tâm dữ liệu dự phòng",
      "nguoi_trinh": "Văn thư Ban CNTT",
      "ngay_trinh": "2026-10-20T15:29:42.467615+07:00",
      "trang_thai": "TU_CHOI",
      "nhan_trang_thai": "Từ chối",
      "can_toi_ky": false
    },
    {
      "id": 3,
      "tieu_de": "103/KH-CNTT — Kế hoạch triển khai hệ thống quản lý văn bản điện tử năm 2027",
      "nguoi_trinh": "Văn thư Ban CNTT",
      "ngay_trinh": "2026-10-19T15:29:42.083004+07:00",
      "trang_thai": "CHO_KY",
      "nhan_trang_thai": "Chờ ký",
      "can_toi_ky": false
    }
  ]
}
```

Tài khoản nên đăng nhập để thấy dữ liệu: `truongphong` (2 hồ sơ chờ ký), `giamdoc` (3 hồ sơ chờ ký), `vanthu`
(người trình, có đủ trạng thái), `admin`.

## 6. Lệnh quản trị của phân hệ

| Lệnh | Mục đích |
|---|---|
| `seed_signing_demo` | Dữ liệu mẫu (mục 4) |
| `nhac_han_trinh_ky` | Thông báo `NHAC_HAN` khi còn dưới 24 giờ tới hạn cấp; `QUA_HAN` mỗi ngày quá hạn (người ký và người tạo) |
| `gui_thong_bao_trinh_ky` | Gửi lại email `CHO_GUI`/`THAT_BAI` (tối đa 5 lần) |
