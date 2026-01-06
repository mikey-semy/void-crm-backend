"""
AI интеграция - клиенты для LLM провайдеров.

Модуль экспортирует:
- BaseLLMClient - абстрактный базовый класс
- OpenRouterClient - клиент для OpenRouter (все API методы)
- get_llm_client - фабрика для создания клиентов

Pydantic схемы для OpenRouter находятся в app.schemas.v1.openrouter.
"""

from .base import BaseLLMClient
from .factory import get_llm_client
from .openrouter import OpenRouterClient

__all__ = [
    # Base
    "BaseLLMClient",
    # Factory
    "get_llm_client",
    # OpenRouter client
    "OpenRouterClient",
]
