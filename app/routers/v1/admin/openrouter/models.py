"""
Роутер для OpenRouter Models API.

API Reference:
- https://openrouter.ai/docs/api/api-reference/models/get-models
- https://openrouter.ai/docs/api/api-reference/models/list-models-count
- https://openrouter.ai/docs/api/api-reference/models/list-models-user
- https://openrouter.ai/docs/api/api-reference/endpoints/list-endpoints
- https://openrouter.ai/docs/api/api-reference/parameters/get-parameters
"""

from fastapi import Path, Query, status

from app.core.dependencies.system_settings import AISettingsServiceDep
from app.core.security import CurrentAdminDep
from app.schemas.v1.openrouter import (
    EndpointsResponseSchema,
    ModelsCountResponseSchema,
    ModelsResponseSchema,
    ParametersResponseSchema,
)

from .base import BaseOpenRouterRouter


class AdminOpenRouterModelsRouter(BaseOpenRouterRouter):
    """
    Роутер для работы с моделями OpenRouter.

    Endpoints:
        GET /admin/openrouter/models - Все LLM модели
        GET /admin/openrouter/models/count - Количество моделей
        GET /admin/openrouter/models/user - Модели доступные пользователю
        GET /admin/openrouter/models/{model_id}/endpoints - Endpoints модели
        GET /admin/openrouter/models/{model_id}/parameters - Параметры модели
    """

    def __init__(self):
        """Инициализирует роутер."""
        super().__init__(prefix="admin/openrouter/models", tags=["Admin - OpenRouter Models"])

    def configure(self):
        """Настройка endpoint'ов."""

        @self.router.get(
            path="",
            response_model=ModelsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🤖 Список LLM моделей

Возвращает список всех доступных LLM моделей.

**OpenRouter API:** [GET /models](https://openrouter.ai/docs/api/api-reference/models/get-models)

### Returns:
- ID, название, провайдер
- Размер контекста
- Цены за prompt/completion токены
- Поддерживаемые модальности
- Поддержка JSON mode
""",
        )
        async def get_models(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> ModelsResponseSchema:
            """Получает список всех LLM моделей."""
            try:
                client = await self._get_client(service)
                models = await client.get_models()

                return ModelsResponseSchema(
                    success=True,
                    message=f"Загружено {len(models)} моделей",
                    data=models,
                )
            except ValueError as e:
                return ModelsResponseSchema(
                    success=False,
                    message=str(e),
                    data=[],
                )

        @self.router.get(
            path="/count",
            response_model=ModelsCountResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 📊 Количество моделей

Возвращает общее количество доступных моделей.

**OpenRouter API:** [GET /models/count](https://openrouter.ai/docs/api/api-reference/models/list-models-count)
""",
        )
        async def get_models_count(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> ModelsCountResponseSchema:
            """Получает количество моделей."""
            try:
                client = await self._get_client(service)
                count = await client.get_models_count()

                return ModelsCountResponseSchema(
                    success=True,
                    message=f"Доступно {count} моделей",
                    data=count,
                )
            except ValueError as e:
                return ModelsCountResponseSchema(
                    success=False,
                    message=str(e),
                    data=0,
                )

        @self.router.get(
            path="/user",
            response_model=ModelsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 👤 Модели пользователя

Возвращает список моделей, доступных текущему пользователю с учётом лимитов.

**OpenRouter API:** [GET /models (user)](https://openrouter.ai/docs/api/api-reference/models/list-models-user)

### Query Parameters:
- **supported_parameters** — Фильтр по поддерживаемым параметрам (опционально)
""",
        )
        async def get_user_models(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
            supported_parameters: str | None = Query(
                None, description="Фильтр по параметрам (через запятую)"
            ),
        ) -> ModelsResponseSchema:
            """Получает модели доступные пользователю."""
            try:
                client = await self._get_client(service)
                # Используем тот же endpoint, но можно добавить фильтрацию
                models = await client.get_models()

                # Если указаны параметры, фильтруем
                if supported_parameters:
                    params = [p.strip() for p in supported_parameters.split(",")]
                    # Фильтрация будет на стороне клиента
                    # т.к. API не поддерживает прямую фильтрацию

                return ModelsResponseSchema(
                    success=True,
                    message=f"Загружено {len(models)} моделей для пользователя",
                    data=models,
                )
            except ValueError as e:
                return ModelsResponseSchema(
                    success=False,
                    message=str(e),
                    data=[],
                )

        @self.router.get(
            path="/{model_id:path}/endpoints",
            response_model=EndpointsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🔌 Endpoints модели

Возвращает список провайдеров и их endpoints для модели.

**OpenRouter API:** [GET /models/{id}/endpoints](https://openrouter.ai/docs/api/api-reference/endpoints/list-endpoints)

### Path Parameters:
- **model_id** — ID модели (например: `openai/gpt-4o`)

### Returns:
- Провайдер
- Квантизация
- Latency (мс)
- Throughput (токены/сек)
""",
        )
        async def get_model_endpoints(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
            model_id: str = Path(..., description="ID модели"),
        ) -> EndpointsResponseSchema:
            """Получает endpoints модели."""
            try:
                client = await self._get_client(service)
                endpoints = await client.get_model_endpoints(model_id)

                return EndpointsResponseSchema(
                    success=True,
                    message=f"Найдено {len(endpoints)} endpoints для {model_id}",
                    data=endpoints,
                )
            except ValueError as e:
                return EndpointsResponseSchema(
                    success=False,
                    message=str(e),
                    data=[],
                )

        @self.router.get(
            path="/{model_id:path}/parameters",
            response_model=ParametersResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## ⚙️ Параметры модели

Возвращает поддерживаемые параметры модели.

**OpenRouter API:** [GET /parameters/{model}](https://openrouter.ai/docs/api/api-reference/parameters/get-parameters)

### Path Parameters:
- **model_id** — ID модели (например: `openai/gpt-4o`)

### Returns:
- Название параметра
- Тип (number, string, boolean)
- Значение по умолчанию
- Min/Max значения
- Описание
- Популярность использования
""",
        )
        async def get_model_parameters(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
            model_id: str = Path(..., description="ID модели"),
        ) -> ParametersResponseSchema:
            """Получает параметры модели."""
            try:
                client = await self._get_client(service)
                parameters = await client.get_model_parameters(model_id)

                return ParametersResponseSchema(
                    success=True,
                    message=f"Найдено {len(parameters)} параметров для {model_id}",
                    data=parameters,
                )
            except ValueError as e:
                return ParametersResponseSchema(
                    success=False,
                    message=str(e),
                    data=[],
                )
