"""Админские роутеры v1."""

from .openrouter import (
    AdminOpenRouterChatRouter,
    AdminOpenRouterCreditsRouter,
    AdminOpenRouterEmbeddingsRouter,
    AdminOpenRouterGenerationsRouter,
    AdminOpenRouterKeysRouter,
    AdminOpenRouterModelsRouter,
    AdminOpenRouterProvidersRouter,
)
from .settings import AdminAISettingsRouter

__all__ = [
    # AI Settings
    "AdminAISettingsRouter",
    # OpenRouter - по категориям
    "AdminOpenRouterModelsRouter",
    "AdminOpenRouterEmbeddingsRouter",
    "AdminOpenRouterProvidersRouter",
    "AdminOpenRouterCreditsRouter",
    "AdminOpenRouterGenerationsRouter",
    "AdminOpenRouterKeysRouter",
    "AdminOpenRouterChatRouter",
]
