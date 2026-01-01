"""
Заглушка для отключенного кеша.

Используется когда кеширование не требуется или отключено в конфигурации.
Все операции возвращают пустые результаты без выполнения реальных действий.
"""

import logging
from typing import Any

from .backend import CacheBackend

logger = logging.getLogger(__name__)


class NoCacheBackend(CacheBackend):
    """
    Пустая реализация кеша (No-Op).

    Используется по умолчанию когда кеширование отключено.
    Все методы возвращают значения, указывающие на отсутствие кеша.

    Преимущества:
    - Нулевой оверхед
    - Не требует внешних зависимостей
    - Безопасна для использования в тестах

    Example:
        >>> cache = NoCacheBackend()
        >>> await cache.set("key", "value")  # Ничего не делает
        >>> result = await cache.get("key")  # Всегда None
    """

    async def get(self, key: str) -> Any | None:
        """
        Всегда возвращает None (кеш отключен).

        Args:
            key (str): Ключ (игнорируется).

        Returns:
            None: Всегда None, т.к. кеш отключен.
        """
        logger.debug("NoCacheBackend: get(%s) -> None (cache disabled)", key)
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Ничего не делает (кеш отключен).

        Args:
            key (str): Ключ (игнорируется).
            value (Any): Значение (игнорируется).
            ttl (int): TTL (игнорируется).

        Returns:
            bool: Всегда False, т.к. ничего не сохранено.
        """
        logger.debug("NoCacheBackend: set(%s, ..., ttl=%d) -> False (cache disabled)", key, ttl)
        return False

    async def delete(self, key: str) -> bool:
        """
        Ничего не делает (кеш отключен).

        Args:
            key (str): Ключ (игнорируется).

        Returns:
            bool: Всегда False, т.к. нечего удалять.
        """
        logger.debug("NoCacheBackend: delete(%s) -> False (cache disabled)", key)
        return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Ничего не делает (кеш отключен).

        Args:
            pattern (str): Паттерн (игнорируется).

        Returns:
            int: Всегда 0, т.к. нечего инвалидировать.
        """
        logger.debug("NoCacheBackend: invalidate_pattern(%s) -> 0 (cache disabled)", pattern)
        return 0
