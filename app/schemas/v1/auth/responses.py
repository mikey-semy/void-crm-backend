"""Схемы ответов для аутентификации и авторизации."""

from pydantic import Field

from app.schemas import BaseResponseSchema

from .base import (
    LogoutDataSchema,
    PasswordChangeDataSchema,
    PasswordResetConfirmDataSchema,
    PasswordResetDataSchema,
    UserCurrentSchema,
)


class TokenResponseSchema(BaseResponseSchema):
    """
    Схема ответа с токеном доступа.

    Note:
        Swagger UI для OAuth2 password flow ожидает поля access_token
        и token_type на верхнем уровне (не в data).
    """

    access_token: str | None = Field(None, description="JWT токен доступа")
    refresh_token: str | None = Field(None, description="Токен обновления")
    token_type: str = Field(default="Bearer", description="Тип токена")
    expires_in: int = Field(description="Время жизни токена в секундах")


class LogoutResponseSchema(BaseResponseSchema):
    """
    Схема ответа при выходе из системы.

    Подтверждает успешную инвалидацию токенов и завершение сессии.

    Attributes:
        data: Данные о времени выхода.

    Example:
        {
            "success": true,
            "message": "Выход выполнен успешно",
            "data": {
                "logged_out_at": "2024-01-15T10:30:00Z"
            }
        }
    """

    data: LogoutDataSchema


class CurrentUserResponseSchema(BaseResponseSchema):
    """
    Схема ответа с данными текущего пользователя.

    Возвращается при запросе информации о текущем аутентифицированном
    пользователе (GET /auth/me).

    Attributes:
        data: Данные текущего пользователя.

    Example:
        {
            "success": true,
            "message": null,
            "data": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@company.com",
                "full_name": "Иванов Иван Иванович",
                "role": "user"
            }
        }
    """

    data: UserCurrentSchema


class PasswordResetResponseSchema(BaseResponseSchema):
    """
    Схема ответа на запрос восстановления пароля.

    Подтверждает отправку письма с инструкциями по сбросу пароля.

    Attributes:
        data: Данные о восстановлении пароля.

    Example:
        {
            "success": true,
            "message": "Инструкции по сбросу пароля отправлены на ваш email",
            "data": {
                "email": "user@company.com",
                "expires_in": 1800
            }
        }
    """

    data: PasswordResetDataSchema


class PasswordResetConfirmResponseSchema(BaseResponseSchema):
    """
    Схема ответа на подтверждение сброса пароля.

    Подтверждает успешное изменение пароля.

    Attributes:
        data: Данные о времени изменения пароля.

    Example:
        {
            "success": true,
            "message": "Пароль успешно изменен",
            "data": {
                "password_changed_at": "2024-01-15T10:35:00Z"
            }
        }
    """

    data: PasswordResetConfirmDataSchema


class PasswordChangeResponseSchema(BaseResponseSchema):
    """
    Схема ответа на смену пароля авторизованным пользователем.

    Подтверждает успешное изменение пароля и инвалидацию всех токенов.
    После этого ответа пользователь должен авторизоваться заново.

    Attributes:
        data: Данные о времени изменения пароля.

    Example:
        {
            "success": true,
            "message": "Пароль успешно изменен. Войдите в систему с новым паролем",
            "data": {
                "password_changed_at": "2024-01-15T10:35:00Z"
            }
        }

    Note:
        После успешной смены пароля все access и refresh токены
        пользователя инвалидируются. Требуется повторная аутентификация.
    """

    data: PasswordChangeDataSchema
