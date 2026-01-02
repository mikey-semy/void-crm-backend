"""
Зависимости для сервиса работы с токенами.

Провайдер для создания экземпляра TokenService с автоматическим
внедрением зависимостей через FastAPI Depends.

Providers:
    - get_token_service: Провайдер для TokenService

Typed Dependencies:
    - TokenServiceDep: Типизированная зависимость для TokenService

Usage:
    ```python
    from app.core.dependencies import TokenServiceDep

    async def some_handler(
        token_service: TokenServiceDep,
    ):
        access_token = await token_service.create_access_token(user_creds)
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends

from app.core.dependencies.cache import RedisDep
from app.services.v1.token import TokenService

logger = logging.getLogger(__name__)


async def get_token_service(
    redis: RedisDep,
) -> TokenService:
    """
    Провайдер для TokenService.

    Создает экземпляр TokenService с внедренными зависимостями:
    - Redis клиент (для сохранения и валидации токенов)

    Args:
        redis: Клиент Redis для работы с токенами.

    Returns:
        TokenService: Настроенный экземпляр сервиса токенов.

    Raises:
        ServiceUnavailableException: Если не удается создать сервис.

    Example:
        ```python
        # Автоматическое внедрение через FastAPI
        async def handler(token_service: TokenServiceDep):
            token = await token_service.create_access_token(user_creds)
        ```
    """
    try:
        logger.debug("Создание экземпляра TokenService")
        return TokenService(redis=redis)
    except Exception as e:
        logger.error("Ошибка при создании TokenService: %s", str(e), exc_info=True)
        raise


# Типизированная зависимость для удобства использования
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]
