"""
In-memory кеш для разработки и тестирования.

Реализация кеша в памяти с поддержкой TTL.
Используется для разработки и тестов, когда Redis недоступен.
"""

import logging
import time
from typing import Any

from .backend import CacheBackend

logger = logging.getLogger(__name__)


class InMemoryCacheBackend(CacheBackend):
    """
    In-memory кеш с поддержкой TTL.

    Сохраняет данные в словаре с отслеживанием времени истечения.
    Подходит для разработки и тестирования.

    Warning:
        Не использовать в production! Данные теряются при перезапуске.
        Не распределен между процессами/серверами.

    Attributes:
        _storage (Dict): Словарь для хранения значений.
        _expiry (Dict): Словарь для хранения времени истечения.

    Example:
        >>> cache = InMemoryCacheBackend()
        >>> await cache.set("key", "value", ttl=60)
        >>> value = await cache.get("key")  # "value"
        >>> await asyncio.sleep(61)
        >>> value = await cache.get("key")  # None (истек TTL)
    """

    def __init__(self):
        """Инициализация in-memory кеша."""
        self._storage: dict[str, Any] = {}
        self._expiry: dict[str, float] = {}  # Время истечения (timestamp)

    def _is_expired(self, key: str) -> bool:
        """
        Проверить истек ли TTL ключа.

        Args:
            key (str): Ключ для проверки.

        Returns:
            bool: True если ключ истек или не существует.
        """
        if key not in self._expiry:
            return True

        return time.time() > self._expiry[key]

    def _cleanup_expired(self, key: str) -> None:
        """
        Удалить истекший ключ из хранилища.

        Args:
            key (str): Ключ для удаления.
        """
        if key in self._storage:
            del self._storage[key]
        if key in self._expiry:
            del self._expiry[key]

    async def get(self, key: str) -> Any | None:
        """
        Получить значение из in-memory кеша.

        Args:
            key (str): Ключ для поиска.

        Returns:
            Optional[Any]: Значение или None если не найдено/истекло.

        Example:
            >>> value = await cache.get("user:123")
        """
        if key not in self._storage:
            logger.debug("Cache MISS: %s (not found)", key)
            return None

        if self._is_expired(key):
            logger.debug("Cache MISS: %s (expired)", key)
            self._cleanup_expired(key)
            return None

        logger.debug("Cache HIT: %s", key)
        return self._storage[key]

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Сохранить значение в in-memory кеш.

        Args:
            key (str): Ключ для сохранения.
            value (Any): Значение для кеширования.
            ttl (int): Время жизни в секундах.

        Returns:
            bool: Всегда True.

        Example:
            >>> await cache.set("user:123", user_data, ttl=600)
        """
        self._storage[key] = value
        self._expiry[key] = time.time() + ttl

        logger.debug("Cache SET: %s (TTL=%ds)", key, ttl)
        return True

    async def delete(self, key: str) -> bool:
        """
        Удалить значение из in-memory кеша.

        Args:
            key (str): Ключ для удаления.

        Returns:
            bool: True если ключ был удален.

        Example:
            >>> await cache.delete("user:123")
        """
        if key in self._storage:
            self._cleanup_expired(key)
            logger.debug("Cache DELETE: %s", key)
            return True

        logger.debug("Cache DELETE (not found): %s", key)
        return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Инвалидировать все ключи по паттерну.

        Поддерживает простую wildcart подстановку (*).

        Args:
            pattern (str): Паттерн для поиска (например "user:*").

        Returns:
            int: Количество удаленных ключей.

        Example:
            >>> count = await cache.invalidate_pattern("user:*")
        """
        import fnmatch

        # Найти все ключи, соответствующие паттерну
        matching_keys = [key for key in self._storage.keys() if fnmatch.fnmatch(key, pattern)]

        # Удалить найденные ключи
        for key in matching_keys:
            self._cleanup_expired(key)

        count = len(matching_keys)
        if count > 0:
            logger.info("Cache INVALIDATE: pattern='%s', deleted=%d keys", pattern, count)
        else:
            logger.debug("Cache INVALIDATE: pattern='%s', no keys found", pattern)

        return count

    async def clear(self) -> None:
        """
        Очистить весь кеш.

        Утилитарный метод для тестов.

        Example:
            >>> await cache.clear()
        """
        self._storage.clear()
        self._expiry.clear()
        logger.debug("Cache CLEAR: all keys removed")
