"""
Зависимости для работы с кэшем (Redis) в FastAPI.

Предоставляет зависимости для получения клиента Redis
через src.core.connections.cache.
"""

import logging
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.core.connections.cache import get_redis_client
from app.core.exceptions import ServiceUnavailableException

logger = logging.getLogger(__name__)


async def get_redis_dependency() -> Redis:
    """
    Зависимость для получения клиента Redis.

    Использует функцию get_redis_client из src.core.connections.cache
    для создания подключения к Redis.

    Returns:
        Redis: Асинхронный клиент Redis

    Raises:
        ServiceUnavailableException: Если не удается подключиться к Redis (503 Service Unavailable).

    Usage:
        ```python
        @router.get("/cache")
        async def get_cache(redis: RedisDep):
            value = await redis.get("key")
            return {"value": value}
        ```
    """
    try:
        logger.debug("Создание экземпляра Redis")
        return await get_redis_client()
    except Exception as e:
        logger.error("Ошибка при создании Redis клиента: %s", str(e), exc_info=True)
        raise ServiceUnavailableException(service_name="Redis") from e


# Типизированная зависимость
RedisDep = Annotated[Redis, Depends(get_redis_dependency)]
