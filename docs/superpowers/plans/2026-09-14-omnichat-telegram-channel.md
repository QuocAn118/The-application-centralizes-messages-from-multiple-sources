# OmniChat #1 Telegram — Implementation Plan

> **For agentic workers:** task-by-task. Mỗi task xong: test xanh + ruff/format/mypy/import-linter sạch. Mỗi giai đoạn review trước khi sang tiếp.

**Goal:** Thêm Telegram Bot API làm kênh thứ ba của #1 để chạy được luồng đầu-cuối thật mà không cần Zalo OA (cần GPKD) hay Meta Developer (đang lỗi tài khoản). Telegram là kênh **bổ sung cho test/demo**, không thuộc phạm vi đề bài gốc.

**Spec:** [2026-09-14-omnichat-telegram-channel-design.md](../specs/2026-09-14-omnichat-telegram-channel-design.md)

**Tech Stack:** kế thừa #0–#5 (Python 3.13 · FastAPI · SQLAlchemy 2.0 async · psycopg 3 · PostgreSQL 17 · Alembic · Pydantic v2 · uv · pytest · ruff · mypy · import-linter). **Không thêm dependency** — dùng `httpx` đã có, không cài thư viện Telegram.

## Global Constraints

Kế thừa toàn bộ Global Constraints #0–#5 (event loop Windows, UUID v7 `new_id()`, `timestamptz` UTC, tên test tiếng Việt không dấu, mọi lệnh qua `uv run` trong `backend/`, coverage domain+application ≥ 90%, tổng thể ≥ 80%). Bổ sung cho Telegram:

- **Không sửa luồng chung.** Máy trạng thái `Conversation`, `IngestInboundMessage`, các hook `post_ingest_hooks`/`post_reply_hooks`/`post_close_hooks` **giữ nguyên**. Telegram chỉ là nguồn ingest mới cắm vào luồng có sẵn.
- **Không đổi port `IChannelAdapter`.** Đã kiểm chứng port đủ tổng quát (spec §4). Nếu phát sinh nhu cầu đổi port thì **dừng, báo cáo** — đó là quyết định kiến trúc.
- **import-linter giữ nguyên 16 kept, 0 broken.** Chỉ thêm module tuân theo layer rule sẵn có, không thêm/sửa contract.
- **Xác thực riêng, không ép khuôn HMAC.** Telegram dùng secret-token so khớp hằng thời gian; viết implementation riêng thay vì nhồi vào khuôn HMAC của Zalo/Meta.

## Bản đồ file

| Đường dẫn | Trách nhiệm | Loại |
|---|---|---|
| `src/modules/inbox/domain/value_objects/platform.py` | Thêm `TELEGRAM = "TELEGRAM"` | **Sửa (1 dòng)** |
| `src/modules/inbox/infrastructure/channels/telegram_adapter.py` | `TelegramAdapter`: verify secret-token, chuẩn hoá Update, `sendMessage`/`sendPhoto`, `getFile` | **Mới** |
| `migrations/versions/<rev>_them_telegram_vao_platform.py` | Mở rộng CHECK `ck_channel_platform_hop_le` | **Mới** |
| `src/shared/infrastructure/config.py` | `telegram_bot_token`, `telegram_webhook_secret` | Sửa |
| `src/main.py` | Đăng ký `TelegramAdapter` vào `ChannelAdapterRegistry` | Sửa |
| `backend/.env.example` | Hai biến mới | Sửa |
| `tests/unit/inbox/test_telegram_adapter.py` | Verify, chuẩn hoá, gửi tin, tải ảnh | **Mới** |
| `tests/e2e/test_inbox_api.py` | E2E webhook Telegram vào inbox | Sửa |
| `tests/integration/test_inbox_schema.py` | CHECK constraint nhận `TELEGRAM` | Sửa |

**Không đụng:** router webhook (đã nhận `{platform}` theo path param), `IngestInboundMessage`, registry, `errors.py`, mọi thứ thuộc #2–#5.

## Danh sách Task

### Giai đoạn 1 — Domain + Migration

| Task | Nội dung | Deliverable |
|---|---|---|
| 1 | Thêm `TELEGRAM` vào `Platform` enum | Unit test enum có đủ 4 giá trị |
| 2 | Migration mở rộng CHECK `ck_channel_platform_hop_le` (drop + tạo lại kèm `TELEGRAM`); `downgrade` chặn nếu còn kênh TELEGRAM | Integration test: chèn kênh `TELEGRAM` thành công; giá trị lạ vẫn bị chặn |

### Giai đoạn 2 — Infrastructure adapter

| Task | Nội dung | Deliverable |
|---|---|---|
| 3 | `TelegramAdapter.parse_webhook` — verify secret hằng thời gian; secret rỗng thì từ chối tất cả | Unit: đúng secret pass; sai/thiếu/rỗng ném `WebhookSignatureError` |
| 4 | Chuẩn hoá Update thành `InboundEvent` (text, caption+ảnh, tên khách, `chat_id:message_id`) | Unit: text; ảnh lấy `photo[-1]`; sticker/voice bỏ qua trả rỗng; tên khách ghép đúng |
| 5 | `send_message` qua `sendMessage`; có ảnh thì `sendPhoto` | Unit với `MockTransport`: đúng URL, payload, trả `message_id` |
| 6 | `download_attachment` hai bước `getFile` rồi tải bytes | Unit: gọi đúng hai URL, trả đúng bytes |

### Giai đoạn 3 — Cấu hình + Composition root

| Task | Nội dung | Deliverable |
|---|---|---|
| 7 | `Settings`: `telegram_bot_token`, `telegram_webhook_secret`; cập nhật `.env.example` | Test `.env.example` phủ đủ mọi field `Settings` |
| 8 | Wiring `TelegramAdapter` vào registry ở `main.py` | App khởi động được; registry tra được `TELEGRAM` |

### Giai đoạn 4 — E2E + Tài liệu

| Task | Nội dung | Deliverable |
|---|---|---|
| 9 | E2E: webhook Telegram → tin vào inbox; sai secret trả 403; webhook trùng không nhân đôi; hai khách cùng `message_id` cho hai tin riêng | Test e2e xanh, dùng client giả (không ra mạng) |
| 10 | ADR quyết định secret-token vs HMAC + không tách router | `docs/superpowers/adr/` |
| 11 | Cập nhật roadmap + `docs/van-hanh/ket-noi-kenh-that.md` (mục Telegram) | Tài liệu khớp code thật |

## Tiến độ

| Giai đoạn | Trạng thái | Test |
|---|---|---|
| 1 — Domain + Migration | ✅ XONG | enum 4 giá trị; migration `e5f6a7b8c9d0` upgrade/downgrade/upgrade sạch; schema 9 passed |
| 2 — Infrastructure adapter | ✅ XONG | `test_telegram_adapter.py` 24 passed; coverage adapter 98% |
| 3 — Cấu hình + Wiring | ✅ XONG | `.env.example` phủ đủ mọi field `Settings`; registry tra được cả 4 nền tảng |
| 4 — E2E + Tài liệu | ✅ XONG | `test_inbox_api.py` 13 passed (8 → 13); spec/plan/ADR/roadmap/vận hành đã cập nhật |

**Tổng kết:** 903 passed, 1 skipped (trước: 873) — **+30 test**, không giảm test nào.
ruff sạch · mypy sạch (337 files) · import-linter **16 kept, 0 broken** (đúng bằng trước).
Coverage tổng 94%, `telegram_adapter.py` 98%.

**Xác nhận RB-1:** thay đổi ở `domain` đúng **một dòng** (thêm `TELEGRAM` vào enum). Không
sửa máy trạng thái `Conversation`, `IngestInboundMessage`, các hook, port `IChannelAdapter`,
registry, hay router webhook.

## Ghi chú thực hiện

- **Bot id lấy từ token**, phần trước dấu hai chấm. Token `123456:ABC...` cho bot id `123456`. Đây là `external_channel_id` khi tạo kênh.
- **Không gọi `setWebhook` từ ứng dụng** — thao tác thủ công, ghi ở tài liệu vận hành.
- **Test không được ra mạng**: luôn tiêm `client_factory` trả `httpx.MockTransport`, đúng quy ước Zalo/Meta đang dùng.
