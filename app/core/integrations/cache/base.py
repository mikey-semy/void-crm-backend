"""
Базовый класс для работы с Redis.

Предоставляет общие методы для работы с различными типами данных Redis:
- Строки (get, set, delete)
- Множества (sadd, srem, smembers, sismember)
- TTL (set_expire)
"""

import logging

from redis.asyncio import Redis


class BaseRedisManager:
    """
    Базовый класс для работы с Redis.

    Attributes:
        redis: Экземпляр Redis.

    Methods:
        set: Записывает значение в Redis.
        get: Получает значение из Redis.
        delete: Удаляет значение из Redis.
        sadd: Добавляет значение в множество Redis.
        srem: Удаляет значение из множества Redis.
        smembers: Получает все значения из множества Redis.
        keys: Возвращает список всех ключей в Redis.
    """

    def __init__(self, redis: Redis):
        self.redis = redis
        self.logger = logging.getLogger(self.__class__.__name__)

    async def set(self, key: str, value: str, expires: int | None = None) -> None:
        """
        Записывает значение в Redis.

        Args:
            key: Ключ для записи
            value: Значение для записи
            expires: Время жизни ключа в секундах

        Returns:
            None
        """
        await self.redis.set(key, value, ex=expires)

    async def get(self, key: str) -> str | None:
        """
        Получает значение из Redis.

        Args:
            key: Ключ для получения

        Returns:
            Значение из Redis или None, если ключ не найден
        """
        result = await self.redis.get(key)
        return result.decode() if result else None

    async def delete(self, key: str) -> None:
        """
        Удаляет ключ из Redis.

        Args:
            key: Ключ для удаления

        Returns:
            None
        """
        await self.redis.delete(key)

    async def sadd(self, key: str, value: str) -> None:
        """
        Добавляет значение в множество в Redis.

        Args:
            key: Ключ множества
            value: Значение для добавления

        Returns:
            None
        """
        await self.redis.sadd(key, value)

    async def srem(self, key: str, value: str) -> None:
        """
        Удаляет значение из множества в Redis.

        Args:
            key: Ключ множества
            value: Значение для удаления

        Returns:
            None
        """
        await self.redis.srem(key, value)

    async def keys(self, pattern: str) -> list[bytes]:
        """
        Получает ключи по паттерну

        Args:
            pattern: Паттерн для поиска ключей

        Returns:
            List[bytes]: Список ключей
        """
        return await self.redis.keys(pattern)

    async def smembers(self, key: str) -> list[str]:
        """
        Получает все элементы множества

        Args:
            key: Ключ множества

        Returns:
            List[str]: Список элементов множества
        """
        result = await self.redis.smembers(key)
        return [member.decode() for member in result] if result else []

    async def sismember(self, key: str, value: str) -> bool:
        """
        Проверяет, содержит ли множество указанное значение.

        Args:
            key: Ключ множества
            value: Значение для проверки

        Returns:
            bool: True, если значение содержится в множестве, иначе False
        """
        return bool(await self.redis.sismember(key, value))

    async def set_expire(self, key: str, seconds: int) -> None:
        """
        Устанавливает время жизни ключа.

        Args:
            key: Ключ
            seconds: Время жизни в секундах

        Returns:
            None
        """
        await self.redis.expire(key, seconds)

    async def scan(
        self, cursor: int = 0, match: str | None = None, count: int = 100
    ) -> tuple[int, list[bytes]]:
        """
        Итеративно сканирует ключи Redis без блокировки.

        В отличие от KEYS, SCAN не блокирует Redis и безопасен для production.
        Возвращает курсор для продолжения итерации и список найденных ключей.

        Args:
            cursor: Позиция курсора (0 для начала сканирования)
            match: Паттерн для фильтрации ключей (например, "token:*")
            count: Примерное количество ключей за итерацию

        Returns:
            tuple[int, list[bytes]]: (новый_курсор, список_ключей)
                - Когда курсор = 0, сканирование завершено

        Example:
            >>> cursor = 0
            >>> while True:
            ...     cursor, keys = await redis.scan(cursor, match="token:*")
            ...     for key in keys:
            ...         print(key)
            ...     if cursor == 0:
            ...         break
        """
        return await self.redis.scan(cursor=cursor, match=match, count=count)
