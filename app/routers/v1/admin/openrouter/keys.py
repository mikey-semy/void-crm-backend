"""
Роутер для OpenRouter API Keys.

API Reference:
- https://openrouter.ai/docs/api/api-reference/api-keys/list
- https://openrouter.ai/docs/api/api-reference/api-keys/create-keys
- https://openrouter.ai/docs/api/api-reference/api-keys/get-key
- https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key
- https://openrouter.ai/docs/api/api-reference/api-keys/update-keys
- https://openrouter.ai/docs/api/api-reference/api-keys/delete-keys
"""

from fastapi import Path, status

from app.core.dependencies.system_settings import AISettingsServiceDep
from app.core.security import CurrentAdminDep
from app.schemas.v1.openrouter import (
    ApiKeyCreatedResponseSchema,
    ApiKeyCreateRequestSchema,
    ApiKeyDeletedResponseSchema,
    ApiKeyResponseSchema,
    ApiKeysResponseSchema,
    ApiKeyUpdateRequestSchema,
    OpenRouterApiKeySchema,
)

from .base import BaseOpenRouterRouter


class AdminOpenRouterKeysRouter(BaseOpenRouterRouter):
    """
    Роутер для управления API ключами OpenRouter.

    Endpoints:
        GET /admin/openrouter/keys - Список ключей
        POST /admin/openrouter/keys - Создать ключ
        GET /admin/openrouter/keys/current - Текущий ключ
        GET /admin/openrouter/keys/{key_id} - Получить ключ
        PATCH /admin/openrouter/keys/{key_id} - Обновить ключ
        DELETE /admin/openrouter/keys/{key_id} - Удалить ключ
    """

    def __init__(self):
        """Инициализирует роутер."""
        super().__init__(prefix="admin/openrouter/keys", tags=["Admin - OpenRouter API Keys"])

    def configure(self):
        """Настройка endpoint'ов."""

        @self.router.get(
            path="",
            response_model=ApiKeysResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🔐 Список API ключей

Возвращает список всех API ключей в аккаунте.

**OpenRouter API:** [GET /keys](https://openrouter.ai/docs/api/api-reference/api-keys/list)

### Returns:
- ID ключа
- Название
- Префикс ключа
- Дата создания
- Последнее использование
- Статус активности
- Лимит запросов в минуту
""",
        )
        async def get_api_keys(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> ApiKeysResponseSchema:
            """Получает список API ключей."""
            try:
                client = await self._get_client(service)
                keys = await client.get_api_keys()

                return ApiKeysResponseSchema(
                    success=True,
                    message=f"Найдено {len(keys)} ключей",
                    data=keys,
                )
            except ValueError as e:
                return ApiKeysResponseSchema(
                    success=False,
                    message=str(e),
                    data=[],
                )

        @self.router.post(
            path="",
            response_model=ApiKeyCreatedResponseSchema,
            status_code=status.HTTP_201_CREATED,
            description="""\
## ➕ Создать API ключ

Создаёт новый API ключ в аккаунте OpenRouter.

**OpenRouter API:** [POST /keys](https://openrouter.ai/docs/api/api-reference/api-keys/create-keys)

### Request Body:
- **name** — Название ключа (обязательно)
- **limit_per_minute** — Лимит запросов в минуту (опционально)
- **credit_limit** — Лимит кредитов (опционально)

### Returns:
- Созданный ключ (**показывается только один раз!**)

⚠️ **Важно:** Сохраните ключ сразу после создания!
""",
        )
        async def create_api_key(
            data: ApiKeyCreateRequestSchema,
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> ApiKeyCreatedResponseSchema:
            """Создаёт новый API ключ."""
            try:
                client = await self._get_client(service)
                result = await client.create_api_key(
                    name=data.name,
                    limit_per_minute=data.limit_per_minute,
                )

                return ApiKeyCreatedResponseSchema(
                    success=True,
                    message="API ключ создан. Сохраните его - он показывается только один раз!",
                    data=result,
                )
            except ValueError as e:
                return ApiKeyCreatedResponseSchema(
                    success=False,
                    message=str(e),
                    data={},
                )

        @self.router.get(
            path="/current",
            response_model=ApiKeyResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🔑 Текущий API ключ

Возвращает информацию о текущем используемом API ключе.

**OpenRouter API:** [GET /keys/current](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key)
""",
        )
        async def get_current_key(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
        ) -> ApiKeyResponseSchema:
            """Получает информацию о текущем ключе."""
            try:
                client = await self._get_client(service)
                key_info = await client.get_current_api_key()

                return ApiKeyResponseSchema(
                    success=True,
                    message="Информация о текущем ключе",
                    data=key_info,
                )
            except ValueError as e:
                return ApiKeyResponseSchema(
                    success=False,
                    message=str(e),
                    data=OpenRouterApiKeySchema(
                        id="",
                        name="",
                        key_prefix="",
                        is_active=False,
                    ),
                )

        @self.router.get(
            path="/{key_id}",
            response_model=ApiKeyResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🔍 Получить API ключ

Возвращает информацию о конкретном API ключе.

**OpenRouter API:** [GET /keys/{id}](https://openrouter.ai/docs/api/api-reference/api-keys/get-key)

### Path Parameters:
- **key_id** — ID ключа
""",
        )
        async def get_api_key(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
            key_id: str = Path(..., description="ID ключа"),
        ) -> ApiKeyResponseSchema:
            """Получает информацию о ключе."""
            try:
                client = await self._get_client(service)
                key_info = await client.get_api_key(key_id)

                return ApiKeyResponseSchema(
                    success=True,
                    message=f"Ключ {key_id}",
                    data=key_info,
                )
            except ValueError as e:
                return ApiKeyResponseSchema(
                    success=False,
                    message=str(e),
                    data=OpenRouterApiKeySchema(
                        id=key_id,
                        name="",
                        key_prefix="",
                        is_active=False,
                    ),
                )

        @self.router.patch(
            path="/{key_id}",
            response_model=ApiKeyResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## ✏️ Обновить API ключ

Обновляет параметры API ключа.

**OpenRouter API:** [PATCH /keys/{id}](https://openrouter.ai/docs/api/api-reference/api-keys/update-keys)

### Path Parameters:
- **key_id** — ID ключа

### Request Body:
- **name** — Новое название (опционально)
- **is_disabled** — Отключить ключ (опционально)
- **limit_per_minute** — Новый лимит (опционально)
- **credit_limit** — Новый лимит кредитов (опционально)
""",
        )
        async def update_api_key(
            data: ApiKeyUpdateRequestSchema,
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
            key_id: str = Path(..., description="ID ключа"),
        ) -> ApiKeyResponseSchema:
            """Обновляет API ключ."""
            try:
                client = await self._get_client(service)
                key_info = await client.update_api_key(
                    key_id=key_id,
                    name=data.name,
                    is_active=not data.is_disabled if data.is_disabled is not None else None,
                    limit_per_minute=data.limit_per_minute,
                )

                return ApiKeyResponseSchema(
                    success=True,
                    message=f"Ключ {key_id} обновлён",
                    data=key_info,
                )
            except ValueError as e:
                return ApiKeyResponseSchema(
                    success=False,
                    message=str(e),
                    data=OpenRouterApiKeySchema(
                        id=key_id,
                        name="",
                        key_prefix="",
                        is_active=False,
                    ),
                )

        @self.router.delete(
            path="/{key_id}",
            response_model=ApiKeyDeletedResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🗑️ Удалить API ключ

Удаляет API ключ из аккаунта.

**OpenRouter API:** [DELETE /keys/{id}](https://openrouter.ai/docs/api/api-reference/api-keys/delete-keys)

### Path Parameters:
- **key_id** — ID ключа

⚠️ **Внимание:** Это действие необратимо!
""",
        )
        async def delete_api_key(
            service: AISettingsServiceDep,
            current_admin: CurrentAdminDep,
            key_id: str = Path(..., description="ID ключа"),
        ) -> ApiKeyDeletedResponseSchema:
            """Удаляет API ключ."""
            try:
                client = await self._get_client(service)
                success = await client.delete_api_key(key_id)

                if success:
                    return ApiKeyDeletedResponseSchema(
                        success=True,
                        message=f"Ключ {key_id} удалён",
                        data={"deleted": True, "key_id": key_id},
                    )
                else:
                    return ApiKeyDeletedResponseSchema(
                        success=False,
                        message=f"Не удалось удалить ключ {key_id}",
                        data={"deleted": False, "key_id": key_id},
                    )
            except ValueError as e:
                return ApiKeyDeletedResponseSchema(
                    success=False,
                    message=str(e),
                    data={"deleted": False, "key_id": key_id},
                )
