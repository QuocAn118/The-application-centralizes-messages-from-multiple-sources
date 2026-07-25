# OmniChat Sub-project #1 — Omnichannel Inbox: Thiết kế

> Nối tiếp [Foundation](2026-07-21-omnichat-foundation-design.md) và [roadmap](2026-07-21-omnichat-roadmap.md). Phạm vi chốt qua brainstorm ngày 2026-07-24.

## 1. Mục tiêu

Gom tin nhắn từ nhiều nền tảng (Zalo OA, Facebook Page, Instagram — và **thêm nền tảng khác về sau**) vào một inbox thống nhất; nhân viên đọc, trả lời, và xử lý hội thoại tại một nơi duy nhất. Đây là sub-project tạo ra *giá trị nhìn thấy được* đầu tiên của hệ thống.

Không thuộc #1: phân tích AI/keyword (#2), tự động phân hội thoại (#3), template/quick-reply, gộp danh tính khách đa kênh. #1 **chừa sẵn chỗ móc** cho #3 (mỗi hội thoại có phòng ban + người xử lý gán được).

## 2. Ràng buộc kiến trúc quyết định (đọc trước khi thiết kế chi tiết)

**RB-1 — Adapter là cổng trung lập.** Việc thêm một nền tảng mới phải là *viết một adapter mới*, không sửa domain hay luồng inbox. Do đó domain định nghĩa một `IChannelAdapter` (port); Zalo/Meta chỉ là hai implementation đầu tiên ở tầng infrastructure. Đây là ràng buộc mạnh nhất của #1 vì người dùng dự định tích hợp nhiều nền tảng nữa.

**RB-2 — inbox độc lập với identity.** Module `inbox` mới, song song `identity`, cùng bốn tầng. inbox tham chiếu User/Department **chỉ qua UUID thuần**; không import `identity.domain`. Cần thông tin người dùng thì gọi qua một port `IWorkforceDirectory` do inbox tự định nghĩa, implementation ở infrastructure mới được biết tới identity. `import-linter` thêm contract cấm `inbox → identity`.

**RB-3 — Webhook không đáng tin.** Webhook đến từ Internet: phải verify chữ ký trước khi xử lý, và phải idempotent (nền tảng gửi lại webhook trùng là hành vi bình thường, không được tạo tin trùng).

**RB-4 — Media của nền tảng là tạm.** URL media Zalo/Meta trả về hết hạn; phải tải về lưu lại để lịch sử hội thoại không mất ảnh.

## 3. Ngôn ngữ miền (domain)

| Khái niệm | Ý nghĩa |
|---|---|
| **Channel** | Một tài khoản kết nối trên một nền tảng: một Zalo OA, một Facebook Page, một Instagram account. Thuộc một phòng ban (mặc định của hội thoại đến từ kênh đó). Giữ credential/token của kênh. |
| **Platform** | Loại nền tảng: `ZALO`, `FACEBOOK`, `INSTAGRAM` (enum mở rộng được). |
| **Customer** | Người nhắn tin, định danh bởi (platform + external_id do nền tảng cấp). Mỗi kênh một hồ sơ riêng — **không** gộp danh tính. |
| **Conversation** | Luồng hội thoại giữa một Customer và một Channel. Có trạng thái, phòng ban, người xử lý. |
| **Message** | Một tin trong hội thoại: chiều đến (inbound) hoặc đi (outbound), nội dung text và/hoặc attachment. |
| **Attachment** | Ảnh/file đính kèm, đã tải về và lưu lại. |

### Trạng thái Conversation

```
        tin đến (chưa có kênh→phòng)         Manager phân
  [inbound] ─────────────────────────► CHO_PHAN ───────────► DANG_MO
        │                                                        │
        │ kênh đã gắn phòng                          nhân viên nhận / được giao
        └───────────────────────────────────────────────────► DANG_MO
                                                                 │
                                          nhân viên đánh dấu xong │
                                                                 ▼
                                                              DA_DONG
                                                                 │
                                              khách nhắn tin mới  │
                                                                 ▼
                                                              DANG_MO (mở lại)
```

- `CHO_PHAN`: hội thoại chưa thuộc phòng nào (kênh không gắn sẵn phòng, hoặc luật phân chưa xác định) → chỉ **Manager** phân về phòng. *Ở #3, AI thay Manager làm bước này.*
- `DANG_MO`: đã thuộc một phòng, đang chờ hoặc đang được xử lý.
- `DA_DONG`: nhân viên đánh dấu đã xử lý xong. Tin mới từ khách mở lại (`DANG_MO`).

**Gán người xử lý** (`assigned_user_id`) là tùy chọn và tách khỏi trạng thái: một hội thoại `DANG_MO` có thể chưa có ai nhận. Nhân viên "nhận" hội thoại = gán mình vào.

## 4. Phân quyền (dùng lại RBAC #0)

| Hành động | Admin | Manager | Staff |
|---|---|---|---|
| Xem hội thoại | tất cả | phòng mình + mục chờ-phân | phòng mình |
| Phân hội thoại từ "chờ phân" về phòng | ✓ | ✓ (chỉ về phòng mình) | ✗ |
| Nhận / được giao hội thoại | ✓ | trong phòng mình | trong phòng mình |
| Trả lời (gửi tin) | hội thoại xem được | hội thoại xem được | hội thoại xem được |
| Đánh dấu đã xử lý xong | hội thoại xem được | hội thoại xem được | hội thoại xem được |
| CRUD Channel (kết nối kênh) | ✓ | ✗ | ✗ |

Quy tắc "ai xem được gì" trả lời ở tầng **use case** (phụ thuộc dữ liệu: hội thoại này thuộc phòng nào), như #0 đã làm với User.

## 5. Cổng (ports) mà domain/application định nghĩa

- `IChannelAdapter` — gửi tin đi tới một nền tảng; chuẩn hoá webhook đến thành sự kiện miền chung. Một implementation mỗi nền tảng.
  - `parse_webhook(raw, headers) -> list[InboundEvent]` — verify chữ ký + chuẩn hoá; ném lỗi nếu chữ ký sai.
  - `send_message(channel_credentials, external_customer_id, content) -> SentMessageRef`.
  - `download_attachment(ref) -> bytes` — tải media tạm về.
- `IWorkforceDirectory` — hỏi identity gián tiếp: "user X thuộc phòng nào", "phòng Y có tồn tại/đang hoạt động không". Implementation ở infrastructure gọi sang identity; domain inbox không biết identity tồn tại.
- `IAttachmentStore` — lưu và phục vụ lại media. Implementation dev: đĩa local. Đổi S3 sau không đụng use case.
- `IChannelAdapterRegistry` — tra adapter theo `Platform`. Router webhook dùng nó để chọn adapter đúng.
- `ICredentialCipher` — mã hoá/giải mã credential kênh. Implementation dev: Fernet với khoá từ `.env`. Đổi secret manager sau không đụng use case.

## 6. Realtime

WebSocket một chiều tối thiểu: khi có tin đến (hoặc hội thoại đổi trạng thái), server đẩy một **tín hiệu "có thay đổi"** kèm `conversation_id` tới các client đang xem phạm vi liên quan. Client tự gọi REST API để lấy nội dung. Không truyền nội dung tin qua WebSocket ở #1 — giảm bề mặt state realtime, và tránh phải phân quyền lại trên kênh WS.

Phân phối theo phòng ban: client đăng ký nghe theo phạm vi quyền của mình (Staff/Manager: phòng mình; Admin: tất cả). Việc lọc "ai được nhận tín hiệu nào" dựa trên cùng luật xem hội thoại ở mục 4.

## 7. Webhook — luồng xử lý

```
POST /webhooks/{platform}
  → chọn adapter theo {platform}
  → adapter.parse_webhook(raw, headers): verify chữ ký; nếu sai → 403 (không lộ lý do)
  → với mỗi InboundEvent:
      → idempotency: bỏ qua nếu external_message_id đã xử lý
      → tìm/ tạo Customer (platform + external_id)
      → tìm/ tạo Conversation (channel + customer); mở lại nếu đang DA_DONG
      → nếu conversation chưa có phòng → CHO_PHAN
      → tải attachment (nếu có) qua IAttachmentStore
      → lưu Message (inbound)
      → phát tín hiệu realtime
  → 200 nhanh (xử lý nặng có thể đẩy nền sau; #1 làm đồng bộ trước, ghi chú nợ nếu chậm)
```

Nền tảng coi 2xx là "đã nhận"; trả 200 kể cả khi event trùng (đã idempotent) để nền tảng không gửi lại mãi. Chữ ký sai trả 403.

## 8. Mô hình lưu trữ (bảng mới, module inbox)

- `channels` — id, platform, external_channel_id (OA id / page id / ig id), name, department_id (nullable UUID, tham chiếu identity qua ID), credential (mã hoá/tham chiếu secret), is_active, timestamps.
- `customers` — id, platform, external_id, display_name, avatar_url, channel_id, timestamps. Unique (channel_id, external_id).
- `conversations` — id, channel_id, customer_id, department_id (nullable UUID), assigned_user_id (nullable UUID), status (CHO_PHAN/DANG_MO/DA_DONG), last_message_at, timestamps.
- `messages` — id, conversation_id, direction (INBOUND/OUTBOUND), sender_user_id (nullable UUID, cho outbound), text (nullable), external_message_id (nullable, cho idempotency inbound), status, created_at.
- `attachments` — id, message_id, kind (IMAGE/FILE), stored_path, original_url, content_type, size, created_at.

`department_id`/`assigned_user_id`/`sender_user_id` là UUID thuần, **không** foreign key sang bảng users/departments của identity (giữ độc lập module; toàn vẹn tham chiếu đảm bảo ở tầng use case qua `IWorkforceDirectory`).

## 9. Tiêu chí thành công #1

1. Khách nhắn Zalo/FB/IG → tin hiện trong inbox, đúng phòng nếu kênh gắn phòng, nếu không thì vào "chờ phân".
2. Nhân viên trả lời → khách nhận được trên đúng nền tảng.
3. Gửi/nhận được ảnh; ảnh xem lại được sau khi URL gốc của nền tảng đã hết hạn.
4. Webhook gửi trùng không tạo tin trùng; webhook chữ ký sai bị từ chối (403).
5. Có tin mới → client đang xem phạm vi liên quan được báo realtime.
6. Manager phân được hội thoại từ "chờ phân" về phòng mình; Staff không phân được.
7. `import-linter`: `inbox` không phụ thuộc `identity`; adapter là port, thêm nền tảng không sửa domain.

## 10. Giới hạn đã biết (ghi rõ, không giấu)

- **Không gộp danh tính đa kênh.** Cùng một người nhắn Zalo và FB là hai Customer. Gộp thủ công/để sau.
- **Media lưu đĩa local khi dev.** Chưa bền cho production nhiều bản sao; đổi object storage sau, đã tách qua `IAttachmentStore`.
- **Realtime chỉ báo tín hiệu.** Không có typing/presence; nội dung lấy qua REST.
- **Xử lý webhook đồng bộ.** Nếu tải attachment chậm làm webhook lâu, cần đẩy sang hàng đợi nền — ghi nợ, làm khi thấy chậm thật.
- **Chỉ text + ảnh/file.** Template, quick-reply, nút bấm để iteration sau.

## 11. Quyết định đã chốt (khép câu hỏi mở)

- **Lưu credential kênh:** mã hoá trường token ngay tại DB. Token (Zalo OA token, Meta page/IG token, app secret) được mã hoá đối xứng (Fernet/AES) bằng một khoá đọc từ `.env` trước khi ghi cột `channels.credential`; đọc DB không thấy token thô. Việc mã hoá/giải mã tách sau một port `ICredentialCipher` để đổi sang secret manager (Vault/AWS SM) về sau không đụng use case. Khoá mã hoá là bí mật, nằm trong `.env` (đã gitignore), không commit.
- **FB Page và IG account:** **hai Channel riêng**, mỗi Channel đúng một `Platform` (`FACEBOOK` / `INSTAGRAM`). Nhất quán "một kênh một nền tảng", cho phép gắn phòng ban khác nhau cho Facebook và Instagram, adapter mỗi nền tảng độc lập.
