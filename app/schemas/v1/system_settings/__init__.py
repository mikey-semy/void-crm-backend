"""Схемы для системных настроек."""

from .base import AISettingsSchema
from .requests import AISettingsUpdateSchema
from .responses import (
    AISettingsResponseSchema,
    EmbeddingModelsResponseSchema,
    LLMModelsResponseSchema,
)

__all__ = [
    # Base
    "AISettingsSchema",
    # Requests
    "AISettingsUpdateSchema",
    # Responses
    "AISettingsResponseSchema",
    "EmbeddingModelsResponseSchema",
    "LLMModelsResponseSchema",
]
