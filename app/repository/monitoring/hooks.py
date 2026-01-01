"""
Система хуков для трассировки запросов к БД.

Определяет интерфейс QueryHook и структуру данных QueryMetrics
для мониторинга производительности запросов в репозиториях.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """
    Метрики выполнения запроса к БД.

    Содержит информацию о времени выполнения, количестве затронутых строк
    и дополнительных параметрах запроса.

    Attributes:
        query_type (str): Тип запроса (select, insert, update, delete, count).
        model_name (str): Имя модели SQLAlchemy.
        execution_time_ms (float): Время выполнения в миллисекундах.
        rows_affected (int): Количество затронутых/полученных строк.
        timestamp (datetime): Время выполнения запроса.
        query_params (Dict): Параметры запроса (фильтры, опции и т.д.).
        cache_hit (bool): Был ли запрос взят из кеша.
        error (Optional[str]): Описание ошибки, если произошла.

    Example:
        >>> metrics = QueryMetrics(
        ...     query_type="select",
        ...     model_name="ProductModel",
        ...     execution_time_ms=45.2,
        ...     rows_affected=150
        ... )
    """

    query_type: str
    model_name: str
    execution_time_ms: float
    rows_affected: int
    timestamp: datetime = field(default_factory=datetime.now)
    query_params: dict[str, Any] = field(default_factory=dict)
    cache_hit: bool = False
    error: str | None = None

    def __str__(self) -> str:
        """Форматированное представление метрик."""
        status = "CACHE HIT" if self.cache_hit else f"{self.rows_affected} rows"
        error_part = f" ERROR: {self.error}" if self.error else ""

        return f"Query '{self.query_type}' for {self.model_name}: {self.execution_time_ms:.2f}ms, {status}{error_part}"


class QueryHook(ABC):
    """
    Абстрактный интерфейс хука для трассировки запросов.

    Хуки вызываются до и после выполнения запросов к БД,
    позволяя собирать метрики, логировать или отправлять данные в системы мониторинга.

    Реализации должны переопределить методы before_execute и after_execute.

    Example:
        >>> class MyHook(QueryHook):
        ...     async def before_execute(self, query_type, model_name):
        ...         print(f"Starting {query_type} on {model_name}")
        ...
        ...     async def after_execute(self, metrics):
        ...         print(f"Completed in {metrics.execution_time_ms}ms")
    """

    @abstractmethod
    async def before_execute(
        self,
        query_type: str,
        model_name: str,
        query_params: dict[str, Any] | None = None,
    ) -> None:
        """
        Вызывается перед выполнением запроса.

        Args:
            query_type (str): Тип запроса (select, insert, update, delete).
            model_name (str): Имя модели SQLAlchemy.
            query_params (Optional[Dict]): Параметры запроса.

        Example:
            >>> await hook.before_execute("select", "UserModel", {"is_active": True})
        """
        pass

    @abstractmethod
    async def after_execute(self, metrics: QueryMetrics) -> None:
        """
        Вызывается после выполнения запроса.

        Args:
            metrics (QueryMetrics): Метрики выполненного запроса.

        Example:
            >>> await hook.after_execute(metrics)
        """
        pass


class CompositeQueryHook(QueryHook):
    """
    Композитный хук для объединения нескольких хуков.

    Позволяет вызывать несколько хуков последовательно.
    Используется внутри BaseRepository для управления списком хуков.

    Attributes:
        hooks (list): Список активных хуков.

    Example:
        >>> composite = CompositeQueryHook()
        >>> composite.add(LoggingHook())
        >>> composite.add(PrometheusHook())
        >>> await composite.after_execute(metrics)  # Вызовет оба хука
    """

    def __init__(self):
        """Инициализация композитного хука."""
        self.hooks: list[QueryHook] = []

    def add(self, hook: QueryHook) -> None:
        """
        Добавить хук в список.

        Args:
            hook (QueryHook): Хук для добавления.
        """
        if hook not in self.hooks:
            self.hooks.append(hook)
            logger.debug("Added hook: %s", hook.__class__.__name__)

    def remove(self, hook: QueryHook) -> bool:
        """
        Удалить хук из списка.

        Args:
            hook (QueryHook): Хук для удаления.

        Returns:
            bool: True если хук был удален.
        """
        if hook in self.hooks:
            self.hooks.remove(hook)
            logger.debug("Removed hook: %s", hook.__class__.__name__)
            return True
        return False

    def clear(self) -> None:
        """Удалить все хуки."""
        self.hooks.clear()
        logger.debug("Cleared all hooks")

    async def before_execute(
        self,
        query_type: str,
        model_name: str,
        query_params: dict[str, Any] | None = None,
    ) -> None:
        """Вызвать before_execute для всех хуков."""
        for hook in self.hooks:
            try:
                await hook.before_execute(query_type, model_name, query_params)
            except Exception as e:
                logger.error(
                    "Error in hook %s.before_execute: %s",
                    hook.__class__.__name__,
                    e,
                    exc_info=True,
                )

    async def after_execute(self, metrics: QueryMetrics) -> None:
        """Вызвать after_execute для всех хуков."""
        for hook in self.hooks:
            try:
                await hook.after_execute(metrics)
            except Exception as e:
                logger.error(
                    "Error in hook %s.after_execute: %s",
                    hook.__class__.__name__,
                    e,
                    exc_info=True,
                )
