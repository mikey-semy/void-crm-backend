"""Базовые схемы системных настроек."""

from pydantic import Field

from app.schemas.base import BaseSchema, CommonBaseSchema


class AISettingsSchema(CommonBaseSchema):
    """
    AI настройки (OpenRouter).

    Включает API ключ, embedding модель, LLM модели, статус индексации.
    """

    # API Configuration
    api_key_hint: str | None = Field(
        None,
        description="Маска API ключа",
        examples=["sk-or...7x2f"],
    )
    has_api_key: bool = Field(
        False,
        description="Настроен ли API ключ",
    )

    # Embedding
    embedding_provider: str = Field(
        "openrouter",
        description="Провайдер для эмбеддингов",
        examples=["openrouter"],
    )
    embedding_model: str = Field(
        "",
        description="Модель эмбеддингов",
        examples=["openai/text-embedding-3-small"],
    )
    embedding_dimension: int = Field(
        1536,
        description="Размерность вектора эмбеддинга",
    )

    # LLM Models
    llm_model: str | None = Field(
        None,
        description="Основная LLM модель",
        examples=["anthropic/claude-3.5-sonnet"],
    )
    llm_fallback_model: str | None = Field(
        None,
        description="Запасная LLM модель",
        examples=["openai/gpt-4o"],
    )

    # Status
    indexed_articles_count: int = Field(
        0,
        description="Статей с эмбеддингами",
    )


class AISettingsUpdateSchema(CommonBaseSchema):
    """Схема обновления AI настроек."""

    api_key: str | None = Field(None, description="API ключ OpenRouter")
    embedding_model: str | None = Field(None, description="Модель эмбеддингов")
    llm_model: str | None = Field(None, description="Основная LLM")
    llm_fallback_model: str | None = Field(None, description="Запасная LLM")
