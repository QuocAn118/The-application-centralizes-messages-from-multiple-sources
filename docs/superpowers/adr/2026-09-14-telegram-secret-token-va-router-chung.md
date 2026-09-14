# ADR 2026-09-14 — Telegram: xác thực secret-token và dùng chung router webhook

Trạng thái: **Chấp nhận / Đã làm** (2026-09-14). Bối cảnh: thêm Telegram làm kênh thứ ba
của #1 để chạy được luồng đầu-cuối thật mà không cần giấy phép kinh doanh (điều kiện Zalo
OA) hay tài khoản Meta Developer (đang lỗi phía Meta). Telegram là kênh **bổ sung cho
test/demo nội bộ**, không thuộc phạm vi đề bài gốc.

---

## A. Xác thực bằng secret-token, không ép theo khuôn HMAC

### Vấn đề
Hai adapter sẵn có đều xác thực webhook bằng chữ ký HMAC trên body thô: Zalo ký
`app_id + raw_body + timestamp + oa_secret`, Meta ký `HMAC-SHA256(app_secret, raw_body)`.
Telegram **không ký request**. Cơ chế duy nhất nó cung cấp là một secret token do mình đặt
lúc `setWebhook`, được gửi lại nguyên văn ở header `X-Telegram-Bot-Api-Secret-Token`.

Cám dỗ là nhồi Telegram vào khuôn "verify chữ ký" sẵn có cho đồng bộ.

### Quyết định
**Viết verifier riêng trong `TelegramAdapter`, so khớp bằng `hmac.compare_digest`** — dùng
hàm so sánh hằng thời gian, nhưng **không** tính HMAC. Không tạo lớp trừu tượng chung cho
"họ xác thực webhook".

Lý do không trừu tượng hoá: kiểm tra code thật cho thấy **không có module xác thực dùng
chung nào tồn tại** — mỗi adapter tự verify trong một hàm private (`_xac_minh_chu_ky`).
Thứ được chia sẻ chỉ là `WebhookSignatureError`, và docstring của nó đã ghi sẵn là dùng
chung cho "Zalo, Meta, và nền tảng thêm sau". Tạo một lớp trừu tượng cho ba cơ chế khác
hẳn nhau (hai kiểu HMAC khác công thức + một kiểu so khớp trực tiếp) sẽ đắt hơn lợi.

### Hệ quả
- **Bảo mật yếu hơn Zalo/Meta, phải ghi rõ:** secret token chứng minh *người gọi* là
  Telegram, **không** chứng minh *body chưa bị sửa*. Ai biết secret gửi được payload bất kỳ.
  Bù lại bằng: secret dài ngẫu nhiên (tối đa 256 ký tự) + **bắt buộc HTTPS**.
- **Secret rỗng ⇒ từ chối tất cả**, không phải bỏ qua kiểm tra. Ngược hẳn với
  `WEBHOOK_VERIFY_TOKEN` (rỗng = bỏ qua) vốn chỉ dùng cho bước verify GET của Meta/Zalo.
  Một webhook công khai không xác thực là lỗ hổng; cấu hình thiếu chỉ là lỗi vận hành sẽ
  lộ ra ngay vì không tin nào vào được.
- Router không đổi: `WebhookSignatureError` vẫn cho ra 403 như hai nền tảng kia (RB-3).

---

## B. Dùng chung router webhook, không tách riêng cho Telegram

### Vấn đề
Có nên thêm `POST /api/v1/webhooks/telegram` riêng, vì Telegram khác hai nền tảng kia ở
cách xác thực?

### Quyết định
**Không.** Dùng tiếp `POST /api/v1/webhooks/{platform}` đã có.

Router hiện tại không chứa logic riêng nền tảng nào: nó nhận `platform` làm path param,
tra adapter qua `IChannelAdapterRegistry`, gọi `parse_webhook`, rồi đẩy vào
`IngestInboundMessage`. Toàn bộ khác biệt của Telegram nằm gọn trong adapter.

### Hệ quả
- Thêm nền tảng thứ tư vẫn không phải đụng presentation.
- **RB-1 được xác nhận bằng thực nghiệm:** thay đổi ở `domain` đúng **một dòng** (thêm
  `TELEGRAM` vào enum `Platform`). Mọi thứ còn lại là một file adapter mới + một migration
  + wiring ở composition root. Đây là lần đầu RB-1 được kiểm chứng bằng một nền tảng thật
  sự khác kiểu (không ký chữ ký), chứ không phải hai nền tảng cùng họ HMAC.

---

## C. Khoá idempotency ghép `chat_id`

### Vấn đề
`external_message_id` là chốt idempotency của `IngestInboundMessage`. Trường tự nhiên để
lấy là `message.message_id` của Telegram.

Nhưng `message_id` của Telegram **chỉ duy nhất trong phạm vi một chat**, không duy nhất
toàn cục — khác `msg_id` của Zalo và `mid` của Meta.

### Quyết định
Dùng `"<chat_id>:<message_id>"` làm `external_message_id`.

### Hệ quả
- Tránh một lỗi **im lặng và mất dữ liệu**: nếu dùng trần `message_id`, tin đầu tiên của
  khách B (message_id = 1) sẽ bị coi là trùng tin đầu tiên của khách A (cũng message_id = 1)
  và bị bỏ qua. Webhook vẫn trả 200, không có log lỗi, tin biến mất.
- Có test e2e riêng khoá hành vi này
  (`test_hai_khach_cung_message_id_khong_bi_coi_la_trung`).

---

## D. Một bot là một kênh (`external_channel_id` = bot id)

### Vấn đề
`external_channel_id` phải tra ra được bản ghi `channels`. Ứng viên: `message.chat.id`
(chat với khách) hay id của bot.

### Quyết định
Dùng **bot id** — phần số trước dấu hai chấm của bot token.

### Hệ quả
- Song song đúng với mô hình sẵn có: "một OA là một kênh, mỗi người nhắn OA là một khách".
- Nếu lấy `chat.id` thì **mỗi khách sẽ thành một kênh riêng**, phá vỡ việc gắn phòng ban
  cho kênh và làm bảng `channels` phình theo số khách.
- Token rỗng/dị dạng cho bot id rỗng → không khớp kênh nào. Cố ý: thà không nhận tin còn
  hơn đoán bừa và gắn tin vào sai kênh.

---

## Ghi nhận sai lệch giữa tài liệu và code thật

Trong lúc đọc code để làm việc này, phát hiện hai chỗ tài liệu mô tả chưa khớp code:

1. **Đường dẫn webhook có tiền tố `/api/v1`.** Spec #1 §7 viết `POST /webhooks/{platform}`,
   nhưng `main.py` mount router với `prefix="/api/v1"`, nên đường thật là
   `POST /api/v1/webhooks/{platform}`. Tài liệu vận hành đã dùng đúng đường thật.
2. **Cột lưu credential tên là `credential`**, không phải `encrypted_credential` như tên
   gọi trong một số mô tả. Spec §8 ghi đúng (`credential`).

Không sửa code theo tài liệu — code là nguồn sự thật; chỉ ghi nhận ở đây.
