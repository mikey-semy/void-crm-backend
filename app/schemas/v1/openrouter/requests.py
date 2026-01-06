"""
Схемы запросов для OpenRouter API.

Схемы для входных данных endpoints OpenRouter.
"""

from pydantic import Field

from app.schemas.base import BaseRequestSchema

from .base import OpenRouterChatMessageSchema


# ==================== ЧАТ ====================


class ChatCompletionRequestSchema(BaseRequestSchema):
    """
    Запрос на генерацию текста через чат.

    Attributes:
        messages: Список сообщений чата
        model: ID модели (опционально, если есть дефолтная)
        temperature: Температура генерации (0-2)
        max_tokens: Максимум токенов в ответе
        system_prompt: Системный промпт (альтернатива system message)
    """

    messages: list[OpenRouterChatMessageSchema] = Field(
        ..., description="Сообщения чата"
    )
    model: str | None = Field(None, description="ID модели")
    temperature: float | None = Field(
        None, ge=0.0, le=2.0, description="Температура (0-2)"
    )
    max_tokens: int | None = Field(None, gt=0, description="Макс. токенов")
    system_prompt: str | None = Field(None, description="Системный промпт")


class ChatCompletionSimpleRequestSchema(BaseRequestSchema):
    """
    Простой запрос на генерацию текста (один промпт).

    Attributes:
        prompt: Текст промпта
        model: ID модели (опционально)
        temperature: Температура генерации
        max_tokens: Максимум токенов в ответе
        system_prompt: Системный промпт
    """

    prompt: str = Field(..., min_length=1, description="Текст промпта")
    model: str | None = Field(None, description="ID модели")
    temperature: float | None = Field(
        None, ge=0.0, le=2.0, description="Температура (0-2)"
    )
    max_tokens: int | None = Field(None, gt=0, description="Макс. токенов")
    system_prompt: str | None = Field(None, description="Системный промпт")


class StructuredOutputRequestSchema(BaseRequestSchema):
    """
    Запрос на структурированный вывод (JSON).

    Attributes:
        prompt: Текст промпта
        output_schema: JSON Schema для валидации ответа
        model: ID модели
        temperature: Температура генерации
        max_tokens: Максимум токенов
    """

    prompt: str = Field(..., min_length=1, description="Текст промпта")
    output_schema: dict = Field(..., description="JSON Schema для ответа")
    model: str | None = Field(None, description="ID модели")
    temperature: float | None = Field(
        None, ge=0.0, le=2.0, description="Температура (0-2)"
    )
    max_tokens: int | None = Field(None, gt=0, description="Макс. токенов")


# ==================== ЭМБЕДДИНГИ ====================


class EmbeddingRequestSchema(BaseRequestSchema):
    """
    Запрос на создание эмбеддинга.

    Attributes:
        text: Текст для эмбеддинга
        model: ID модели эмбеддингов
    """

    text: str = Field(..., min_length=1, description="Текст для эмбеддинга")
    model: str | None = Field(None, description="ID модели")


class EmbeddingBatchRequestSchema(BaseRequestSchema):
    """
    Запрос на создание эмбеддингов для нескольких текстов.

    Attributes:
        texts: Список текстов
        model: ID модели эмбеддингов
    """

    texts: list[str] = Field(..., min_length=1, description="Список текстов")
    model: str | None = Field(None, description="ID модели")


# ==================== API КЛЮЧИ ====================


class ApiKeyCreateRequestSchema(BaseRequestSchema):
    """
    Запрос на создание API ключа OpenRouter.

    Attributes:
        name: Название ключа
        limit_per_minute: Лимит запросов в минуту (опционально)
    """

    name: str = Field(..., min_length=1, max_length=100, description="Название ключа")
    limit_per_minute: int | None = Field(
        None, gt=0, description="Лимит запросов/мин"
    )


class ApiKeyUpdateRequestSchema(BaseRequestSchema):
    """
    Запрос на обновление API ключа OpenRouter.

    Attributes:
        name: Новое название ключа
        is_active: Статус активности
        limit_per_minute: Новый лимит запросов в минуту
    """

    name: str | None = Field(None, min_length=1, max_length=100, description="Название")
    is_active: bool | None = Field(None, description="Активен")
    limit_per_minute: int | None = Field(None, description="Лимит запросов/мин")


# ==================== АНАЛИТИКА ====================


class AnalyticsRequestSchema(BaseRequestSchema):
    """
    Параметры запроса аналитики.

    Attributes:
        period: Период группировки (hour, day, week, month)
        limit: Максимум записей
    """

    period: str = Field(
        default="day",
        pattern="^(hour|day|week|month)$",
        description="Период (hour, day, week, month)",
    )
    limit: int = Field(default=100, ge=1, le=1000, description="Макс. записей")
