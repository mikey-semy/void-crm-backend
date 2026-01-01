#!/bin/sh

set -e

echo "🚀 Starting optimized backend..."

# Активируем venv
export PATH="/usr/src/app/.venv/bin:$PATH"

# Ждем готовности PostgreSQL
if [ -n "${POSTGRES_HOST}" ]; then
  echo "⏳ Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
  timeout=60
  while [ $timeout -gt 0 ]; do
    if python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('${POSTGRES_HOST}', ${POSTGRES_PORT:-5432})); s.close()" 2>/dev/null; then
      echo "✅ PostgreSQL ready"
      break
    fi
    echo "PostgreSQL unavailable - waiting... ($timeout seconds left)"
    timeout=$((timeout - 1))
    sleep 1
  done

  if [ $timeout -eq 0 ]; then
    echo "⚠️ PostgreSQL connection timeout, continuing anyway..."
  fi
fi

# Запускаем миграции
echo "🔄 Running migrations..."
python -m alembic upgrade head || echo "⚠️ Migrations skipped"

# Фикстуры загружаются автоматически через lifespan при старте приложения
# если LOAD_FIXTURES=true в .env

echo "🌟 Starting Uvicorn (optimized for 1GB RAM)..."

# Запускаем с оптимизированными параметрами
APP_PORT="${API_PORT:-8000}"
exec python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${APP_PORT}" \
  --workers 1 \
  --limit-concurrency 50 \
  --timeout-keep-alive 30 \
  --backlog 128 \
  --no-access-log \
  --log-level warning
