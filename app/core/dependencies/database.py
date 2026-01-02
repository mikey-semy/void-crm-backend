"""
Зависимости для работы с базой данных в FastAPI.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connections import get_db_session
from app.core.exceptions.dependencies import ServiceUnavailableException

logger = logging.getLogger("app.dependencies.database")


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость для получения асинхронной сессии базы данных.

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy

    Raises:
        ServiceUnavailableException: Если не удается подключиться к Postgres.
    """
    try:
        logger.debug("Создание сессии базы данных")
        async for session in get_db_session():
            yield session
    except RuntimeError as e:
        # Ловим только ошибки инициализации/подключения к базе
        logger.error("Ошибка подключения к базе данных: %s", e)
        raise ServiceUnavailableException("Database (Postgres)") from e
    except Exception:
        # Все остальные ошибки пробрасываем дальше!
        raise


# Типизированная зависимость
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
