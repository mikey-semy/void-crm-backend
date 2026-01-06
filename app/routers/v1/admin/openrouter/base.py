"""Базовый класс для OpenRouter роутеров."""

from app.core.dependencies.system_settings import AISettingsServiceDep
from app.core.integrations.ai import OpenRouterClient
from app.core.settings import settings
from app.routers.base import ProtectedRouter
from app.services.v1.system_settings import AISettingsService


class BaseOpenRouterRouter(ProtectedRouter):
    """
    Базовый роутер для OpenRouter endpoints.

    Предоставляет общий метод для создания клиента.
    """

    async def _get_client(self, service: AISettingsService) -> OpenRouterClient:
        """
        Создаёт OpenRouter клиент с ключом из настроек.

        Args:
            service: Сервис AI настроек

        Returns:
            OpenRouterClient

        Raises:
            ValueError: Если API ключ не настроен
        """
        api_key = await service.get_decrypted_api_key()

        if not api_key:
            raise ValueError("API ключ не настроен. Настройте ключ в AI настройках.")

        return OpenRouterClient(
            api_key=api_key,
            base_url=settings.ai.OPENROUTER_BASE_URL,
            site_url=settings.ai.OPENROUTER_SITE_URL,
            app_name=settings.ai.OPENROUTER_APP_NAME,
            timeout=settings.ai.OPENROUTER_TIMEOUT,
        )
