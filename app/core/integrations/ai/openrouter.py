"""
Клиент для OpenRouter API.

Реализация BaseLLMClient для работы с OpenRouter.
Поддерживает все API методы OpenRouter:
- Chat/Completions (text generation)
- Embeddings (vector generation)
- Models (list models, count, parameters)
- Providers (list all providers)
- Analytics (user activity)
- Credits (balance info)
- API Keys (manage keys)
- Generations (request metadata)
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

import httpx

from app.core.exceptions import ExternalAPIError
from app.schemas.v1.openrouter import (
    OpenRouterAnalyticsPointSchema,
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

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


# ==================== IN-MEMORY CACHE ====================

class OpenRouterCache:
    """
    Простой in-memory кэш для OpenRouter API.

    Кэширует:
    - LLM models (5 минут)
    - Embedding models (5 минут)
    - Providers (10 минут)
    - Credits (1 минута)
    """

    _instance: "OpenRouterCache | None" = None

    def __new__(cls) -> "OpenRouterCache":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_cache()
        return cls._instance

    def _init_cache(self) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl: dict[str, int] = {
            "llm_models": 300,      # 5 минут
            "embedding_models": 300, # 5 минут
            "providers": 600,        # 10 минут
            "credits": 60,           # 1 минута
        }

    def get(self, key: str) -> Any | None:
        """Получить значение из кэша если не истёк TTL."""
        if key not in self._cache:
            return None
        value, timestamp = self._cache[key]
        ttl = self._ttl.get(key, 60)
        if time.time() - timestamp > ttl:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Сохранить значение в кэш."""
        self._cache[key] = (value, time.time())

    def invalidate(self, key: str | None = None) -> None:
        """Инвалидировать кэш (один ключ или весь)."""
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]


# Global cache instance
_cache = OpenRouterCache()


class OpenRouterClient(BaseLLMClient):
    """
    Клиент для OpenRouter API с retry логикой.

    Использует httpx для асинхронных запросов к OpenRouter.
    Поддерживает exponential backoff и retry для rate limiting.

    Attributes:
        api_key: API ключ OpenRouter
        base_url: Base URL (https://openrouter.ai/api/v1)
        site_url: URL сайта для HTTP-Referer
        app_name: Название приложения для X-Title
        timeout: Таймаут запроса в секундах (default: 30)
        retry_attempts: Количество повторных попыток (default: 3)
        retry_delay_base: Базовая задержка между попытками (default: 1.0s)
        use_exponential_backoff: Использовать exponential backoff (default: True)

    Retry Strategy:
        - Ретраит: timeout, 429 (rate limit), 503 (service unavailable)
        - НЕ ретраит: 400, 401, 404 и другие client errors
        - Exponential backoff: delay = base_delay * (2 ** attempt)

    Example:
        >>> client = OpenRouterClient(
        ...     api_key="sk-or-v1-...",
        ...     base_url="https://openrouter.ai/api/v1",
        ...     site_url="https://void-crm.ru",
        ...     app_name="Void CRM"
        ... )
        >>> response = await client.complete(
        ...     prompt="Hello",
        ...     model="anthropic/claude-3-haiku"
        ... )
    """

    # Известные размерности эмбеддингов (fallback если API не вернул)
    KNOWN_EMBEDDING_DIMENSIONS: dict[str, int] = {
        "openai/text-embedding-3-small": 1536,
        "openai/text-embedding-3-large": 3072,
        "openai/text-embedding-ada-002": 1536,
        "voyage/voyage-3": 1024,
        "voyage/voyage-3-lite": 512,
        "voyage/voyage-code-3": 1024,
        "voyage/voyage-finance-2": 1024,
        "voyage/voyage-law-2": 1024,
        "voyage/voyage-multilingual-2": 1024,
        "cohere/embed-english-v3.0": 1024,
        "cohere/embed-multilingual-v3.0": 1024,
        "cohere/embed-english-light-v3.0": 384,
        "cohere/embed-multilingual-light-v3.0": 384,
    }

    def __init__(
        self,
        api_key: str,
        base_url: str,
        site_url: str | None = None,
        app_name: str | None = None,
        timeout: float = 30.0,
        retry_attempts: int = 3,
        retry_delay_base: float = 1.0,
        use_exponential_backoff: bool = True,
        default_model: str | None = None,
        default_embedding_model: str | None = None,
    ):
        """
        Инициализирует OpenRouter клиент.

        Args:
            api_key: API ключ OpenRouter
            base_url: Base URL API
            site_url: URL сайта для HTTP-Referer (опционально)
            app_name: Название приложения для X-Title (опционально)
            timeout: Таймаут запроса в секундах
            retry_attempts: Количество повторных попыток
            retry_delay_base: Базовая задержка между попытками (секунды)
            use_exponential_backoff: Использовать exponential backoff
            default_model: Модель по умолчанию для completions
            default_embedding_model: Модель по умолчанию для embeddings
        """
        super().__init__(api_key, base_url)
        self.site_url = site_url
        self.app_name = app_name
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay_base = retry_delay_base
        self.use_exponential_backoff = use_exponential_backoff
        self.default_model = default_model or "anthropic/claude-3-haiku"
        self.default_embedding_model = (
            default_embedding_model or "openai/text-embedding-3-small"
        )

    def _build_headers(self) -> dict[str, str]:
        """Собирает заголовки для запроса к OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name
        return headers

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Выполняет HTTP запрос с retry логикой и exponential backoff.

        Args:
            method: HTTP метод (GET, POST, DELETE, PATCH)
            url: URL запроса
            **kwargs: Параметры для httpx.request

        Returns:
            httpx.Response

        Raises:
            ExternalAPIError: При ошибках API
        """
        last_error: Exception | None = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.retry_attempts):
                try:
                    response = await client.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response

                except httpx.TimeoutException as e:
                    last_error = ExternalAPIError(
                        detail=f"OpenRouter API timeout after {self.timeout}s",
                        extra={"attempt": attempt + 1, "url": url},
                    )
                    self.logger.warning(
                        "OpenRouter timeout (attempt %d/%d): %s",
                        attempt + 1,
                        self.retry_attempts,
                        str(e),
                    )

                except httpx.HTTPStatusError as e:
                    status_code = e.response.status_code

                    # 429 = rate limit, 503 = service unavailable - ретраим
                    if status_code in (429, 503):
                        last_error = ExternalAPIError(
                            detail=f"OpenRouter {status_code}: {'Rate limit' if status_code == 429 else 'Service unavailable'}",
                            extra={
                                "status_code": status_code,
                                "attempt": attempt + 1,
                                "response": e.response.text[:500],
                            },
                        )
                        self.logger.warning(
                            "OpenRouter %d error (attempt %d/%d): %s",
                            status_code,
                            attempt + 1,
                            self.retry_attempts,
                            e.response.text[:200],
                        )
                    else:
                        # Другие HTTP ошибки НЕ ретраим
                        error_detail = self._parse_error(e.response)
                        raise ExternalAPIError(
                            detail=f"OpenRouter API error: {error_detail}",
                            extra={"status_code": status_code},
                        ) from e

                except Exception as e:
                    raise ExternalAPIError(
                        detail=f"Unexpected error: {str(e)}",
                        extra={"error_type": type(e).__name__},
                    ) from e

                # Задержка перед следующей попыткой
                if attempt < self.retry_attempts - 1:
                    if self.use_exponential_backoff:
                        delay = self.retry_delay_base * (2**attempt)
                    else:
                        delay = self.retry_delay_base

                    self.logger.debug(
                        "Waiting %.1fs before retry (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        self.retry_attempts,
                    )
                    await asyncio.sleep(delay)

        if last_error:
            raise last_error
        raise ExternalAPIError(detail="Failed to complete request")

    def _parse_error(self, response: httpx.Response) -> str:
        """Извлекает сообщение об ошибке из ответа."""
        try:
            data = response.json()
            if "error" in data:
                error = data["error"]
                if isinstance(error, dict):
                    return error.get("message", str(error))
                return str(error)
            return response.text
        except Exception:
            return response.text

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Парсит ISO datetime строку."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _validate_price(self, price: str | float | int | None) -> str | None:
        """
        Валидирует и форматирует цену.

        OpenRouter возвращает цену за токен.
        Некорректные значения (отрицательные, слишком большие) фильтруются.

        Args:
            price: Цена за токен (может быть строкой, числом или None)

        Returns:
            Строка с ценой или None если некорректная
        """
        if price is None:
            return None
        try:
            p = float(price)
            # Фильтруем некорректные цены
            # Цена за токен должна быть >= 0 и разумной (< 0.01 за токен = < $10,000/1M)
            if p < 0 or p > 0.01:
                return None
            return str(price)
        except (ValueError, TypeError):
            return None

    # ==================== CHAT / COMPLETIONS ====================

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Генерирует текст по промпту через OpenRouter.

        Args:
            prompt: Текст промпта
            model: ID модели OpenRouter
            temperature: Температура (0.0-2.0)
            max_tokens: Максимум токенов
            **kwargs: Дополнительные параметры (system_prompt, и т.д.)

        Returns:
            Сгенерированный текст
        """
        url = f"{self.base_url}/chat/completions"
        model = model or self.default_model

        messages = []
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            system_content = kwargs["system_prompt"]
            if not isinstance(system_content, str):
                system_content = json.dumps(system_content, ensure_ascii=False)
            messages.append({"role": "system", "content": system_content})

        if not isinstance(prompt, str):
            prompt = json.dumps(prompt, ensure_ascii=False)
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        self.logger.info("OpenRouter request: model=%s, tokens=%s", model, max_tokens)

        response = await self._request_with_retry(
            "POST", url, headers=self._build_headers(), json=payload
        )

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        self.logger.info("OpenRouter response: %d chars", len(content))
        return content

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
            output_schema: JSON Schema для валидации
            model: ID модели
            temperature: Температура
            max_tokens: Максимум токенов
            **kwargs: Дополнительные параметры

        Returns:
            Распарсенный JSON dict
        """
        url = f"{self.base_url}/chat/completions"
        model = model or self.default_model

        enhanced_prompt = f"{prompt}\n\nОтветь ТОЛЬКО валидным JSON согласно схеме:\n{json.dumps(output_schema, ensure_ascii=False)}"

        messages = []
        if "system_prompt" in kwargs and kwargs["system_prompt"]:
            system_content = kwargs["system_prompt"]
            if not isinstance(system_content, str):
                system_content = json.dumps(system_content, ensure_ascii=False)
            messages.append({"role": "system", "content": system_content})

        messages.append({"role": "user", "content": enhanced_prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        self.logger.info(
            "OpenRouter structured request: model=%s, schema_keys=%s",
            model,
            list(output_schema.get("properties", {}).keys()),
        )

        response = await self._request_with_retry(
            "POST", url, headers=self._build_headers(), json=payload
        )

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        try:
            result = json.loads(content)
            self.logger.info("OpenRouter structured response: OK")
            return result
        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse JSON: %s", content)
            raise ExternalAPIError(
                detail=f"Invalid JSON from AI: {str(e)}",
                extra={"content": content, "schema": output_schema},
            ) from e

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> OpenRouterChatResponseSchema:
        """
        Отправляет сообщения в чат и получает ответ.

        Args:
            messages: Список сообщений [{"role": "user", "content": "..."}]
            model: ID модели OpenRouter
            temperature: Температура (0.0-2.0)
            max_tokens: Максимум токенов
            **kwargs: Дополнительные параметры

        Returns:
            OpenRouterChatResponseSchema с полной информацией об ответе
        """
        url = f"{self.base_url}/chat/completions"
        model = model or self.default_model

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        self.logger.info(
            "OpenRouter chat: model=%s, messages=%d", model, len(messages)
        )

        response = await self._request_with_retry(
            "POST", url, headers=self._build_headers(), json=payload
        )

        data = response.json()
        choice = data.get("choices", [{}])[0]
        usage = data.get("usage", {})

        return OpenRouterChatResponseSchema(
            id=data.get("id", ""),
            model=data.get("model", model),
            content=choice.get("message", {}).get("content", ""),
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason"),
        )

    # ==================== EMBEDDINGS ====================

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
        embeddings = await self.create_embeddings_batch([text], model)
        return embeddings[0]

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
        if not texts:
            return []

        url = f"{self.base_url}/embeddings"
        model = model or self.default_embedding_model

        payload = {
            "model": model,
            "input": texts,
        }

        self.logger.info("OpenRouter embeddings: model=%s, texts=%d", model, len(texts))

        response = await self._request_with_retry(
            "POST", url, headers=self._build_headers(), json=payload
        )

        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]

        self.logger.info(
            "OpenRouter embeddings response: %d vectors, dim=%d",
            len(embeddings),
            len(embeddings[0]) if embeddings else 0,
        )

        return embeddings

    def get_embedding_dimension(self, model: str | None = None) -> int:
        """
        Возвращает размерность эмбеддинга для модели.

        Args:
            model: ID модели. Если None, используется default.

        Returns:
            Размерность вектора
        """
        model = model or self.default_embedding_model
        return self.KNOWN_EMBEDDING_DIMENSIONS.get(model, 1536)

    # ==================== MODELS ====================

    async def get_models(self, use_cache: bool = True) -> list[OpenRouterModelSchema]:
        """
        Получает список доступных LLM моделей из OpenRouter API.

        Args:
            use_cache: Использовать кэш (по умолчанию True)

        Returns:
            Список моделей с метаданными
        """
        # Проверяем кэш
        if use_cache:
            cached = _cache.get("llm_models")
            if cached is not None:
                self.logger.debug("Using cached LLM models (%d)", len(cached))
                return cached

        url = f"{self.base_url}/models"

        self.logger.info("Fetching OpenRouter models list")

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        data = response.json()
        models = []

        for item in data.get("data", []):
            # Пропускаем embedding модели
            output_modalities = item.get("architecture", {}).get(
                "output_modalities", []
            )
            if "embeddings" in output_modalities and "text" not in output_modalities:
                continue

            pricing = item.get("pricing", {})
            architecture = item.get("architecture", {})

            # OpenRouter может вернуть цену как число или строку
            prompt_price = pricing.get("prompt")
            completion_price = pricing.get("completion")

            models.append(
                OpenRouterModelSchema(
                    id=item["id"],
                    name=item.get("name", item["id"]),
                    provider="openrouter",
                    context_length=item.get("context_length", 0),
                    pricing_prompt=self._validate_price(prompt_price),
                    pricing_completion=self._validate_price(completion_price),
                    description=item.get("description"),
                    input_modalities=architecture.get("input_modalities"),
                    output_modalities=architecture.get("output_modalities"),
                    supports_json_mode="json_mode" in item.get("supported_parameters", [])
                    or "response_format" in item.get("supported_parameters", []),
                )
            )

        self.logger.info("Fetched %d LLM models from OpenRouter", len(models))

        # Сортируем по цене (от дешёвых к дорогим)
        # Модели без цены или с ценой 0 идут первыми
        def get_sort_price(model: OpenRouterModelSchema) -> float:
            if model.pricing_prompt is None:
                return 0.0
            try:
                return float(model.pricing_prompt)
            except (ValueError, TypeError):
                return 0.0

        models.sort(key=get_sort_price)

        # Сохраняем в кэш
        _cache.set("llm_models", models)

        return models

    async def get_models_count(self) -> int:
        """
        Получает общее количество доступных моделей.

        Returns:
            Количество моделей
        """
        url = f"{self.base_url}/models/count"

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        data = response.json()
        return data.get("count", 0)

    async def get_embedding_models(self, use_cache: bool = True) -> list[OpenRouterEmbeddingModelSchema]:
        """
        Получает список доступных моделей эмбеддингов из OpenRouter API.

        Args:
            use_cache: Использовать кэш (по умолчанию True)

        Returns:
            Список моделей эмбеддингов с метаданными
        """
        # Проверяем кэш
        if use_cache:
            cached = _cache.get("embedding_models")
            if cached is not None:
                self.logger.debug("Using cached embedding models (%d)", len(cached))
                return cached

        url = f"{self.base_url}/embeddings/models"

        self.logger.info("Fetching OpenRouter embedding models list")

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        data = response.json()
        models = []

        for item in data.get("data", []):
            model_id = item["id"]
            pricing = item.get("pricing", {})
            prompt_price = pricing.get("prompt")

            # Определяем размерность
            dimension = self.KNOWN_EMBEDDING_DIMENSIONS.get(model_id, 1536)

            models.append(
                OpenRouterEmbeddingModelSchema(
                    id=model_id,
                    name=item.get("name", model_id),
                    provider="openrouter",
                    dimension=dimension,
                    context_length=item.get("context_length", 8192),
                    pricing_prompt=str(prompt_price) if prompt_price is not None else None,
                    description=item.get("description"),
                )
            )

        self.logger.info("Fetched %d embedding models from OpenRouter", len(models))

        # Сортируем по цене (от дешёвых к дорогим)
        def get_sort_price(model: OpenRouterEmbeddingModelSchema) -> float:
            if model.pricing_prompt is None:
                return 0.0
            try:
                return float(model.pricing_prompt)
            except (ValueError, TypeError):
                return 0.0

        models.sort(key=get_sort_price)

        # Сохраняем в кэш
        _cache.set("embedding_models", models)

        return models

    async def get_model_endpoints(
        self, model_id: str
    ) -> list[OpenRouterEndpointSchema]:
        """
        Получает список endpoints (провайдеров) для модели.

        Args:
            model_id: ID модели (например "anthropic/claude-3-opus")

        Returns:
            Список endpoints с информацией о латентности и пропускной способности
        """
        url = f"{self.base_url}/models/{model_id}/endpoints"

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        data = response.json()
        endpoints = []

        # API возвращает {data: {id, name, endpoints: [...]}}
        model_data = data.get("data", {})
        endpoints_list = model_data.get("endpoints", []) if isinstance(model_data, dict) else []

        for item in endpoints_list:
            endpoints.append(
                OpenRouterEndpointSchema(
                    provider=item.get("provider_name", item.get("tag", "")),
                    model=item.get("name", model_id),
                    quantization=item.get("quantization"),
                    latency=None,  # API не возвращает latency напрямую
                    throughput=None,  # API не возвращает throughput напрямую
                )
            )

        return endpoints

    async def get_model_parameters(
        self, model_id: str
    ) -> list[OpenRouterParameterSchema]:
        """
        Получает поддерживаемые параметры модели.

        Args:
            model_id: ID модели

        Returns:
            Список параметров с описанием и популярностью
        """
        url = f"{self.base_url}/parameters/{model_id}"

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        data = response.json()
        params = []

        # API возвращает {data: {model, supported_parameters: [...]}}
        model_data = data.get("data", {})
        supported_params = model_data.get("supported_parameters", [])

        for name in supported_params:
            params.append(
                OpenRouterParameterSchema(
                    name=name,
                    type="unknown",  # API не возвращает типы параметров
                    default=None,
                    min_value=None,
                    max_value=None,
                    description=None,
                    popularity=None,
                )
            )

        return params

    # ==================== PROVIDERS ====================

    async def get_providers(self, use_cache: bool = True) -> list[OpenRouterProviderSchema]:
        """
        Получает список всех провайдеров моделей.

        Args:
            use_cache: Использовать кэш (по умолчанию True)

        Returns:
            Список провайдеров
        """
        # Проверяем кэш
        if use_cache:
            cached = _cache.get("providers")
            if cached is not None:
                self.logger.debug("Using cached providers (%d)", len(cached))
                return cached

        url = f"{self.base_url}/providers"

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        data = response.json()
        providers = []

        for item in data.get("data", []):
            providers.append(
                OpenRouterProviderSchema(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    website=item.get("website"),
                    priority=item.get("priority", 0),
                )
            )

        # Сохраняем в кэш
        _cache.set("providers", providers)

        return providers

    # ==================== CREDITS ====================

    async def get_credits(self, use_cache: bool = True) -> OpenRouterCreditsSchema:
        """
        Получает информацию о балансе кредитов.

        Args:
            use_cache: Использовать кэш (по умолчанию True, TTL 1 мин)

        Returns:
            Информация о балансе
        """
        # Проверяем кэш
        if use_cache:
            cached = _cache.get("credits")
            if cached is not None:
                self.logger.debug("Using cached credits")
                return cached

        url = f"{self.base_url}/credits"

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        data = response.json()
        # OpenRouter возвращает: { data: { total_credits: X, total_usage: Y } }
        credits_data = data.get("data", {})
        total_credits = credits_data.get("total_credits", 0.0)
        total_usage = credits_data.get("total_usage", 0.0)
        remaining = total_credits - total_usage

        result = OpenRouterCreditsSchema(
            total_credits=total_credits,
            usage_credits=total_usage,
            remaining_credits=remaining,
            currency="USD",
        )

        # Сохраняем в кэш
        _cache.set("credits", result)

        return result

    # ==================== ANALYTICS ====================

    async def get_analytics(
        self,
        period: str = "day",
        limit: int = 100,
    ) -> list[OpenRouterAnalyticsPointSchema]:
        """
        Получает аналитику использования API сгруппированную по endpoint.

        Args:
            period: Период группировки ("hour", "day", "week", "month")
            limit: Максимум записей

        Returns:
            Список точек данных аналитики
        """
        url = f"{self.base_url}/analytics"
        params = {
            "period": period,
            "limit": limit,
        }

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers(), params=params
        )

        data = response.json()
        analytics = []

        for item in data.get("data", []):
            analytics.append(
                OpenRouterAnalyticsPointSchema(
                    endpoint=item.get("endpoint", ""),
                    requests=item.get("requests", 0),
                    tokens_prompt=item.get("tokens_prompt", 0),
                    tokens_completion=item.get("tokens_completion", 0),
                    cost=item.get("cost", 0.0),
                    period=item.get("period", ""),
                )
            )

        return analytics

    # ==================== GENERATIONS ====================

    async def get_generation(self, generation_id: str) -> OpenRouterGenerationSchema:
        """
        Получает информацию о конкретной генерации (запросе к модели).

        Args:
            generation_id: ID генерации (возвращается в заголовке X-Request-Id
                           или в поле id ответа chat/completions)

        Returns:
            Информация о генерации включая токены, стоимость, латентность
        """
        url = f"{self.base_url}/generation"
        params = {"id": generation_id}

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers(), params=params
        )

        data = response.json().get("data", {})

        return OpenRouterGenerationSchema(
            id=data.get("id", generation_id),
            model=data.get("model", ""),
            created_at=self._parse_datetime(data.get("created_at")),
            total_cost=data.get("total_cost", 0.0),
            tokens_prompt=data.get("tokens_prompt", 0),
            tokens_completion=data.get("tokens_completion", 0),
            native_tokens_prompt=data.get("native_tokens_prompt"),
            native_tokens_completion=data.get("native_tokens_completion"),
            latency_ms=data.get("latency"),
            generation_time_ms=data.get("generation_time"),
            status=data.get("status"),
            origin=data.get("origin"),
            provider_name=data.get("provider_name"),
            prompt=data.get("prompt"),
            completion=data.get("completion"),
        )

    # ==================== API KEYS ====================

    async def get_api_keys(self) -> list[OpenRouterApiKeySchema]:
        """
        Получает список API ключей аккаунта.

        Returns:
            Список API ключей
        """
        url = f"{self.base_url}/keys"

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        data = response.json()
        keys = []

        for item in data.get("data", []):
            keys.append(
                OpenRouterApiKeySchema(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    key_prefix=item.get("key_prefix", ""),
                    created_at=self._parse_datetime(item.get("created_at")),
                    last_used_at=self._parse_datetime(item.get("last_used_at")),
                    is_active=item.get("is_active", True),
                    limit_per_minute=item.get("limit_per_minute"),
                )
            )

        return keys

    async def get_api_key(self, key_id: str) -> OpenRouterApiKeySchema:
        """
        Получает информацию о конкретном API ключе.

        Args:
            key_id: ID ключа

        Returns:
            Информация о ключе
        """
        url = f"{self.base_url}/keys/{key_id}"

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        item = response.json().get("data", {})

        return OpenRouterApiKeySchema(
            id=item.get("id", key_id),
            name=item.get("name", ""),
            key_prefix=item.get("key_prefix", ""),
            created_at=self._parse_datetime(item.get("created_at")),
            last_used_at=self._parse_datetime(item.get("last_used_at")),
            is_active=item.get("is_active", True),
            limit_per_minute=item.get("limit_per_minute"),
        )

    async def get_current_api_key(self) -> OpenRouterApiKeySchema:
        """
        Получает информацию о текущем API ключе.

        Returns:
            Информация о ключе
        """
        url = f"{self.base_url}/keys/current"

        response = await self._request_with_retry(
            "GET", url, headers=self._build_headers()
        )

        item = response.json().get("data", {})

        return OpenRouterApiKeySchema(
            id=item.get("id", ""),
            name=item.get("name", ""),
            key_prefix=item.get("key_prefix", ""),
            created_at=self._parse_datetime(item.get("created_at")),
            last_used_at=self._parse_datetime(item.get("last_used_at")),
            is_active=item.get("is_active", True),
            limit_per_minute=item.get("limit_per_minute"),
        )

    async def create_api_key(
        self,
        name: str,
        limit_per_minute: int | None = None,
    ) -> dict[str, Any]:
        """
        Создаёт новый API ключ.

        Args:
            name: Название ключа
            limit_per_minute: Лимит запросов в минуту

        Returns:
            Данные созданного ключа (включая сам ключ - показывается только 1 раз)
        """
        url = f"{self.base_url}/keys"

        payload: dict[str, Any] = {"name": name}
        if limit_per_minute is not None:
            payload["limit_per_minute"] = limit_per_minute

        response = await self._request_with_retry(
            "POST", url, headers=self._build_headers(), json=payload
        )

        return response.json().get("data", {})

    async def delete_api_key(self, key_id: str) -> bool:
        """
        Удаляет API ключ.

        Args:
            key_id: ID ключа

        Returns:
            True если успешно удалён
        """
        url = f"{self.base_url}/keys/{key_id}"

        await self._request_with_retry("DELETE", url, headers=self._build_headers())

        return True

    async def update_api_key(
        self,
        key_id: str,
        name: str | None = None,
        is_active: bool | None = None,
        limit_per_minute: int | None = None,
    ) -> OpenRouterApiKeySchema:
        """
        Обновляет API ключ.

        Args:
            key_id: ID ключа
            name: Новое название
            is_active: Статус активности
            limit_per_minute: Новый лимит

        Returns:
            Обновлённая информация о ключе
        """
        url = f"{self.base_url}/keys/{key_id}"

        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if is_active is not None:
            payload["is_active"] = is_active
        if limit_per_minute is not None:
            payload["limit_per_minute"] = limit_per_minute

        response = await self._request_with_retry(
            "PATCH", url, headers=self._build_headers(), json=payload
        )

        item = response.json().get("data", {})

        return OpenRouterApiKeySchema(
            id=item.get("id", key_id),
            name=item.get("name", ""),
            key_prefix=item.get("key_prefix", ""),
            created_at=self._parse_datetime(item.get("created_at")),
            last_used_at=self._parse_datetime(item.get("last_used_at")),
            is_active=item.get("is_active", True),
            limit_per_minute=item.get("limit_per_minute"),
        )
