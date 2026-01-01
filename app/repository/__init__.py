"""
Инициализация модуля репозиториев.
"""

from app.repository.base import BaseRepository, SessionMixin

__all__ = [
    "BaseRepository",
    "SessionMixin",
]
