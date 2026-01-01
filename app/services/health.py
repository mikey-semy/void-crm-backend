"""
Сервис для проверки состояния приложения и его зависимостей.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connections.cache import RedisClient
from app.repository.health import HealthRepository
from app.services import BaseService


class HealthService(BaseService):
    """
    Сервис для проверки состояния приложения и его зависимостей.

    Attributes:
        repository (HealthRepository): Репозиторий для проверки состояния БД
        redis_client (RedisClient): Клиент Redis

    Methods:
        check: Проверяет состояние приложения и его зависимостей (БД, Redis)
        check_liveness: Быстрая проверка жизнеспособности без зависимостей
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует сервис проверки состояния.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных
        """
        super().__init__(session)
        self.repository = HealthRepository(session)
        self.redis_client = RedisClient()

    async def check(self) -> dict[str, str]:
        """
        Проверяет состояние приложения и его зависимостей.

        Returns:
            Dict[str, str]: Словарь со статусами сервисов (app, db, redis)

        Raises:
            ValueError: Если критичные сервисы недоступны
        """
        self.logger.info("Checking application health")

        db_ok = await self.repository.check_database_connection()
        redis_ok = await self._check_redis()

        self._validate_critical_services(db_ok, redis_ok)

        status = {
            "app": "ok",
            "db": "ok" if db_ok else "fail",
            "redis": "ok" if redis_ok else "fail",
        }

        self.logger.info("Health check completed: %s", status)

        return status

    async def check_liveness(self) -> dict[str, str]:
        """
        Быстрая проверка жизнеспособности без проверки зависимостей.

        Используется для liveness probe в Kubernetes/Docker.

        Returns:
            Dict[str, str]: Минимальный словарь со статусом (app, остальные=unknown)
        """
        self.logger.debug("Liveness check")

        return {
            "app": "ok",
            "db": "unknown",
            "redis": "unknown",
            "rabbitmq": "unknown",
            "s3": "unknown",
        }

    async def _check_redis(self) -> bool:
        """
        Проверяет доступность Redis.

        Returns:
            bool: True если Redis доступен, False иначе
        """
        try:
            return await self.redis_client.health_check()
        except Exception as e:
            self.logger.warning("Redis health check failed: %s", str(e))
            return False

    def _validate_critical_services(self, db_ok: bool, redis_ok: bool) -> None:
        """
        Проверяет доступность критичных сервисов.

        Args:
            db_ok (bool): Статус базы данных
            redis_ok (bool): Статус Redis

        Raises:
            ValueError: Если критичные сервисы недоступны
        """
        if not db_ok:
            self.logger.error("Критичная проверка сервиса не пройдена: база данных недоступна")
            raise ValueError("База данных недоступна")

        if not redis_ok:
            self.logger.error("Критичная проверка сервиса не пройдена: Redis недоступен")
            raise ValueError("Redis недоступен")
