"""
Хук для логирования метрик запросов.

Реализация QueryHook для вывода метрик в логи приложения.
"""

import logging
from typing import Any

from .hooks import QueryHook, QueryMetrics

logger = logging.getLogger(__name__)


class LoggingHook(QueryHook):
    """
    Хук для логирования метрик запросов в stdout/файлы.

    Выводит информацию о запросах в лог с уровнем INFO/WARNING/ERROR
    в зависимости от результата выполнения и времени.

    Attributes:
        slow_query_threshold_ms (float): Порог медленного запроса в мс (по умолчанию 100мс).
        log_query_params (bool): Логировать ли параметры запроса (по умолчанию False).

    Example:
        >>> hook = LoggingHook(slow_query_threshold_ms=200)
        >>> repo.add_hook(hook)
        >>> # INFO: Query 'select' for ProductModel: 45.2ms, 150 rows
        >>> # WARNING: SLOW Query 'select' for ProductModel: 250.5ms, 1000 rows
    """

    def __init__(self, slow_query_threshold_ms: float = 100.0, log_query_params: bool = False):
        """
        Инициализация logging hook.

        Args:
            slow_query_threshold_ms (float): Порог медленного запроса (мс).
            log_query_params (bool): Логировать параметры запроса.
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.log_query_params = log_query_params

    async def before_execute(
        self,
        query_type: str,
        model_name: str,
        query_params: dict[str, Any] | None = None,
    ) -> None:
        """
        Логирование перед выполнением запроса.

        Args:
            query_type (str): Тип запроса.
            model_name (str): Имя модели.
            query_params (Optional[Dict]): Параметры запроса.
        """
        if self.log_query_params and query_params:
            logger.debug(
                "Starting query '%s' for %s with params: %s",
                query_type,
                model_name,
                query_params,
            )
        else:
            logger.debug("Starting query '%s' for %s", query_type, model_name)

    async def after_execute(self, metrics: QueryMetrics) -> None:
        """
        Логирование после выполнения запроса.

        Выбирает уровень логирования:
        - ERROR: если произошла ошибка
        - WARNING: если запрос медленный (> threshold)
        - INFO: обычный запрос

        Args:
            metrics (QueryMetrics): Метрики запроса.
        """
        # Формируем базовое сообщение
        message = str(metrics)

        # Добавляем параметры если нужно
        if self.log_query_params and metrics.query_params:
            message += f" | Params: {metrics.query_params}"

        # Выбираем уровень логирования
        if metrics.error:
            logger.error(message)
        elif metrics.execution_time_ms > self.slow_query_threshold_ms:
            logger.warning("SLOW %s", message)
        else:
            logger.info(message)


class DetailedLoggingHook(LoggingHook):
    """
    Расширенная версия LoggingHook с детальной информацией.

    Дополнительно логирует:
    - Количество запросов за сессию
    - Среднее время выполнения
    - Кеш hit rate

    Example:
        >>> hook = DetailedLoggingHook()
        >>> repo.add_hook(hook)
    """

    def __init__(
        self,
        slow_query_threshold_ms: float = 100.0,
        log_query_params: bool = True,  # По умолчанию логируем параметры
    ):
        """Инициализация detailed logging hook."""
        super().__init__(slow_query_threshold_ms, log_query_params)
        self.query_count = 0
        self.total_time_ms = 0.0
        self.cache_hits = 0
        self.cache_misses = 0

    async def after_execute(self, metrics: QueryMetrics) -> None:
        """
        Логирование с дополнительной статистикой.

        Args:
            metrics (QueryMetrics): Метрики запроса.
        """
        # Обновляем статистику
        self.query_count += 1
        self.total_time_ms += metrics.execution_time_ms

        if metrics.cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        # Вызываем базовое логирование
        await super().after_execute(metrics)

        # Каждые 10 запросов выводим статистику
        if self.query_count % 10 == 0:
            avg_time = self.total_time_ms / self.query_count
            cache_hit_rate = (self.cache_hits / self.query_count * 100) if self.query_count > 0 else 0

            logger.info(
                "Query stats: count=%d, avg_time=%.2fms, cache_hit_rate=%.1f%%",
                self.query_count,
                avg_time,
                cache_hit_rate,
            )
