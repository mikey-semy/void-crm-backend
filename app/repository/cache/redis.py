"""
Реализация кеша через Redis.

Использует существующий Redis клиент из src.core.connections.cache.
Поддерживает сериализацию/десериализацию Python объектов через pickle.
"""

import logging
import pickle
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.connections.cache import get_redis_client

from .backend import CacheBackend

logger = logging.getLogger(__name__)


class RedisCacheBackend(CacheBackend):
    """
    Реализация кеша через Redis.

    Использует существующее подключение к Redis из приложения.
    Автоматически сериализует/десериализует Python объекты через pickle.

    Attributes:
        _redis (Optional[Redis]): Клиент Redis (lazy initialization).

    Example:
        >>> cache = RedisCacheBackend()
        >>> await cache.set("user:123", {"name": "John"}, ttl=600)
        >>> user = await cache.get("user:123")
    """

    def __init__(self):
        """Инициализация Redis cache backend."""
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis:
        """
        Получить Redis клиент (lazy initialization).

        Переиспользует существующее подключение из src.core.connections.cache.

        Returns:
            Redis: Асинхронный Redis клиент.

        Raises:
            RedisError: При ошибке подключения к Redis.
        """
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis

    async def get(self, key: str) -> Any | None:
        """
        Получить значение из Redis по ключу.

        Args:
            key (str): Ключ для поиска.

        Returns:
            Optional[Any]: Десериализованное значение или None.

        Example:
            >>> user = await cache.get("user:123")
        """
        try:
            redis = await self._get_redis()
            raw_value = await redis.get(key)

            if raw_value is None:
                logger.debug("Cache MISS: %s", key)
                return None

            # Десериализуем через pickle
            value = pickle.loads(raw_value)
            logger.debug("Cache HIT: %s", key)
            return value

        except RedisError as e:
            logger.error("Redis error on GET %s: %s", key, e)
            return None
        except (pickle.PickleError, Exception) as e:
            logger.error("Failed to deserialize cache value for %s: %s", key, e)
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Сохранить значение в Redis с TTL.

        Args:
            key (str): Ключ для сохранения.
            value (Any): Значение для кеширования.
            ttl (int): Время жизни в секундах.

        Returns:
            bool: True если успешно сохранено.

        Example:
            >>> await cache.set("user:123", user_data, ttl=600)
        """
        try:
            redis = await self._get_redis()

            # Сериализуем через pickle
            serialized = pickle.dumps(value)

            # Сохраняем с TTL
            await redis.setex(key, ttl, serialized)
            logger.debug("Cache SET: %s (TTL=%ds)", key, ttl)
            return True

        except RedisError as e:
            logger.error("Redis error on SET %s: %s", key, e)
            return False
        except (pickle.PickleError, Exception) as e:
            logger.error("Failed to serialize value for %s: %s", key, e)
            return False

    async def delete(self, key: str) -> bool:
        """
        Удалить значение из Redis.

        Args:
            key (str): Ключ для удаления.

        Returns:
            bool: True если ключ был удален.

        Example:
            >>> await cache.delete("user:123")
        """
        try:
            redis = await self._get_redis()
            result = await redis.delete(key)

            if result > 0:
                logger.debug("Cache DELETE: %s", key)
                return True
            else:
                logger.debug("Cache DELETE (not found): %s", key)
                return False

        except RedisError as e:
            logger.error("Redis error on DELETE %s: %s", key, e)
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Инвалидировать все ключи по паттерну в Redis.

        Использует SCAN для безопасного поиска ключей и DELETE для удаления.

        Args:
            pattern (str): Паттерн Redis (например "user:*").

        Returns:
            int: Количество удаленных ключей.

        Example:
            >>> count = await cache.invalidate_pattern("user:*")
        """
        try:
            redis = await self._get_redis()
            count = 0

            # Используем SCAN для безопасного поиска (не блокирует Redis)
            async for key in redis.scan_iter(match=pattern, count=100):
                await redis.delete(key)
                count += 1

            if count > 0:
                logger.info("Cache INVALIDATE: pattern='%s', deleted=%d keys", pattern, count)
            else:
                logger.debug("Cache INVALIDATE: pattern='%s', no keys found", pattern)

            return count

        except RedisError as e:
            logger.error("Redis error on INVALIDATE pattern '%s': %s", pattern, e)
            return 0
