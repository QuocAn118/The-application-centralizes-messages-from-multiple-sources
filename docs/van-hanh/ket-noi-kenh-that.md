# Kết nối kênh thật & chạy thử đầu-cuối

Tài liệu này là các bước **chỉ bạn làm được** (cần tài khoản Zalo OA / Meta / Anthropic).
Phần cấu hình cục bộ đã xong sẵn — xem "Đã xong" ở cuối.

Mục tiêu: khách nhắn Zalo → tin vào inbox → nhân viên trả lời → khách nhận được.

---

## Bước 1 — Mở một địa chỉ công khai (bắt buộc)

Zalo/Meta phải gọi được vào máy bạn. Máy dev nằm sau NAT nên cần đường hầm:

```bash
cloudflared tunnel --url http://localhost:8003
```

Lệnh in ra một URL dạng `https://<ngau-nhien>.trycloudflare.com`. Giữ cửa sổ này
chạy suốt buổi thử — **URL đổi mỗi lần chạy lại**, đổi thì phải cập nhật lại ở
bước 2 và bước 3.

Đặt URL đó vào `backend/.env`:

```
ATTACHMENT_PUBLIC_BASE_URL=https://<ngau-nhien>.trycloudflare.com
```

> Bỏ trống ô này thì tin vẫn gửi được, nhưng **ảnh đính kèm sẽ không tới tay
> khách** — Zalo/Meta tự tải ảnh từ URL ta cung cấp, không nhận upload trực tiếp.

---

## Bước 2 — Lấy bí mật cấp ứng dụng, điền vào `.env`

| Biến | Lấy ở đâu |
|---|---|
| `ZALO_APP_ID`, `ZALO_OA_SECRET_KEY` | Zalo OA → Quản lý ứng dụng → app của bạn |
| `META_APP_SECRET` | developers.facebook.com → App → Settings → Basic → App Secret |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |

`WEBHOOK_VERIFY_TOKEN` **đã sinh sẵn** trong `.env` — không cần tạo mới, chỉ cần
dán đúng chuỗi đó sang ô "Verify Token" ở bước 3.

Sửa `.env` xong phải **khởi động lại server** (cấu hình chỉ đọc lúc khởi động):

```bash
cd backend
uv run python -m scripts.run_server --port 8003
```

---

## Bước 3 — Đăng ký webhook trên nền tảng

Điền URL webhook (dùng URL công khai ở bước 1, **nhớ có `/api/v1`**):

- Zalo: `https://<url-cong-khai>/api/v1/webhooks/ZALO`
- Facebook: `https://<url-cong-khai>/api/v1/webhooks/FACEBOOK`
- Instagram: `https://<url-cong-khai>/api/v1/webhooks/INSTAGRAM`

Ô "Verify Token" điền đúng giá trị `WEBHOOK_VERIFY_TOKEN` trong `.env`.

Với Meta, nhớ **Subscribe** vào field `messages`. Không subscribe thì webhook
verify vẫn xanh nhưng tin nhắn không bao giờ được gửi tới.

Bắt tay verify đã được kiểm tra sẵn và hoạt động đúng: token đúng → trả lại
challenge; token sai → 403.

---

## Bước 4 — Kết nối kênh (nạp access token của OA/Page)

Đây là **credential cấp kênh**, khác với bí mật cấp ứng dụng ở bước 2. Gọi API
bằng tài khoản ADMIN:

```bash
curl -X POST http://127.0.0.1:8003/api/v1/channels \
  -H "Authorization: Bearer <access_token_admin>" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "ZALO",
    "external_channel_id": "<OA_ID_that>",
    "name": "OA Cong ty",
    "credential": "<OA_ACCESS_TOKEN_that>",
    "department_id": null
  }'
```

- `external_channel_id` phải khớp **chính xác** `oa_id` (Zalo) / Page ID (Meta)
  mà nền tảng gửi trong webhook — sai thì tin đến sẽ bị bỏ vì không tìm ra kênh.
- `credential` được mã hoá bằng `CHANNEL_CIPHER_KEY` trước khi ghi DB và **không
  bao giờ** trả ra response.

> **Ba kênh `ext-zalo` / `ext-facebook` / `ext-instagram` đang có trong DB là dữ
> liệu thử, credential không giải mã được** (mã bằng khoá cũ). Cứ tạo kênh thật
> mới; nếu muốn dọn thì gọi `POST /api/v1/channels/{id}/deactivate`.

---

## Bước 5 — Chạy thử đầu-cuối

1. Từ điện thoại, nhắn tin cho OA/Page bằng một tài khoản **không phải admin**.
2. Kiểm tra tin vào DB / hiện ở inbox:
   - Có `ANTHROPIC_API_KEY`: hội thoại được LLM phân về phòng.
   - Không có: hội thoại nằm ở `CHO_PHAN`, phải phân phòng tay.
3. Mở frontend (`cd frontend && npm run dev` → http://localhost:3000), đăng nhập,
   mở hội thoại, trả lời.
4. Xác nhận khách **nhận được** tin trên điện thoại.
5. Thử gửi kèm một ảnh (chỉ chạy nếu đã đặt `ATTACHMENT_PUBLIC_BASE_URL`).

### Khi có trục trặc

| Hiện tượng | Nguyên nhân thường gặp |
|---|---|
| Nền tảng báo verify thất bại | Sai URL (thiếu `/api/v1`), hoặc token không khớp `.env`, hoặc chưa restart sau khi sửa `.env` |
| Webhook 403 | `ZALO_OA_SECRET_KEY` / `META_APP_SECRET` sai hoặc còn rỗng |
| Webhook 200 nhưng không thấy tin | `external_channel_id` không khớp OA/Page ID; xem log server |
| Trả lời lỗi 500 | Access token kênh sai/hết hạn |
| Khách không nhận được ảnh | `ATTACHMENT_PUBLIC_BASE_URL` rỗng hoặc URL đường hầm đã đổi |
| Webhook chậm/nền tảng gửi lại | Nợ đã biết: hook #2 gọi LLM **đồng bộ** trong request (`webhook_router.py:113`) |

---

## Kết nối Telegram Bot (đường nhanh nhất để test)

Dùng khi chưa có Zalo OA (cần giấy phép kinh doanh) hoặc tài khoản Meta Developer đang
lỗi. Telegram Bot chỉ cần **một tài khoản Telegram thường** — không duyệt, không giấy tờ.
Đây là kênh phục vụ test/demo nội bộ, không thay thế Zalo/Meta trong phạm vi sản phẩm.

Vẫn cần **Bước 1** (địa chỉ công khai) ở trên: Telegram chỉ gọi webhook qua **HTTPS**.

### T1 — Tạo bot, lấy token

1. Mở Telegram, tìm **@BotFather**, bấm Start.
2. Gửi `/newbot`, đặt tên hiển thị, rồi đặt username kết thúc bằng `bot`.
3. BotFather trả token dạng `123456789:AAH...`. **Token này là credential của kênh** —
   giữ bí mật như Zalo OA access token.

Phần số trước dấu hai chấm (`123456789`) là **bot id**, dùng làm `external_channel_id` ở
bước T4.

### T2 — Sinh secret token, điền `.env`

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Điền vào `backend/.env`:

```
TELEGRAM_BOT_TOKEN=123456789:AAH...
TELEGRAM_WEBHOOK_SECRET=<chuỗi vừa sinh>
```

> **Để trống `TELEGRAM_WEBHOOK_SECRET` thì MỌI webhook Telegram bị từ chối 403.** Đây là
> cố ý, khác `WEBHOOK_VERIFY_TOKEN` (để trống = bỏ qua). Telegram không ký body, nên secret
> là thứ duy nhất chứng minh request đến từ Telegram — không có nó thì endpoint là cửa mở.

Sửa `.env` xong phải **khởi động lại server**.

### T3 — Đăng ký webhook

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook"  \
  -H "Content-Type: application/json"  \
  -d '{
    "url": "https://<url-cong-khai>/api/v1/webhooks/TELEGRAM",
    "secret_token": "<TELEGRAM_WEBHOOK_SECRET>"
  }'
```

Trả `{"ok":true,...}` là xong. Kiểm tra lại bất cứ lúc nào:

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Xem `last_error_message` trong kết quả — đây là chỗ Telegram nói thẳng vì sao nó không
gửi được tin tới bạn.

### T4 — Kết nối kênh trong OmniChat

```bash
curl -X POST http://127.0.0.1:8003/api/v1/channels  \
  -H "Authorization: Bearer <access_token_admin>"  \
  -H "Content-Type: application/json"  \
  -d '{
    "platform": "TELEGRAM",
    "external_channel_id": "123456789",
    "name": "Bot CSKH",
    "credential": "123456789:AAH...",
    "department_id": null
  }'
```

- `external_channel_id` là **bot id** (số trước dấu hai chấm), **không phải** id đoạn chat.
  Một bot là một kênh; mỗi người nhắn bot là một khách.
- `credential` là **token đầy đủ** (cả phần sau dấu hai chấm).

### T5 — Chạy thử đầu-cuối

1. Mở Telegram, tìm bot theo username, bấm **Start**, nhắn một câu.
2. Tin phải hiện trong inbox. Có `ANTHROPIC_API_KEY` thì hội thoại được phân phòng; không
   có thì nằm ở `CHO_PHAN`.
3. Trả lời từ frontend, xác nhận nhận được trong Telegram.
4. Gửi thử một ảnh (chỉ hoạt động nếu đã đặt `ATTACHMENT_PUBLIC_BASE_URL`).

### Khi có trục trặc (Telegram)

| Hiện tượng | Nguyên nhân thường gặp |
|---|---|
| `setWebhook` báo lỗi SSL / URL | URL phải là **HTTPS** công khai; `localhost` không dùng được |
| Nhắn bot nhưng inbox trống, `getWebhookInfo` báo 403 | `TELEGRAM_WEBHOOK_SECRET` trong `.env` khác `secret_token` đã đăng ký, hoặc chưa restart server |
| Webhook 200 nhưng không thấy tin | `external_channel_id` không phải bot id (dễ nhầm sang chat id) |
| Bot không phản hồi `/start` | Chưa bấm Start, hoặc token sai |
| Trả lời lỗi 500 | `credential` của kênh không phải token đầy đủ |
| Ảnh khách gửi không hiện | Ảnh >20MB (giới hạn `getFile` của Bot API) |
| Khách không nhận được ảnh | `ATTACHMENT_PUBLIC_BASE_URL` rỗng hoặc URL đường hầm đã đổi |
| Tin trong nhóm không vào inbox | Cố ý: bản này chỉ nhận chat 1-1 với bot |

---

## Đã xong (không cần làm lại)

- `CHANNEL_CIPHER_KEY` — đã sinh khoá Fernet thật, đã kiểm tra mã hoá/giải mã
  đúng. **Không đổi khoá này**: đổi là mọi credential kênh đã lưu thành rác.
- `WEBHOOK_VERIFY_TOKEN` — đã sinh sẵn.
- `CORS_ALLOW_ORIGINS` — đã đặt, preflight từ `localhost:3000` trả 200.
- `.env.example` — đã bổ sung đủ **mọi** biến cấu hình.
- Đã kiểm chứng trên server thật: health 200; verify webhook đúng token → trả
  challenge, sai token → 403; webhook ký đúng → 200, ký sai/không ký → 403.
- Test: 873 passed, 1 skipped.
