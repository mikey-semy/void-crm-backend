"""
Зависимости для работы с системой обмена сообщениями в FastAPI.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from aio_pika.abc import AbstractRobustConnection
from fastapi import Depends

from app.core.connections.messaging import RabbitMQClient, RabbitMQContextManager
from app.core.dependencies.base import BaseDependency
from app.core.exceptions.dependencies import ServiceUnavailableException

logger = logging.getLogger("src.dependencies.messaging")


class MessagingDependency(BaseDependency):
    """
    Зависимость для работы с системой обмена сообщениями.

    Наследует BaseDependency и предоставляет методы для получения
    подключений к RabbitMQ с обработкой ошибок.
    """

    def __init__(self) -> None:
        super().__init__()
        self._client = RabbitMQClient()

    async def get_dependency(self) -> AbstractRobustConnection:
        """
        Получает подключение к RabbitMQ.

        Returns:
            AbstractRobustConnection: Подключение к RabbitMQ

        Raises:
            ServiceUnavailableException: Если не удается подключиться к RabbitMQ
        """
        try:
            self.logger.debug("Получение подключения к RabbitMQ")
            return await self._client.connect()
        except Exception as e:
            await self.handle_exception(e, "RabbitMQ")


async def get_rabbitmq_connection() -> AsyncGenerator[AbstractRobustConnection, None]:
    """
    Зависимость для получения подключения к RabbitMQ.

    Yields:
        AbstractRobustConnection: Подключение к RabbitMQ

    Raises:
        ServiceUnavailableException: Если не удается подключиться к RabbitMQ.
    """
    dependency = MessagingDependency()
    try:
        logger.debug("Создание подключения к RabbitMQ")
        connection = await dependency.get_dependency()
        yield connection
    except Exception as e:
        logger.error("Ошибка подключения к RabbitMQ: %s", e)
        raise ServiceUnavailableException("Messaging (RabbitMQ)") from e


async def get_rabbitmq_context() -> AsyncGenerator[AbstractRobustConnection, None]:
    """
    Зависимость для получения подключения к RabbitMQ через контекстный менеджер.

    Yields:
        AbstractRobustConnection: Подключение к RabbitMQ

    Raises:
        ServiceUnavailableException: Если не удается подключиться к RabbitMQ.
    """
    try:
        logger.debug("Создание подключения к RabbitMQ через контекстный менеджер")
        async with RabbitMQContextManager() as connection:
            yield connection
    except Exception as e:
        logger.error("Ошибка подключения к RabbitMQ через контекстный менеджер: %s", e)
        raise ServiceUnavailableException("Messaging (RabbitMQ)") from e


# Типизированные зависимости
RabbitMQConnectionDep = Annotated[
    AbstractRobustConnection, Depends(get_rabbitmq_connection)
]
RabbitMQContextDep = Annotated[AbstractRobustConnection, Depends(get_rabbitmq_context)]
