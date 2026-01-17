"""Схемы запросов для системных настроек."""

from pydantic import Field

from app.schemas.base import BaseRequestSchema


class AISettingsUpdateSchema(BaseRequestSchema):
    """Схема обновления AI настроек."""

    api_key: str | None = Field(
        None,
        min_length=10,
        description="API ключ OpenRouter (будет зашифрован)",
    )
    embedding_model: str | None = Field(
        None,
        description="Модель для эмбеддингов",
    )
    llm_model: str | None = Field(
        None,
        description="Основная LLM модель",
    )
    llm_fallback_model: str | None = Field(
        None,
        description="Запасная LLM модель",
    )


class ReindexRequestSchema(BaseRequestSchema):
    """Схема запроса переиндексации статей."""

    force: bool = Field(
        False,
        description="Принудительная переиндексация всех статей (сброс и создание заново)",
    )
