from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .users import UserModel


class RoleCode(str, Enum):
    """
    Перечисление доступных ролей в системе.

    Attributes:
        ADMIN: Администратор системы (полный доступ).
        USER: Пользователь - стандартная роль (ограниченный доступ).

    Example:
        >>> role = RoleCode.ADMIN
        >>> role.value
        "admin"
        >>> RoleCode("user")
        <RoleCode.USER: 'user'>
    """

    ADMIN = "admin"
    USER = "user"


class UserRoleModel(BaseModel):
    """
    Модель связи пользователя с ролью (Many-to-Many).

    Хранит назначения ролей пользователям. В текущей версии у пользователя
    может быть только одна роль, но архитектура поддерживает множественные
    роли для будущего расширения.

    Attributes:
        user_id (UUID): ID пользователя из таблицы users.
        role_code (RoleCode): Код роли (enum: admin/user).
        user (UserModel): Связанный пользователь.

    Relationships:
        user: Many-to-One связь с UserModel.

    Example:
        >>> role = UserRoleModel(user_id=user.id, role_code=RoleCode.USER)
        >>> role.role_code.value
        "user"

    Note:
        При удалении пользователя все его роли удаляются автоматически (CASCADE).
    """

    __tablename__ = "user_role_assignments"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID пользователя",
    )

    role_code: Mapped[RoleCode] = mapped_column(
        SQLEnum(RoleCode), nullable=False, index=True, comment="Код роли"
    )

    # Связи
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys=[user_id],
        passive_deletes=True,
        back_populates="user_roles",
    )

    def __repr__(self) -> str:
        """Строковое представление модели для отладки."""
        return f"<UserRoleModel(user_id={self.user_id}, role_code={self.role_code})>"
