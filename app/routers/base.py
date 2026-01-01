"""Базовый класс для всех роутеров."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends


class BaseRouter:
    """
    Базовый класс для всех роутеров.

    Предоставляет общий функционал для создания маршрутов.

    Attributes:
        router (APIRouter): Базовый FastAPI роутер
        _dependencies (List[Depends]): Список глобальных зависимостей для роутера
    """

    def __init__(
        self,
        prefix: str = "",
        tags: Sequence[str] | None = None,
        dependencies: list[Depends] | None = None,
    ):
        """
        Инициализирует базовый роутер.

        Args:
            prefix: Префикс URL для всех маршрутов
            tags: Список тегов для документации Swagger
            dependencies: Список глобальных зависимостей
        """
        self._dependencies = dependencies or []
        self.router = APIRouter(
            prefix=f"/{prefix}" if prefix else "",
            tags=tags or [],
            dependencies=self._dependencies,
        )
        self.configure()

    def configure(self):
        """Переопределяется в дочерних классах для настройки роутов"""

    def get_router(self) -> APIRouter:
        """
        Возвращает настроенный FastAPI роутер.

        Returns:
            APIRouter: Настроенный FastAPI роутер
        """
        return self.router


class ProtectedRouter(BaseRouter):
    """
    Защищенный роутер с автоматической аутентификацией.

    Все эндпоинты в этом роутере автоматически защищены через CurrentUserDep.
    Пользователь доступен в каждом эндпоинте через параметр `current_user`.

    Attributes:
        router (APIRouter): FastAPI роутер с глобальной защитой через CurrentUserDep
    """

    def __init__(
        self,
        prefix: str = "",
        tags: Sequence[str] | None = None,
        additional_dependencies: list[Depends] | None = None,
    ):
        """
        Инициализирует защищенный роутер.

        Args:
            prefix: Префикс URL для всех маршрутов
            tags: Список тегов для документации Swagger
            additional_dependencies: Дополнительные зависимости (кроме аутентификации)
        """
        # TODO: Раскомментировать когда будет авторизация
        # from app.core.security import get_current_user
        # dependencies = [Depends(get_current_user)]
        dependencies = []
        if additional_dependencies:
            dependencies.extend(additional_dependencies)

        super().__init__(prefix=prefix, tags=tags, dependencies=dependencies)


class ApiKeyProtectedRouter(BaseRouter):
    """
    Защищенный роутер с поддержкой JWT токена ИЛИ API Key.

    Используется для endpoint'ов, к которым могут обращаться:
    - Пользователи через JWT токен
    - Внешние сервисы через API Key (X-API-Key header)
    """

    def __init__(
        self,
        prefix: str = "",
        tags: Sequence[str] | None = None,
        additional_dependencies: list[Depends] | None = None,
    ):
        """
        Инициализирует роутер с поддержкой API Key.

        Args:
            prefix: Префикс URL для всех маршрутов
            tags: Список тегов для документации Swagger
            additional_dependencies: Дополнительные зависимости
        """
        # TODO: Раскомментировать когда будет авторизация
        # from app.core.security import get_current_user_or_api_key
        # dependencies = [Depends(get_current_user_or_api_key)]
        dependencies = []
        if additional_dependencies:
            dependencies.extend(additional_dependencies)

        super().__init__(prefix=prefix, tags=tags, dependencies=dependencies)
