"""
Модуль для работы с системой обмена сообщениями.

Предоставляет классы для управления подключением к RabbitMQ:
- RabbitMQClient: Клиент для установки и управления подключением к брокеру сообщений
  с поддержкой автоматических повторных попыток подключения

Модуль использует настройки подключения из конфигурации приложения и реализует
базовые интерфейсы из модуля base.py.
"""

import asyncio

from aio_pika import connect_robust
from aio_pika.abc import AbstractRobustConnection
from aio_pika.exceptions import AMQPConnectionError

from app.core.settings import settings

from .base import BaseClient, BaseContextManager


class RabbitMQClient(BaseClient[AbstractRobustConnection]):
    """
    Клиент для работы с RabbitMQ

    Реализует базовый класс BaseClient для установки и управления
    подключением к брокеру сообщений RabbitMQ с механизмом повторных попыток.

    Attributes:
        _client (Optional[AbstractRobustConnection]): Экземпляр подключения к RabbitMQ (унаследован от BaseClient)
        _is_connected (bool): Флаг состояния подключения
        _max_retries (int): Максимальное количество попыток подключения
        _initial_retry_delay (int): Начальная задержка между попытками подключения в секундах
        _max_retry_delay (int): Максимальная задержка между попытками подключения в секундах
        _connection_params (dict): Параметры подключения из настроек
        _debug_mode (bool): Режим отладки из настроек приложения
        logger (logging.Logger): Логгер для записи событий (унаследован от BaseClient)
    """

    _is_connected: bool = False
    _max_retries: int = 10
    _initial_retry_delay: int = 2
    _max_retry_delay: int = 30

    def __init__(self) -> None:
        """
        Инициализация клиента RabbitMQ.
        Настраивает параметры подключения и режим отладки из конфигурации.
        """
        super().__init__()
        self._connection_params = settings.rabbitmq_params
        self._debug_mode = getattr(settings, "DEBUG", False)

    async def connect(self) -> AbstractRobustConnection:
        """
        Создает подключение к RabbitMQ

        Устанавливает подключение к брокеру сообщений с механизмом повторных попыток
        и экспоненциальной задержкой (exponential backoff).
        В режиме отладки при неудачном подключении возвращает mock-объект вместо исключения.

        Returns:
            AbstractRobustConnection: Подключение к RabbitMQ

        Raises:
            AMQPConnectionError: При ошибке подключения после всех попыток
        """
        if not self._client and not self._is_connected:
            retry_delay = self._initial_retry_delay

            for attempt in range(self._max_retries):
                try:
                    self.logger.debug("Подключение к RabbitMQ...")
                    self._client = await connect_robust(**self._connection_params)
                    self._is_connected = True
                    self.logger.info("Подключение к RabbitMQ установлено")
                    break
                except (AMQPConnectionError, Exception) as e:
                    self.logger.error("Ошибка подключения к RabbitMQ: %s", str(e))
                    if attempt < self._max_retries - 1:
                        self.logger.warning(
                            f"Повторная попытка {attempt + 1}/{self._max_retries} через {retry_delay} секунд..."
                        )
                        await asyncio.sleep(retry_delay)
                        # Exponential backoff: увеличиваем задержку в 2 раза, но не более max_retry_delay
                        retry_delay = min(retry_delay * 2, self._max_retry_delay)
                    else:
                        self._is_connected = False
                        self._client = None
                        self.logger.warning("RabbitMQ недоступен после всех попыток")

                        # В режиме разработки не выбрасываем исключение
                        if self._debug_mode:
                            self.logger.warning(
                                "Приложение продолжит работу без RabbitMQ (DEBUG режим)"
                            )
                            # Создаем mock-объект для debug режима
                            from unittest.mock import AsyncMock

                            mock_connection = AsyncMock()
                            mock_connection.is_closed = False
                            self._client = mock_connection
                            self._is_connected = True
                            break
                        else:
                            raise AMQPConnectionError(
                                "Не удалось подключиться к RabbitMQ после всех попыток"
                            ) from None

        if self._client is None:
            raise AMQPConnectionError("Подключение к RabbitMQ не установлено")

        return self._client

    async def close(self) -> None:
        """
        Закрывает подключение к RabbitMQ

        Безопасно закрывает активное подключение к брокеру сообщений.
        """
        if self._client and self._is_connected:
            try:
                self.logger.debug("Закрытие подключения к RabbitMQ...")
                await self._client.close()
                self.logger.info("Подключение к RabbitMQ закрыто")
            finally:
                self._client = None
                self._is_connected = False

    async def health_check(self) -> bool:
        """
        Проверяет состояние подключения

        Returns:
            bool: True если подключение активно и работает, False в противном случае
        """
        if not self._client or not self._is_connected:
            return False
        try:
            return not self._client.is_closed
        except (AMQPConnectionError, AttributeError):
            return False

    @property
    def is_connected(self) -> bool:
        """
        Возвращает статус подключения

        Returns:
            bool: True если подключение установлено, False в противном случае
        """
        return self._is_connected


class RabbitMQContextManager(BaseContextManager[AbstractRobustConnection]):
    """
    Контекстный менеджер для работы с RabbitMQ

    Реализует базовый класс BaseContextManager для автоматического управления
    подключением к брокеру сообщений RabbitMQ с использованием контекстного менеджера.

    Attributes:
        _client (Optional[AbstractRobustConnection]): Экземпляр подключения к RabbitMQ (унаследован от BaseContextManager)
        _connection_params (dict): Параметры подключения из настроек
        _debug_mode (bool): Режим отладки из настроек приложения
        logger (logging.Logger): Логгер для записи событий (унаследован от BaseContextManager)
    """

    def __init__(self) -> None:
        """
        Инициализация контекстного менеджера RabbitMQ.
        Настраивает параметры подключения и режим отладки из конфигурации.
        """
        super().__init__()
        self._connection_params = settings.rabbitmq_params
        self._debug_mode = getattr(settings, "DEBUG", False)

    async def connect(self) -> AbstractRobustConnection:
        """
        Создает подключение к RabbitMQ

        Устанавливает подключение к брокеру сообщений для использования в контексте.

        Returns:
            AbstractRobustConnection: Подключение к RabbitMQ

        Raises:
            AMQPConnectionError: При ошибке подключения
        """
        try:
            self.logger.debug(
                "Создание подключения к RabbitMQ в контекстном менеджере..."
            )
            self._client = await connect_robust(**self._connection_params)
            self.logger.info(
                "Подключение к RabbitMQ установлено в контекстном менеджере"
            )
            return self._client
        except AMQPConnectionError as e:
            self.logger.error(
                "Ошибка подключения к RabbitMQ в контекстном менеджере: %s", str(e)
            )
            if self._debug_mode:
                self.logger.warning("Создание mock-подключения для DEBUG режима")
                from unittest.mock import AsyncMock

                mock_connection = AsyncMock()
                mock_connection.is_closed = False
                self._client = mock_connection
                return self._client
            else:
                raise

    async def close(self) -> None:
        """
        Закрывает подключение к RabbitMQ

        Безопасно закрывает активное подключение к брокеру сообщений.
        """
        if self._client:
            try:
                self.logger.debug(
                    "Закрытие подключения к RabbitMQ в контекстном менеджере..."
                )
                await self._client.close()
                self.logger.info(
                    "Подключение к RabbitMQ закрыто в контекстном менеджере"
                )
            except Exception as e:
                self.logger.error(
                    "Ошибка при закрытии подключения к RabbitMQ: %s", str(e)
                )
            finally:
                self._client = None


# Глобальный ленивый клиент для переиспользования в разных частях приложения
_global_rabbitmq_client: RabbitMQClient | None = None


def get_global_rabbitmq_client() -> RabbitMQClient:
    """
    Возвращает глобальный экземпляр RabbitMQClient (ленивый синглтон).

    Это удобно для случаев, когда нужно разделять один клиент между HTTP-зависимостями
    и фоновыми обработчиками (например, FastStream) и избежать гонки при создании
    и инициализации подключения.
    """
    global _global_rabbitmq_client
    if _global_rabbitmq_client is None:
        _global_rabbitmq_client = RabbitMQClient()
    return _global_rabbitmq_client
