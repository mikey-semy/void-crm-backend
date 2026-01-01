from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.settings import settings

from .logging import LoggingMiddleware
from .rate_limits import RateLimitMiddleware as RateLimitMiddleware
from .timing import TimingMiddleware


def setup_middlewares(app: FastAPI):
    """
    Настраивает все middleware для приложения FastAPI.

    ВАЖНО: В Starlette middleware выполняются в ОБРАТНОМ порядке добавления!
    Последний добавленный = первый в цепочке обработки.
    CORSMiddleware должен быть ПОСЛЕДНИМ в add_middleware, чтобы выполняться ПЕРВЫМ.
    """
    secret_key = settings.TOKEN_SECRET_KEY.get_secret_value()
    # Порядок выполнения (сверху вниз): CORS -> Session -> Readiness -> Timing -> Logging
    # Порядок добавления (обратный): Logging -> Timing -> Readiness -> Session -> CORS
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(TimingMiddleware, slow_threshold_ms=settings.SLOW_THRESHOLD_MS)
    app.add_middleware(RateLimitMiddleware, **settings.rate_limit_params)
    app.add_middleware(SessionMiddleware, secret_key=secret_key)
    # CORSMiddleware ПОСЛЕДНИМ в add_middleware = ПЕРВЫМ в обработке!
    app.add_middleware(CORSMiddleware, **settings.cors_params)
