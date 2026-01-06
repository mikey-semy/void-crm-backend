"""Базовые схемы настроек пользователей."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class AccessTokenBaseSchema(BaseSchema):
    """Базовая схема токена доступа."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Название токена",
        examples=["MCP Server Token"],
    )


class AccessTokenDetailSchema(BaseSchema):
    """Детальная схема токена доступа."""

    id: UUID
    name: str
    token_prefix: str = Field(
        ...,
        description="Префикс токена для идентификации (void_...)",
    )
    is_active: bool
    expires_at: datetime | None = Field(
        None,
        description="Время истечения (NULL = бессрочный)",
    )
    last_used_at: datetime | None = None
    last_used_ip: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AccessTokenCreatedSchema(AccessTokenDetailSchema):
    """Схема созданного токена (с полным токеном)."""

    full_token: str = Field(
        ...,
        description="Полный токен (показывается ТОЛЬКО при создании!)",
    )


class AccessTokenListSchema(BaseSchema):
    """Схема для списка токенов."""

    tokens: list[AccessTokenDetailSchema]
    total: int


class AccessTokenRevokedSchema(BaseSchema):
    """Схема отозванного токена."""

    id: UUID
    token_prefix: str
    revoked_at: datetime


# ==================== EXPIRATION OPTIONS ====================


EXPIRATION_OPTIONS = [
    {"value": None, "label": "Бессрочный"},
    {"value": 7, "label": "7 дней"},
    {"value": 30, "label": "30 дней"},
    {"value": 90, "label": "90 дней"},
    {"value": 180, "label": "180 дней"},
    {"value": 365, "label": "1 год"},
]
