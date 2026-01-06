"""Зависимости для работы с настройками пользователя."""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies.database import AsyncSessionDep
from app.services.v1.user_settings import UserAccessTokenService


async def get_user_access_token_service(
    session: AsyncSessionDep,
) -> UserAccessTokenService:
    """
    Зависимость для получения сервиса токенов доступа.

    Args:
        session: Асинхронная сессия базы данных

    Returns:
        UserAccessTokenService: Экземпляр сервиса токенов

    Usage:
        ```python
        @router.post("/access-tokens")
        async def create_token(service: UserAccessTokenServiceDep):
            return await service.create_token(...)
        ```
    """
    return UserAccessTokenService(session)


# Типизированная зависимость
UserAccessTokenServiceDep = Annotated[
    UserAccessTokenService,
    Depends(get_user_access_token_service),
]
