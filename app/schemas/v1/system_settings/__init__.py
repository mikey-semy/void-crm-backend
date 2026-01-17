"""Схемы для системных настроек."""

from .base import AISettingsSchema, ArticleIndexStatusSchema, IndexationStatsSchema
from .requests import AISettingsUpdateSchema, ReindexRequestSchema
from .responses import (
    AISettingsResponseSchema,
    EmbeddingModelsResponseSchema,
    IndexationStatsResponseSchema,
    LLMModelsResponseSchema,
    ReindexResponseSchema,
)

__all__ = [
    # Base
    "AISettingsSchema",
    "ArticleIndexStatusSchema",
    "IndexationStatsSchema",
    # Requests
    "AISettingsUpdateSchema",
    "ReindexRequestSchema",
    # Responses
    "AISettingsResponseSchema",
    "EmbeddingModelsResponseSchema",
    "IndexationStatsResponseSchema",
    "LLMModelsResponseSchema",
    "ReindexResponseSchema",
]
