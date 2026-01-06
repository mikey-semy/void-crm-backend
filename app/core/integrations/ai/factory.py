"""
Фабрика для создания LLM клиентов.

Выбирает и создает клиент на основе провайдера.
"""

import logging

from app.core.exceptions import ExternalAPIError

from .base import BaseLLMClient
from .openrouter import OpenRouterClient

logger = logging.getLogger(__name__)


def get_llm_client(
    provider: str,
    api_key: str,
    api_url: str,
    **kwargs,
) -> BaseLLMClient:
    """
    Создает LLM клиент для указанного провайдера.

    Args:
        provider: Провайдер (openrouter/openai/anthropic)
        api_key: API ключ
        api_url: Base URL API
        **kwargs: Дополнительные параметры:
            - site_url: URL сайта для HTTP-Referer
            - app_name: Название приложения
            - timeout: Таймаут запроса
            - retry_attempts: Количество retry
            - default_model: Модель по умолчанию
            - default_embedding_model: Embedding модель по умолчанию

    Returns:
        Экземпляр BaseLLMClient для провайдера

    Raises:
        ExternalAPIError: При неизвестном провайдере

    Example:
        >>> from app.core.settings import settings
        >>>
        >>> client = get_llm_client(
        ...     provider="openrouter",
        ...     api_key="sk-or-...",
        ...     api_url="https://openrouter.ai/api/v1",
        ...     site_url="https://void-crm.ru",
        ...     app_name="Void CRM"
        ... )
        >>>
        >>> text = await client.complete(
        ...     prompt="Hello",
        ...     model="anthropic/claude-3-haiku"
        ... )
    """
    if provider == "openrouter":
        logger.info("Creating OpenRouter client")
        return OpenRouterClient(
            api_key=api_key,
            base_url=api_url,
            site_url=kwargs.get("site_url"),
            app_name=kwargs.get("app_name"),
            timeout=kwargs.get("timeout", 30.0),
            retry_attempts=kwargs.get("retry_attempts", 3),
            retry_delay_base=kwargs.get("retry_delay_base", 1.0),
            use_exponential_backoff=kwargs.get("use_exponential_backoff", True),
            default_model=kwargs.get("default_model"),
            default_embedding_model=kwargs.get("default_embedding_model"),
        )
    elif provider == "openai":
        # TODO: Реализовать OpenAIClient
        raise ExternalAPIError(
            detail="OpenAI provider not implemented yet",
            extra={"provider": provider},
        )
    elif provider == "anthropic":
        # TODO: Реализовать AnthropicClient
        raise ExternalAPIError(
            detail="Anthropic provider not implemented yet",
            extra={"provider": provider},
        )
    else:
        raise ExternalAPIError(
            detail=f"Unknown AI provider: {provider}",
            extra={"provider": provider},
        )
