"""
Роутер для OpenRouter Credits и Analytics API.

API Reference:
- https://openrouter.ai/docs/api/api-reference/credits/get-credits
- https://openrouter.ai/docs/api/api-reference/analytics/get-user-activity
"""

from fastapi import Query, status

from app.core.dependencies.system_settings import AISettingsServiceDep
from app.core.security import CurrentAdminDep
from app.schemas.v1.openrouter import (
    AnalyticsResponseSchema,
    CreditsResponseSchema,
    OpenRouterCreditsSchema,
)

from .base import BaseOpenRouterRouter


class AdminOpenRouterCreditsRouter(BaseOpenRouterRouter):
    """
    Роутер для работы с кредитами и аналитикой OpenRouter.

    Endpoints:
        GET /admin/openrouter/credits - Баланс кредитов
        GET /admin/openrouter/credits/analytics - Аналитика использования
    """

    def __init__(self):
        """Инициализирует роутер."""
        super().__init__(prefix="admin/openrouter/credits", tags=["Admin - OpenRouter Credits"])

    def configure(self):
        """Настройка endpoint'ов."""

        @self.router.get(
            path="",
            response_model=CreditsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 💰 Баланс кредитов

Возвращает текущий баланс кредитов OpenRouter.

**OpenRouter API:** [GET /credits](https://openrouter.ai/docs/api/api-reference/credits/get-credits)

### Returns:
- Общая сумма кредитов
- Использовано
- Остаток
- Валюта (USD)
""",
        )
        async def get_credits(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> CreditsResponseSchema:
            """Получает баланс кредитов."""
            try:
                client = await self._get_client(service)
                credits = await client.get_credits()

                return CreditsResponseSchema(
                    success=True,
                    message=f"Остаток: ${credits.remaining_credits:.4f}",
                    data=credits,
                )
            except ValueError as e:
                return CreditsResponseSchema(
                    success=False,
                    message=str(e),
                    data=OpenRouterCreditsSchema(
                        total_credits=0,
                        usage_credits=0,
                        remaining_credits=0,
                    ),
                )

        @self.router.get(
            path="/analytics",
            response_model=AnalyticsResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 📈 Аналитика использования

Возвращает статистику использования API.

**OpenRouter API:** [GET /analytics](https://openrouter.ai/docs/api/api-reference/analytics/get-user-activity)

### Query Parameters:
- **period** — Период группировки (hour, day, week, month)
- **limit** — Максимум записей

### Returns:
- Endpoint
- Количество запросов
- Токены (prompt/completion)
- Стоимость
- Период
""",
        )
        async def get_analytics(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
            period: str = Query(default="day", description="Период (hour, day, week, month)"),
            limit: int = Query(default=100, ge=1, le=1000, description="Максимум записей"),
        ) -> AnalyticsResponseSchema:
            """Получает аналитику использования."""
            try:
                client = await self._get_client(service)
                analytics = await client.get_analytics(period=period, limit=limit)

                return AnalyticsResponseSchema(
                    success=True,
                    message=f"Аналитика за период {period} ({len(analytics)} записей)",
                    data=analytics,
                )
            except ValueError as e:
                return AnalyticsResponseSchema(
                    success=False,
                    message=str(e),
                    data=[],
                )
