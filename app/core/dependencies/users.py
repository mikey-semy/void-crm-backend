"""
Dependencies для работы с пользователями.

Модуль предоставляет dependency injection для UserService:
- UserService: управление профилями пользователей
"""

from typing import Annotated

from fastapi import Depends

from app.core.dependencies.database import AsyncSessionDep
from app.services.v1.users import UserService


def get_user_service(session: AsyncSessionDep) -> UserService:
    """
    Создает экземпляр UserService с внедренной сессией БД.

    Args:
        session: Асинхронная сессия SQLAlchemy

    Returns:
        UserService: Сервис для работы с профилями пользователей

    Example:
        >>> @router.get("/users/me")
        >>> async def get_profile(service: UserServiceDep, current_user: CurrentUserDep):
        ...     return await service.get_profile(current_user.id)
    """
    return UserService(session=session)


# Типизированная зависимость для использования в роутерах
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
