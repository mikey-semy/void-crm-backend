"""
Роутер для OpenRouter Generations API.

API Reference:
- https://openrouter.ai/docs/api/api-reference/generations/get-generation
"""

from fastapi import Path, status

from app.core.dependencies.system_settings import AISettingsServiceDep
from app.core.security import CurrentAdminDep
from app.schemas.v1.openrouter import (
    GenerationResponseSchema,
    OpenRouterGenerationSchema,
)

from .base import BaseOpenRouterRouter


class AdminOpenRouterGenerationsRouter(BaseOpenRouterRouter):
    """
    Роутер для работы с генерациями OpenRouter.

    Endpoints:
        GET /admin/openrouter/generations/{generation_id} - Информация о генерации
    """

    def __init__(self):
        """Инициализирует роутер."""
        super().__init__(prefix="admin/openrouter/generations", tags=["Admin - OpenRouter Generations"])

    def configure(self):
        """Настройка endpoint'ов."""

        @self.router.get(
            path="/{generation_id}",
            response_model=GenerationResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 📝 Информация о генерации

Возвращает детальную информацию о конкретном запросе к модели.

**OpenRouter API:** [GET /generation](https://openrouter.ai/docs/api/api-reference/generations/get-generation)

### Path Parameters:
- **generation_id** — ID генерации (из заголовка X-Request-Id или поля id ответа)

### Returns:
- Модель
- Время создания
- Стоимость
- Токены (prompt/completion, native)
- Latency и generation time (мс)
- Статус
- Origin
- Провайдер
- Prompt и completion (если сохранены)
""",
        )
        async def get_generation(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
            generation_id: str = Path(..., description="ID генерации"),
        ) -> GenerationResponseSchema:
            """Получает информацию о генерации."""
            try:
                client = await self._get_client(service)
                generation = await client.get_generation(generation_id)

                return GenerationResponseSchema(
                    success=True,
                    message=f"Генерация {generation_id}",
                    data=generation,
                )
            except ValueError as e:
                return GenerationResponseSchema(
                    success=False,
                    message=str(e),
                    data=OpenRouterGenerationSchema(
                        id=generation_id,
                        model="",
                        total_cost=0,
                        tokens_prompt=0,
                        tokens_completion=0,
                    ),
                )
