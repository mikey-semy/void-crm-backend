"""Модели настроек пользователей."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .users import UserModel


class UserAccessTokenModel(BaseModel):
    """
    Модель для хранения токенов доступа пользователей.

    Используется для аутентификации MCP сервера к API бэкенда.
    Токен генерируется пользователем и используется в настройках Claude Code.

    Attributes:
        user_id (UUID): ID пользователя-владельца токена.
        token_hash (str): Хеш токена (bcrypt). Сам токен показывается только при создании.
        name (str): Название токена для идентификации.
        is_active (bool): Активен ли токен.
        expires_at (datetime | None): Время истечения (None = бессрочный).
        last_used_at (datetime | None): Время последнего использования.
        last_used_ip (str | None): IP последнего использования.

    Relationships:
        user: Many-to-One связь с UserModel.

    Example:
        >>> token = UserAccessTokenModel(
        ...     user_id=user.id,
        ...     token_hash=hash_token(raw_token),
        ...     name="MCP Server Token"
        ... )
    """

    __tablename__ = "user_access_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID пользователя-владельца",
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Хеш токена (bcrypt)",
    )

    # Префикс токена для идентификации (первые 8 символов)
    token_prefix: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        comment="Префикс токена для отображения",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Название токена",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Активен ли токен",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время истечения (NULL = бессрочный)",
    )

    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время последнего использования",
    )

    last_used_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IP последнего использования",
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="access_tokens",
    )


