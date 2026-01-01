"""Конфигурация приложения."""

from typing import Any

from pydantic import PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings.logging import LoggingSettings
from app.core.settings.paths import PathSettings

env_file_path, app_env = PathSettings.get_env_file_and_type()


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    # Виртуальное окружение приложения
    app_env: str = app_env

    logging: LoggingSettings = LoggingSettings()
    paths: PathSettings = PathSettings()

    # App
    TITLE: str = "VOID CMS API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Backend для внутренней CMS веб-студии"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8010

    # PostgreSQL
    POSTGRES_USER: str = "void_cms"
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "void_cms_db"

    # Redis
    REDIS_USER: str = "default"
    REDIS_PASSWORD: SecretStr
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DATABASE: int = 0
    REDIS_POOL_SIZE: int = 10

    # Настройки доступа в docs/redoc
    DOCS_ACCESS: bool = True
    DOCS_USERNAME: str = "admin"
    DOCS_PASSWORD: SecretStr

    # Секретный ключ для сессий и токенов
    TOKEN_SECRET_KEY: SecretStr

    SLOW_THRESHOLD_MS: float = 500.0  # ms

    # Настройки CORS
    ALLOW_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ]
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    ALLOW_HEADERS: list[str] = [
        "accept",
        "accept-encoding",
        "authorization",
        "content-type",
        "dnt",
        "origin",
        "user-agent",
        "x-csrftoken",
        "x-requested-with",
        "x-api-key",
        "manifest-fetch-site",
        "cache-control",
        "pragma",
    ]

    # Fixtures
    LOAD_FIXTURES: bool = True

    @property
    def app_params(self) -> dict:
        """
        Параметры для инициализации FastAPI приложения.

        Returns:
            Dict с настройками FastAPI
        """
        # Ленивый импорт lifespan для избежания circular import
        from app.core.lifespan import lifespan

        return {
            "title": self.TITLE,
            "description": self.DESCRIPTION,
            "version": self.VERSION,
            "swagger_ui_parameters": {"defaultModelsExpandDepth": -1},
            "root_path": "",
            "lifespan": lifespan,
        }

    @property
    def uvicorn_params(self) -> dict:
        """
        Параметры для запуска uvicorn сервера.

        Returns:
            Dict с настройками uvicorn
        """
        return {
            "host": self.HOST,
            "port": self.PORT,
            "proxy_headers": True,
            "forwarded_allow_ips": "*",  # Доверять всем прокси (для Traefik)
            "log_level": "debug",
        }

    @property
    def database_dsn(self) -> PostgresDsn:
        """
        Создает DSN для подключения к PostgreSQL.

        Returns:
            PostgresDsn: DSN для подключения к PostgreSQL.
        """
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DATABASE,
        )

    @property
    def database_url(self) -> str:
        """
        Строка подключения к базе данных (используется Alembic и SQLAlchemy).

        Returns:
            str: Строка подключения к базе данных.
        """
        return str(self.database_dsn)

    @property
    def engine_params(self) -> dict[str, Any]:
        """
        Параметры для создания SQLAlchemy engine.

        Returns:
            dict: Параметры подключения к PostgreSQL.
        """
        return {
            "echo": False,  # Логирование SQL-запросов (для отладки)
            "pool_size": 20,  # Размер пула соединений (по умолчанию 5)
            "max_overflow": 10,  # Дополнительные соединения сверх pool_size
            "pool_timeout": 30,  # Таймаут ожидания свободного соединения (секунды)
            "pool_recycle": 3600,  # Переиспользование соединений каждый час
            "pool_pre_ping": True,  # Проверка соединения перед использованием
        }

    @property
    def session_params(self) -> dict[str, Any]:
        """
        Параметры для создания SQLAlchemy session.

        Returns:
            dict: Параметры подключения к PostgreSQL.
        """
        return {
            "autocommit": False,  # Автоматическое подтверждение транзакций для сессии
            "autoflush": False,  # Автоматическая очистка буфера перед выполнением запроса
            "expire_on_commit": False,  # Не инвалидировать объекты после коммита
            "class_": AsyncSession,
        }

    @property
    def redis_dsn(self) -> RedisDsn:
        """
        Создает DSN для подключения к Redis.

        Returns:
            RedisDsn: DSN для подключения к Redis.
        """
        return RedisDsn.build(
            scheme="redis",
            username=self.REDIS_USER,
            password=self.REDIS_PASSWORD.get_secret_value(),
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path=f"/{self.REDIS_DATABASE}",
        )

    @property
    def redis_url(self) -> str:
        """
        Строковое представление DSN для подключения к Redis.

        returns:
            str: Строка подключения к Redis.
        """
        return str(self.redis_dsn)

    @property
    def redis_params(self) -> dict[str, Any]:
        """
        Параметры для создания Redis connection pool.

        Returns:
            dict: Параметры подключения к Redis.
        """
        return {"url": self.redis_url, "max_connections": self.REDIS_POOL_SIZE}

    # Настройки ограничения частоты запросов
    @property
    def rate_limit_params(self) -> dict:
        """
        Параметры для настройки ограничения частоты запросов.

        Returns:
            Dict с параметрами ограничения частоты запросов:
                limit: Максимальное количество запросов
                window: Временное окно в секундах
                exclude_paths: Исключить пути из ограничения
        """
        return {
            "capacity": 100,  # Максимальное количество токенов (burst)
            "refill_rate": 2.0,  # Количество токенов в секунду (sustained rate)
            "redis_url": self.redis_url,
            "exclude_paths": [
                "/docs",
                "/docs/",
                "/docs/swagger",
                "/docs/oauth2-redirect",
                "/redoc",
                "/openapi.json",
                "/health",
                "/ready",
                "/static",
            ],
        }

    @property
    def cors_params(self) -> dict:
        """
        Параметры для настройки CORS middleware.

        Returns:
            dict: Параметры CORS.
        """
        return {
            "allow_origins": self.ALLOW_ORIGINS,
            "allow_credentials": self.ALLOW_CREDENTIALS,
            "allow_methods": self.ALLOW_METHODS,
            "allow_headers": self.ALLOW_HEADERS,
        }

    model_config = SettingsConfigDict(
        env_file=env_file_path,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="allow",
    )
