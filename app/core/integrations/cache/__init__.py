"""
Интеграции с Redis для кэширования данных.

Содержит менеджеры для работы с различными типами данных в Redis:
- BaseRedisManager: Базовый класс для работы с Redis
- AuthRedisManager: Менеджер для аутентификации и токенов
"""

from .auth import AuthRedisManager
from .base import BaseRedisManager

__all__ = [
    "BaseRedisManager",
    "AuthRedisManager",
]
