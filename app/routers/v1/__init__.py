"""API v1 роутеры."""

from app.routers.base import BaseRouter
from app.routers.v1.auth import AdminAuthRouter
from app.routers.v1.user import UserRouter
from app.routers.v1.users.websocket import UsersWebSocketRouter
from app.routers.v1.checklist import (
    ChecklistCategoryRouter,
    ChecklistCategoryTaskRouter,
    ChecklistStatisticsRouter,
    ChecklistTaskRouter,
    ChecklistWebSocketRouter,
    DecisionFieldRouter,
    PartnershipDecisionsRouter,
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
        # Auth роутер для админов
        self.router.include_router(AdminAuthRouter().get_router())
        # User роутер
        self.router.include_router(UserRouter().get_router())
        # Users WebSocket роутер
        self.router.include_router(UsersWebSocketRouter().get_router())
        # Checklist роутеры
        self.router.include_router(ChecklistCategoryRouter().get_router())
        self.router.include_router(ChecklistTaskRouter().get_router())
        self.router.include_router(ChecklistCategoryTaskRouter().get_router())
        self.router.include_router(ChecklistStatisticsRouter().get_router())
        self.router.include_router(ChecklistWebSocketRouter().get_router())
        # Decision роутеры
        self.router.include_router(DecisionFieldRouter().get_router())
        self.router.include_router(PartnershipDecisionsRouter().get_router())


__all__ = ["APIv1"]
