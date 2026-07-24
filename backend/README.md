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
uv run alembic upgrade head                        # áp migration mới nhất
uv run alembic revision --autogenerate -m "mô tả"  # sinh migration mới
uv run alembic downgrade -1                        # lùi một bước
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
