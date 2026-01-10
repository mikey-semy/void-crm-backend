from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .roles import UserRoleModel
    from .knowledge import KnowledgeArticleModel, KnowledgeChatSessionModel
    from .user_settings import UserAccessTokenModel


class UserModel(BaseModel):
    """
    Модель пользователя B2B системы.

    Представляет пользователя платформы - представителя компании-покупателя
    или администратора системы. Содержит информацию для аутентификации,
    контактные данные и связь с компанией.

    Attributes:
        username (str): Уникальное имя пользователя для входа в систему.
        email (str): Email адрес для входа в систему (уникальный).
        phone (Optional[str]): Контактный телефон представителя (заполняется в профиле).
        password_hash (Optional[str]): Bcrypt хеш пароля для аутентификации.
        is_active (bool): Флаг активности аккаунта (деактивированные не могут входить).
        email_verified (bool): Подтвержден ли email адрес (по умолчанию False).
        verification_token (Optional[str]): Токен для верификации email.
        email_verified_at (Optional[datetime]): Время подтверждения email.
        reset_token (Optional[str]): Токен для сброса пароля.
        reset_token_expires_at (Optional[datetime]): Срок действия reset_token.
        last_login_at (Optional[datetime]): Последний вход в систему.
        last_activity_at (Optional[datetime]): Последняя активность пользователя.
        full_name (Optional[str]): ФИО представителя компании (заполняется в профиле).
        position (Optional[str]): Должность представителя в компании.
        user_roles (List[UserRoleModel]): Список ролей пользователя (admin/buyer).

    Relationships:
        user_roles: One-to-Many связь с UserRoleModel (роли пользователя).

    Properties:
        role: Основная роль пользователя для API ("admin" или "buyer").

    Note:
        При регистрации создается пользователь с минимальными данными (username, email, password).
        Поля phone, full_name заполняются позже в профиле.

    Example:
        >>> # Регистрация с минимальными данными
        >>> user = UserModel(
        ...     username="john_doe",
        ...     email="john@example.com",
        ...     password_hash=hashed_password,
        ...     is_active=True
        ... )
        >>> user.role
        "buyer"
        >>>
        >>> # Заполнение профиля позже
        >>> user.phone = "+79991234567"
        >>> user.full_name = "Иванов Иван Иванович"
        >>> user.position = "Менеджер по закупкам"
    """

    __tablename__ = "users"

    # Основная информация
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Уникальное имя пользователя для входа",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Email адрес пользователя",
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="Контактный телефон (опционально)",
    )

    # Аутентификация
    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Хеш пароля"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Активен ли пользователь"
    )

    email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Подтвержден ли email адрес"
    )

    # Email verification
    verification_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Токен для верификации email",
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Время подтверждения email"
    )

    # Password reset
    reset_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Токен для сброса пароля",
    )

    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Срок действия reset_token"
    )

    # Activity tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Последний вход в систему"
    )

    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Последняя активность пользователя",
    )

    # Персональные данные
    full_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="ФИО представителя компании (опционально)"
    )

    position: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Должность в компании"
    )

    # Связи
    user_roles: Mapped[list["UserRoleModel"]] = relationship(
        "UserRoleModel",
        foreign_keys="[UserRoleModel.user_id]",
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    knowledge_articles: Mapped[list["KnowledgeArticleModel"]] = relationship(
        "KnowledgeArticleModel",
        back_populates="author",
        order_by="desc(KnowledgeArticleModel.created_at)",
    )

    access_tokens: Mapped[list["UserAccessTokenModel"]] = relationship(
        "UserAccessTokenModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    knowledge_chat_sessions: Mapped[list["KnowledgeChatSessionModel"]] = relationship(
        "KnowledgeChatSessionModel",
        back_populates="user",
        order_by="desc(KnowledgeChatSessionModel.updated_at)",
        cascade="all, delete-orphan",
    )

    def has_role(self, role_code: str) -> bool:
        """
        Проверяет наличие роли у пользователя.

        Args:
            role_code: Код роли для проверки ("admin" или "user").

        Returns:
            True если роль назначена, False в противном случае.

        Example:
            >>> user.has_role("admin")
            False
            >>> user.has_role("user")
            True
        """
        return any(ur.role_code.value == role_code for ur in self.user_roles)

    @property
    def role(self) -> str:
        """
        Возвращает основную роль пользователя для API.

        Используется для сериализации в API responses. Если у пользователя
        несколько ролей, возвращается первая из списка. По умолчанию "user".

        Returns:
            Код роли: "admin" или "user".

        Note:
            В текущей реализации у пользователя может быть только одна роль,
            но модель поддерживает множественные роли для будущего расширения.
        """
        if self.user_roles:
            return self.user_roles[0].role_code.value
        return "user"
