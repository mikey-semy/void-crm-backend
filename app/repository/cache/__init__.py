"""
Модуль кеширования для репозиториев.

Предоставляет абстрактный интерфейс и реализации кеша:
- CacheBackend: Абстрактный интерфейс
- RedisCacheBackend: Production кеш через Redis
- InMemoryCacheBackend: Development/testing кеш в памяти
- NoCacheBackend: Заглушка для отключенного кеша

Example:
    >>> from app.repository.cache import RedisCacheBackend
    >>> cache = RedisCacheBackend()
    >>> await cache.set("key", "value", ttl=300)
"""

from .backend import CacheBackend
from .memory import InMemoryCacheBackend
from .none import NoCacheBackend
from .redis import RedisCacheBackend

__all__ = [
    "CacheBackend",
    "RedisCacheBackend",
    "InMemoryCacheBackend",
    "NoCacheBackend",
]
