"""
Модуль мониторинга для репозиториев.

Предоставляет систему хуков для трассировки запросов:
- QueryHook: Абстрактный интерфейс хука
- QueryMetrics: Структура данных метрик
- CompositeQueryHook: Композитный хук
- LoggingHook: Хук для логирования
- DetailedLoggingHook: Расширенный хук с статистикой

Example:
    >>> from app.repository.monitoring import LoggingHook
    >>> hook = LoggingHook(slow_query_threshold_ms=200)
    >>> repo.add_hook(hook)
"""

from .hooks import CompositeQueryHook, QueryHook, QueryMetrics
from .logging import DetailedLoggingHook, LoggingHook

__all__ = [
    "QueryHook",
    "QueryMetrics",
    "CompositeQueryHook",
    "LoggingHook",
    "DetailedLoggingHook",
]
