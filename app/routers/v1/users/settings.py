"""
Роутер для настроек пользователя.

Модуль предоставляет HTTP API для управления:
- Токенами доступа пользователя (для MCP интеграции)

Все endpoints защищены через ProtectedRouter.
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status

from app.core.dependencies.user_settings import UserAccessTokenServiceDep
from app.core.security import CurrentUserDep
from app.routers.base import ProtectedRouter
from app.schemas.v1.user_settings import (
    EXPIRATION_OPTIONS,
    AccessTokenCreatedResponseSchema,
    AccessTokenCreatedSchema,
    AccessTokenCreateSchema,
    AccessTokenDetailSchema,
    AccessTokenListResponseSchema,
    AccessTokenListSchema,
    AccessTokenRevokedResponseSchema,
    AccessTokenRevokedSchema,
)


class UserSettingsRouter(ProtectedRouter):
    """
    Роутер для настроек пользователя.

    Protected Endpoints:
        GET /users/me/access-tokens - Список токенов
        POST /users/me/access-tokens - Создать токен
        DELETE /users/me/access-tokens/{token_id} - Отозвать токен
        DELETE /users/me/access-tokens - Отозвать все токены
    """

    def __init__(self):
        """Инициализирует роутер."""
        super().__init__(prefix="users/me", tags=["User Settings"])

    def configure(self):
        """Настройка endpoint'ов."""

        # ==================== ACCESS TOKENS ====================

        @self.router.get(
            path="/access-tokens",
            response_model=AccessTokenListResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🔑 Получить список токенов доступа

Возвращает все активные токены текущего пользователя.
Токены используются для аутентификации MCP сервера.

### Returns:
- Список токенов с метаданными (без полных значений)
""",
        )
        async def get_access_tokens(
            service: UserAccessTokenServiceDep,
            current_user: CurrentUserDep,
        ) -> AccessTokenListResponseSchema:
            """Получает список токенов доступа пользователя."""
            tokens = await service.get_user_tokens(current_user.id)

            token_schemas = [
                AccessTokenDetailSchema(
                    id=token.id,
                    name=token.name,
                    token_prefix=token.token_prefix,
                    is_active=token.is_active,
                    expires_at=token.expires_at,
                    last_used_at=token.last_used_at,
                    last_used_ip=token.last_used_ip,
                    created_at=token.created_at,
                )
                for token in tokens
            ]

            return AccessTokenListResponseSchema(
                success=True,
                message="Токены получены",
                data=AccessTokenListSchema(
                    tokens=token_schemas,
                    total=len(token_schemas),
                ),
            )

        @self.router.post(
            path="/access-tokens",
            response_model=AccessTokenCreatedResponseSchema,
            status_code=status.HTTP_201_CREATED,
            description="""\
## ➕ Создать токен доступа

Создаёт новый токен для аутентификации MCP сервера.

**ВАЖНО**: Полный токен показывается только один раз при создании!
Сохраните его сразу, так как после этого увидеть его будет невозможно.

### Request Body:
- **name** — Название токена для идентификации
- **expires_in_days** — Срок действия в днях (пусто = бессрочный)

### Returns:
- Созданный токен с полным значением (void_...)
""",
        )
        async def create_access_token(
            data: AccessTokenCreateSchema,
            service: UserAccessTokenServiceDep,
            current_user: CurrentUserDep,
        ) -> AccessTokenCreatedResponseSchema:
            """Создаёт токен доступа."""
            token, full_token = await service.create_token(
                user_id=current_user.id,
                name=data.name,
                expires_in_days=data.expires_in_days,
            )

            return AccessTokenCreatedResponseSchema(
                success=True,
                message="Токен создан. Сохраните его — он показывается только один раз!",
                data=AccessTokenCreatedSchema(
                    id=token.id,
                    name=token.name,
                    token_prefix=token.token_prefix,
                    is_active=token.is_active,
                    expires_at=token.expires_at,
                    last_used_at=token.last_used_at,
                    last_used_ip=token.last_used_ip,
                    created_at=token.created_at,
                    full_token=full_token,
                ),
            )

        @self.router.delete(
            path="/access-tokens/{token_id}",
            response_model=AccessTokenRevokedResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🗑️ Отозвать токен

Отзывает (деактивирует) токен доступа. После отзыва токен перестаёт работать.

### Path Parameters:
- **token_id** — UUID токена

### Returns:
- Подтверждение отзыва
""",
        )
        async def revoke_access_token(
            token_id: UUID,
            service: UserAccessTokenServiceDep,
            current_user: CurrentUserDep,
        ) -> AccessTokenRevokedResponseSchema:
            """Отзывает токен доступа."""
            token = await service.get_token_by_id(token_id, current_user.id)
            token_prefix = token.token_prefix

            await service.revoke_token(token_id, current_user.id)

            return AccessTokenRevokedResponseSchema(
                success=True,
                message="Токен отозван",
                data=AccessTokenRevokedSchema(
                    id=token_id,
                    token_prefix=token_prefix,
                    revoked_at=datetime.now(UTC),
                ),
            )

        @self.router.delete(
            path="/access-tokens",
            response_model=AccessTokenRevokedResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""\
## 🗑️ Отозвать все токены

Отзывает все активные токены пользователя.
Используйте с осторожностью!

### Returns:
- Количество отозванных токенов
""",
        )
        async def revoke_all_access_tokens(
            service: UserAccessTokenServiceDep,
            current_user: CurrentUserDep,
        ) -> AccessTokenRevokedResponseSchema:
            """Отзывает все токены пользователя."""
            count = await service.revoke_all_tokens(current_user.id)

            return AccessTokenRevokedResponseSchema(
                success=True,
                message=f"Отозвано токенов: {count}",
                data=AccessTokenRevokedSchema(
                    id=current_user.id,  # Используем ID пользователя
                    token_prefix="all",
                    revoked_at=datetime.now(UTC),
                ),
            )

        # ==================== СПРАВОЧНИКИ ====================

        @self.router.get(
            path="/access-tokens/expiration-options",
            status_code=status.HTTP_200_OK,
            description="""\
## 📋 Варианты срока действия

Возвращает доступные варианты срока действия токена.
""",
        )
        async def get_expiration_options(
            current_user: CurrentUserDep,
        ) -> dict:
            """Возвращает варианты срока действия."""
            return {
                "success": True,
                "message": "Варианты получены",
                "data": EXPIRATION_OPTIONS,
            }
