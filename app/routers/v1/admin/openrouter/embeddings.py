"""
Роутер для OpenRouter Embeddings API.

API Reference:
- https://openrouter.ai/docs/api/api-reference/embeddings/list-embeddings-models
- https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings
"""

from fastapi import status

from app.core.dependencies.system_settings import AISettingsServiceDep
from app.core.integrations.ai import OpenRouterClient
from app.core.security import CurrentAdminDep
from app.schemas.v1.openrouter import (
    EmbeddingBatchRequestSchema,
    EmbeddingBatchResponseSchema,
    EmbeddingModelsResponseSchema,
    EmbeddingRequestSchema,
    EmbeddingResponseSchema,
    OpenRouterEmbeddingModelSchema,
)

from .base import BaseOpenRouterRouter


class AdminOpenRouterEmbeddingsRouter(BaseOpenRouterRouter):
    """
    Роутер для работы с embeddings OpenRouter.

    Endpoints:
        GET /admin/openrouter/embeddings/models - Список embedding моделей
        POST /admin/openrouter/embeddings - Создать embedding
        POST /admin/openrouter/embeddings/batch - Создать batch embeddings
    """

    def __init__(self):
        """Инициализирует роутер."""
        super().__init__(prefix="admin/openrouter/embeddings", tags=["Admin - OpenRouter Embeddings"])

    def configure(self):
        """Настройка endpoint'ов."""

        @self.router.get(
            path="/models",
            response_model=EmbeddingModelsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🧠 Список Embedding моделей

Возвращает список доступных моделей для создания embeddings.

**OpenRouter API:** [GET /embeddings/models](https://openrouter.ai/docs/api/api-reference/embeddings/list-embeddings-models)

### Returns:
- ID модели
- Название
- Размерность вектора
- Размер контекста
- Цена за токены
""",
        )
        async def get_embedding_models(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> EmbeddingModelsResponseSchema:
            """Получает список embedding моделей."""
            try:
                client = await self._get_client(service)
                models = await client.get_embedding_models()

                return EmbeddingModelsResponseSchema(
                    success=True,
                    message=f"Загружено {len(models)} embedding моделей",
                    data=models,
                )
            except ValueError as e:
                # Fallback - известные модели
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
                    message=f"{e} - используется fallback",
                    data=fallback_models,
                )

        @self.router.post(
            path="",
            response_model=EmbeddingResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 📊 Создать Embedding

Создаёт векторное представление текста.

**OpenRouter API:** [POST /embeddings](https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings)

### Request Body:
- **text** — Текст для создания embedding
- **model** — ID модели (опционально, default: text-embedding-3-small)

### Returns:
- Вектор embedding (list[float])
- Размерность вектора
""",
        )
        async def create_embedding(
            data: EmbeddingRequestSchema,
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> EmbeddingResponseSchema:
            """Создаёт embedding для текста."""
            try:
                client = await self._get_client(service)
                embedding = await client.create_embedding(
                    text=data.text,
                    model=data.model,
                )

                return EmbeddingResponseSchema(
                    success=True,
                    message=f"Embedding создан (dim={len(embedding)})",
                    data={
                        "embedding": embedding,
                        "dimension": len(embedding),
                        "model": data.model or client.default_embedding_model,
                    },
                )
            except ValueError as e:
                return EmbeddingResponseSchema(
                    success=False,
                    message=str(e),
                    data={},
                )

        @self.router.post(
            path="/batch",
            response_model=EmbeddingBatchResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 📊 Batch Embeddings

Создаёт векторные представления для нескольких текстов.

**OpenRouter API:** [POST /embeddings](https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings)

### Request Body:
- **texts** — Список текстов
- **model** — ID модели (опционально)

### Returns:
- Список векторов embedding
- Количество и размерность
""",
        )
        async def create_embeddings_batch(
            data: EmbeddingBatchRequestSchema,
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> EmbeddingBatchResponseSchema:
            """Создаёт embeddings для нескольких текстов."""
            try:
                client = await self._get_client(service)
                embeddings = await client.create_embeddings_batch(
                    texts=data.texts,
                    model=data.model,
                )

                return EmbeddingBatchResponseSchema(
                    success=True,
                    message=f"Создано {len(embeddings)} embeddings",
                    data={
                        "embeddings": embeddings,
                        "count": len(embeddings),
                        "dimension": len(embeddings[0]) if embeddings else 0,
                        "model": data.model or client.default_embedding_model,
                    },
                )
            except ValueError as e:
                return EmbeddingBatchResponseSchema(
                    success=False,
                    message=str(e),
                    data={},
                )
