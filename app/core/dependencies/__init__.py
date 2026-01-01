"""
Модуль зависимостей FastAPI.

Содержит все зависимости для внедрения в роуты и сервисы приложения.
Организован по категориям соответствующим src.core.connections.
"""

# Database dependencies
from .database import AsyncSessionDep
from .health import HealthServiceDep
from .pagination import PaginationDep

__all__ = [
    # Database dependencies
    "AsyncSessionDep",
    # Health dependencies
    "HealthServiceDep",
    # Pagination dependencies
    "PaginationDep",
]
