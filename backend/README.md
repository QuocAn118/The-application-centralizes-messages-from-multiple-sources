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
uv run ruff check .
uv run mypy src
uv run lint-imports
```
