"""Конфигурация приложения."""

from typing import Any

from pydantic import AmqpDsn, EmailStr, PostgresDsn, RedisDsn, SecretStr, field_validator
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
    TITLE: str = "VOID CRM API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Backend для внутренней CRM веб-студии"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8010

    # PostgreSQL
    POSTGRES_USER: str = "void_crm"
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "void_crm_db"

    # Настройки RabbitMQ
    RABBITMQ_CONNECTION_TIMEOUT: int = 60
    RABBITMQ_EXCHANGE: str = "profitool_exchange"
    RABBITMQ_USER: str
    RABBITMQ_PASS: SecretStr
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5673

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

    # Настройки аутентификации
    DEFAULT_USER_ROLE: str = "user"

    # API Key для service-to-service авторизации (внешние админки)
    ADMIN_API_KEY: SecretStr | None = None

    # Настройки токенов
    TOKEN_TYPE: str = "Bearer"
    TOKEN_ALGORITHM: str = "HS256"

    # Пути для куки
    ACCESS_TOKEN_PATH: str = "/"
    REFRESH_TOKEN_PATH: str = "/"

    # Время жизни токенов (в минутах/днях)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Время жизни токена сброса пароля (в минутах)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Время жизни токена верификации email (в минутах)
    VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 часа

    @property
    def ACCESS_TOKEN_MAX_AGE(self) -> int:
        """Время жизни access токена в секундах."""
        return self.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    @property
    def REFRESH_TOKEN_MAX_AGE(self) -> int:
        """Время жизни refresh токена в секундах."""
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    @property
    def PASSWORD_RESET_TOKEN_TTL(self) -> int:
        """Время жизни токена сброса пароля в секундах."""
        return self.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES * 60

    # Настройки паролей
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPER: bool = True
    PASSWORD_REQUIRE_LOWER: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_FORBID_USERNAME: bool = True
    PASSWORD_COMMON_SEQUENCES: list[str] = [
        "12345",
        "qwerty",
        "password",
        "admin",
        "123456789",
        "abc123",
    ]

    # Параметры хеширования Argon2
    PASSWORD_HASH_SCHEME: str = "argon2"
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 102400
    ARGON2_PARALLELISM: int = 8

    @property
    def crypt_context_params(self) -> dict[str, Any]:
        """
        Параметры для CryptContext из passlib.

        Returns:
            Dict с настройками для Argon2 хеширования
        """
        return {
            "schemes": [self.PASSWORD_HASH_SCHEME],
            "deprecated": "auto",
            "argon2__time_cost": self.ARGON2_TIME_COST,
            "argon2__memory_cost": self.ARGON2_MEMORY_COST,
            "argon2__parallelism": self.ARGON2_PARALLELISM,
        }

    # Настройки куки
    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = (
        "None"  # None для cross-domain cookies (разные домены API и фронтенда)
    )
    COOKIE_HTTPONLY: bool = True

    @property
    def access_token_cookie_params(self) -> dict[str, Any]:
        """Параметры для access_token куки."""
        return {
            "domain": self.COOKIE_DOMAIN,
            "secure": self.COOKIE_SECURE,
            "samesite": self.COOKIE_SAMESITE,
            "httponly": self.COOKIE_HTTPONLY,
            "path": self.ACCESS_TOKEN_PATH,
            "max_age": self.ACCESS_TOKEN_MAX_AGE,
        }

    @property
    def refresh_token_cookie_params(self) -> dict[str, Any]:
        """Параметры для refresh_token куки."""
        return {
            "domain": self.COOKIE_DOMAIN,
            "secure": self.COOKIE_SECURE,
            "samesite": self.COOKIE_SAMESITE,
            "httponly": self.COOKIE_HTTPONLY,
            "path": self.REFRESH_TOKEN_PATH,
            "max_age": self.REFRESH_TOKEN_MAX_AGE,
        }

    # Настройки методов аутентификации
    USERNAME_ALLOWED_TYPES: list[str] = ["email", "phone", "username"]

    @field_validator("USERNAME_ALLOWED_TYPES", mode="before")
    @classmethod
    def parse_allowed_types(cls, v):
        """
        Преобразование строки в список, если передано как строка.

        Args:
            v: Значение, которое может быть строкой или списком.

        Returns:
            List[str]: Список разрешённых типов.
        """
        if isinstance(v, str):
            return [t.strip() for t in v.split(",")]
        return v

    # Дефолтный админ (обязательный)
    # Создаётся автоматически при первом запуске, если не существует
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: EmailStr = "admin@proffitool.ru"
    DEFAULT_ADMIN_PHONE: str = "+79991234567"
    DEFAULT_ADMIN_PASSWORD: SecretStr

    # Дополнительные админы (опционально)
    # Формат: username:email:phone:password,username2:email2:phone2:password2
    # Пример: ADMINS=mike:mike@example.com:+79001234567:SecurePass123,anna:anna@example.com:+79007654321:AnotherPass456
    ADMINS: str | None = None

    @property
    def additional_admins(self) -> list[dict[str, str]]:
        """
        Парсинг дополнительных администраторов из ENV.

        Returns:
            List[Dict]: Список словарей с данными админов:
                [
                    {
                        "username": "mike",
                        "email": "mike@example.com",
                        "phone": "+79001234567",
                        "password": "SecurePass123"
                    },
                    ...
                ]
        """
        if not self.ADMINS:
            return []

        admins = []
        for admin_str in self.ADMINS.split(","):
            admin_str = admin_str.strip()
            if not admin_str:
                continue

            parts = admin_str.split(":")
            if len(parts) != 4:
                self.logging.logger.warning(
                    "⚠️ Неверный формат администратора: '%s'. Ожидается username:email:phone:password",
                    admin_str,
                )
                continue

            username, email, phone, password = parts
            admins.append(
                {
                    "username": username.strip(),
                    "email": email.strip(),
                    "phone": phone.strip(),
                    "password": password.strip(),
                }
            )

        return admins

    # Настройки логирования медленных запросов
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
    def rabbitmq_dsn(self) -> AmqpDsn:
        return AmqpDsn.build(
            scheme="amqp",
            username=self.RABBITMQ_USER,
            password=self.RABBITMQ_PASS.get_secret_value(),
            host=self.RABBITMQ_HOST,
            port=self.RABBITMQ_PORT,
        )

    @property
    def rabbitmq_url(self) -> str:
        """
        Для pika нужно строку с подключением к RabbitMQ
        """
        return str(self.rabbitmq_dsn)

    @property
    def rabbitmq_params(self) -> dict[str, Any]:
        """
        Формирует параметры подключения к RabbitMQ.

        Returns:
            Dict с параметрами подключения к RabbitMQ
        """
        return {
            "url": self.rabbitmq_url,
            "connection_timeout": self.RABBITMQ_CONNECTION_TIMEOUT,
            "exchange": self.RABBITMQ_EXCHANGE,
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
