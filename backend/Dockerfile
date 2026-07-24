# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Cài dependency trước, tách khỏi mã nguồn để tận dụng cache của Docker.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev

FROM python:3.13-slim AS runtime

# Chạy bằng người dùng thường, không phải root.
RUN useradd --create-home --uid 1000 omnichat

WORKDIR /app
COPY --from=builder --chown=omnichat:omnichat /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER omnichat
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
