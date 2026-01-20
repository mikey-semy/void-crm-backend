"""Схемы ответов для системных настроек."""

from app.schemas.base import BaseResponseSchema
from app.schemas.v1.openrouter import (
    OpenRouterEmbeddingModelSchema,
    OpenRouterModelSchema,
)

from .base import (
    AISettingsSchema,
    IndexationStatsSchema,
    PromptListSchema,
    PromptSchema,
    SearchSettingsSchema,
)


class AISettingsResponseSchema(BaseResponseSchema):
    """Ответ с AI настройками."""

    data: AISettingsSchema


class EmbeddingModelsResponseSchema(BaseResponseSchema):
    """Ответ со списком моделей эмбеддингов."""

    data: list[OpenRouterEmbeddingModelSchema]


class LLMModelsResponseSchema(BaseResponseSchema):
    """Ответ со списком LLM моделей."""

    data: list[OpenRouterModelSchema]


class ReindexResponseSchema(BaseResponseSchema):
    """Ответ на запрос переиндексации статей."""

    indexed_count: int
    total_published: int = 0
    cleared_count: int = 0


class IndexationStatsResponseSchema(BaseResponseSchema):
    """Ответ со статистикой индексации."""

    data: IndexationStatsSchema


class PromptResponseSchema(BaseResponseSchema):
    """Ответ с одним промптом."""

    data: PromptSchema


class PromptListResponseSchema(BaseResponseSchema):
    """Ответ со списком промптов."""

    data: PromptListSchema


class SearchSettingsResponseSchema(BaseResponseSchema):
    """Ответ с настройками поиска."""

    data: SearchSettingsSchema
