# Void CRM Backend

FastAPI backend для системы управления веб-студией с чек-листом партнёрства.

## Технологии

- **FastAPI** — современный асинхронный веб-фреймворк
- **SQLAlchemy 2.0** — ORM для работы с PostgreSQL
- **Alembic** — миграции базы данных
- **Pydantic v2** — валидация данных
- **PostgreSQL 16 + pgvector** — основная база данных с поддержкой векторного поиска
- **Redis** — кэш и PubSub для WebSocket
- **RabbitMQ** — очереди сообщений для фоновых задач
- **UV** — быстрый пакетный менеджер для Python

## Требования

- Python 3.12+
- PostgreSQL 16+ (с расширением pgvector)
- Redis 7+
- RabbitMQ 3+
- Docker и Docker Compose

## Быстрый старт

### 1. Клонирование и установка зависимостей

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd void-crm-backend

# Установите UV (если ещё не установлен)
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Установите зависимости проекта
uv sync
```

### 2. Настройка переменных окружения

```bash
# Скопируйте пример конфигурации
cp .env.dev.example .env.dev

# Отредактируйте .env.dev и заполните обязательные значения
```

#### Обязательные переменные в `.env.dev`:

| Переменная | Описание | Пример |
|------------|----------|--------|
| `TOKEN_SECRET_KEY` | Секретный ключ для JWT | Сгенерируйте: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DOCS_PASSWORD` | Пароль для Swagger UI | `MyDocsPass123!` |
| `DEFAULT_ADMIN_PASSWORD` | Пароль дефолтного админа | `SecureAdmin123!` |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL | `postgres_pass` |
| `RABBITMQ_USER` | Пользователь RabbitMQ | `admin` |
| `RABBITMQ_PASS` | Пароль RabbitMQ | `rabbitmq_pass` |
| `REDIS_PASSWORD` | Пароль Redis | `redis_pass` |

#### Минимальный `.env.dev` для запуска:

```bash
# Безопасность (ОБЯЗАТЕЛЬНО измените!)
TOKEN_SECRET_KEY=your_generated_secret_key_64_chars_minimum_use_secrets_module
DOCS_PASSWORD=DocsPass123!
DEFAULT_ADMIN_PASSWORD=AdminPass123!

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=void_crm_db

# RabbitMQ
RABBITMQ_USER=admin
RABBITMQ_PASS=admin
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672

# Redis
REDIS_USER=default
REDIS_PASSWORD=redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DATABASE=0

# Дефолтный админ
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_EMAIL=admin@example.com
DEFAULT_ADMIN_PHONE=+79991234567

# Фикстуры и отладка
LOAD_FIXTURES=true
DEBUG=true
LOG_LEVEL=DEBUG
```

### 3. Запуск инфраструктуры

```bash
# Первый запуск (полная инициализация)
uv run bootstrap
```

Эта команда автоматически:
1. Остановит и очистит старые контейнеры и volumes
2. Запустит Docker контейнеры (PostgreSQL + Redis + RabbitMQ)
3. Создаст базу данных и применит миграции
4. Загрузит начальные данные (если `LOAD_FIXTURES=true`)
5. Запустит FastAPI сервер с hot-reload

Для последующих запусков можно использовать:
```bash
uv run dev    # Запуск без полной очистки
```

### 4. Доступ к приложению

После успешного запуска:

| Сервис | URL | Примечание |
|--------|-----|------------|
| **API** | http://localhost:8000 | Основной API |
| **Swagger UI** | http://localhost:8000/docs | Интерактивная документация |
| **ReDoc** | http://localhost:8000/redoc | Альтернативная документация |
| **RabbitMQ UI** | http://localhost:15672 | Управление очередями |

## Доступные команды

```bash
# Разработка
uv run bootstrap        # Первый запуск (очистка + инициализация + сервер)
uv run dev              # Последующие запуски (Docker + миграции + сервер)
uv run serve            # Запустить только сервер (без Docker)

# База данных
uv run migrate          # Применить миграции
uv run makemigrations   # Создать новую миграцию
uv run downgrade        # Откатить последнюю миграцию

# Фоновые задачи
uv run worker           # Запустить воркер RabbitMQ

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
uv run infra-test       # Запустить тестовую инфраструктуру
```

## Структура проекта

```
void-crm-backend/
├── app/
│   ├── core/                   # Ядро приложения
│   │   ├── connections/        # Подключения к БД, Redis
│   │   ├── dependencies/       # FastAPI зависимости
│   │   ├── exceptions/         # Обработка ошибок
│   │   ├── integrations/       # Внешние интеграции (AI, OpenRouter)
│   │   ├── lifespan/           # Startup/shutdown события
│   │   ├── logging/            # Настройка логирования
│   │   ├── messaging/          # RabbitMQ клиент
│   │   ├── middlewares/        # CORS, Rate Limit, Auth
│   │   ├── migrations/         # Alembic миграции
│   │   ├── security/           # JWT, хеширование паролей
│   │   ├── settings/           # Конфигурация из ENV
│   │   ├── utils/              # Вспомогательные функции
│   │   └── websocket/          # WebSocket менеджер
│   ├── models/                 # SQLAlchemy модели
│   ├── schemas/                # Pydantic схемы
│   ├── routers/                # API эндпоинты
│   ├── services/               # Бизнес-логика
│   └── repository/             # Слой доступа к данным
├── data/
│   └── fixtures/               # Начальные данные (JSON)
├── docs/                       # Документация
├── scripts/                    # Команды (dev, migrate, и т.д.)
├── worker/                     # RabbitMQ воркеры
│   └── handlers/               # Обработчики очередей
├── docker-compose.dev.yml      # Docker для разработки
├── docker-compose.test.yml     # Docker для тестов
├── .env.dev.example            # Пример конфигурации
├── alembic.ini                 # Конфигурация миграций
└── pyproject.toml              # Зависимости и скрипты
```

## API Endpoints

### Аутентификация

- POST /api/v1/auth/login — Вход в систему
- POST /api/v1/auth/logout — Выход из системы
- POST /api/v1/auth/refresh — Обновление токенов

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

## Решение проблем

### Docker не запускается

```bash
# Убедитесь, что Docker Desktop запущен
docker info

# Если порты заняты, удалите все контейнеры
docker rm -f $(docker ps -aq)
docker volume prune -f
```

### Ошибка подключения к БД

```bash
# Проверьте, что PostgreSQL запущен
docker ps | grep postgres

# Проверьте порты в .env.dev
# POSTGRES_PORT должен совпадать с портом контейнера
```

### Миграции не применяются

```bash
# Убедитесь, что БД создана
docker exec -it <postgres_container> psql -U postgres -c "SELECT datname FROM pg_database;"

# Примените миграции вручную
uv run migrate
```

## Лицензия

Private - Проприетарное ПО
