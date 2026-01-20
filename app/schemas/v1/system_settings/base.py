"""Базовые схемы системных настроек."""

from enum import Enum

from pydantic import Field

from app.schemas.base import BaseSchema, CommonBaseSchema


class PromptType(str, Enum):
    """Типы AI промптов."""

    KNOWLEDGE_CHAT = "knowledge_chat"
    DESCRIPTION_GENERATOR = "description_generator"
    SEARCH_QUERY_EXTRACTOR = "search_query_extractor"


class SearchMode(str, Enum):
    """Режимы поиска."""

    FULLTEXT = "fulltext"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class AISettingsSchema(CommonBaseSchema):
    """
    AI настройки (OpenRouter).

    Включает API ключ, embedding модель, LLM модели, статус индексации.
    """

    # AI Enabled/Disabled
    ai_enabled: bool = Field(
        True,
        description="AI функции включены",
    )

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

    ai_enabled: bool | None = Field(None, description="AI функции включены")
    api_key: str | None = Field(None, description="API ключ OpenRouter")
    embedding_model: str | None = Field(None, description="Модель эмбеддингов")
    llm_model: str | None = Field(None, description="Основная LLM")
    llm_fallback_model: str | None = Field(None, description="Запасная LLM")


class ArticleIndexStatusSchema(CommonBaseSchema):
    """Статус индексации одной статьи."""

    id: str = Field(..., description="UUID статьи")
    title: str = Field(..., description="Заголовок статьи")
    slug: str = Field(..., description="Slug статьи")
    has_embedding: bool = Field(..., description="Есть эмбеддинг статьи")
    has_chunks: bool = Field(..., description="Есть чанки статьи")
    chunks_count: int = Field(0, description="Количество чанков")
    chunks_indexed: int = Field(0, description="Чанков с эмбеддингами")


class IndexationStatsSchema(CommonBaseSchema):
    """Статистика индексации для визуализации."""

    total_published: int = Field(0, description="Всего опубликованных статей")
    articles_indexed: int = Field(0, description="Статей с эмбеддингами")
    articles_not_indexed: int = Field(0, description="Статей без эмбеддингов")
    total_chunks: int = Field(0, description="Всего чанков")
    chunks_indexed: int = Field(0, description="Чанков с эмбеддингами")
    articles: list[ArticleIndexStatusSchema] = Field(
        default_factory=list,
        description="Детальный статус каждой статьи",
    )


# ==================== ПРОМПТЫ ====================


class PromptSchema(CommonBaseSchema):
    """Схема промпта."""

    type: PromptType = Field(..., description="Тип промпта")
    name: str = Field(..., description="Человекочитаемое название")
    description: str = Field(..., description="Описание назначения промпта")
    content: str = Field(..., description="Текст промпта")
    is_default: bool = Field(True, description="Используется дефолтный промпт")


class PromptListSchema(CommonBaseSchema):
    """Список всех промптов."""

    prompts: list[PromptSchema] = Field(
        default_factory=list,
        description="Список промптов",
    )


class PromptUpdateSchema(CommonBaseSchema):
    """Схема обновления промпта."""

    content: str = Field(..., min_length=10, description="Новый текст промпта")


# ==================== НАСТРОЙКИ ПОИСКА ====================


class SearchSettingsSchema(CommonBaseSchema):
    """Глобальные настройки поиска."""

    default_mode: SearchMode = Field(
        SearchMode.HYBRID,
        description="Режим поиска по умолчанию",
    )
    similarity_threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Минимальный порог схожести для семантического поиска",
    )
    fts_weight: float = Field(
        1.0,
        ge=0.0,
        le=2.0,
        description="Вес полнотекстового поиска в гибридном режиме",
    )
    semantic_weight: float = Field(
        1.0,
        ge=0.0,
        le=2.0,
        description="Вес семантического поиска в гибридном режиме",
    )


class SearchSettingsUpdateSchema(CommonBaseSchema):
    """Схема обновления настроек поиска."""

    default_mode: SearchMode | None = Field(None, description="Режим поиска")
    similarity_threshold: float | None = Field(
        None, ge=0.0, le=1.0, description="Порог схожести"
    )
    fts_weight: float | None = Field(None, ge=0.0, le=2.0, description="Вес FTS")
    semantic_weight: float | None = Field(
        None, ge=0.0, le=2.0, description="Вес семантики"
    )
