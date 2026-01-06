"""
Сервис для работы с настройками пользователей.

Модуль предоставляет:
- UserAccessTokenService - управление токенами доступа для MCP
"""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import PasswordManager
from app.models.v1 import UserAccessTokenModel
from app.repository.v1.user_settings import UserAccessTokenRepository
from app.services.base import BaseService


class UserAccessTokenService(BaseService):
    """
    Сервис для управления токенами доступа пользователей.

    Токены используются для аутентификации MCP сервера к API.
    Генерируются с префиксом и хешируются для безопасного хранения.
    """

    # Префикс для токенов (void_)
    TOKEN_PREFIX = "void_"
    # Длина случайной части токена
    TOKEN_LENGTH = 32

    def __init__(self, session: AsyncSession):
        """
        Инициализирует сервис.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session)
        self.repository = UserAccessTokenRepository(session)
        self.password_manager = PasswordManager()

    def _generate_token(self) -> tuple[str, str, str]:
        """
        Генерирует новый токен.

        Returns:
            tuple[full_token, token_hash, token_display_prefix]
        """
        # Генерируем случайную часть
        random_part = secrets.token_urlsafe(self.TOKEN_LENGTH)
        full_token = f"{self.TOKEN_PREFIX}{random_part}"

        # Хешируем для хранения
        token_hash = self.password_manager.hash_password(full_token)

        # Префикс для отображения (первые 12 символов)
        display_prefix = full_token[:12]

        return full_token, token_hash, display_prefix

    async def get_user_tokens(
        self,
        user_id: UUID,
        include_expired: bool = False,
    ) -> list[UserAccessTokenModel]:
        """
        Получает токены пользователя.

        Args:
            user_id: UUID пользователя
            include_expired: Включать истёкшие токены

        Returns:
            Список токенов (без хешей)
        """
        return await self.repository.get_user_tokens(
            user_id=user_id,
            active_only=not include_expired,
        )

    async def get_token_by_id(
        self,
        token_id: UUID,
        user_id: UUID,
    ) -> UserAccessTokenModel:
        """
        Получает токен по ID.

        Args:
            token_id: UUID токена
            user_id: UUID пользователя (для проверки владельца)

        Returns:
            UserAccessTokenModel

        Raises:
            NotFoundError: Если токен не найден
        """
        token = await self.repository.get_item_by_id(token_id)

        if not token or token.user_id != user_id:
            raise NotFoundError(
                detail="Токен не найден",
                field="id",
                value=str(token_id),
            )

        return token

    async def create_token(
        self,
        user_id: UUID,
        name: str,
        expires_in_days: int | None = None,
    ) -> tuple[UserAccessTokenModel, str]:
        """
        Создаёт новый токен доступа.

        Args:
            user_id: UUID пользователя
            name: Название токена
            expires_in_days: Срок действия в днях (None = бессрочный)

        Returns:
            tuple[созданный токен, полный токен для отображения]
            ВАЖНО: полный токен показывается только один раз!
        """
        full_token, token_hash, display_prefix = self._generate_token()

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        token = await self.repository.create_item({
            "user_id": user_id,
            "token_hash": token_hash,
            "token_prefix": display_prefix,
            "name": name,
            "is_active": True,
            "expires_at": expires_at,
        })

        self.logger.info(
            "Создан токен доступа для пользователя %s: %s",
            user_id,
            display_prefix,
        )

        return token, full_token

    async def verify_token(
        self,
        full_token: str,
        ip_address: str | None = None,
    ) -> UserAccessTokenModel | None:
        """
        Проверяет токен и возвращает информацию о нём.

        Используется при аутентификации MCP запросов.

        Args:
            full_token: Полный токен (void_...)
            ip_address: IP адрес запроса

        Returns:
            UserAccessTokenModel если токен валиден, иначе None
        """
        if not full_token.startswith(self.TOKEN_PREFIX):
            return None

        # Получаем префикс для поиска
        display_prefix = full_token[:12]

        # Ищем токен в БД
        token = await self.repository.get_valid_token(display_prefix)

        if not token:
            return None

        # Проверяем хеш
        if not self.password_manager.verify_password(full_token, token.token_hash):
            return None

        # Обновляем время использования
        await self.repository.update_last_used(token.id, ip_address)

        return token

    async def revoke_token(
        self,
        token_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Отзывает токен.

        Args:
            token_id: UUID токена
            user_id: UUID пользователя

        Raises:
            NotFoundError: Если токен не найден
        """
        token = await self.get_token_by_id(token_id, user_id)

        await self.repository.update_item(token.id, {"is_active": False})

        self.logger.info(
            "Отозван токен %s пользователя %s",
            token.token_prefix,
            user_id,
        )

    async def revoke_all_tokens(self, user_id: UUID) -> int:
        """
        Отзывает все токены пользователя.

        Args:
            user_id: UUID пользователя

        Returns:
            Количество отозванных токенов
        """
        count = await self.repository.revoke_all_user_tokens(user_id)

        self.logger.info(
            "Отозваны все токены (%d) пользователя %s",
            count,
            user_id,
        )

        return count
