"""
Модуль подключений к внешним сервисам.

Exports:
    - DatabaseClient: PostgreSQL connection
    - get_db_session: Утилита для получения сессии базы данных
    - RedisClient: Redis connection
    - get_redis_client: Утилита для получения Redis клиента
"""

from .cache import RedisClient, get_redis_client
from .database import DatabaseClient, get_db_session

__all__ = [
    "DatabaseClient",
    "get_db_session",
    "RedisClient",
    "get_redis_client",
]
