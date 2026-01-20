"""Модели системных настроек."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..base import BaseModel


class SystemSettingsModel(BaseModel):
    """
    Модель для хранения системных настроек.

    Использует key-value подход для гибкого хранения настроек.
    Для каждой группы настроек (rag, general, security) создаётся отдельная запись.

    Attributes:
        key (str): Уникальный ключ настройки.
        value (str): Значение настройки (JSON для сложных объектов).
        description (str | None): Описание настройки.

    Example:
        >>> setting = SystemSettingsModel(
        ...     key="rag.embedding_provider",
        ...     value="openrouter",
        ...     description="Провайдер для эмбеддингов"
        ... )
    """

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Уникальный ключ настройки",
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="Значение настройки",
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Описание настройки",
    )


class SystemSettingsKeys:
    """Константы ключей системных настроек."""

    # RAG настройки
    RAG_EMBEDDING_PROVIDER = "rag.embedding_provider"
    RAG_EMBEDDING_MODEL = "rag.embedding_model"
    RAG_EMBEDDING_DIMENSION = "rag.embedding_dimension"
    RAG_PROVIDER_BASE_URL = "rag.provider_base_url"
    RAG_API_KEY = "rag.api_key"  # Зашифрованный ключ

    # AI настройки (LLM модели)
    AI_ENABLED = "ai.enabled"  # AI функции включены/выключены
    AI_LLM_MODEL = "ai.llm_model"  # Основная LLM модель
    AI_LLM_FALLBACK_MODEL = "ai.llm_fallback_model"  # Резервная LLM модель

    # AI промпты
    AI_PROMPT_KNOWLEDGE_CHAT = "ai.prompt.knowledge_chat"  # Чат по базе знаний
    AI_PROMPT_DESCRIPTION_GENERATOR = "ai.prompt.description_generator"  # Генерация описания
    AI_PROMPT_SEARCH_QUERY_EXTRACTOR = "ai.prompt.search_query_extractor"  # Извлечение поискового запроса

    # Глобальные настройки поиска
    SEARCH_DEFAULT_MODE = "search.default_mode"  # fulltext / semantic / hybrid
    SEARCH_SIMILARITY_THRESHOLD = "search.similarity_threshold"  # Порог схожести (0-1)
    SEARCH_FTS_WEIGHT = "search.fts_weight"  # Вес FTS в гибридном поиске
    SEARCH_SEMANTIC_WEIGHT = "search.semantic_weight"  # Вес семантики в гибридном поиске

    # Все ключи для удобства
    ALL_RAG_KEYS = [
        RAG_EMBEDDING_PROVIDER,
        RAG_EMBEDDING_MODEL,
        RAG_EMBEDDING_DIMENSION,
        RAG_PROVIDER_BASE_URL,
        RAG_API_KEY,
    ]

    ALL_AI_KEYS = [
        AI_ENABLED,
        AI_LLM_MODEL,
        AI_LLM_FALLBACK_MODEL,
    ]

    ALL_PROMPT_KEYS = [
        AI_PROMPT_KNOWLEDGE_CHAT,
        AI_PROMPT_DESCRIPTION_GENERATOR,
        AI_PROMPT_SEARCH_QUERY_EXTRACTOR,
    ]

    ALL_SEARCH_KEYS = [
        SEARCH_DEFAULT_MODE,
        SEARCH_SIMILARITY_THRESHOLD,
        SEARCH_FTS_WEIGHT,
        SEARCH_SEMANTIC_WEIGHT,
    ]
