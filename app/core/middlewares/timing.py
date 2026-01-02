"""
Middleware для измерения времени выполнения HTTP запросов.

Измеряет время обработки каждого запроса и:
- Добавляет заголовок X-Process-Time-Ms в ответ
- Логирует медленные запросы (> threshold) как WARNING
- Логирует обычные запросы как DEBUG

Использование:
    from app.core.middlewares.timing import TimingMiddleware

    app = FastAPI()
    app.add_middleware(TimingMiddleware, slow_threshold_ms=500.0)

Зависимости:
    - FastAPI/Starlette для обработки HTTP
    - logging для работы с логами
    - time для измерения времени
"""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """
    Middleware для измерения и логирования времени выполнения запросов.

    Attributes:
        slow_threshold_ms: Порог медленного запроса в миллисекундах.
            Запросы дольше этого значения логируются как WARNING.

    Example:
        >>> app.add_middleware(TimingMiddleware, slow_threshold_ms=500.0)
        >>>
        >>> # При запросе:
        >>> # DEBUG: POST /api/v1/specifications/filters 45.23ms
        >>> # WARNING: POST /api/v1/specifications/filters 650.45ms (slow)
    """

    def __init__(self, app, slow_threshold_ms: float = 500.0):
        """
        Инициализация TimingMiddleware.

        Args:
            app: ASGI приложение
            slow_threshold_ms: Порог медленного запроса в миллисекундах (default: 500.0)
        """
        super().__init__(app)
        self.slow_threshold_ms = slow_threshold_ms

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Обработка запроса с измерением времени выполнения.

        Args:
            request: HTTP запрос
            call_next: Следующий обработчик в цепочке

        Returns:
            Response с добавленным заголовком X-Process-Time-Ms
        """
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000

        # Добавляем заголовок с временем выполнения
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

        # Логирование с разным уровнем в зависимости от времени
        method = request.method
        path = request.url.path

        if duration_ms > self.slow_threshold_ms:
            logger.warning(
                "%s %s %.2fms (slow, threshold=%.0fms)",
                method,
                path,
                duration_ms,
                self.slow_threshold_ms,
            )
        else:
            logger.debug("%s %s %.2fms", method, path, duration_ms)

        return response
