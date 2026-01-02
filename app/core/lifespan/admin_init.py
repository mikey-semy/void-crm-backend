"""
Обработчик инициализации дефолтного администратора.

Автоматически создаёт дефолтного администратора из ENV переменных
при первом запуске приложения.
"""

from fastapi import FastAPI

from app.core.dependencies.database import get_async_session
from app.core.lifespan.base import register_startup_handler
from app.services.v1.admin_init import AdminInitService


@register_startup_handler
async def initialize_default_admin(app: FastAPI) -> None:
    """
    Создаёт дефолтного администратора из настроек при старте приложения.

    Вызывается автоматически через lifespan manager.
    Если админ уже существует - пропускается.

    Args:
        app: Экземпляр FastAPI приложения.
    """
    # Получаем сессию из dependency
    session_generator = get_async_session()
    session = await anext(session_generator)

    try:
        # Создаём сервис инициализации
        admin_init_service = AdminInitService(session=session)

        # Пытаемся создать дефолтного админа
        await admin_init_service.create_default_admin_if_not_exists()

    finally:
        # Закрываем сессию
        await session.close()
