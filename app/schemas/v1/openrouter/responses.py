"""
Схемы ответов API для OpenRouter.

Все ответы соответствуют стандарту проекта: {success, message, data}.
"""

from pydantic import Field

from app.schemas.base import BaseResponseSchema

from .base import (
    OpenRouterAnalyticsPointSchema,
    OpenRouterApiKeyCreateSchema,
    OpenRouterApiKeySchema,
    OpenRouterChatResponseSchema,
    OpenRouterCreditsSchema,
    OpenRouterEmbeddingModelSchema,
    OpenRouterEndpointSchema,
    OpenRouterGenerationSchema,
    OpenRouterModelSchema,
    OpenRouterParameterSchema,
    OpenRouterProviderSchema,
)


# ==================== МОДЕЛИ ====================


class ModelsResponseSchema(BaseResponseSchema):
    """Ответ со списком LLM моделей."""

    data: list[OpenRouterModelSchema] = Field(description="Список моделей")


class EmbeddingModelsResponseSchema(BaseResponseSchema):
    """Ответ со списком моделей эмбеддингов."""

    data: list[OpenRouterEmbeddingModelSchema] = Field(
        description="Список моделей эмбеддингов"
    )


class ModelsCountResponseSchema(BaseResponseSchema):
    """Ответ с количеством моделей."""

    data: int = Field(description="Количество моделей")


# ==================== ПРОВАЙДЕРЫ ====================


class ProvidersResponseSchema(BaseResponseSchema):
    """Ответ со списком провайдеров."""

    data: list[OpenRouterProviderSchema] = Field(description="Список провайдеров")


# ==================== ENDPOINTS ====================


class EndpointsResponseSchema(BaseResponseSchema):
    """Ответ со списком endpoints модели."""

    data: list[OpenRouterEndpointSchema] = Field(description="Список endpoints")


# ==================== ПАРАМЕТРЫ ====================


class ParametersResponseSchema(BaseResponseSchema):
    """Ответ со списком параметров модели."""

    data: list[OpenRouterParameterSchema] = Field(description="Список параметров")


# ==================== КРЕДИТЫ ====================


class CreditsResponseSchema(BaseResponseSchema):
    """Ответ с информацией о балансе кредитов."""

    data: OpenRouterCreditsSchema = Field(description="Баланс кредитов")


# ==================== АНАЛИТИКА ====================


class AnalyticsResponseSchema(BaseResponseSchema):
    """Ответ с аналитикой использования."""

    data: list[OpenRouterAnalyticsPointSchema] = Field(
        description="Данные аналитики"
    )


# ==================== ГЕНЕРАЦИИ ====================


class GenerationResponseSchema(BaseResponseSchema):
    """Ответ с информацией о генерации."""

    data: OpenRouterGenerationSchema = Field(description="Информация о генерации")


# ==================== API КЛЮЧИ ====================


class ApiKeysResponseSchema(BaseResponseSchema):
    """Ответ со списком API ключей."""

    data: list[OpenRouterApiKeySchema] = Field(description="Список ключей")


class ApiKeyResponseSchema(BaseResponseSchema):
    """Ответ с информацией об одном API ключе."""

    data: OpenRouterApiKeySchema = Field(description="Информация о ключе")


class ApiKeyCreatedResponseSchema(BaseResponseSchema):
    """Ответ с созданным API ключом (включает сам ключ)."""

    data: OpenRouterApiKeyCreateSchema = Field(
        description="Созданный ключ (показывается только 1 раз!)"
    )


class ApiKeyDeletedResponseSchema(BaseResponseSchema):
    """Ответ об удалении API ключа."""

    message: str = Field(default="API ключ успешно удалён", description="Сообщение")


# ==================== ЧАТ ====================


class ChatResponseSchema(BaseResponseSchema):
    """Ответ от AI модели в чате."""

    data: OpenRouterChatResponseSchema = Field(description="Ответ модели")


class StructuredOutputResponseSchema(BaseResponseSchema):
    """Ответ со структурированными данными (JSON)."""

    data: dict = Field(description="Структурированный ответ")


# ==================== ЭМБЕДДИНГИ ====================


class EmbeddingResponseSchema(BaseResponseSchema):
    """Ответ с эмбеддингом."""

    data: dict = Field(description="Данные эмбеддинга (embedding, dimension, model)")


class EmbeddingBatchResponseSchema(BaseResponseSchema):
    """Ответ с эмбеддингами для нескольких текстов."""

    data: dict = Field(description="Данные эмбеддингов (embeddings, count, dimension, model)")
