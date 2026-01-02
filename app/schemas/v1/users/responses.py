"""Схемы ответов для управления пользователями."""

from app.schemas import BaseResponseSchema

from .base import (
    PasswordChangedSchema,
    UserDeletedSchema,
    UserDetailSchema,
    UserListItemSchema,
    UserPublicProfileSchema,
)


class UserResponseSchema(BaseResponseSchema):
    """Схема ответа с одним пользователем."""

    data: UserDetailSchema


class UserListResponseSchema(BaseResponseSchema):
    """Схема ответа со списком пользователей."""

    data: list[UserListItemSchema]


class UserDeleteResponseSchema(BaseResponseSchema):
    """Схема ответа при удалении пользователя."""

    data: UserDeletedSchema


class UserActivateResponseSchema(BaseResponseSchema):
    """Схема ответа при активации/деактивации пользователя."""

    data: UserDetailSchema


class UserPasswordChangedResponseSchema(BaseResponseSchema):
    """Схема ответа при успешной смене пароля."""

    data: PasswordChangedSchema


class ProfileResponseSchema(BaseResponseSchema):
    """
    Схема ответа с данными профиля текущего пользователя.

    Используется для endpoint'а GET /users/me.
    Содержит полные данные пользователя включая информацию о компании.
    """

    data: UserDetailSchema


class UserPublicProfileResponseSchema(BaseResponseSchema):
    """
    Схема ответа с публичным профилем пользователя.

    Используется для endpoint'а GET /users/{user_id}.
    Содержит только публичную информацию о пользователе.
    """

    data: UserPublicProfileSchema
