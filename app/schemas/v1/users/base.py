"""
Базовые схемы для работы с пользователями.

Модуль содержит базовые Pydantic схемы для сериализации данных пользователей
в API responses.

Схемы:
    - UserBaseSchema: Базовая схема со всеми полями пользователя
    - UserListItemSchema: Краткая схема для списка пользователей
    - UserDetailSchema: Детальная схема пользователя
    - UserDeletedSchema: Схема для удаленного пользователя
    - PasswordChangedSchema: Схема результата смены пароля
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import EmailStr, Field, model_validator

from app.schemas import BaseSchema, CommonBaseSchema


class UserBaseSchema(BaseSchema):
    """
    Базовая схема пользователя со всеми полями.

    Attributes:
        email: Email адрес для входа в систему
        username: Имя пользователя
        full_name: ФИО пользователя (опционально)
        phone: Контактный телефон (опционально)
        is_active: Флаг активности аккаунта
        role: Роль пользователя в системе (admin/user)
    """

    email: EmailStr = Field(
        description="Email адрес для входа в систему",
        examples=["user@example.com"],
    )

    username: str = Field(
        description="Имя пользователя",
        examples=["john_doe", "user123"],
    )

    full_name: str | None = Field(
        None,
        description="ФИО пользователя",
        examples=["Иванов Иван Иванович"],
    )

    phone: str | None = Field(
        None,
        description="Контактный телефон",
        examples=["+79991234567"],
    )

    is_active: bool = Field(
        description="Флаг активности аккаунта",
        examples=[True],
    )

    role: str = Field(
        description="Роль пользователя в системе (admin или user)",
        examples=["user", "admin"],
    )


class UserListItemSchema(CommonBaseSchema):
    """
    Схема элемента списка пользователей.

    Краткая информация о пользователе для отображения в таблицах и списках.

    Attributes:
        id: UUID пользователя
        email: Email адрес
        username: Имя пользователя
        full_name: ФИО пользователя (может быть None)
        is_active: Статус активности аккаунта
    """

    id: uuid.UUID = Field(
        description="UUID пользователя",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    email: EmailStr = Field(
        description="Email адрес пользователя",
        examples=["user@example.com"],
    )

    username: str = Field(
        description="Имя пользователя",
        examples=["john_doe"],
    )

    full_name: str | None = Field(
        None,
        description="ФИО пользователя",
        examples=["Иванов Иван Иванович", None],
    )

    is_active: bool = Field(
        description="Статус активности аккаунта",
        examples=[True],
    )


class UserDetailSchema(BaseSchema):
    """
    Схема детальной информации о пользователе.

    Полная информация о пользователе.
    Используется для просмотра профиля и редактирования данных.

    Attributes:
        id: UUID пользователя
        email: Email адрес для входа
        username: Имя пользователя
        full_name: ФИО пользователя (опционально)
        phone: Контактный телефон (опционально)
        is_active: Флаг активности аккаунта
        email_verified: Подтвержден ли email адрес
        email_verified_at: Время подтверждения email (опционально)
        last_login_at: Последний вход в систему (опционально)
        last_activity_at: Последняя активность пользователя (опционально)
        role: Роль пользователя (admin/user)
        created_at: Дата создания аккаунта
        updated_at: Дата последнего обновления
    """

    id: uuid.UUID = Field(
        description="UUID пользователя",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    email: EmailStr = Field(
        description="Email адрес для входа",
        examples=["john@example.com"],
    )

    username: str = Field(
        description="Имя пользователя",
        examples=["john_doe"],
    )

    full_name: str | None = Field(
        None,
        description="ФИО пользователя",
        examples=["Иванов Иван Иванович"],
    )

    phone: str | None = Field(
        None,
        description="Контактный телефон",
        examples=["+79991234567"],
    )

    position: str | None = Field(
        None,
        description="Должность пользователя",
        examples=["Менеджер", "Разработчик"],
    )

    is_active: bool = Field(
        description="Флаг активности аккаунта",
        examples=[True],
    )

    email_verified: bool = Field(
        False,
        description="Подтвержден ли email адрес",
        examples=[True, False],
    )

    email_verified_at: datetime | None = Field(
        None,
        description="Время подтверждения email",
        examples=["2025-10-29T11:00:00Z"],
    )

    last_login_at: datetime | None = Field(
        None,
        description="Последний вход в систему",
        examples=["2025-11-07T14:30:00Z"],
    )

    last_activity_at: datetime | None = Field(
        None,
        description="Последняя активность пользователя",
        examples=["2025-11-07T15:45:00Z"],
    )

    role: str = Field(
        description="Роль пользователя (admin/user)",
        examples=["user", "admin"],
    )

    created_at: datetime = Field(
        description="Дата и время создания аккаунта",
        examples=["2025-10-29T10:30:00Z"],
    )

    updated_at: datetime = Field(
        description="Дата и время последнего обновления",
        examples=["2025-10-29T10:30:00Z"],
    )

    @model_validator(mode="before")
    @classmethod
    def extract_role(cls, data: Any) -> Any:
        """
        Извлекает role из SQLAlchemy model.
        """
        if hasattr(data, "role") and not isinstance(data, dict):
            data_dict = {
                "id": data.id,
                "email": data.email,
                "username": data.username,
                "full_name": data.full_name,
                "phone": data.phone,
                "position": data.position,
                "is_active": data.is_active,
                "email_verified": data.email_verified,
                "email_verified_at": data.email_verified_at,
                "last_login_at": data.last_login_at,
                "last_activity_at": data.last_activity_at,
                "role": data.role,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
            return data_dict
        return data


class UserDeletedSchema(CommonBaseSchema):
    """
    Схема удаленного пользователя.

    Возвращается при успешном удалении пользователя.
    Содержит минимальную информацию об удаленном аккаунте.

    Attributes:
        id: UUID удаленного пользователя
        email: Email удаленного пользователя
        deleted_at: Время выполнения операции удаления
    """

    id: uuid.UUID = Field(
        description="UUID удаленного пользователя",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    email: EmailStr = Field(
        description="Email удаленного пользователя",
        examples=["deleted@example.com"],
    )

    deleted_at: datetime = Field(
        description="Время выполнения операции удаления",
        examples=["2025-10-29T15:30:00Z"],
    )


class PasswordChangedSchema(CommonBaseSchema):
    """
    Схема данных о смене пароля.

    Возвращается при успешной смене пароля пользователем или администратором.
    Содержит временную метку и ID пользователя.

    Attributes:
        user_id: UUID пользователя, пароль которого был изменен
        changed_at: Время выполнения операции смены пароля
    """

    user_id: uuid.UUID = Field(
        description="UUID пользователя, пароль которого был изменен",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    changed_at: datetime = Field(
        description="Время выполнения операции смены пароля",
        examples=["2025-10-29T16:45:00Z"],
    )


class AdminListItemSchema(CommonBaseSchema):
    """
    Схема элемента списка администраторов.

    Attributes:
        id: UUID администратора
        username: Имя пользователя
        email: Email адрес
        full_name: ФИО (опционально)
    """

    id: uuid.UUID = Field(
        description="UUID администратора",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    username: str = Field(
        description="Имя пользователя",
        examples=["admin"],
    )

    email: EmailStr = Field(
        description="Email адрес",
        examples=["admin@example.com"],
    )

    full_name: str | None = Field(
        None,
        description="ФИО администратора",
        examples=["Иванов Иван Иванович"],
    )


class UserPublicProfileSchema(CommonBaseSchema):
    """
    Публичная схема профиля пользователя.

    Используется для просмотра профиля другого пользователя.
    Содержит публичную информацию о пользователе.

    Attributes:
        id: UUID пользователя
        username: Имя пользователя
        email: Email пользователя
        full_name: ФИО пользователя (опционально)
        phone: Телефон пользователя (опционально)
        position: Должность пользователя (опционально)
        role: Роль пользователя (admin/user)
        is_active: Флаг активности аккаунта
        last_login_at: Последний вход в систему (опционально)
        last_activity_at: Последняя активность пользователя (опционально)
        created_at: Дата регистрации
    """

    id: uuid.UUID = Field(
        description="UUID пользователя",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    username: str = Field(
        description="Имя пользователя",
        examples=["john_doe"],
    )

    email: EmailStr = Field(
        description="Email пользователя",
        examples=["user@example.com"],
    )

    full_name: str | None = Field(
        None,
        description="ФИО пользователя",
        examples=["Иванов Иван Иванович"],
    )

    phone: str | None = Field(
        None,
        description="Телефон пользователя",
        examples=["+79991234567"],
    )

    position: str | None = Field(
        None,
        description="Должность пользователя",
        examples=["Менеджер"],
    )

    role: str = Field(
        description="Роль пользователя (admin/user)",
        examples=["user", "admin"],
    )

    is_active: bool = Field(
        description="Флаг активности аккаунта",
        examples=[True],
    )

    last_login_at: datetime | None = Field(
        None,
        description="Последний вход в систему",
        examples=["2025-11-07T14:30:00Z"],
    )

    last_activity_at: datetime | None = Field(
        None,
        description="Последняя активность пользователя",
        examples=["2025-11-07T15:45:00Z"],
    )

    created_at: datetime = Field(
        description="Дата регистрации",
        examples=["2025-10-29T10:30:00Z"],
    )

    @model_validator(mode="before")
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        """Извлекает поля из SQLAlchemy model."""
        if hasattr(data, "role") and not isinstance(data, dict):
            data_dict = {
                "id": data.id,
                "username": data.username,
                "email": data.email,
                "full_name": data.full_name,
                "phone": data.phone,
                "position": data.position,
                "role": data.role,
                "is_active": data.is_active,
                "last_login_at": data.last_login_at,
                "last_activity_at": data.last_activity_at,
                "created_at": data.created_at,
            }
            return data_dict
        return data
