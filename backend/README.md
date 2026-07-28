# OmniChat Backend

Nền tảng backend cho hệ thống tập trung tin nhắn đa kênh OmniChat.

## Yêu cầu môi trường

- Python 3.13
- PostgreSQL 17 (cài native, không dùng Docker)
- uv

## Cài đặt

```bash
cd backend
uv sync
cp .env.example .env
```

Sửa `.env`, đặt `JWT_SECRET_KEY` bằng khoá thật:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Tạo cơ sở dữ liệu

```bash
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -c "CREATE DATABASE omnichat;"
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -h localhost -c "CREATE DATABASE omnichat_test;"
```

## Chạy test

```bash
uv run pytest tests/unit -v                 # nhanh, không cần cơ sở dữ liệu
uv run pytest tests/integration -v          # cần PostgreSQL
uv run pytest -v                            # toàn bộ
```

## Kiểm tra chất lượng mã

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run lint-imports
```

## Tạo quản trị viên đầu tiên

Hệ thống không có đăng ký công khai. Sau khi áp migration, chạy:

```bash
uv run python -m scripts.seed_admin
```

## Chạy ứng dụng

```bash
uv run uvicorn src.main:app --reload
```

Tài liệu API: http://localhost:8000/docs

## Migration

```bash
uv run alembic upgrade head                        # áp migration mới nhất (DB dev)
uv run alembic revision --autogenerate -m "mô tả"  # sinh migration mới
uv run alembic downgrade -1                        # lùi một bước
```

Cơ sở dữ liệu test dùng cùng migration; áp bằng cách trỏ `DATABASE_URL` sang nó:

```bash
DATABASE_URL="postgresql+psycopg://postgres@localhost:5432/omnichat_test" \
  uv run alembic upgrade head
```

## Kiến trúc

Clean Architecture tổ chức theo module dọc. Quy tắc phụ thuộc:

```
presentation → application → domain
                    ↑            ↑
                    └ infrastructure ┘
```

`domain/` chỉ import thư viện chuẩn. `import-linter` kiểm tra quy tắc này trong
CI — nếu vi phạm, pipeline sẽ đỏ.

Hai module song song: `identity` (người dùng, phòng ban, xác thực) và `inbox`
(kênh, hội thoại, tin nhắn đa nền tảng). `import-linter` bắt buộc **`inbox`
không phụ thuộc `identity`**: inbox tham chiếu User/Department qua UUID thuần và
port `IWorkforceDirectory`; chỉ `inbox/infrastructure/directory` được chạm
identity, và `main.py` (composition root) tiêm nó vào qua `app.state`.

## Module Inbox (đa kênh)

Gom tin nhắn Zalo OA / Facebook / Instagram vào một inbox; nhân viên đọc, trả
lời, xử lý theo phòng ban.

- **Webhook**: `POST /api/v1/webhooks/{platform}` (`ZALO`/`FACEBOOK`/
  `INSTAGRAM`). Adapter verify chữ ký (`X-ZEvent-Signature` cho Zalo,
  `X-Hub-Signature-256` cho Meta) trên **body thô**; sai chữ ký → 403 không lộ
  lý do. Idempotent theo `external_message_id`; trùng vẫn trả 200.
- **REST**: `GET /inbox`, `GET /inbox/{id}`, `POST /inbox/{id}/{reply|assign|
  take|close}`. Phân quyền theo phòng ở tầng use case (Staff: phòng mình;
  Manager: +chờ-phân; Admin: tất cả).
- **Channel CRUD** (Admin): `GET/POST /channels`, `PATCH /channels/{id}`,
  `POST /channels/{id}/deactivate`. Credential mã hoá Fernet trước khi lưu,
  **không bao giờ ra response**.
- **Realtime**: WebSocket `/ws/inbox?token=<access_token>` chỉ đẩy *tín hiệu*
  `{conversation_id, change}`, lọc theo phạm vi quyền; client tự gọi REST lấy
  nội dung.

Biến môi trường thêm (xem `.env.example`): `CHANNEL_CIPHER_KEY` (Fernet),
`ATTACHMENT_STORAGE_DIR`, `ZALO_APP_ID`, `ZALO_OA_SECRET_KEY`, `META_APP_SECRET`,
`WEBHOOK_VERIFY_TOKEN`.

Nợ đã biết ở #1: media chỉ text+ảnh/file, tải về lưu đĩa local (`var/`, không
commit); gửi đi mới hỗ trợ text; xử lý webhook đồng bộ; không gộp danh tính khách
đa kênh.

## Module HRM (nhân sự vận hành)

Ca làm việc + phân ca, KPI (mục tiêu do Manager đặt, thực đạt tính từ Inbox), và
đơn từ nội bộ với phê duyệt một cấp. Module `hrm` độc lập — không import
`identity` lẫn `inbox`; mọi tham chiếu chéo qua UUID + port, wiring ở
composition root.

- **Ca & phân ca**: `GET/POST /shifts`, `PATCH /shifts/{id}`,
  `POST /shifts/{id}/deactivate`; `POST /shift-assignments`,
  `POST /shift-assignments/{id}/cancel`, `GET /shift-assignments`. Chồng ca
  (cùng nhân viên, cùng ngày, giẫm giờ) → 409; ngày quá khứ/giờ ngược → 422.
  Manager thao tác phòng mình; Admin mọi phòng; Staff xem ca của mình.
- **KPI**: `POST /kpi-targets` (đặt/cập nhật), `GET /kpi-targets`,
  `GET /kpi-progress` (ghép mục tiêu + thực đạt + % hoàn thành). Thực đạt lấy
  từ Inbox qua port `IPerformanceSource`. Chỉ số "càng thấp càng tốt"
  (`AVG_RESPONSE_MINUTES`) tính % ngược chiều.
- **Đơn từ**: `POST /requests`, `GET /requests`, `GET /requests/{id}`,
  `POST /requests/{id}/{cancel|approve|reject}`. Một cấp: đơn Staff → Manager
  phòng đó; đơn Manager → Admin; không tự duyệt đơn mình. Đơn đã quyết là bất
  biến; từ chối bắt buộc kèm lý do.

Nợ đã biết ở #4: KPI `CONVERSATIONS_CLOSED` đếm xấp xỉ theo `updated_at` (inbox
chưa có `closed_at`); `AVG_RESPONSE_MINUTES` chưa tính (trả `null`); không chấm
công thực tế; ca không qua nửa đêm; realtime đơn từ chỉ ghi log (client polling
REST) — realtime đầy đủ và mốc đóng chính xác để #5.

## Ghi chú khi phát triển trên Windows

psycopg không chạy được trên `ProactorEventLoop` — event loop mặc định của
Windows từ Python 3.8. Vì vậy mọi entry point chạy code async đều gọi
`cau_hinh_event_loop()` từ `src/shared/infrastructure/event_loop.py` trước khi
mở kết nối: `tests/conftest.py`, `migrations/env.py`, `src/main.py`, và
`scripts/seed_admin.py`.

Nếu bạn thêm một entry point async mới mà quên gọi hàm này, lỗi sẽ là:

```
psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in
async mode. Please use a compatible event loop, for instance by setting
'asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())'
```

Trên Linux và macOS hàm này không làm gì.

## Giới hạn đã biết

- **Thu hồi quyền có độ trễ tối đa 15 phút.** Vô hiệu hoá tài khoản thu hồi
  refresh token ngay, nhưng access token đang lưu hành vẫn hợp lệ tới khi hết
  hạn.
- **Rate limit chỉ đúng khi chạy một bản sao.** Bộ đếm nằm trong bộ nhớ tiến
  trình; khi mở rộng nhiều bản sao phải chuyển sang Redis.
