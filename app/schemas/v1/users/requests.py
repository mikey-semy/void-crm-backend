"""Схемы запросов для управления пользователями."""

from pydantic import EmailStr, Field

from app.schemas import BaseRequestSchema


class UserCreateSchema(BaseRequestSchema):
    """
    Схема для создания пользователя администратором.

    Attributes:
        email: Email для входа (должен быть уникальным).
        password: Пароль в открытом виде (будет захеширован).
        full_name: ФИО представителя компании.
        phone: Контактный телефон.
        company_name: Название компании-покупателя.
        inn: ИНН компании (опционально).
        position: Должность представителя (опционально).
        is_active: Флаг активности (по умолчанию true).
        role: Роль пользователя (admin/user, по умолчанию user).
    """

    email: EmailStr = Field(description="Email для входа")
    password: str = Field(
        min_length=8, max_length=128, description="Пароль (минимум 8 символов)"
    )
    full_name: str = Field(
        min_length=3, max_length=255, description="ФИО представителя"
    )
    phone: str = Field(description="Контактный телефон")
    company_name: str = Field(
        min_length=2, max_length=255, description="Название компании"
    )
    inn: str | None = Field(None, description="ИНН компании")
    position: str | None = Field(
        None, max_length=255, description="Должность представителя"
    )
    is_active: bool = Field(True, description="Флаг активности аккаунта")
    role: str = Field("user", description="Роль пользователя (admin/user)")


class UserUpdateSchema(BaseRequestSchema):
    """
    Схема для обновления данных пользователя.

    Attributes:
        username: Новый username (nickname) для входа.
        email: Новый email (если нужно изменить).
        full_name: Новое ФИО.
        phone: Новый телефон.
        position: Новая должность.
    """

    username: str | None = Field(
        None,
        min_length=3,
        max_length=50,
        description="Новый username (nickname) для входа",
    )
    email: EmailStr | None = Field(None, description="Новый email")
    full_name: str | None = Field(
        None, min_length=3, max_length=255, description="Новое ФИО"
    )
    phone: str | None = Field(None, description="Новый телефон")
    position: str | None = Field(None, max_length=255, description="Новая должность")


class UserPasswordChangeSchema(BaseRequestSchema):
    """
    Схема для смены пароля пользователем.

    Attributes:
        old_password: Текущий пароль для подтверждения.
        new_password: Новый пароль (минимум 8 символов).
    """

    old_password: str = Field(description="Текущий пароль для подтверждения")
    new_password: str = Field(
        min_length=8, max_length=128, description="Новый пароль (минимум 8 символов)"
    )


class UserPasswordResetByAdminSchema(BaseRequestSchema):
    """
    Схема для сброса пароля администратором.

    Attributes:
        new_password: Новый временный пароль (минимум 8 символов).
    """

    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="Новый временный пароль (минимум 8 символов)",
    )


class UserFilterSchema(BaseRequestSchema):
    """
    Схема для фильтрации списка пользователей.

    Attributes:
        email: Фильтр по email (частичное совпадение).
        username: Фильтр по имени пользователя (частичное совпадение).
        is_active: Фильтр по статусу активности.
        role: Фильтр по роли (admin/user).
    """

    email: str | None = Field(None, description="Фильтр по email")
    username: str | None = Field(None, description="Фильтр по имени пользователя")
    is_active: bool | None = Field(None, description="Фильтр по статусу активности")
    role: str | None = Field(None, description="Фильтр по роли")
