"""API v1 роутеры."""

from app.routers.base import BaseRouter
from app.routers.v1.checklist import (
    ChecklistCategoryRouter,
    ChecklistCategoryTaskRouter,
    ChecklistStatisticsRouter,
    ChecklistTaskRouter,
    ChecklistWebSocketRouter,
)


class APIv1(BaseRouter):
    """
    Агрегатор роутеров для API v1.

    Объединяет все публичные роутеры v1.
    """

    def configure_routes(self):
        """
        Настройка маршрутов для API v1.
        """
        # Checklist роутеры
        self.router.include_router(ChecklistCategoryRouter().get_router())
        self.router.include_router(ChecklistTaskRouter().get_router())
        self.router.include_router(ChecklistCategoryTaskRouter().get_router())
        self.router.include_router(ChecklistStatisticsRouter().get_router())
        self.router.include_router(ChecklistWebSocketRouter().get_router())


__all__ = ["APIv1"]
