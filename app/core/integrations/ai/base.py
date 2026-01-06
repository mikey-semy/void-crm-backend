"""
Базовый класс для LLM клиентов.

Определяет интерфейс для всех AI провайдеров (OpenRouter, OpenAI, Anthropic).
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.schemas.v1.openrouter import (
    OpenRouterEmbeddingModelSchema,
    OpenRouterModelSchema,
)

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """
    Абстрактный базовый класс для LLM клиентов.

    Определяет общий интерфейс для работы с AI провайдерами.
    Все конкретные реализации (OpenRouter, OpenAI, Anthropic)
    должны наследоваться от этого класса.

    Attributes:
        api_key (str): API ключ провайдера
        base_url (str): Base URL API
        logger (logging.Logger): Логгер клиента

    Example:
        >>> class OpenRouterClient(BaseLLMClient):
        ...     async def complete(self, prompt: str, **kwargs) -> str:
        ...         # Реализация для OpenRouter
        ...         pass
    """

    def __init__(self, api_key: str, base_url: str):
        """
        Инициализирует LLM клиент.

        Args:
            api_key: API ключ провайдера
            base_url: Base URL API провайдера
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Генерирует текст по промпту.

        Args:
            prompt: Текст промпта
            model: ID модели (если None, используется default)
            temperature: Температура генерации (0.0-2.0)
            max_tokens: Максимальное количество токенов
            **kwargs: Дополнительные параметры провайдера

        Returns:
            Сгенерированный текст

        Raises:
            AIProviderError: При ошибке провайдера
            AITimeoutError: При таймауте запроса
        """
        pass

    @abstractmethod
    async def complete_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Генерирует структурированный JSON по промпту.

        Args:
            prompt: Текст промпта
            output_schema: JSON Schema для валидации выхода
            model: ID модели (если None, используется default)
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            **kwargs: Дополнительные параметры

        Returns:
            Распарсенный JSON dict

        Raises:
            AIProviderError: При ошибке провайдера
            AIValidationError: При невалидном JSON
        """
        pass

    @abstractmethod
    async def create_embedding(
        self,
        text: str,
        model: str | None = None,
    ) -> list[float]:
        """
        Создаёт эмбеддинг для текста.

        Args:
            text: Текст для эмбеддинга
            model: ID модели эмбеддингов

        Returns:
            Вектор эмбеддинга
        """
        pass

    @abstractmethod
    async def create_embeddings_batch(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> list[list[float]]:
        """
        Создаёт эмбеддинги для нескольких текстов.

        Args:
            texts: Список текстов
            model: ID модели эмбеддингов

        Returns:
            Список векторов эмбеддингов
        """
        pass

    @abstractmethod
    async def get_models(self) -> list[OpenRouterModelSchema]:
        """
        Получает список доступных LLM моделей.

        Returns:
            Список моделей с метаданными
        """
        pass

    @abstractmethod
    async def get_embedding_models(self) -> list[OpenRouterEmbeddingModelSchema]:
        """
        Получает список доступных моделей эмбеддингов.

        Returns:
            Список моделей эмбеддингов с метаданными
        """
        pass
