"""
Репозиторий для работы с настройками пользователей.

Модуль предоставляет:
- UserAccessTokenRepository - CRUD для токенов доступа

Использует базовые методы BaseRepository согласно документации.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.v1 import UserAccessTokenModel
from app.repository.base import BaseRepository


class UserAccessTokenRepository(BaseRepository[UserAccessTokenModel]):
    """
    Репозиторий для работы с токенами доступа пользователей.

    Предоставляет методы для CRUD операций с токенами для MCP интеграции.
    Использует базовые методы BaseRepository где возможно.
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session, UserAccessTokenModel)

    async def get_user_tokens(
        self,
        user_id: UUID,
        active_only: bool = True,
    ) -> list[UserAccessTokenModel]:
        """
        Получает токены доступа пользователя.

        Args:
            user_id: UUID пользователя
            active_only: Только активные токены

        Returns:
            Список токенов

        Note:
            Сложная логика с проверкой expires_at требует custom query,
            т.к. filter_by не поддерживает OR условия.
        """
        query = select(UserAccessTokenModel).where(
            UserAccessTokenModel.user_id == user_id
        )

        if active_only:
            query = query.where(UserAccessTokenModel.is_active == True)  # noqa: E712
            # Также проверяем срок действия
            query = query.where(
                (UserAccessTokenModel.expires_at.is_(None)) |
                (UserAccessTokenModel.expires_at > datetime.now(UTC))
            )

        query = query.order_by(UserAccessTokenModel.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_valid_token(
        self,
        token_prefix: str,
    ) -> UserAccessTokenModel | None:
        """
        Получает валидный (активный и не истёкший) токен по префиксу.

        Args:
            token_prefix: Префикс токена

        Returns:
            Токен или None
        """
        # Используем filter_by для получения активного токена
        tokens = await self.filter_by(
            token_prefix=token_prefix,
            is_active=True,
            limit=1,
        )

        if not tokens:
            return None

        token = tokens[0]

        # Проверяем срок действия
        if token.expires_at and token.expires_at < datetime.now(UTC):
            return None

        return token

    async def update_last_used(
        self,
        token_id: UUID,
        ip_address: str | None = None,
    ) -> None:
        """
        Обновляет время последнего использования токена.

        Использует update_item из BaseRepository.

        Args:
            token_id: UUID токена
            ip_address: IP адрес запроса
        """
        update_data = {"last_used_at": datetime.now(UTC)}
        if ip_address:
            update_data["last_used_ip"] = ip_address

        await self.update_item(token_id, update_data)

    async def revoke_token(self, token_id: UUID, user_id: UUID) -> bool:
        """
        Отзывает токен (деактивирует).

        Args:
            token_id: UUID токена
            user_id: UUID пользователя (для проверки владельца)

        Returns:
            True если токен отозван
        """
        token = await self.get_item_by_id(token_id)

        if not token or token.user_id != user_id:
            return False

        await self.update_item(token_id, {"is_active": False})
        return True

    async def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """
        Отзывает все токены пользователя.

        Args:
            user_id: UUID пользователя

        Returns:
            Количество отозванных токенов
        """
        tokens = await self.get_user_tokens(user_id, active_only=True)

        for token in tokens:
            token.is_active = False

        if tokens:
            await self.session.commit()

        return len(tokens)
