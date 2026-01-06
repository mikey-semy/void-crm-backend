"""Интеграции с внешними сервисами."""

from .ai import (
    BaseLLMClient,
    OpenRouterClient,
    get_llm_client,
)

__all__ = [
    # AI клиенты
    "BaseLLMClient",
    "OpenRouterClient",
    "get_llm_client",
]
