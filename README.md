# Void CRM Backend

FastAPI backend для системы управления веб-студией с чек-листом партнёрства.

## Технологии

- **FastAPI** — современный асинхронный веб-фреймворк
- **SQLAlchemy 2.0** — ORM для работы с PostgreSQL
- **Alembic** — миграции базы данных
- **Pydantic v2** — валидация данных
- **PostgreSQL** — основная база данных
- **Redis** — кэш и PubSub для WebSocket
- **UV** — быстрый пакетный менеджер для Python

## Требования

- Python 3.12+
- PostgreSQL 14+
- Redis 7+
- Docker и Docker Compose (для локальной разработки)

## Быстрый старт

### 1. Установка зависимостей

```bash
# Установите UV (если ещё не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Установите зависимости проекта
uv sync
```

### 2. Настройка окружения

Создайте файл `.env.dev` в корне проекта:

```bash
# Database
POSTGRES_USER=void_crm_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=void_crm_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5435

# Redis
REDIS_HOST=localhost
REDIS_PORT=6381
REDIS_DB=0

# Application
APP_HOST=0.0.0.0
APP_PORT=8002
DEBUG=true
RELOAD=true

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# Fixtures
LOAD_FIXTURES=true
```

### 3. Запуск инфраструктуры

```bash
# Запустить PostgreSQL, Redis и приложение с hot-reload
uv run bootstrap
```

Эта команда:
1. Запустит Docker контейнеры (PostgreSQL + Redis)
2. Применит миграции базы данных
3. Загрузит начальные данные (если LOAD_FIXTURES=true)
4. Запустит FastAPI с hot-reload

### 4. Доступ к приложению

- **API**: http://localhost:8002
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

## Доступные команды

```bash
# Разработка
uv run dev              # Запустить приложение с hot-reload
uv run bootstrap        # Полный старт (контейнеры + миграции + dev server)

# База данных
uv run migrate          # Применить миграции
uv run makemigrations   # Создать новую миграцию
uv run downgrade        # Откатить последнюю миграцию

# Docker
uv run docker:up        # Запустить контейнеры
uv run docker:down      # Остановить контейнеры
uv run docker:logs      # Показать логи контейнеров

# Качество кода
uv run check            # Проверить код (ruff check)
uv run format           # Отформатировать код (ruff format)
uv run lint             # Линтинг + форматирование

# Тесты
uv run test             # Запустить тесты
```

## API Endpoints

### Категории чек-листа

- GET /api/v1/checklist/categories — Получить все категории
- GET /api/v1/checklist/categories/{id} — Получить категорию по ID
- POST /api/v1/checklist/categories — Создать категорию

### Задачи

- GET /api/v1/checklist/tasks/{id} — Получить задачу
- POST /api/v1/checklist/tasks — Создать задачу
- PATCH /api/v1/checklist/tasks/{id}/status — Обновить статус
- PATCH /api/v1/checklist/tasks/{id}/notes — Обновить заметки
- PATCH /api/v1/checklist/tasks/{id}/assignee — Назначить исполнителя
- DELETE /api/v1/checklist/tasks/{id} — Удалить задачу

### WebSocket

- WS /api/v1/checklist/ws — Real-time синхронизация

События WebSocket:
- task:created — Задача создана
- task:updated — Задача обновлена
- task:deleted — Задача удалена
- category:updated — Категория обновлена

## Лицензия

Private - Проприетарное ПО
