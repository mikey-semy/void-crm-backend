"""
Репозиторий для работы с пользователями.

Обеспечивает доступ к данным пользователей для операций аутентификации
и управления пользователями. Максимально использует наследование от BaseRepository.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.settings import settings
from app.models.v1.users import UserModel
from app.models.v1.roles import RoleCode, UserRoleModel
from app.repository.cache import CacheBackend
from app.repository.base import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """
    Репозиторий для работы с пользователями.

    Наследует все CRUD операции от BaseRepository:
    - create_item, get_item_by_id, update_item, delete_item
    - get_item_by_field, get_item_by_fields_or, exists_by_field
    - filter_by, create_with_related

    Автоматически загружает user_roles для всех запросов.
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        super().__init__(session, UserModel, cache_backend, enable_tracing)

    # Автозагрузка ролей для всех запросов
    default_options = [
        selectinload(UserModel.user_roles),
    ]

    async def get_item_by_id(
        self, item_id: UUID, options: list[Any] | None = None
    ) -> UserModel | None:
        """
        Получение пользователя по ID с автозагрузкой ролей.

        Переопределяет базовый метод для применения default_options.
        Параметр options игнорируется - всегда используются default_options.

        Args:
            item_id: UUID пользователя.
            options: Игнорируется (для совместимости с базовым классом).

        Returns:
            UserModel с загруженными user_roles или None.
        """
        return await super().get_item_by_id(item_id, options=self.default_options)

    async def get_item_by_field(
        self,
        field_name: str,
        field_value: Any,
        options: list[Any] | None = None,
    ) -> UserModel | None:
        """
        Получение пользователя по полю с автозагрузкой ролей.

        Переопределяет базовый метод для применения default_options.
        Параметр options игнорируется - всегда используются default_options.

        Args:
            field_name: Название поля.
            field_value: Значение поля.
            options: Игнорируется (для совместимости с базовым классом).

        Returns:
            UserModel с загруженными user_roles или None.
        """
        return await super().get_item_by_field(
            field_name, field_value, options=self.default_options
        )

    async def get_user_by_identifier(self, identifier: str) -> UserModel | None:
        """
        Получение пользователя по email, телефону или username (nickname).

        Автоматически определяет тип идентификатора:
        - Если содержит @ - ищет по email
        - Если начинается с + - ищет по телефону
        - Иначе - ищет по username (nickname)

        Args:
            identifier: email, телефон или username пользователя.

        Returns:
            UserModel с загруженными ролями и компанией или None.

        Example:
            >>> user = await repo.get_user_by_identifier("user@example.com")
            >>> role = user.role  # ✅ Роли уже загружены
            >>> user = await repo.get_user_by_identifier("john_doe")  # По username
            >>> user = await repo.get_user_by_identifier("+79991234567")  # По телефону
        """
        # Получаем разрешенные типы идентификаторов из настроек
        allowed = set(settings.USERNAME_ALLOWED_TYPES)

        # Email (содержит @)
        if "email" in allowed and "@" in identifier:
            return await self.get_item_by_field_cached("email", identifier)

        # Phone (начинается с +)
        if "phone" in allowed and identifier.startswith("+"):
            return await self.get_item_by_field_cached("phone", identifier)

        # Username (nickname) - по умолчанию
        if "username" in allowed:
            return await self.get_item_by_field_cached("username", identifier)

        # Если ничего не подошло — пользователь не найден
        return None

    async def create_item(
        self,
        data: dict[str, Any],
        commit: bool = True,
        options: list[Any] | None = None,
        refresh: bool = True,
    ) -> UserModel:
        """
        Создать пользователя и автоматически сбросить кеш.

        Args:
            data: Данные для создания пользователя.
            commit: Если True - делает commit после создания.
            options: Опции загрузки relationships.
            refresh: Выполнять ли refresh созданной записи.

        Returns:
            UserModel: Созданный пользователь.

        Raises:
            SQLAlchemyError: Если произошла ошибка при создании.
        """
        item = await super().create_item(data, commit, options, refresh)
        await self._invalidate_cache()
        return item

    async def update_item(
        self,
        item_id: UUID,
        data: dict[str, Any],
        options: list[Any] | None = None,
        refresh: bool = True,
    ) -> UserModel | None:
        """
        Обновить пользователя и автоматически сбросить кеш.

        Args:
            item_id: UUID пользователя для обновления.
            data: Данные для обновления.
            options: Опции загрузки relationships (по умолчанию используются default_options).
            refresh: Выполнять ли refresh после commit.

        Returns:
            Optional[UserModel]: Обновленный пользователь или None, если не найден.

        Raises:
            SQLAlchemyError: Если произошла ошибка при обновлении.
        """
        item = await super().update_item(item_id, data, options, refresh)
        await self._invalidate_cache()
        return item

    async def delete_item(self, item_id: UUID) -> bool:
        """
        Удалить пользователя и автоматически сбросить кеш.

        Args:
            item_id: UUID пользователя для удаления.

        Returns:
            bool: True если пользователь был удален, False если не найден.

        Raises:
            SQLAlchemyError: Если произошла ошибка при удалении.
        """
        result = await super().delete_item(item_id)
        if result:
            await self._invalidate_cache()
        return result

    async def get_user_by_identifier_with_roles(
        self, identifier: str
    ) -> UserModel | None:
        """
        Получение пользователя по email/phone/username с загруженными ролями и компанией.

        Алиас для get_user_by_identifier (для обратной совместимости).
        Роли и компания загружаются автоматически через default_options.

        Args:
            identifier: email, телефон или имя пользователя.

        Returns:
            UserModel с загруженными user_roles или None.

        Example:
            >>> user = await repo.get_user_by_identifier_with_roles("user@example.com")
            >>> role = user.role  # ✅ Не вызывает lazy load
            >>> company_name = user.company.name  # ✅ Не вызывает lazy load
        """
        return await self.get_user_by_identifier(identifier)

    async def get_user_with_roles(self, user_id: UUID) -> UserModel | None:
        """
        Получение пользователя по ID с загруженными ролями и компанией.

        Алиас для get_item_by_id (для обратной совместимости).
        Роли и компания загружаются автоматически через default_options.

        Args:
            user_id: UUID пользователя.

        Returns:
            UserModel с загруженными user_roles или None.

        Example:
            >>> user = await repo.get_user_with_roles(user_id)
            >>> role = user.role  # ✅ Не вызывает lazy load
            >>> company_name = user.company.name  # ✅ Не вызывает lazy load
        """
        return await self.get_item_by_id(user_id)

    async def find_by_email_or_username(
        self, email: str, username: str
    ) -> UserModel | None:
        """
        Поиск пользователя по email ИЛИ username.

        Используется для валидации уникальности при регистрации.
        Делегирует работу базовому методу get_item_by_fields_or().

        Args:
            email: Email для проверки.
            username: Username для проверки.

        Returns:
            UserModel если найден пользователь с таким email или username,
            None если оба поля свободны.

        Example:
            >>> existing = await repo.find_by_email_or_username(
            ...     "test@example.com", "testuser"
            ... )
            >>> if existing:
            ...     print(f"Занято поле: {existing.email or existing.username}")
        """
        return await self.get_item_by_fields_or(email=email, username=username)

    async def create_user_with_role(self, user_data: dict, role_code: str) -> UserModel:
        """
        Создать пользователя и присвоить ему роль в одной транзакции.

        Атомарная операция создания пользователя и назначения роли.
        Используется при регистрации для гарантии целостности данных.
        Делегирует работу базовому методу create_with_related().

        Args:
            user_data: Данные пользователя для создания
                (username, email, password_hash, company_id, is_active, email_verified).
            role_code: Код роли для присвоения (из RoleCode enum).

        Returns:
            Созданный UserModel с присвоенной ролью.

        Raises:
            SQLAlchemyError: При ошибках работы с БД (откатывает обе операции).

        Example:
            >>> user = await repo.create_user_with_role(
            ...     {
            ...         "username": "john",
            ...         "email": "j@ex.com",
            ...         "password_hash": "hash",
            ...         "company_id": company_id,
            ...         "is_active": True,
            ...         "email_verified": False,
            ...     },
            ...     "user"
            ... )
        """

        return await self.create_with_related(
            main_data=user_data,
            related_items=[
                (UserRoleModel, {"user_id": None, "role_code": role_code})
                # user_id=None будет автоматически заменён на реальный ID
            ],
        )

    async def get_users_by_role(self, role_code: str) -> list[UserModel]:
        """
        Получить всех активных пользователей с определённой ролью.

        Используется для списка администраторов в настройках.

        Args:
            role_code: Код роли (например, "admin").

        Returns:
            Список UserModel с указанной ролью.

        Example:
            >>> admins = await repo.get_users_by_role("admin")
        """

        stmt = (
            select(UserModel)
            .join(UserRoleModel, UserModel.id == UserRoleModel.user_id)
            .where(
                UserRoleModel.role_code == RoleCode(role_code),
                UserModel.is_active == True,  # noqa: E712
            )
            .order_by(UserModel.username)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
