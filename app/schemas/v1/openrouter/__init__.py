"""
Pydantic схемы для OpenRouter API.

Экспортирует все схемы для работы с OpenRouter:
- Базовые схемы данных (модели, провайдеры, кредиты и т.д.)
- Схемы запросов
- Схемы ответов API
"""

from .base import (
    OpenRouterAnalyticsPointSchema,
    OpenRouterApiKeyCreateSchema,
    OpenRouterApiKeySchema,
    OpenRouterChatMessageSchema,
    OpenRouterChatResponseSchema,
    OpenRouterCreditsSchema,
    OpenRouterEmbeddingModelSchema,
    OpenRouterEndpointSchema,
    OpenRouterGenerationSchema,
    OpenRouterModelSchema,
    OpenRouterParameterSchema,
    OpenRouterProviderSchema,
)
from .requests import (
    AnalyticsRequestSchema,
    ApiKeyCreateRequestSchema,
    ApiKeyUpdateRequestSchema,
    ChatCompletionRequestSchema,
    ChatCompletionSimpleRequestSchema,
    EmbeddingBatchRequestSchema,
    EmbeddingRequestSchema,
    StructuredOutputRequestSchema,
)
from .responses import (
    AnalyticsResponseSchema,
    ApiKeyCreatedResponseSchema,
    ApiKeyDeletedResponseSchema,
    ApiKeyResponseSchema,
    ApiKeysResponseSchema,
    ChatResponseSchema,
    CreditsResponseSchema,
    EmbeddingBatchResponseSchema,
    EmbeddingResponseSchema,
    EmbeddingModelsResponseSchema,
    EndpointsResponseSchema,
    GenerationResponseSchema,
    ModelsCountResponseSchema,
    ModelsResponseSchema,
    ParametersResponseSchema,
    ProvidersResponseSchema,
    StructuredOutputResponseSchema,
)

__all__ = [
    # Base schemas
    "OpenRouterModelSchema",
    "OpenRouterEmbeddingModelSchema",
    "OpenRouterProviderSchema",
    "OpenRouterEndpointSchema",
    "OpenRouterParameterSchema",
    "OpenRouterCreditsSchema",
    "OpenRouterAnalyticsPointSchema",
    "OpenRouterGenerationSchema",
    "OpenRouterApiKeySchema",
    "OpenRouterApiKeyCreateSchema",
    "OpenRouterChatMessageSchema",
    "OpenRouterChatResponseSchema",
    # Request schemas
    "ChatCompletionRequestSchema",
    "ChatCompletionSimpleRequestSchema",
    "StructuredOutputRequestSchema",
    "EmbeddingRequestSchema",
    "EmbeddingBatchRequestSchema",
    "ApiKeyCreateRequestSchema",
    "ApiKeyUpdateRequestSchema",
    "AnalyticsRequestSchema",
    # Response schemas
    "ModelsResponseSchema",
    "EmbeddingModelsResponseSchema",
    "ModelsCountResponseSchema",
    "ProvidersResponseSchema",
    "EndpointsResponseSchema",
    "ParametersResponseSchema",
    "CreditsResponseSchema",
    "AnalyticsResponseSchema",
    "GenerationResponseSchema",
    "ApiKeysResponseSchema",
    "ApiKeyResponseSchema",
    "ApiKeyCreatedResponseSchema",
    "ApiKeyDeletedResponseSchema",
    "ChatResponseSchema",
    "StructuredOutputResponseSchema",
    "EmbeddingResponseSchema",
    "EmbeddingBatchResponseSchema",
]
