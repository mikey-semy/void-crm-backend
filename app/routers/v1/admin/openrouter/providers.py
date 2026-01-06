"""
Роутер для OpenRouter Providers API.

API Reference:
- https://openrouter.ai/docs/api/api-reference/providers/list-providers
"""

from fastapi import status

from app.core.dependencies.system_settings import AISettingsServiceDep
from app.core.security import CurrentAdminDep
from app.schemas.v1.openrouter import ProvidersResponseSchema

from .base import BaseOpenRouterRouter


class AdminOpenRouterProvidersRouter(BaseOpenRouterRouter):
    """
    Роутер для работы с провайдерами OpenRouter.

    Endpoints:
        GET /admin/openrouter/providers - Список всех провайдеров
    """

    def __init__(self):
        """Инициализирует роутер."""
        super().__init__(prefix="admin/openrouter/providers", tags=["Admin - OpenRouter Providers"])

    def configure(self):
        """Настройка endpoint'ов."""

        @self.router.get(
            path="",
            response_model=ProvidersResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🏢 Список провайдеров

Возвращает список всех провайдеров моделей в OpenRouter.

**OpenRouter API:** [GET /providers](https://openrouter.ai/docs/api/api-reference/providers/list-providers)

### Returns:
- ID провайдера
- Название
- Веб-сайт
- Приоритет
""",
        )
        async def get_providers(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> ProvidersResponseSchema:
            """Получает список провайдеров."""
            try:
                client = await self._get_client(service)
                providers = await client.get_providers()

                return ProvidersResponseSchema(
                    success=True,
                    message=f"Найдено {len(providers)} провайдеров",
                    data=providers,
                )
            except ValueError as e:
                return ProvidersResponseSchema(
                    success=False,
                    message=str(e),
                    data=[],
                )
