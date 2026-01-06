"""Схемы запросов для настроек пользователей."""

from pydantic import Field

from app.schemas.base import BaseRequestSchema

from .base import AccessTokenBaseSchema


class AccessTokenCreateSchema(BaseRequestSchema, AccessTokenBaseSchema):
    """Схема создания токена доступа."""

    expires_in_days: int | None = Field(
        None,
        ge=1,
        le=365,
        description="Срок действия в днях (пусто = бессрочный)",
        examples=[30, 90, 365],
    )
