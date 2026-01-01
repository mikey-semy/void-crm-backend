"""
Зависимости для сервисов приложения.

Этот модуль содержит провайдеры (фабрики) для создания экземпляров всех сервисов
с автоматическим внедрением их зависимостей через FastAPI Depends.

Providers:
    - get_health_service: Провайдер для HealthService


Typed Dependencies:
    - HealthServiceDep: Типизированная зависимость для HealthService

Usage:
    ```python
    from src.core.dependencies.services import WebhookServiceDep

    @router.post("/webhook")
    async def webhook(service: WebhookServiceDep):
        return await service.process_update(data)
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends

from app.core.dependencies.database import AsyncSessionDep
from app.services.health import HealthService

logger = logging.getLogger("src.dependencies.services")


# Health Service Provider
def get_health_service(session: AsyncSessionDep) -> HealthService:
    """
    Провайдер для HealthService.

    Создает экземпляр HealthService с автоматически внедренными
    зависимостями базы данных.

    Args:
        session: Асинхронная сессия базы данных

    Returns:
        HealthService: Настроенный сервис проверки здоровья

    Usage:
        ```python
        @router.get("/health")
        async def health_check(service: HealthServiceDep):
            return await service.check()
        ```
    """
    logger.debug("Создание экземпляра HealthService")
    return HealthService(session=session)


# Типизированные зависимости для удобства использования
HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]
