"""
Базовые Pydantic схемы для OpenRouter API.

Схемы данных для всех сущностей OpenRouter:
- Модели (LLM и Embedding)
- Провайдеры
- Endpoints и параметры моделей
- Кредиты и аналитика
- Генерации
- API ключи
- Чат
"""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import CommonBaseSchema


# ==================== МОДЕЛИ ====================


class OpenRouterModelSchema(CommonBaseSchema):
    """
    Информация о LLM модели OpenRouter.

    Attributes:
        id: Уникальный идентификатор модели (например "anthropic/claude-3-opus")
        name: Человекочитаемое название
        provider: Провайдер модели (например "anthropic")
        context_length: Максимальная длина контекста в токенах
        pricing_prompt: Цена за 1M токенов промпта (строка для точности)
        pricing_completion: Цена за 1M токенов ответа
        description: Описание модели
        input_modalities: Поддерживаемые типы входных данных (text, image)
        output_modalities: Поддерживаемые типы выходных данных (text, embeddings)
        supports_json_mode: Поддержка JSON mode / structured output
    """

    id: str = Field(..., description="ID модели (например anthropic/claude-3-opus)")
    name: str = Field(..., description="Название модели")
    provider: str = Field(default="openrouter", description="Провайдер")
    context_length: int = Field(default=0, description="Макс. контекст в токенах")
    pricing_prompt: str | None = Field(None, description="Цена за 1M токенов промпта")
    pricing_completion: str | None = Field(
        None, description="Цена за 1M токенов ответа"
    )
    description: str | None = Field(None, description="Описание модели")
    input_modalities: list[str] | None = Field(
        None, description="Типы входных данных"
    )
    output_modalities: list[str] | None = Field(
        None, description="Типы выходных данных"
    )
    supports_json_mode: bool = Field(
        default=False, description="Поддержка JSON mode"
    )


class OpenRouterEmbeddingModelSchema(CommonBaseSchema):
    """
    Информация о модели эмбеддингов OpenRouter.

    Attributes:
        id: Уникальный идентификатор модели
        name: Человекочитаемое название
        provider: Провайдер модели
        dimension: Размерность вектора эмбеддинга
        context_length: Максимальная длина входного текста в токенах
        pricing_prompt: Цена за 1M токенов
        description: Описание модели
    """

    id: str = Field(..., description="ID модели")
    name: str = Field(..., description="Название модели")
    provider: str = Field(default="openrouter", description="Провайдер")
    dimension: int = Field(..., description="Размерность вектора")
    context_length: int = Field(default=8192, description="Макс. контекст в токенах")
    pricing_prompt: str | None = Field(None, description="Цена за 1M токенов")
    description: str | None = Field(None, description="Описание модели")


# ==================== ПРОВАЙДЕРЫ ====================


class OpenRouterProviderSchema(CommonBaseSchema):
    """
    Информация о провайдере моделей.

    Attributes:
        id: Уникальный идентификатор провайдера
        name: Название провайдера
        website: URL сайта провайдера
        priority: Приоритет (для сортировки)
    """

    id: str = Field(..., description="ID провайдера")
    name: str = Field(..., description="Название провайдера")
    website: str | None = Field(None, description="URL сайта")
    priority: int = Field(default=0, description="Приоритет")


# ==================== ENDPOINTS ====================


class OpenRouterEndpointSchema(CommonBaseSchema):
    """
    Информация об endpoint модели (конкретный провайдер/инстанс).

    Attributes:
        provider: Название провайдера
        model: ID модели
        quantization: Тип квантизации (если применимо)
        latency: Средняя латентность в мс
        throughput: Пропускная способность
    """

    provider: str = Field(..., description="Провайдер")
    model: str = Field(..., description="ID модели")
    quantization: str | None = Field(None, description="Квантизация")
    latency: float | None = Field(None, description="Латентность (мс)")
    throughput: float | None = Field(None, description="Пропускная способность")


# ==================== ПАРАМЕТРЫ ====================


class OpenRouterParameterSchema(CommonBaseSchema):
    """
    Информация о параметре модели.

    Attributes:
        name: Название параметра (temperature, max_tokens, etc.)
        type: Тип данных (number, integer, string, boolean)
        default: Значение по умолчанию
        min_value: Минимальное значение
        max_value: Максимальное значение
        description: Описание параметра
        popularity: Популярность использования (0-1)
    """

    name: str = Field(..., description="Название параметра")
    type: str = Field(..., description="Тип данных")
    default: Any | None = Field(None, description="Значение по умолчанию")
    min_value: Any | None = Field(None, description="Минимальное значение")
    max_value: Any | None = Field(None, description="Максимальное значение")
    description: str | None = Field(None, description="Описание")
    popularity: float | None = Field(None, description="Популярность (0-1)")


# ==================== КРЕДИТЫ ====================


class OpenRouterCreditsSchema(CommonBaseSchema):
    """
    Информация о балансе кредитов OpenRouter.

    Attributes:
        total_credits: Общая сумма пополнений
        usage_credits: Использовано кредитов
        remaining_credits: Остаток на балансе
        currency: Валюта (USD)
    """

    total_credits: float = Field(default=0.0, description="Всего пополнено")
    usage_credits: float = Field(default=0.0, description="Использовано")
    remaining_credits: float = Field(default=0.0, description="Остаток")
    currency: str = Field(default="USD", description="Валюта")


# ==================== АНАЛИТИКА ====================


class OpenRouterAnalyticsPointSchema(CommonBaseSchema):
    """
    Точка данных аналитики использования API.

    Attributes:
        endpoint: Endpoint API (chat/completions, embeddings, etc.)
        requests: Количество запросов
        tokens_prompt: Токенов промптов
        tokens_completion: Токенов ответов
        cost: Стоимость в USD
        period: Период (ISO дата или интервал)
    """

    endpoint: str = Field(..., description="Endpoint")
    requests: int = Field(default=0, description="Количество запросов")
    tokens_prompt: int = Field(default=0, description="Токенов промптов")
    tokens_completion: int = Field(default=0, description="Токенов ответов")
    cost: float = Field(default=0.0, description="Стоимость (USD)")
    period: str = Field(..., description="Период")


# ==================== ГЕНЕРАЦИИ ====================


class OpenRouterGenerationSchema(CommonBaseSchema):
    """
    Информация о генерации (отдельном запросе к модели).

    Attributes:
        id: ID генерации
        model: ID использованной модели
        created_at: Время создания
        total_cost: Общая стоимость запроса
        tokens_prompt: Токенов в промпте
        tokens_completion: Токенов в ответе
        native_tokens_prompt: Нативных токенов промпта (для моделей с разной токенизацией)
        native_tokens_completion: Нативных токенов ответа
        latency_ms: Общая латентность
        generation_time_ms: Время генерации
        status: Статус (success, error)
        origin: Источник запроса
        provider_name: Провайдер который обработал запрос
        prompt: Текст промпта (если сохранён)
        completion: Текст ответа (если сохранён)
    """

    id: str = Field(..., description="ID генерации")
    model: str = Field(..., description="ID модели")
    created_at: datetime | None = Field(None, description="Время создания")
    total_cost: float = Field(default=0.0, description="Стоимость")
    tokens_prompt: int = Field(default=0, description="Токенов промпта")
    tokens_completion: int = Field(default=0, description="Токенов ответа")
    native_tokens_prompt: int | None = Field(
        None, description="Нативных токенов промпта"
    )
    native_tokens_completion: int | None = Field(
        None, description="Нативных токенов ответа"
    )
    latency_ms: int | None = Field(None, description="Латентность (мс)")
    generation_time_ms: int | None = Field(None, description="Время генерации (мс)")
    status: str | None = Field(None, description="Статус")
    origin: str | None = Field(None, description="Источник")
    provider_name: str | None = Field(None, description="Провайдер")
    prompt: str | None = Field(None, description="Текст промпта")
    completion: str | None = Field(None, description="Текст ответа")


# ==================== API КЛЮЧИ ====================


class OpenRouterApiKeySchema(CommonBaseSchema):
    """
    Информация об API ключе OpenRouter.

    Attributes:
        id: ID ключа
        name: Название ключа
        key_prefix: Префикс ключа (для идентификации)
        created_at: Дата создания
        last_used_at: Последнее использование
        is_active: Активен ли ключ
        limit_per_minute: Лимит запросов в минуту
    """

    id: str = Field(..., description="ID ключа")
    name: str = Field(..., description="Название")
    key_prefix: str = Field(..., description="Префикс ключа")
    created_at: datetime | None = Field(None, description="Создан")
    last_used_at: datetime | None = Field(None, description="Последнее использование")
    is_active: bool = Field(default=True, description="Активен")
    limit_per_minute: int | None = Field(None, description="Лимит запросов/мин")


class OpenRouterApiKeyCreateSchema(CommonBaseSchema):
    """
    Созданный API ключ (включает сам ключ - показывается только 1 раз).

    Attributes:
        id: ID ключа
        name: Название ключа
        key: Сам ключ (показывается только при создании!)
        key_prefix: Префикс ключа
    """

    id: str = Field(..., description="ID ключа")
    name: str = Field(..., description="Название")
    key: str = Field(..., description="Ключ (показывается только 1 раз!)")
    key_prefix: str = Field(..., description="Префикс ключа")


# ==================== ЧАТ ====================


class OpenRouterChatMessageSchema(CommonBaseSchema):
    """
    Сообщение в чате.

    Attributes:
        role: Роль отправителя (system, user, assistant)
        content: Содержимое сообщения
    """

    role: str = Field(..., description="Роль (system, user, assistant)")
    content: str = Field(..., description="Содержимое")


class OpenRouterChatResponseSchema(CommonBaseSchema):
    """
    Ответ от модели в чате.

    Attributes:
        id: ID генерации
        model: ID модели
        content: Текст ответа
        tokens_prompt: Токенов в промпте
        tokens_completion: Токенов в ответе
        finish_reason: Причина завершения (stop, length, etc.)
    """

    id: str = Field(..., description="ID генерации")
    model: str = Field(..., description="ID модели")
    content: str = Field(..., description="Текст ответа")
    tokens_prompt: int = Field(default=0, description="Токенов промпта")
    tokens_completion: int = Field(default=0, description="Токенов ответа")
    finish_reason: str | None = Field(None, description="Причина завершения")
