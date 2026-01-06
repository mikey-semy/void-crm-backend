"""Зависимости для работы с системными настройками."""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies.database import AsyncSessionDep
from app.services.v1.system_settings import AISettingsService


async def get_ai_settings_service(session: AsyncSessionDep) -> AISettingsService:
    """
    Зависимость для получения сервиса AI настроек.

    Args:
        session: Асинхронная сессия базы данных

    Returns:
        AISettingsService: Экземпляр сервиса

    Usage:
        ```python
        @router.get("/admin/settings/ai")
        async def get_settings(service: AISettingsServiceDep):
            return await service.get_settings()
        ```
    """
    return AISettingsService(session)


# Типизированная зависимость
AISettingsServiceDep = Annotated[AISettingsService, Depends(get_ai_settings_service)]
