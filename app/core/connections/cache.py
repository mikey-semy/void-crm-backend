"""
Модуль для работы с Redis.

Предоставляет классы для управления подключением к Redis:
- RedisClient: Клиент для установки и управления подключением к Redis
- RedisContextManager: Контекстный менеджер для автоматического управления подключением

Redis используется в приложении как универсальное хранилище данных в памяти,
поддерживающее различные структуры данных и паттерны использования.

Модуль использует настройки подключения из конфигурации приложения и реализует
базовые интерфейсы из модуля base.py.
"""

import asyncio
from typing import Optional

from redis.asyncio import Redis, from_url

from app.core.connections.base import BaseClient, BaseContextManager
from app.core.settings import Settings, settings


class RedisClient(BaseClient[Redis]):
    """
    Клиент для работы с Redis

    Реализует базовый класс BaseClient для установки и управления
    подключением к Redis серверу.

    Attributes:
        _redis_params (dict): Параметры подключения к Redis из конфигурации
        _client (Optional[Redis]): Экземпляр подключения к Redis
        logger (logging.Logger): Логгер для записи событий подключения
    """

    _instance: Optional["RedisClient"] = None
    _lock = asyncio.Lock()
    _initialized = False

    def __new__(cls, _settings: Settings = settings) -> "RedisClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, _settings: Settings = settings) -> None:
        """
        Инициализация клиента Redis.

        Args:
            _settings (Settings): Конфигурация приложения с параметрами подключения к Redis.
                              По умолчанию использует глобальные настройки приложения.
        """
        if getattr(self, "_initialized", False):
            return
        super().__init__()
        self._redis_params = _settings.redis_params
        self._client: Redis | None = None
        self._initialized = True

    async def connect(self) -> Redis:
        """Создает подключение к Redis

        Устанавливает соединение с Redis сервером, используя параметры
        из конфигурации приложения.

        Returns:
            Redis: Экземпляр подключенного Redis клиента

        Raises:
            RedisError: При ошибке подключения к Redis серверу
        """
        if self._client is not None:
            return self._client

        async with self._lock:
            if self._client is not None:
                return self._client

            self.logger.debug("Подключение к Redis...")
            self._client = await from_url(**self._redis_params)
            self.logger.info("Подключение к Redis установлено")
        return self._client

    async def close(self) -> None:
        """
        Закрывает подключение к Redis

        Корректно завершает соединение с Redis сервером и очищает
        ссылку на клиент. Безопасно обрабатывает случай, когда
        подключение уже закрыто.
        """
        async with self._lock:
            if self._client:
                self.logger.debug("Закрытие подключения к Redis...")
                await self._client.close()
                self._client = None
                RedisClient._instance = None
                RedisClient._initialized = False
                self.logger.info("Подключение к Redis закрыто")

    async def _health_check_probe(self) -> None:
        if self._client:
            await self._client.ping()

    async def health_check(self) -> bool:
        """
        Проверяет состояние подключения к Redis.

        Returns:
            bool: True если подключение активно, False иначе
        """
        try:
            await self._health_check_probe()
            return True
        except Exception:
            return False


class RedisContextManager(BaseContextManager[Redis]):
    """
    Контекстный менеджер для Redis

    Реализует контекстный менеджер для автоматического управления
    жизненным циклом подключения к Redis.

    Attributes:
        redis_client (RedisClient): Экземпляр клиента Redis
        _client (Optional[Redis]): Ссылка на активное подключение
        logger (logging.Logger): Логгер для записи событий
    """

    def __init__(self, _settings: Settings = settings) -> None:
        """
        Инициализация контекстного менеджера.
        Создает экземпляр RedisClient для управления подключением.
        """
        super().__init__()
        self.redis_client = RedisClient(_settings)

    async def connect(self) -> Redis:
        """
        Создает подключение к Redis

        Делегирует создание подключения экземпляру RedisClient.

        Returns:
            Redis: Экземпляр подключенного Redis клиента
        """
        return await self.redis_client.connect()

    async def close(self) -> None:
        """
        Закрывает подключение к Redis

        Делегирует закрытие подключения экземпляру RedisClient.
        """
        await self.redis_client.close()


async def get_redis_client(_settings: Settings = settings) -> Redis:
    """
    Утилитарная функция для получения глобального клиента Redis.

    Args:
        _settings (Settings): Конфигурация приложения с параметрами подключения к Redis.
                              По умолчанию использует глобальные настройки приложения.
    Returns:
        Redis: Экземпляр подключенного Redis клиента

    Usage:
        ```python
        redis_client = await get_redis_client()

        # Использование в коде
        async with redis_client.pipeline() as pipe:
            await pipe.set('key', 'value')
            await pipe.execute()
        ```
    """
    client = RedisClient(_settings)
    return await client.connect()
