"""
Зависимости для сервиса аутентификации.

Этот модуль содержит провайдер (фабрику) для создания экземпляра сервиса
аутентификации с автоматическим внедрением зависимостей через FastAPI Depends.

Providers:
    - get_auth_service: Провайдер для AuthService

Typed Dependencies:
    - AuthServiceDep: Типизированная зависимость для AuthService

Usage:
    ```python
    from app.core.dependencies import AuthServiceDep

    @router.post("/auth/login")
    async def login(
        auth_service: AuthServiceDep,
        form_data: OAuth2PasswordRequestForm = Depends(),
    ) -> TokenResponseSchema:
        return await auth_service.authenticate(form_data)
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends

from app.core.dependencies.database import AsyncSessionDep
from app.core.dependencies.token import TokenServiceDep
from app.services.v1.auth import AuthService

logger = logging.getLogger(__name__)


async def get_auth_service(
    session: AsyncSessionDep,
    token_service: TokenServiceDep,
) -> AuthService:
    """
    Провайдер для AuthService.

    Создает экземпляр AuthService с внедренными зависимостями:
    - Сессия базы данных (для работы с UserModel)
    - TokenService (для работы с токенами)

    Args:
        session: Асинхронная сессия базы данных.
        token_service: Сервис для работы с токенами.

    Returns:
        AuthService: Настроенный экземпляр сервиса аутентификации.

    Raises:
        ServiceUnavailableException: Если не удается создать сервис.

    Example:
        ```python
        # Автоматическое внедрение через FastAPI
        @router.post("/auth/login")
        async def login(
            auth_service: AuthServiceDep,
            form_data: OAuth2PasswordRequestForm = Depends(),
        ):
            return await auth_service.authenticate(form_data)
        ```
    """
    try:
        logger.debug("Создание экземпляра AuthService")
        return AuthService(session=session, token_service=token_service)
    except Exception as e:
        logger.error("Ошибка при создании AuthService: %s", str(e), exc_info=True)
        raise


# Типизированная зависимость для удобства использования
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
