# OmniChat #2 — Gemini + hàng đợi nền — Implementation Plan

> **For agentic workers:** task-by-task. Mỗi task xong: test xanh + ruff/format/mypy/import-linter sạch. Mỗi giai đoạn review trước khi sang tiếp.

**Goal:** (1) Thêm Gemini làm nhà cung cấp LLM cho #2, chọn qua cấu hình, giữ Claude dùng lại được. (2) Trả nợ "hook gọi LLM đồng bộ trong webhook": đẩy phân tích sang hàng đợi Procrastinate chạy trên chính PostgreSQL, chịu được restart.

**Spec:** [2026-07-28-omnichat-keyword-ai-design.md](../specs/2026-07-28-omnichat-keyword-ai-design.md) (đã cập nhật) · **ADR:** [2026-09-15-gemini-va-hang-doi-procrastinate.md](../adr/2026-09-15-gemini-va-hang-doi-procrastinate.md)

**Tech Stack:** kế thừa #0–#5. Thêm **một** dependency: `procrastinate>=3` (3.9.0). **Không** cài `google-generativeai` — dùng `httpx` sẵn có (lý do ở ADR mục A).

## Global Constraints

Kế thừa toàn bộ Global Constraints #0–#5. Bổ sung cho đợt này:

- **Không sửa máy trạng thái `Conversation`** ngoài phạm vi cần cho job bất đồng bộ (thực tế: không sửa dòng nào).
- **Không sửa `IngestInboundMessage`** và khoá idempotency đang dùng.
- **import-linter giữ nguyên 16 kept, 0 broken.** Module `src.jobs` đặt ở tầng composition (ngang `main.py`), không nằm trong `src.modules.*` nên không chạm contract nào.
- **Schema Procrastinate phải đi qua Alembic** — giữ nguyên tắc "một nguồn sự thật cho schema".
- **Test không được ra mạng:** classifier Gemini luôn tiêm `httpx.MockTransport`.

## Bản đồ file

| Đường dẫn | Trách nhiệm | Loại |
|---|---|---|
| `src/modules/keyword/infrastructure/classifier/prompt_parsing.py` | Prompt + parse/gác JSON dùng chung mọi nhà cung cấp | **Mới** |
| `src/modules/keyword/infrastructure/classifier/gemini_classifier.py` | Gọi Gemini REST, bóc text khỏi `candidates[]` | **Mới** |
| `src/modules/keyword/infrastructure/classifier/claude_classifier.py` | Bỏ phần đã tách; API công khai giữ nguyên | Sửa |
| `src/jobs/{__init__,app,tasks,wiring,enqueue_hook}.py` | Hàng đợi: App, task, wiring worker, hook đẩy job | **Mới** |
| `scripts/run_worker.py` | Tiến trình worker | **Mới** |
| `migrations/versions/f6a7b8c9d0e1_them_schema_procrastinate.py` | Bọc SQL Procrastinate vào Alembic | **Mới** |
| `src/shared/infrastructure/config.py` | `llm_provider`, `gemini_*`, `queue_enabled` | Sửa |
| `src/main.py` | Chọn nhà cung cấp; chọn hook đẩy-job vs đồng bộ | Sửa |
| `tests/unit/keyword/test_gemini_classifier.py` | 16 test adapter Gemini | **Mới** |
| `tests/integration/test_jobs_queue.py` | 6 test hàng đợi (chịu restart, retry, tốc độ) | **Mới** |
| `tests/e2e/conftest.py` | E2E chạy chế độ đồng bộ | Sửa |
| `backend/.env.example` | Biến mới | Sửa |

**Không đụng:** `IngestInboundMessage`, máy trạng thái `Conversation`, `webhook_router.py`, các hook của #3/#4, mọi thứ thuộc #1/#5.

## Danh sách Task

### Giai đoạn 1 — Gemini classifier

| Task | Nội dung | Deliverable |
|---|---|---|
| 1 | Tách `prompt_parsing.py`; sửa Claude dùng lại | 10 test Claude sẵn có vẫn xanh, không sửa test |
| 2 | `GeminiConversationClassifier` qua `httpx` | Unit: URL, khoá ở header, prompt đúng |
| 3 | Test JSON hỏng / confidence ngoài [0,1] / UUID sai / HTTP lỗi | 16 test xanh |
| 4 | Config `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL` + wiring | `.env.example` phủ đủ field `Settings` |

### Giai đoạn 2 — Hàng đợi Procrastinate

| Task | Nội dung | Deliverable |
|---|---|---|
| 5 | **Kiểm tra khả thi** bọc schema vào Alembic *trước khi làm gì khác* | `SchemaManager.get_schema()` trả SQL → khả thi |
| 6 | Revision `f6a7b8c9d0e1` + downgrade xoá sạch | upgrade→downgrade→upgrade sạch trên DB thật |
| 7 | `src/jobs/`: App, task (retry), wiring worker, hook đẩy job | mypy sạch, import-linter 16 kept |
| 8 | `scripts/run_worker.py` | Chạy thật, nhặt job thật, xử lý xong |
| 9 | Wiring `QUEUE_ENABLED` ở `main.py` | Bật/tắt được, có log cảnh báo |

### Giai đoạn 3 — Test + Tài liệu

| Task | Nội dung | Deliverable |
|---|---|---|
| 10 | Test chịu restart: đẩy job, không worker → job vẫn nằm trong bảng | Xanh |
| 11 | Test worker nhặt job; test chạy lại; test hết retry → `failed`, hội thoại ở `CHO_PHAN` | Xanh |
| 12 | Test đẩy job nhanh hơn hẳn gọi LLM | Xanh |
| 13 | ADR + spec + plan + tài liệu vận hành (mục chạy worker) | Tài liệu khớp code thật |

## Tiến độ

| Giai đoạn | Trạng thái | Test |
|---|---|---|
| 1 — Gemini classifier | ✅ XONG | `test_gemini_classifier.py` 16 passed; 10 test Claude cũ vẫn xanh |
| 2 — Hàng đợi Procrastinate | ✅ XONG | Migration round-trip sạch; worker chạy thật nhặt được job |
| 3 — Test + Tài liệu | ✅ XONG | `test_jobs_queue.py` 6 passed |

**Tổng kết:** 925 passed, 1 skipped (trước: 903) — **+22 test**, không giảm test nào.
ruff sạch · mypy sạch (344 files) · import-linter **16 kept, 0 broken** (đúng bằng trước).

## Ghi chú thực hiện

- **Worker là tiến trình RIÊNG.** Không bật worker thì webhook vẫn nhận tin bình thường nhưng AI không bao giờ chạy — hội thoại ở mãi `CHO_PHAN`, **không có lỗi nào hiện ra**. Đây là bẫy dễ gặp nhất; đã ghi vào tài liệu vận hành.
- **`max_attempts` đếm số lần THỬ LẠI**, không phải tổng số lần chạy (`3` → tối đa 4 lần). Phát hiện khi test, đã khoá bằng assertion.
- **`replace_connector` là context manager**, không phải setter — dùng sai thì test âm thầm ghi vào DB dev thay vì DB test.
- **E2E chạy chế độ đồng bộ** (`QUEUE_ENABLED=false` trong `app_test`): test e2e kiểm hành vi trong một request, không có worker. Hàng đợi được kiểm riêng ở `test_jobs_queue.py`.
