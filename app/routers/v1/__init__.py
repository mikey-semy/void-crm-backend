"""API v1 роутеры."""

from app.routers.base import BaseRouter
from app.routers.v1.admin import (
    AdminAISettingsRouter,
    AdminOpenRouterChatRouter,
    AdminOpenRouterCreditsRouter,
    AdminOpenRouterEmbeddingsRouter,
    AdminOpenRouterGenerationsRouter,
    AdminOpenRouterKeysRouter,
    AdminOpenRouterModelsRouter,
    AdminOpenRouterProvidersRouter,
)
from app.routers.v1.auth import AdminAuthRouter
from app.routers.v1.checklist import (
    ChecklistCategoryRouter,
    ChecklistCategoryTaskRouter,
    ChecklistStatisticsRouter,
    ChecklistTaskRouter,
    ChecklistWebSocketRouter,
    DecisionFieldRouter,
    PartnershipDecisionsRouter,
)
from app.routers.v1.knowledge import (
    KnowledgeArticleProtectedRouter,
    KnowledgeArticleRouter,
    KnowledgeCategoryProtectedRouter,
    KnowledgeCategoryRouter,
    KnowledgeMCPRouter,
    KnowledgeSearchRouter,
    KnowledgeTagProtectedRouter,
    KnowledgeTagRouter,
)
from app.routers.v1.users import UserRouter, UserSettingsRouter, UsersWebSocketRouter


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
        # Knowledge Base роутеры
        # ВАЖНО: Protected роутер должен быть ПЕРЕД публичным,
        # иначе /{slug} перехватит /drafts
        self.router.include_router(KnowledgeArticleProtectedRouter().get_router())
        self.router.include_router(KnowledgeArticleRouter().get_router())
        self.router.include_router(KnowledgeCategoryRouter().get_router())
        self.router.include_router(KnowledgeCategoryProtectedRouter().get_router())
        self.router.include_router(KnowledgeTagRouter().get_router())
        self.router.include_router(KnowledgeTagProtectedRouter().get_router())
        self.router.include_router(KnowledgeSearchRouter().get_router())
        # Knowledge Base MCP (для Claude Code)
        self.router.include_router(KnowledgeMCPRouter().get_router())
        # User Settings роутер (API ключи пользователя)
        self.router.include_router(UserSettingsRouter().get_router())
        # Admin Settings роутеры (только для админов)
        self.router.include_router(AdminAISettingsRouter().get_router())
        # Admin OpenRouter роутеры (по категориям)
        self.router.include_router(AdminOpenRouterModelsRouter().get_router())
        self.router.include_router(AdminOpenRouterEmbeddingsRouter().get_router())
        self.router.include_router(AdminOpenRouterProvidersRouter().get_router())
        self.router.include_router(AdminOpenRouterCreditsRouter().get_router())
        self.router.include_router(AdminOpenRouterGenerationsRouter().get_router())
        self.router.include_router(AdminOpenRouterKeysRouter().get_router())
        self.router.include_router(AdminOpenRouterChatRouter().get_router())


__all__ = ["APIv1"]
