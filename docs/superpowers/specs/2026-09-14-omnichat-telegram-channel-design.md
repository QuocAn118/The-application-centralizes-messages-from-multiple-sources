# OmniChat #1 Telegram — Thiết kế kênh thứ ba

**Trạng thái:** nháp để duyệt · **Ngày:** 2026-09-14 · **Phụ thuộc:** #1 Inbox (đã merge `main`)

## 1. Mục tiêu

Thêm **Telegram Bot API** làm nền tảng thứ ba của sub-project #1, để chạy được luồng
đầu-cuối thật (khách nhắn → inbox → #2 phân phòng → #3 gán người → nhân viên trả lời →
khách nhận) **mà không cần giấy phép kinh doanh** (điều kiện của Zalo OA) hay tài khoản
Meta Developer (đang lỗi phía Meta).

Telegram là kênh **bổ sung cho mục đích test/demo nội bộ**, không thay thế Zalo/Meta
trong phạm vi sản phẩm gốc. Đề bài gốc chỉ yêu cầu Zalo + Meta; Telegram không nằm trong
tiêu chí nghiệm thu của #1.

Đây cũng là phép thử thật cho **RB-1** (spec #1 §2): thêm một nền tảng phải là *viết một
adapter mới*, không sửa domain hay luồng inbox. Nếu RB-1 đúng, thay đổi ở domain phải chỉ
là **một dòng enum**.

## 2. Phạm vi

**Trong phạm vi:**
- Nhận tin đến (text + ảnh) qua webhook `POST /api/v1/webhooks/TELEGRAM`.
- Gửi tin đi (text) qua `sendMessage`; gửi ảnh qua `sendPhoto`.
- Xác thực webhook bằng `X-Telegram-Bot-Api-Secret-Token`, so sánh hằng thời gian.
- Tải ảnh về qua `getFile` rồi tải nội dung (RB-4: URL nền tảng là tạm).
- Migration thêm `TELEGRAM` vào CHECK constraint `channels.platform`.

**Ngoài phạm vi (giữ nguyên, có chủ đích):**
- Không sửa máy trạng thái `Conversation`, `IngestInboundMessage`, hay các hook
  `post_ingest_hooks` / `post_reply_hooks` / `post_close_hooks`.
- Không đổi port `IChannelAdapter` — port hiện tại đã đủ tổng quát (xem §4).
- Không hỗ trợ sticker, voice, video, document, inline keyboard, nhóm/kênh — bỏ qua hợp lệ.
- Không đăng ký webhook tự động (`setWebhook`) từ trong ứng dụng — làm thủ công, ghi ở
  tài liệu vận hành. Lý do: `setWebhook` cần URL công khai chỉ biết lúc triển khai.

## 3. Hợp đồng webhook Telegram

### 3.1 Xác thực — khác hẳn Zalo/Meta

| Nền tảng | Cơ chế | Ký trên |
|---|---|---|
| Zalo | `X-ZEvent-Signature: mac=<sha256>` | `app_id + raw_body + timestamp + oa_secret` |
| Meta | `X-Hub-Signature-256: sha256=<hmac>` | HMAC-SHA256(app_secret, raw_body) |
| **Telegram** | **`X-Telegram-Bot-Api-Secret-Token: <secret>`** | **không ký — so khớp trực tiếp** |

Telegram **không ký request**. Secret token do mình tự đặt khi gọi `setWebhook`, và
Telegram gửi lại **nguyên văn** ở mọi request. Verifier so sánh header với secret trong
config bằng `hmac.compare_digest` (hằng thời gian) — không dùng HMAC.

**Hệ quả bảo mật phải ghi rõ:** vì không ký trên body, secret token bảo vệ *danh tính
người gọi* chứ không bảo vệ *tính toàn vẹn của body*. Ai biết secret có thể gửi payload
bất kỳ. Do đó secret phải **dài và ngẫu nhiên** (Telegram cho tối đa 256 ký tự, bộ ký tự
`A-Z a-z 0-9 _ -`), và endpoint **bắt buộc chạy HTTPS** — HTTP sẽ lộ secret trên đường truyền.

Thiếu header hoặc sai secret → `WebhookSignatureError` → router trả **403**, đúng như
Zalo/Meta (RB-3: không lộ lý do).

### 3.2 Chuẩn hoá tin đến

`Update` của Telegram chuyển thành `InboundEvent` trung lập:

| Trường `InboundEvent` | Nguồn từ Telegram |
|---|---|
| `platform` | `Platform.TELEGRAM` |
| `external_channel_id` | **id của bot** (phần số trước dấu `:` trong bot token) |
| `external_customer_id` | `message.chat.id` |
| `external_message_id` | `<chat_id>:<message_id>` |
| `content.text` | `message.text`, hoặc `message.caption` khi có ảnh |
| `content.attachments` | `message.photo[-1].file_id` (bản lớn nhất) |
| `customer_display_name` | ghép `message.from.first_name` với `last_name`, thiếu thì `username` |

**Vì sao `external_channel_id` là bot id, không phải `chat.id`:** một bot là *một kênh*,
mỗi người chat với bot là *một khách* — song song với "một OA là một kênh, mỗi người nhắn
OA là một khách" ở Zalo. Lấy `chat.id` làm kênh sẽ tạo một kênh mới cho mỗi khách.

**Vì sao `external_message_id` ghép `chat_id`:** `message_id` của Telegram chỉ duy nhất
*trong một chat*, không duy nhất toàn cục. Dùng trần `message_id` sẽ khiến tin của khách B
bị coi là trùng với tin của khách A (idempotency nuốt mất tin thật) — lỗi im lặng, mất dữ liệu.

### 3.3 Tải ảnh — hai bước

Telegram không trả URL ảnh trong webhook, chỉ trả `file_id`. Phải:

1. `GET /bot<TOKEN>/getFile?file_id=<id>` để lấy `result.file_path`
2. `GET /file/bot<TOKEN>/<file_path>` để lấy bytes

`AttachmentRef.url` vì thế mang **`file_id`**, không phải URL thật; adapter tự đổi
`file_id` thành bytes trong `download_attachment`. Đây là khác biệt so với Zalo/Meta (URL
thật) nhưng **không rò rỉ ra ngoài adapter** — port chỉ hứa "đưa ref, trả bytes".

## 4. Vì sao KHÔNG cần đổi port `IChannelAdapter`

Đã đọc code thật trước khi kết luận:

- `parse_webhook(raw_body, headers)` truyền **nguyên headers**, nên cơ chế secret-token
  dùng được không cần thêm tham số.
- `send_message(access_token, external_customer_id, content)` có `access_token` là chuỗi
  trung lập; với Telegram chính là bot token.
- Không có tham số nào riêng của Zalo/Meta trong port.
- `ChannelAdapterRegistry` là map `Platform` sang adapter, dựng từ một `list`, không hard-code.
- `WebhookSignatureError` đã được ghi trong docstring là dùng chung cho "Zalo, Meta, và
  nền tảng thêm sau".

Kết luận: kiến trúc **đủ tổng quát**; không refactor gì. Thay đổi ở domain đúng **một dòng**
(thêm `TELEGRAM` vào enum). RB-1 được xác nhận bằng thực nghiệm, không phải bằng niềm tin.

## 5. Quyết định chốt

| Vấn đề | Chốt |
|---|---|
| Xác thực webhook | So khớp `X-Telegram-Bot-Api-Secret-Token` hằng thời gian; **không** ép theo khuôn HMAC của Zalo/Meta |
| Router | Dùng **chung** `POST /api/v1/webhooks/{platform}` hiện có; không tạo router riêng |
| `external_channel_id` | **Bot id** (số trước dấu hai chấm trong token) — một bot là một kênh |
| `external_message_id` | `<chat_id>:<message_id>` — `message_id` chỉ duy nhất trong một chat |
| `AttachmentRef.url` khi inbound | Mang **`file_id`**, adapter tự đổi sang bytes qua `getFile` |
| Ảnh: chọn bản nào | `photo[-1]` — Telegram sắp xếp tăng dần theo kích thước, bản cuối là lớn nhất |
| Gửi ảnh đi | Có — `sendPhoto` nhận URL công khai, giống Zalo/Meta (cần `ATTACHMENT_PUBLIC_BASE_URL`) |
| Loại tin chưa hỗ trợ | Bỏ qua **hợp lệ** (trả danh sách rỗng, HTTP 200) — không ném lỗi, không tạo tin rỗng |
| `setWebhook` | Thủ công, ghi ở `docs/van-hanh/`; không gọi từ trong ứng dụng |
| CHECK constraint | Migration mới thêm `TELEGRAM`; **không sửa migration cũ** |
| Credential cấp kênh | Bot token, mã hoá bằng `CHANNEL_CIPHER_KEY` như mọi kênh khác |

## 6. Cấu hình mới

| Biến | Ý nghĩa | Rỗng thì sao |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Token từ @BotFather, dạng `<bot_id>:<chuỗi>` | Adapter vẫn dựng được; gửi tin sẽ lỗi. Bot id rỗng thì không khớp kênh nào |
| `TELEGRAM_WEBHOOK_SECRET` | Secret tự đặt, dán vào `setWebhook` | **Mọi webhook bị từ chối 403** — cố ý: rỗng mà vẫn nhận là lỗ hổng |

Quyết định an toàn: secret rỗng thì **từ chối tất cả**, không phải "bỏ qua kiểm tra". Ngược
với `WEBHOOK_VERIFY_TOKEN` (rỗng = bỏ qua, chỉ dùng cho bước verify GET của Meta/Zalo).

## 7. Tiêu chí thành công

1. Webhook Telegram đúng secret thì tin vào inbox đúng kênh/khách; sai hoặc thiếu secret trả 403.
2. Webhook trùng (`chat_id:message_id`) không tạo tin trùng.
3. Hai khách khác nhau có cùng `message_id` cho ra **hai tin riêng** (không bị idempotency nuốt).
4. Nhân viên trả lời trên frontend thì khách nhận được trên Telegram.
5. Ảnh khách gửi xem lại được sau khi `file_id` hết hiệu lực (đã tải về lưu).
6. `import-linter` giữ nguyên **16 kept, 0 broken**.
7. Không giảm số test hiện có của #1.

## 8. Giới hạn đã biết

- **Secret token không bảo vệ toàn vẹn body** (mục 3.1) — chấp nhận, đây là thiết kế của Telegram.
- **Chỉ chat 1-1 với bot.** Nhóm/kênh/supergroup bỏ qua ở bản này.
- **Bot phải tắt Privacy Mode** nếu muốn dùng trong nhóm — ngoài phạm vi.
- **`getFile` giới hạn 20MB** tải về (giới hạn Bot API); lớn hơn sẽ lỗi và ảnh bị bỏ qua.
- **Không đăng ký webhook tự động** — thao tác thủ công một lần, ghi ở tài liệu vận hành.
