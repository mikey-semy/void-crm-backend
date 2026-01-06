"""
Настройки AI и RAG интеграции.

Модуль содержит конфигурацию для:
- OpenRouter API (LLM + эмбеддинги)
- RAG настройки по умолчанию
- Retry логика

Размерности моделей определяются динамически через API или
используется fallback из OpenRouterClient.KNOWN_EMBEDDING_DIMENSIONS.
"""

from pydantic_settings import BaseSettings


class AISettings(BaseSettings):
    """
    Настройки AI интеграции.

    Attributes:
        OPENROUTER_BASE_URL: Base URL OpenRouter API
        OPENROUTER_SITE_URL: URL сайта для HTTP-Referer
        OPENROUTER_APP_NAME: Название приложения для X-Title
        OPENROUTER_TIMEOUT: Таймаут запросов к API
        OPENROUTER_RETRY_ATTEMPTS: Количество попыток при rate limiting
        OPENROUTER_RETRY_DELAY: Базовая задержка между retry

        RAG_DEFAULT_PROVIDER: Провайдер эмбеддингов по умолчанию
        RAG_DEFAULT_MODEL: Модель эмбеддингов по умолчанию
        RAG_DEFAULT_DIMENSION: Размерность эмбеддингов по умолчанию (fallback)

        LLM_DEFAULT_MODEL: Модель для генерации текста по умолчанию

        SUPPORTED_PROVIDERS: Список поддерживаемых провайдеров

    Example:
        >>> from app.core.settings import settings
        >>> print(settings.ai.RAG_DEFAULT_MODEL)
        "openai/text-embedding-3-small"
    """

    # OpenRouter API
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_SITE_URL: str = "https://void-crm.ru"
    OPENROUTER_APP_NAME: str = "Void CRM"
    OPENROUTER_TIMEOUT: float = 30.0
    OPENROUTER_RETRY_ATTEMPTS: int = 3
    OPENROUTER_RETRY_DELAY: float = 1.0

    # RAG настройки по умолчанию (эмбеддинги)
    RAG_DEFAULT_PROVIDER: str = "openrouter"
    RAG_DEFAULT_MODEL: str = "openai/text-embedding-3-small"
    RAG_DEFAULT_DIMENSION: int = 1536  # Fallback если модель неизвестна

    # LLM настройки по умолчанию (генерация текста)
    LLM_DEFAULT_MODEL: str = "anthropic/claude-3-haiku"

    # Поддерживаемые провайдеры
    SUPPORTED_PROVIDERS: list[str] = [
        "openrouter",
        "openai",
        "anthropic",
    ]

    def get_embedding_dimension(self, model: str) -> int:
        """
        Получить размерность эмбеддинга для модели.

        Использует fallback словарь из OpenRouterClient если модель известна,
        иначе возвращает RAG_DEFAULT_DIMENSION.

        Args:
            model: Название модели.

        Returns:
            Размерность вектора эмбеддинга.
        """
        # Import здесь чтобы избежать circular import
        from app.core.integrations.ai import OpenRouterClient

        return OpenRouterClient.KNOWN_EMBEDDING_DIMENSIONS.get(
            model, self.RAG_DEFAULT_DIMENSION
        )

    class Config:
        env_prefix = "AI_"
        case_sensitive = True
        extra = "ignore"
