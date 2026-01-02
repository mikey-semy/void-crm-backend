"""
Сервис для работы с JWT токенами.

Предоставляет методы для:
- Создания access токенов
- Создания refresh токенов
- Сохранения токенов в Redis
- Валидации токенов
- Удаления токенов

Используется в AuthService, RegisterService и других сервисах,
где требуется работа с токенами.
"""

import logging
from uuid import UUID

from redis.asyncio import Redis

from app.core.integrations.cache.auth import AuthRedisManager
from app.core.security import TokenManager
from app.schemas.v1.auth import UserCredentialsSchema
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class TokenService(BaseService):
    """
    Сервис для работы с JWT токенами.

    Централизованное управление созданием, валидацией и хранением токенов.
    Использует TokenManager для генерации и AuthRedisManager для кэширования.

    Attributes:
        redis: Клиент Redis для хранения токенов.
        redis_manager: Менеджер для работы с токенами в Redis.

    Example:
        >>> token_service = TokenService(redis=redis)
        >>> access_token = await token_service.create_access_token(user_credentials)
        >>> refresh_token = await token_service.create_refresh_token(user_id)
    """

    def __init__(self, redis: Redis):
        """
        Инициализация TokenService.

        Args:
            redis: Клиент Redis для работы с токенами.
        """
        # TokenService не работает с БД, поэтому session=None
        super().__init__(session=None)
        self.redis = redis
        self.redis_manager = AuthRedisManager(redis)

    async def create_access_token(self, user_schema: UserCredentialsSchema) -> str:
        """
        Создание JWT access токена с сохранением в Redis.

        Генерирует JWT access токен на основе данных пользователя
        и сохраняет его в Redis для последующей валидации.

        Args:
            user_schema: Схема с учетными данными пользователя.

        Returns:
            str: Сгенерированный access токен.

        Example:
            >>> user_creds = UserCredentialsSchema(id=uuid, email="user@ex.com", ...)
            >>> token = await token_service.create_access_token(user_creds)
            >>> print(token)  # "eyJ0eXAiOiJKV1QiLC..."
        """
        payload = TokenManager.create_payload(user_schema)
        access_token = TokenManager.generate_token(payload)

        await self.redis_manager.save_token(user_schema, access_token)

        self.logger.info("Access токен создан", extra={"user_id": user_schema.id})

        return access_token

    async def create_refresh_token(self, user_id: UUID) -> str:
        """
        Создание JWT refresh токена с сохранением в Redis.

        Генерирует JWT refresh токен для обновления access токена
        и сохраняет его в Redis для валидации при refresh операции.

        Args:
            user_id: UUID идентификатор пользователя.

        Returns:
            str: Сгенерированный refresh токен.

        Example:
            >>> refresh = await token_service.create_refresh_token(user_id)
            >>> print(refresh)  # "eyJ0eXAiOiJKV1QiLC..."
        """
        payload = TokenManager.create_refresh_payload(user_id)
        refresh_token = TokenManager.generate_token(payload)

        await self.redis_manager.save_refresh_token(user_id, refresh_token)

        self.logger.info("Refresh токен создан", extra={"user_id": user_id})

        return refresh_token

    async def validate_refresh_token(self, refresh_token: str) -> UUID:
        """
        Валидация refresh токена.

        Проверяет refresh токен на корректность и наличие в Redis.

        Args:
            refresh_token: Refresh токен для валидации.

        Returns:
            UUID: ID пользователя из токена.

        Raises:
            TokenInvalidError: Если токен невалиден или отсутствует в Redis.
            TokenExpiredError: Если токен истек.

        Example:
            >>> user_id = await token_service.validate_refresh_token(token)
        """
        payload = TokenManager.decode_token(refresh_token)
        user_id = TokenManager.validate_refresh_token(payload)

        # Проверяем наличие токена в Redis
        if not await self.redis_manager.check_refresh_token(user_id, refresh_token):
            self.logger.warning(
                "Попытка использовать неизвестный refresh токен",
                extra={"user_id": user_id},
            )
            from app.core.exceptions import TokenInvalidError

            raise TokenInvalidError()

        return user_id

    async def remove_token(self, token: str) -> None:
        """
        Удаление токена из Redis (logout).

        Args:
            token: Access токен для удаления.

        Example:
            >>> await token_service.remove_token(access_token)
        """
        await self.redis_manager.remove_token(token)
        self.logger.info("Токен удален из Redis")

    async def remove_refresh_token(self, user_id: UUID, refresh_token: str) -> None:
        """
        Удаление refresh токена из Redis.

        Args:
            user_id: ID пользователя.
            refresh_token: Refresh токен для удаления.

        Example:
            >>> await token_service.remove_refresh_token(user_id, old_refresh)
        """
        await self.redis_manager.remove_refresh_token(user_id, refresh_token)
        self.logger.info("Refresh токен удален", extra={"user_id": user_id})
