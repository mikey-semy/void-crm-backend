"""
Репозиторий для проверки состояния системы.
"""

import logging

from sqlalchemy import text

from app.repository import SessionMixin

logger = logging.getLogger(__name__)


class HealthRepository(SessionMixin):
    """
    Репозиторий для проверки состояния системы.

    Attributes:
        session (AsyncSession): Асинхронная сессия базы данных

    Methods:
        check_database_connection: Проверяет соединение с базой данных
    """

    async def check_database_connection(self) -> bool:
        """
        Проверяет соединение с базой данных.

        Returns:
            bool: True если БД доступна, False если нет
        """
        try:
            result = await self.session.execute(text("SELECT 1"))
            row = result.fetchone()
            is_connected = row is not None

            if is_connected:
                logger.debug("Database connection check: OK")
            else:
                logger.warning("Database connection check: FAIL (no rows returned)")

            return is_connected
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Database connection check failed: %s", exc)
            return False
