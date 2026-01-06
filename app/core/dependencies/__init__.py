"""
Модуль зависимостей FastAPI.

Содержит все зависимости для внедрения в роуты и сервисы приложения.
Организован по категориям соответствующим app.core.connections.
"""

# Database dependencies
from .database import AsyncSessionDep
from .health import HealthServiceDep
from .pagination import PaginationDep
from .auth import AuthServiceDep
from .token import TokenServiceDep
from .users import UserServiceDep
from .user_settings import UserAccessTokenServiceDep

__all__ = [
    # Database dependencies
    "AsyncSessionDep",
    # Health dependencies
    "HealthServiceDep",
    # Pagination dependencies
    "PaginationDep",
    # Auth dependencies
    "AuthServiceDep",
    # Token dependencies
    "TokenServiceDep",
    # User dependencies
    "UserServiceDep",
    # User settings dependencies
    "UserAccessTokenServiceDep",
]
