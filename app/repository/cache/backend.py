"""
Абстрактный интерфейс для кеш-бэкенда репозитория.

Определяет базовый контракт для реализаций кеширования:
- Redis (production)
- In-Memory (development/testing)
- None (отключенный кеш)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """
    Абстрактный интерфейс для кеш-бэкенда.

    Определяет методы для работы с кешем в контексте репозиториев.
    Все реализации должны быть асинхронными для совместимости с AsyncSession.

    Example:
        >>> class MyCacheBackend(CacheBackend):
        ...     async def get(self, key: str) -> Optional[Any]:
        ...         return await self.storage.get(key)
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Получить значение из кеша по ключу.

        Args:
            key (str): Ключ для поиска в кеше.

        Returns:
            Optional[Any]: Закешированное значение или None, если не найдено.

        Example:
            >>> value = await cache.get("user:123")
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Сохранить значение в кеш с TTL.

        Args:
            key (str): Ключ для сохранения.
            value (Any): Значение для кеширования (должно быть сериализуемым).
            ttl (int): Время жизни в секундах (по умолчанию 300 = 5 минут).

        Returns:
            bool: True если успешно, False иначе.

        Example:
            >>> await cache.set("user:123", user_data, ttl=600)
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Удалить значение из кеша.

        Args:
            key (str): Ключ для удаления.

        Returns:
            bool: True если удалено, False если ключ не существовал.

        Example:
            >>> await cache.delete("user:123")
        """
        pass

    @abstractmethod
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Инвалидировать все ключи по паттерну.

        Используется для массовой инвалидации, например при обновлении модели.

        Args:
            pattern (str): Паттерн для поиска ключей (например "user:*").

        Returns:
            int: Количество удаленных ключей.

        Example:
            >>> # Инвалидировать все кеши пользователей
            >>> count = await cache.invalidate_pattern("user:*")
            >>> print(f"Удалено {count} ключей")
        """
        pass

    def build_key(self, model_name: str, operation: str, *args, **kwargs) -> str:
        """
        Построить ключ кеша по шаблону.

        Утилитарный метод для генерации консистентных ключей.

        Args:
            model_name (str): Имя модели (например "UserModel").
            operation (str): Тип операции (например "get_by_id", "filter_by").
            *args: Позиционные аргументы для ключа.
            **kwargs: Именованные аргументы для ключа.

        Returns:
            str: Сгенерированный ключ кеша.

        Example:
            >>> key = cache.build_key("UserModel", "get_by_id", user_id)
            >>> # "UserModel:get_by_id:123e4567-e89b-12d3-a456-426614174000"
        """
        parts = [model_name, operation]

        # Добавляем позиционные аргументы
        for arg in args:
            parts.append(str(arg))

        # Добавляем именованные аргументы (отсортированные для консистентности)
        if kwargs:
            for k in sorted(kwargs.keys()):
                parts.append(f"{k}={kwargs[k]}")

        return ":".join(parts)
