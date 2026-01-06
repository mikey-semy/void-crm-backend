"""
Admin OpenRouter роутеры.

Структура соответствует OpenRouter API Reference:
https://openrouter.ai/docs/api/api-reference

Роутеры:
- models: Модели, endpoints, параметры
- embeddings: Embedding модели
- providers: Провайдеры
- credits: Баланс и аналитика
- generations: Информация о генерациях
- keys: Управление API ключами
- chat: Чат completions (для тестирования)
"""

from .chat import AdminOpenRouterChatRouter
from .credits import AdminOpenRouterCreditsRouter
from .embeddings import AdminOpenRouterEmbeddingsRouter
from .generations import AdminOpenRouterGenerationsRouter
from .keys import AdminOpenRouterKeysRouter
from .models import AdminOpenRouterModelsRouter
from .providers import AdminOpenRouterProvidersRouter

__all__ = [
    "AdminOpenRouterModelsRouter",
    "AdminOpenRouterEmbeddingsRouter",
    "AdminOpenRouterProvidersRouter",
    "AdminOpenRouterCreditsRouter",
    "AdminOpenRouterGenerationsRouter",
    "AdminOpenRouterKeysRouter",
    "AdminOpenRouterChatRouter",
]
