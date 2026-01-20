"""Схемы для системных настроек."""

from .base import (
    AISettingsSchema,
    ArticleIndexStatusSchema,
    IndexationStatsSchema,
    PromptListSchema,
    PromptSchema,
    PromptType,
    PromptUpdateSchema,
    SearchMode,
    SearchSettingsSchema,
    SearchSettingsUpdateSchema,
)
from .requests import AISettingsUpdateSchema, ReindexRequestSchema
from .responses import (
    AISettingsResponseSchema,
    EmbeddingModelsResponseSchema,
    IndexationStatsResponseSchema,
    LLMModelsResponseSchema,
    PromptListResponseSchema,
    PromptResponseSchema,
    ReindexResponseSchema,
    SearchSettingsResponseSchema,
)

__all__ = [
    # Base
    "AISettingsSchema",
    "ArticleIndexStatusSchema",
    "IndexationStatsSchema",
    # Prompts
    "PromptType",
    "PromptSchema",
    "PromptListSchema",
    "PromptUpdateSchema",
    # Search
    "SearchMode",
    "SearchSettingsSchema",
    "SearchSettingsUpdateSchema",
    # Requests
    "AISettingsUpdateSchema",
    "ReindexRequestSchema",
    # Responses
    "AISettingsResponseSchema",
    "EmbeddingModelsResponseSchema",
    "IndexationStatsResponseSchema",
    "LLMModelsResponseSchema",
    "PromptResponseSchema",
    "PromptListResponseSchema",
    "SearchSettingsResponseSchema",
    "ReindexResponseSchema",
]
