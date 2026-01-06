"""Схемы ответов для настроек пользователей."""

from app.schemas.base import BaseResponseSchema

from .base import (
    AccessTokenCreatedSchema,
    AccessTokenDetailSchema,
    AccessTokenListSchema,
    AccessTokenRevokedSchema,
)


class AccessTokenResponseSchema(BaseResponseSchema):
    """Ответ с одним токеном."""

    data: AccessTokenDetailSchema


class AccessTokenCreatedResponseSchema(BaseResponseSchema):
    """Ответ с созданным токеном (включает полный токен)."""

    data: AccessTokenCreatedSchema


class AccessTokenListResponseSchema(BaseResponseSchema):
    """Ответ со списком токенов."""

    data: AccessTokenListSchema


class AccessTokenRevokedResponseSchema(BaseResponseSchema):
    """Ответ на отзыв токена."""

    data: AccessTokenRevokedSchema
