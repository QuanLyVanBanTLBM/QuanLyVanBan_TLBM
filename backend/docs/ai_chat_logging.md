# Log chat AI

Mỗi request `POST /api/ai/chat` ghi đúng một dòng vào logger `qlvb.ai` (`backend/services/ai_logging.py`).
Mức log: `INFO` cho 2xx, `WARNING` cho 4xx, `ERROR` cho 5xx.

```
ai_chat request_id=<id> status=<http> error_stage=<stage> error_reason=<reason> user_id=<id> <số liệu> stage_ms=<stage:ms,...>
```

- `error_stage` và `error_reason` chỉ có khi có exception. Đây là giai đoạn đầu tiên ném exception, kể cả khi exception được xử lý và request vẫn trả 200 (ví dụ retrieval non-SQL bị bỏ qua).
- Với 5xx, dòng `ai_chat exception request_id=<id>` và traceback đầy đủ nằm ngay trước dòng tóm tắt.
- `request_id` là 12 ký tự hex, dùng để nối các dòng của cùng một request.

## Giai đoạn

| Stage | Nội dung | Ghi chú |
|---|---|---|
| `permission` | Kiểm tra quyền `use_aiassistant` | 403, `reason=no_ai_permission` |
| `sql_source` | Đọc tài liệu được phép qua role `qlvb_readonly` | Nhiều nhánh lỗi nhất, xem bảng dưới |
| `sql_index` | Đồng bộ chỉ mục pgvector cho từng tài liệu SQL | `reason` là tên exception |
| `setup` | Khởi tạo LlamaIndex, embedding, LLM | Thiếu API key hoặc cấu hình model lỗi sẽ rơi vào đây |
| `retrieval` | Truy xuất pgvector, lọc quyền | Không có `stage_ms` riêng; xem `hits` và `authz_hits` |
| `llm` | Gọi model sinh câu trả lời | `reason` là tên exception |
| `ask_document` | Lỗi ngoài các stage trên | Ví dụ `match_business_sources` |

## Reason của `sql_source`

| `error_reason` | HTTP | Nguyên nhân | Kiểm tra |
|---|---|---|---|
| `employee_unresolved` | 503 | Không có `accounts_employee` đang hoạt động, `LAM_VIEC`, khớp username | Bản ghi nhân viên của tài khoản |
| `employee_id_invalid` | 503 | Mã nhân viên không hợp lệ | Giá trị `resolve_employee_id` |
| `readonly_alias_missing` | 503 | Không có biến `DB_READONLY_USER` nên không khai báo alias `readonly` | Biến môi trường của server |
| `readonly_role_mismatch` | 503 | Kết nối không dùng role `qlvb_readonly`, role là superuser, hoặc có SELECT trên bảng gốc | Role kết nối và các quyền SELECT |
| `readonly_query_failed` | 503 | Lỗi DB khi đọc view (thiếu view, thiếu GRANT, sai mật khẩu, kết nối lỗi) | Nguyên nhân gốc trong traceback (`__cause__`) |

## Số liệu trong dòng tóm tắt

| Trường | Ý nghĩa |
|---|---|
| `employee_resolved` | Có tìm được nhân viên cho tài khoản hay không |
| `question_chars`, `history_items` | Độ dài câu hỏi và số lượt lịch sử (không ghi nội dung) |
| `has_filename`, `has_category` | Request có chỉ định tài liệu hoặc chủ đề hay không |
| `sql_docs`, `sql_attachments` | Số văn bản và tệp đính kèm mà role đọc được |
| `sql_allowed` | Số tài liệu được đưa vào danh sách cho phép truy xuất |
| `sql_reindexed` | Số tài liệu phải lập chỉ mục lại trong request này |
| `sql_extraction_pending` | Số tài liệu còn tệp chưa trích xuất được văn bản |
| `hits`, `authz_hits` | Số chunk trước và sau khi lọc quyền |
| `fallback` | Có dùng truy xuất dự phòng từ pgvector hay không |
| `target` | Request có tài liệu chỉ định hay không |
| `sources` | Số nguồn đưa vào ngữ cảnh |
| `answer_mode` | `llm`, `no_context`, `model_no_answer`, `conversational`, `inappropriate` |
| `cache_hit` | `True` when an exact shared FAQ answer was served from Redis; `False` otherwise |

The FAQ cache excludes requests with history, a selected file/category, or conversational intent. It stores answers only when every cited source is shared AI knowledge or a static business note; SQL-backed official documents and restricted categories are never cached. Entries expire after 12 hours and the namespace is bounded to 1,000 entries, 10 KiB per entry, and 10 MiB of serialized payload. Updating or removing shared AI knowledge invalidates the namespace without flushing Redis or Celery keys.

Không ghi vào log: câu hỏi, lịch sử hội thoại, tên tệp, tiêu đề tài liệu, nội dung tài liệu.

## Đọc log

Log đi ra stderr của tiến trình backend. Tên service và nơi thu log do vận hành xác nhận.

```bash
# Các request lỗi 5xx
grep "ai_chat request_id=" <file-log> | grep "status=5"

# Toàn bộ dòng của một request
grep "request_id=<id>" <file-log>
```

## Lưu ý

- Ba đường `logger.exception` hiện có trong `rag_service.py` (`SQL document retrieval failed`, `LLM generation failed`, `Document retrieval failed`) vẫn ghi traceback riêng, không có `request_id`. Có thể thấy traceback trùng với traceback của view.
- Cấu hình `LOGGING` trong `backend/config/settings.py` chỉ áp dụng cho logger `qlvb.ai`.
