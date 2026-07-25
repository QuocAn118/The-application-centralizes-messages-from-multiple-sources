# OmniChat #1 Omnichannel Inbox — Implementation Plan

> **For agentic workers:** dùng subagent-driven-development để thực hiện task-by-task. Steps dùng checkbox (`- [ ]`).

**Goal:** Gom tin nhắn Zalo OA / Facebook / Instagram vào một inbox thống nhất; nhân viên đọc, trả lời (text + ảnh/file), và xử lý hội thoại theo phòng ban. Kiến trúc để thêm nền tảng mới dễ dàng.

**Spec:** [2026-07-24-omnichat-inbox-design.md](../specs/2026-07-24-omnichat-inbox-design.md)

**Tech Stack:** kế thừa Foundation (Python 3.13 · FastAPI · SQLAlchemy 2.0 async · psycopg 3 · PostgreSQL 17 · Alembic · Pydantic v2 · uv · pytest · ruff · mypy · import-linter). Thêm: `cryptography` (Fernet mã hoá credential), `httpx` (gọi API Zalo/Meta — đã có ở dev deps), WebSocket của FastAPI/Starlette (đã có).

## Global Constraints

Kế thừa toàn bộ Global Constraints của [Foundation](2026-07-21-omnichat-foundation.md) (event loop Windows, UUID v7 qua `new_id()`, timestamptz UTC, tên test tiếng Việt không dấu, mọi lệnh qua `uv run` trong `backend/`, coverage domain+application ≥ 90%). Bổ sung riêng cho #1:

- **Module mới `inbox` độc lập `identity`.** `src/modules/inbox/**` **không được import** `src/modules/identity/**`. Tham chiếu User/Department chỉ qua `UUID` thuần. `import-linter` thêm contract cấm `inbox → identity` (cả hai chiều domain). Cần dữ liệu identity thì gọi qua port `IWorkforceDirectory`; implementation ở `inbox/infrastructure` mới được biết identity.
- **Adapter là port.** `inbox/domain` định nghĩa `IChannelAdapter`; mỗi nền tảng một implementation ở `inbox/infrastructure/channels/`. Thêm nền tảng = thêm một file adapter + đăng ký, **không sửa** domain/use case.
- **Webhook verify chữ ký + idempotent.** Chữ ký sai → 403 (không lộ lý do). Event trùng (theo `external_message_id`) → bỏ qua, vẫn trả 200.
- **Credential kênh mã hoá trước khi lưu.** Fernet với khoá từ `.env` (`CHANNEL_CIPHER_KEY`), tách sau port `ICredentialCipher`. Không log/serialize token thô ra ngoài.
- **Media tải về lưu lại.** URL nền tảng tạm thời; tải qua `IAttachmentStore`, dev lưu đĩa local dưới `backend/var/attachments/` (gitignore), phục vụ lại qua API của mình.
- **Realtime chỉ đẩy tín hiệu.** WebSocket gửi `{conversation_id, loai_thay_doi}`, không gửi nội dung tin.

## Bản đồ file (module inbox)

| Đường dẫn | Trách nhiệm |
|---|---|
| `src/modules/inbox/domain/value_objects/platform.py` | Enum `Platform` (ZALO/FACEBOOK/INSTAGRAM) |
| `src/modules/inbox/domain/value_objects/message_content.py` | `MessageContent`, `AttachmentRef` (text + media chuẩn hoá) |
| `src/modules/inbox/domain/entities/channel.py` | `Channel` |
| `src/modules/inbox/domain/entities/customer.py` | `Customer` |
| `src/modules/inbox/domain/entities/conversation.py` | `Conversation` + máy trạng thái CHO_PHAN/DANG_MO/DA_DONG |
| `src/modules/inbox/domain/entities/message.py` | `Message` |
| `src/modules/inbox/domain/entities/attachment.py` | `Attachment` |
| `src/modules/inbox/domain/repositories/` | Interface repository (Channel/Customer/Conversation/Message) |
| `src/modules/inbox/domain/ports.py` | `IChannelAdapter`, `IAttachmentStore`, `ICredentialCipher`, `IWorkforceDirectory`, `IRealtimeNotifier`, `InboundEvent` |
| `src/modules/inbox/application/use_cases/` | Một file một use case |
| `src/modules/inbox/application/dto/` | DTO (InboxItem, ConversationView...) |
| `src/modules/inbox/infrastructure/models/` | SQLAlchemy ORM model (5 bảng) |
| `src/modules/inbox/infrastructure/mappers/` | ORM ↔ domain |
| `src/modules/inbox/infrastructure/repositories/` | Repository implementation |
| `src/modules/inbox/infrastructure/channels/zalo_adapter.py` | Adapter Zalo OA |
| `src/modules/inbox/infrastructure/channels/meta_adapter.py` | Adapter Meta (FB + IG) |
| `src/modules/inbox/infrastructure/channels/registry.py` | `ChannelAdapterRegistry` |
| `src/modules/inbox/infrastructure/attachments/local_store.py` | `LocalAttachmentStore` |
| `src/modules/inbox/infrastructure/security/fernet_cipher.py` | `FernetCredentialCipher` |
| `src/modules/inbox/infrastructure/directory/workforce_directory.py` | `IdentityWorkforceDirectory` (chỉ chỗ này chạm identity) |
| `src/modules/inbox/infrastructure/realtime/ws_notifier.py` | `WebSocketNotifier` + connection manager |
| `src/modules/inbox/presentation/routers/webhook_router.py` | `POST /webhooks/{platform}` |
| `src/modules/inbox/presentation/routers/inbox_router.py` | REST inbox: list/xem/trả lời/phân/đóng |
| `src/modules/inbox/presentation/routers/channel_router.py` | CRUD Channel (Admin) |
| `src/modules/inbox/presentation/routers/ws_router.py` | WebSocket endpoint |
| `src/modules/inbox/presentation/schemas/` | Pydantic request/response |

## Danh sách Task

Thực hiện tuần tự. Mỗi task xong: test xanh + ruff/mypy/import-linter sạch, commit.

### Giai đoạn 1 — Domain inbox (thuần, không I/O)

| Task | Nội dung | Deliverable kiểm chứng được |
|---|---|---|
| 1 | `Platform`, `MessageContent`/`AttachmentRef` value objects | Unit test; import-linter thấy package inbox |
| 2 | Entity `Channel`, `Customer` | Unit test bất biến (customer unique theo platform+external_id) |
| 3 | Entity `Conversation` + máy trạng thái | Unit test: CHO_PHAN→DANG_MO→DA_DONG, mở lại khi có tin mới, phân phòng chỉ hợp lệ khi CHO_PHAN |
| 4 | Entity `Message`, `Attachment` | Unit test: inbound cần external_id, outbound cần sender_user_id |
| 5 | Repository interfaces + ports (`IChannelAdapter`, `IAttachmentStore`, `ICredentialCipher`, `IWorkforceDirectory`, `IRealtimeNotifier`) + fakes in-memory | Fake dùng được trong test use case; import-linter cấm inbox→identity |

### Giai đoạn 2 — Use case (application, dùng fake)

| Task | Nội dung | Deliverable |
|---|---|---|
| 6 | `IngestInboundMessage` (webhook → customer/conversation/message, idempotency, phân phòng theo kênh) | Unit test: tin mới tạo hội thoại; event trùng không tạo trùng; kênh không gắn phòng → CHO_PHAN |
| 7 | `ReplyToConversation` (nhân viên gửi tin đi qua adapter + lưu outbound) | Unit test: phân quyền theo phòng; gọi adapter.send; lưu message outbound |
| 8 | `AssignConversationToDepartment` (Manager phân từ CHO_PHAN) + `TakeConversation` (nhận) + `CloseConversation` (đánh dấu xong) | Unit test: chỉ Manager phân; Staff không; đóng rồi tin mới mở lại |
| 9 | `ListInbox` + `GetConversation` (lọc theo phạm vi quyền, mục chờ-phân) | Unit test: Staff phòng mình, Manager +chờ-phân, Admin tất cả |
| 10 | CRUD Channel use cases (Admin) + mã hoá credential qua `ICredentialCipher` | Unit test: chỉ Admin; credential không lưu thô |

### Giai đoạn 3 — Hạ tầng lưu trữ + adapter

| Task | Nội dung | Deliverable |
|---|---|---|
| 11 | ORM models 5 bảng + Alembic migration | Integration test schema trên PostgreSQL thật (unique, index, timestamptz) |
| 12 | Mappers + repository implementations | Integration test round-trip từng repository |
| 13 | `FernetCredentialCipher` + `LocalAttachmentStore` | Unit/integration: mã hoá vòng tròn; lưu+đọc lại file |
| 14 | `IdentityWorkforceDirectory` (chỗ duy nhất chạm identity) | Integration test: đọc được phòng/nhân viên qua identity repo |
| 15 | Zalo adapter: parse webhook (verify chữ ký) + send + download | Unit test với payload mẫu thật; chữ ký sai bị từ chối |
| 16 | Meta adapter (FB + IG): parse webhook + send + download | Unit test với payload mẫu; X-Hub-Signature-256 |
| 17 | `ChannelAdapterRegistry` | Unit test: tra đúng adapter theo Platform |

### Giai đoạn 4 — HTTP + realtime + hoàn thiện

| Task | Nội dung | Deliverable |
|---|---|---|
| 18 | Webhook router `POST /webhooks/{platform}` | e2e: webhook Zalo/Meta giả → tin vào inbox; trùng không nhân đôi; chữ ký sai 403 |
| 19 | Inbox REST router (list/xem/trả lời/phân/nhận/đóng) + schemas | e2e phân quyền theo phòng, luồng trả lời |
| 20 | Channel CRUD router (Admin) | e2e: Admin tạo kênh, credential không lộ ra response |
| 21 | WebSocket notifier + ws router | e2e: tin mới → client nhận tín hiệu; lọc theo phạm vi quyền |
| 22 | Đăng ký router vào `create_app`, wiring DI, cập nhật CI/README | Toàn bộ test xanh; import-linter contract mới kept; test luồng đầy-đủ đa kênh |

## Ghi chú thực hiện

- **Nợ kỹ thuật chấp nhận (ghi trong spec mục 10):** không gộp danh tính đa kênh; media đĩa local; realtime chỉ tín hiệu; webhook xử lý đồng bộ; chỉ text+ảnh/file.
- **Chỗ móc cho #3:** `Conversation.department_id`/`assigned_user_id` + trạng thái CHO_PHAN chính là nơi #3 (auto-assignment) sẽ điền tự động thay Manager.
- **Payload mẫu adapter:** dùng payload thật rút gọn từ tài liệu Zalo/Meta trong unit test (không gọi mạng); test tích hợp mạng thật để cuối, thủ công, không vào CI.

Chi tiết từng task (Files/Interfaces/Steps + code) sẽ viết trong các file phần tiếp theo khi bắt đầu từng giai đoạn, theo đúng cách Foundation đã làm.
