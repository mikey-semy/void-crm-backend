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
    AI_LLM_MODEL = "ai.llm_model"  # Основная LLM модель
    AI_LLM_FALLBACK_MODEL = "ai.llm_fallback_model"  # Резервная LLM модель

    # Все ключи для удобства
    ALL_RAG_KEYS = [
        RAG_EMBEDDING_PROVIDER,
        RAG_EMBEDDING_MODEL,
        RAG_EMBEDDING_DIMENSION,
        RAG_PROVIDER_BASE_URL,
        RAG_API_KEY,
    ]

    ALL_AI_KEYS = [
        AI_LLM_MODEL,
        AI_LLM_FALLBACK_MODEL,
    ]
