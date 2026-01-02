"""
Сервис для управления профилями пользователей.

Модуль предоставляет UserService для работы с профилями пользователей:
- Получение данных профиля текущего пользователя
- Обновление профиля с валидацией уникальности email/phone
- Удаление аккаунта (soft delete через is_active)

КРИТИЧНО: Сервис возвращает только SQLAlchemy модели (UserModel),
конвертация в Pydantic схемы происходит на уровне Router!
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    UserEmailConflictError,
    UserNotFoundError,
    UserPhoneConflictError,
)
from app.models.v1.users import UserModel
from app.repository.v1.users import UserRepository
from app.services.base import BaseService


class UserService(BaseService):
    """
    Сервис для управления профилями пользователей.

    Реализует бизнес-логику работы с пользователями:
    - Получение профиля пользователя
    - Обновление данных профиля с проверкой уникальности
    - Удаление аккаунта (soft delete)

    Attributes:
        repository: Репозиторий для работы с пользователями в БД
        logger: Логгер для отслеживания операций

    Example:
        >>> async with AsyncSession() as session:
        ...     service = UserService(session)
        ...     # Получение профиля
        ...     user = await service.get_profile(user_id)
        ...     print(user.email, user.full_name)
        ...
        ...     # Обновление профиля
        ...     updated = await service.update_profile(user_id, {
        ...         "full_name": "Новое Имя",
        ...         "phone": "+79991234567"
        ...     })
        ...
        ...     # Удаление аккаунта
        ...     deleted = await service.delete_account(user_id)
        ...     assert deleted.is_active is False
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует UserService.

        Args:
            session: Асинхронная сессия SQLAlchemy для работы с БД
        """
        super().__init__(session)
        self.repository = UserRepository(session)

    async def get_profile(self, user_id: UUID) -> UserModel:
        """
        Получает профиль пользователя по ID.

        Args:
            user_id: UUID пользователя

        Returns:
            UserModel: Модель пользователя с данными профиля

        Raises:
            UserNotFoundError: Если пользователь не найден

        Example:
            >>> user = await service.get_profile(user_id)
            >>> print(f"{user.email} - {user.full_name}")
        """
        self.logger.info("Получение профиля пользователя: %s", user_id)

        # Роли и компания загружаются автоматически через default_options
        user = await self.repository.get_item_by_id(user_id)
        if not user:
            self.logger.error("Пользователь не найден: %s", user_id)
            raise UserNotFoundError(field="id", value=str(user_id))

        self.logger.debug("Профиль получен: %s (%s)", user.email, user_id)
        return user

    async def update_profile(self, user_id: UUID, data: dict) -> UserModel:
        """
        Обновляет профиль пользователя с валидацией уникальности.

        Проверяет уникальность email, phone и username если они меняются.
        Игнорирует поля, которые пользователь не может менять сам
        (is_active, role, password_hash).

        Args:
            user_id: UUID пользователя
            data: Словарь с обновляемыми полями
                - username (str, optional): Новый username (nickname)
                - email (str, optional): Новый email
                - full_name (str, optional): Новое ФИО
                - phone (str, optional): Новый телефон
                - position (str, optional): Новая должность
                - company_name (str, optional): Новое название компании
                - inn (str, optional): Новый ИНН компании

        Returns:
            UserModel: Обновленная модель пользователя

        Raises:
            UserNotFoundError: Если пользователь не найден
            UserEmailConflictError: Если email уже занят другим пользователем
            UserPhoneConflictError: Если телефон уже занят другим пользователем
            UserAlreadyExistsError: Если username уже занят другим пользователем

        Example:
            >>> updated = await service.update_profile(user_id, {
            ...     "username": "new_nickname",
            ...     "full_name": "Иванов Иван Иванович",
            ...     "phone": "+79991234567",
            ...     "position": "Менеджер"
            ... })
            >>> print(updated.username)  # "new_nickname"
        """
        from app.core.exceptions import UserAlreadyExistsError

        self.logger.info("Обновление профиля пользователя: %s", user_id)

        # Проверяем существование пользователя
        user = await self.repository.get_item_by_id(user_id)
        if not user:
            self.logger.error("Пользователь не найден: %s", user_id)
            raise UserNotFoundError(field="id", value=str(user_id))

        # Фильтруем защищенные поля (пользователь не может их менять)
        protected_fields = {
            "id",
            "password_hash",
            "is_active",
            "role",
            "created_at",
            "updated_at",
            "email_verified",
            "email_verification_token",
            "password_reset_token",
            "password_reset_expires",
            "last_login_at",
            "login_count",
        }
        update_data = {
            k: v for k, v in data.items() if k not in protected_fields and v is not None
        }

        # Проверяем уникальность username если меняется
        if "username" in update_data and update_data["username"] != user.username:
            existing_username = await self.repository.get_item_by_field(
                "username", update_data["username"]
            )
            if existing_username and existing_username.id != user_id:
                self.logger.error("Username уже занят: %s", update_data["username"])
                raise UserAlreadyExistsError(
                    field="username", value=update_data["username"]
                )

        # Проверяем уникальность email если меняется
        if "email" in update_data and update_data["email"] != user.email:
            existing_email = await self.repository.find_by_email_or_username(
                email=update_data["email"],
                username="",  # Не проверяем username
            )
            if existing_email and existing_email.id != user_id:
                self.logger.error("Email уже занят: %s", update_data["email"])
                raise UserEmailConflictError(email=update_data["email"])

        # Проверяем уникальность phone если меняется
        if "phone" in update_data and update_data["phone"] != user.phone:
            existing_phone = await self.repository.get_item_by_field(
                "phone", update_data["phone"]
            )
            if existing_phone and existing_phone.id != user_id:
                self.logger.error("Телефон уже занят: %s", update_data["phone"])
                raise UserPhoneConflictError(phone=update_data["phone"])

        # Обновляем пользователя
        if not update_data:
            self.logger.warning("Нет данных для обновления профиля: %s", user_id)
            return user

        updated_user = await self.repository.update_item(user_id, update_data)
        if not updated_user:
            self.logger.error("Не удалось обновить профиль: %s", user_id)
            raise UserNotFoundError(field="id", value=str(user_id))

        self.logger.info(
            "Профиль обновлен: %s (обновлено полей: %d)", user_id, len(update_data)
        )
        return updated_user

    async def delete_account(self, user_id: UUID) -> UserModel:
        """
        Удаляет аккаунт пользователя (soft delete).

        Устанавливает is_active=False вместо физического удаления.
        Данные пользователя сохраняются в БД для истории заказов.

        Args:
            user_id: UUID пользователя

        Returns:
            UserModel: Модель деактивированного пользователя

        Raises:
            UserNotFoundError: Если пользователь не найден

        Example:
            >>> deleted = await service.delete_account(user_id)
            >>> assert deleted.is_active is False
        """
        self.logger.info("Удаление аккаунта пользователя: %s", user_id)

        user = await self.repository.get_item_by_id(user_id)
        if not user:
            self.logger.error("Пользователь не найден: %s", user_id)
            raise UserNotFoundError(field="id", value=str(user_id))

        # Soft delete через is_active
        updated_user = await self.repository.update_item(user_id, {"is_active": False})

        if not updated_user:
            self.logger.error("Не удалось деактивировать аккаунт: %s", user_id)
            raise UserNotFoundError(field="id", value=str(user_id))

        self.logger.info("Аккаунт деактивирован: %s (%s)", updated_user.email, user_id)
        return updated_user

    async def get_admins(self) -> list[UserModel]:
        """
        Получает список всех активных администраторов.

        Используется для выбора ADMIN_EMAIL в настройках.

        Returns:
            list[UserModel]: Список администраторов.

        Example:
            >>> admins = await service.get_admins()
            >>> for admin in admins:
            ...     print(admin.email)
        """
        self.logger.info("Получение списка администраторов")
        admins = await self.repository.get_users_by_role("admin")
        self.logger.debug("Найдено администраторов: %d", len(admins))
        return admins

    async def get_all_users(self) -> list[UserModel]:
        """
        Получает список всех активных пользователей.

        Returns:
            list[UserModel]: Список пользователей.
        """
        self.logger.info("Получение списка всех пользователей")
        users = await self.repository.get_all_active_users()
        self.logger.debug("Найдено пользователей: %d", len(users))
        return users
