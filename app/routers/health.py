"""
Модуль для проверки состояния приложения.

Предоставляет эндпоинты для мониторинга здоровья приложения
и его зависимостей (база данных).
"""

from app.core.dependencies.health import HealthServiceDep
from app.routers.base import BaseRouter
from app.schemas import HealthCheckDataSchema, HealthCheckResponseSchema


class HealthRouter(BaseRouter):
    """
    Роутер для проверки состояния приложения.

    Предоставляет эндпоинты для мониторинга здоровья приложения
    и его зависимостей (база данных).

    Endpoints:
        GET /health - Полная проверка состояния всех сервисов
        GET /health/live - Быстрая проверка жизнеспособности приложения
    """

    def __init__(self):
        super().__init__(prefix="health", tags=["Health"])

    def configure(self):
        @self.router.get(
            path="",
            response_model=HealthCheckResponseSchema,
            description="""\
## 🩺 Проверка состояния приложения

Возвращает статусы доступности всех сервисов: приложение, база данных, Redis.

### Returns:
- **success** — успешность запроса
- **message** — сообщение о статусе
- **data** — словарь статусов сервисов (app, db, redis)
""",
        )
        async def health_check(
            health_service: HealthServiceDep,
        ) -> HealthCheckResponseSchema:
            """
            Проверяет состояние приложения и его зависимостей.

            Args:
                health_service: Автоматически внедренный сервис проверки здоровья

            Returns:
                HealthCheckResponseSchema: Результат проверки состояния приложения и его зависимостей
            """
            status = await health_service.check()
            data = HealthCheckDataSchema(**status)

            return HealthCheckResponseSchema(success=True, message="Все сервисы работают", data=data)

        @self.router.get(
            path="/live",
            response_model=HealthCheckResponseSchema,
            description="""\
## 💓 Быстрая проверка жизнеспособности

Минимальная проверка того, что приложение работает.
Не проверяет внешние зависимости — только само приложение.

### Returns:
- Статус жизнеспособности приложения без проверки БД
""",
        )
        async def liveness_check(
            health_service: HealthServiceDep,
        ) -> HealthCheckResponseSchema:
            """
            Быстрая проверка жизнеспособности приложения.

            Args:
                health_service: Автоматически внедренный сервис проверки здоровья

            Returns:
                HealthCheckResponseSchema: Результат проверки жизнеспособности
            """
            status = await health_service.check_liveness()
            data = HealthCheckDataSchema(**status)

            return HealthCheckResponseSchema(success=True, message="Приложение работает", data=data)
