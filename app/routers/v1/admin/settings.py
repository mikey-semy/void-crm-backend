"""
Роутер для AI настроек (только для админов).

Модуль предоставляет HTTP API для управления:
- AI настройками (API ключ, модели эмбеддингов, LLM модели)
- Списком доступных моделей (динамически с OpenRouter)

Все endpoints защищены через CurrentAdminDep.

NOTE: Для полного управления OpenRouter API используйте /admin/openrouter/
"""

from fastapi import status

from app.core.dependencies.system_settings import AISettingsServiceDep
from app.core.integrations.ai import OpenRouterClient
from app.core.security import CurrentAdminDep
from app.core.settings import settings
from app.routers.base import ProtectedRouter
from app.schemas.v1.openrouter import OpenRouterEmbeddingModelSchema
from app.schemas.v1.system_settings import (
    AISettingsResponseSchema,
    AISettingsUpdateSchema,
    EmbeddingModelsResponseSchema,
    LLMModelsResponseSchema,
)


class AdminAISettingsRouter(ProtectedRouter):
    """
    Роутер для AI настроек.

    Protected Endpoints (только для админов):
        GET /admin/settings/ai - Получить настройки
        PUT /admin/settings/ai - Обновить настройки
        GET /admin/settings/ai/embedding-models - Список моделей эмбеддингов
        GET /admin/settings/ai/llm-models - Список LLM моделей
    """

    def __init__(self):
        """Инициализирует роутер."""
        super().__init__(prefix="admin/settings", tags=["Admin Settings"])

    def configure(self):
        """Настройка endpoint'ов."""

        @self.router.get(
            path="/ai",
            response_model=AISettingsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## ⚙️ Получить AI настройки

Возвращает текущие AI настройки (OpenRouter).

### Требования:
- Только для администраторов

### Returns:
- Модель эмбеддингов и размерность
- LLM модели (основная и резервная)
- Статус API ключа
- Количество проиндексированных статей
""",
        )
        async def get_ai_settings(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> AISettingsResponseSchema:
            """Получает текущие AI настройки."""
            ai_settings = await service.get_settings()

            return AISettingsResponseSchema(
                success=True,
                message="AI настройки получены",
                data=ai_settings,
            )

        @self.router.put(
            path="/ai",
            response_model=AISettingsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## ✏️ Обновить AI настройки

Обновляет AI настройки.

### Требования:
- Только для администраторов

### Request Body:
- **api_key** — API ключ OpenRouter (будет зашифрован)
- **embedding_model** — Модель эмбеддингов
- **llm_model** — Основная LLM модель
- **llm_fallback_model** — Резервная LLM модель

### Returns:
- Обновлённые настройки
""",
        )
        async def update_ai_settings(
            data: AISettingsUpdateSchema,
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> AISettingsResponseSchema:
            """Обновляет AI настройки."""
            ai_settings = await service.update_settings(
                api_key=data.api_key,
                embedding_model=data.embedding_model,
                llm_model=data.llm_model,
                llm_fallback_model=data.llm_fallback_model,
            )

            return AISettingsResponseSchema(
                success=True,
                message="AI настройки обновлены",
                data=ai_settings,
            )

        @self.router.get(
            path="/ai/embedding-models",
            response_model=EmbeddingModelsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🧠 Список моделей эмбеддингов

Динамически загружает список доступных моделей эмбеддингов из OpenRouter API.

### Требования:
- Только для администраторов
- Требуется настроенный API ключ

### Returns:
- Список моделей с ценами, размерностями и описаниями
""",
        )
        async def get_embedding_models(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> EmbeddingModelsResponseSchema:
            """Загружает список моделей эмбеддингов из OpenRouter API."""
            api_key = await service.get_decrypted_api_key()

            if not api_key:
                fallback_models = [
                    OpenRouterEmbeddingModelSchema(
                        id=model_id,
                        name=model_id.split("/")[-1].replace("-", " ").title(),
                        provider="openrouter",
                        dimension=dimension,
                    )
                    for model_id, dimension in OpenRouterClient.KNOWN_EMBEDDING_DIMENSIONS.items()
                ]
                return EmbeddingModelsResponseSchema(
                    success=True,
                    message="Список моделей (API ключ не настроен - используется fallback)",
                    data=fallback_models,
                )

            client = OpenRouterClient(
                api_key=api_key,
                base_url=settings.ai.OPENROUTER_BASE_URL,
                site_url=settings.ai.OPENROUTER_SITE_URL,
                app_name=settings.ai.OPENROUTER_APP_NAME,
                timeout=settings.ai.OPENROUTER_TIMEOUT,
            )

            models = await client.get_embedding_models()

            return EmbeddingModelsResponseSchema(
                success=True,
                message=f"Загружено {len(models)} моделей из OpenRouter",
                data=models,
            )

        @self.router.get(
            path="/ai/llm-models",
            response_model=LLMModelsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🤖 Список LLM моделей

Динамически загружает список доступных LLM моделей из OpenRouter API.

### Требования:
- Только для администраторов
- Требуется настроенный API ключ

### Returns:
- Список моделей с ценами, контекстом и возможностями
""",
        )
        async def get_llm_models(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> LLMModelsResponseSchema:
            """Загружает список LLM моделей из OpenRouter API."""
            api_key = await service.get_decrypted_api_key()

            if not api_key:
                return LLMModelsResponseSchema(
                    success=False,
                    message="API ключ не настроен",
                    data=[],
                )

            client = OpenRouterClient(
                api_key=api_key,
                base_url=settings.ai.OPENROUTER_BASE_URL,
                site_url=settings.ai.OPENROUTER_SITE_URL,
                app_name=settings.ai.OPENROUTER_APP_NAME,
                timeout=settings.ai.OPENROUTER_TIMEOUT,
            )

            models = await client.get_models()

            return LLMModelsResponseSchema(
                success=True,
                message=f"Загружено {len(models)} моделей из OpenRouter",
                data=models,
            )
