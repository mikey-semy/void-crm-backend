"""Базовые схемы для аутентификации и авторизации."""

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas import CommonBaseSchema


class TokenDataSchema(CommonBaseSchema):
    """Данные токенов аутентификации."""

    access_token: str = Field(description="JWT токен доступа для авторизации запросов")
    refresh_token: str = Field(description="Токен для обновления access_token")
    token_type: str = Field(
        default="Bearer", description="Тип токена для заголовка Authorization"
    )
    expires_in: int = Field(description="Время жизни access_token в секундах")


class LogoutDataSchema(CommonBaseSchema):
    """Данные выхода из системы."""

    logged_out_at: datetime = Field(description="Время выхода из системы в формате UTC")


class PasswordResetDataSchema(CommonBaseSchema):
    """Данные запроса сброса пароля."""

    email: EmailStr = Field(description="Email адрес для восстановления пароля")
    expires_in: int = Field(
        description="Время действия ссылки восстановления в секундах"
    )


class PasswordResetConfirmDataSchema(CommonBaseSchema):
    """Данные подтверждения сброса пароля."""

    password_changed_at: datetime = Field(
        description="Время изменения пароля в формате UTC"
    )


class PasswordChangeDataSchema(CommonBaseSchema):
    """
    Данные смены пароля авторизованным пользователем.

    Используется в ответе на PUT /auth/password/change для подтверждения
    успешной смены пароля текущим пользователем.

    Attributes:
        password_changed_at: Временная метка изменения пароля в UTC.

    Example:
        {
            "password_changed_at": "2024-01-15T10:35:00Z"
        }
    """

    password_changed_at: datetime = Field(
        description="Время изменения пароля в формате UTC"
    )


class UserCredentialsSchema(CommonBaseSchema):
    """
    Схема учетных данных для внутренней аутентификации.

    ⚠️ ТОЛЬКО для internal использования!
    ⚠️ НИКОГДА не возвращайте в API ответах!
    """

    id: uuid.UUID = Field(description="ID пользователя")
    username: str = Field(description="Уникальное имя пользователя")
    email: EmailStr = Field(description="Email пользователя")
    password_hash: str = Field(description="Хешированный пароль")
    is_active: bool = Field(description="Активность аккаунта")
    full_name: str | None = Field(None, description="ФИО пользователя (опционально)")
    role: str = Field(default="user", description="Роль (admin/user)")


class UserSchema(CommonBaseSchema):
    """
    Схема пользователя для Redis и внутренней логики.

    Используется в AuthRedisManager.

    Attributes:
        id: UUID пользователя
        username: Уникальное имя пользователя
        email: Email пользователя
        full_name: ФИО пользователя (опционально)
        is_active: Активность аккаунта
        email_verified: Подтвержден ли email адрес
        last_login_at: Последний вход в систему
        last_activity_at: Последняя активность пользователя
        role: Роль пользователя (admin/user)
    """

    id: uuid.UUID = Field(description="ID пользователя")
    username: str = Field(description="Уникальное имя пользователя")
    email: EmailStr = Field(description="Email пользователя")
    full_name: str | None = Field(None, description="ФИО пользователя (опционально)")
    is_active: bool = Field(description="Активность аккаунта")
    email_verified: bool = Field(
        default=False, description="Подтвержден ли email адрес"
    )
    last_login_at: datetime | None = Field(None, description="Последний вход в систему")
    last_activity_at: datetime | None = Field(
        None, description="Последняя активность пользователя"
    )
    role: str = Field(default="user", description="Роль (admin/user)")


class UserCurrentSchema(CommonBaseSchema):
    """
    Схема текущего аутентифицированного пользователя.

    Attributes:
        id: UUID пользователя
        username: Уникальное имя пользователя
        email: Email пользователя
        full_name: Полное имя (ФИО), опционально
        email_verified: Подтвержден ли email адрес
        email_verified_at: Время подтверждения email (UTC)
        last_login_at: Последний вход в систему (UTC)
        last_activity_at: Последняя активность пользователя (UTC)
        role: Роль пользователя (admin/user)

    Example:
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "username": "ivan_petrov",
            "email": "ivan@example.com",
            "full_name": "Иванов Иван Петрович",
            "email_verified": true,
            "email_verified_at": "2024-01-15T10:30:00Z",
            "last_login_at": "2024-01-20T14:20:00Z",
            "last_activity_at": "2024-01-20T14:25:00Z",
            "role": "user"
        }
    """

    id: uuid.UUID = Field(description="ID пользователя")
    username: str = Field(description="Уникальное имя пользователя")
    email: EmailStr = Field(description="Email пользователя")
    full_name: str | None = Field(None, description="Полное имя (ФИО), опционально")
    email_verified: bool = Field(
        default=False, description="Подтвержден ли email адрес"
    )
    email_verified_at: datetime | None = Field(
        None, description="Время подтверждения email (UTC)"
    )
    last_login_at: datetime | None = Field(
        None, description="Последний вход в систему (UTC)"
    )
    last_activity_at: datetime | None = Field(
        None, description="Последняя активность пользователя (UTC)"
    )
    role: str = Field(description="Роль пользователя (admin/user)")
