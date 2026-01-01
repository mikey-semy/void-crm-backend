# Multi-stage build для оптимизации размера и скорости
FROM python:3.12-alpine AS builder

WORKDIR /build

# Устанавливаем только необходимые пакеты для сборки
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev

# Копируем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Копируем файлы зависимостей и необходимые пакеты проекта
COPY pyproject.toml uv.lock README.md ./
COPY app ./app

# Устанавливаем зависимости в venv
ENV UV_HTTP_TIMEOUT=60
RUN uv sync --frozen --no-cache --no-dev

# Runtime stage - финальный образ
FROM python:3.12-alpine

WORKDIR /usr/src/app

# Оптимизация Python для минимального использования памяти
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2 \
    MALLOC_ARENA_MAX=2

# Устанавливаем только runtime библиотеки + шрифты для PDF
RUN apk add --no-cache \
    postgresql-libs \
    libffi \
    wget \
    ttf-dejavu \
    && rm -rf /var/cache/apk/*

# Копируем venv из builder
COPY --from=builder /build/.venv /usr/src/app/.venv

# Копируем приложение
COPY . /usr/src/app/

# Делаем entrypoint исполняемым
RUN chmod +x /usr/src/app/docker-entrypoint.sh

# Создаем непривилегированного пользователя для безопасности
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /usr/src/app

USER appuser

EXPOSE 8000

ENTRYPOINT ["sh", "/usr/src/app/docker-entrypoint.sh"]
