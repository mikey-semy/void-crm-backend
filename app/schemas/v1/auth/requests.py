"""Схемы запросов для аутентификации и авторизации."""

from pydantic import EmailStr, Field, field_validator

from app.core.utils import validate_password_strength
from app.schemas import BaseRequestSchema


class AuthSchema(BaseRequestSchema):
    """
    Схема для внутренней валидации аутентификации.

    ⚠️ ТОЛЬКО для internal использования в сервисах!

    Attributes:
        username: Email или username для входа.
        password: Пароль пользователя.
    """

    username: str = Field(description="Email или username пользователя")
    password: str = Field(description="Пароль пользователя")


class LoginRequestSchema(BaseRequestSchema):
    """
    Схема для входа в систему.

    Attributes:
        email: Email пользователя для входа.
        password: Пароль пользователя.
    """

    email: EmailStr = Field(description="Email пользователя")
    password: str = Field(min_length=8, description="Пароль (минимум 8 символов)")


class ForgotPasswordRequestSchema(BaseRequestSchema):
    """
    Схема для запроса сброса пароля.

    Attributes:
        email: Email адрес для восстановления пароля.
    """

    email: EmailStr = Field(description="Email адрес для восстановления пароля")


class PasswordResetConfirmRequestSchema(BaseRequestSchema):
    """
    Схема для подтверждения сброса пароля.

    Attributes:
        token: Токен восстановления из письма.
        password: Новый пароль (минимум 8 символов).
    """

    token: str = Field(description="Токен восстановления из письма")
    password: str = Field(
        min_length=8, max_length=128, description="Новый пароль (минимум 8 символов)"
    )


class RefreshTokenRequestSchema(BaseRequestSchema):
    """
    Схема для обновления токена доступа.

    Attributes:
        refresh_token: Токен обновления из предыдущего ответа login/register.
    """

    refresh_token: str = Field(
        description="Refresh токен для получения новой пары токенов"
    )


class PasswordChangeRequestSchema(BaseRequestSchema):
    """
    Схема для смены пароля авторизованным пользователем.

    Требует аутентификации через Bearer токен.
    После успешной смены все токены пользователя инвалидируются.

    Attributes:
        old_password: Текущий пароль для подтверждения операции.
        new_password: Новый пароль (минимум 8 символов, должен соответствовать требованиям безопасности).

    Example:
        ```json
        {
            "old_password": "OldPassword123!",
            "new_password": "NewSecurePass456@"
        }
        ```
    """

    old_password: str = Field(
        min_length=1, description="Текущий пароль для подтверждения"
    )
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="Новый пароль (минимум 8 символов, заглавная/строчная буквы, цифра, спецсимвол)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """
        Валидатор для проверки нового пароля на соответствие требованиям безопасности.

        Использует общую утилиту validate_password_strength.

        Args:
            v (str): Новый пароль для валидации.

        Returns:
            str: Валидный пароль.

        Raises:
            ValueError: Если пароль не соответствует требованиям безопасности.
        """
        validate_password_strength(v)
        return v


class ForgotPasswordSchema(BaseRequestSchema):
    """
    Схема для запроса сброса пароля.

    Используется когда пользователь забыл пароль и хочет его восстановить.
    На указанный email будет отправлена ссылка для сброса пароля.

    Attributes:
        email: Email адрес для восстановления пароля.

    Example:
        ```json
        {
            "email": "user@example.com"
        }
        ```
    """

    email: EmailStr = Field(description="Email адрес для восстановления пароля")


class PasswordResetConfirmSchema(BaseRequestSchema):
    """
    Схема для подтверждения сброса пароля.

    Используется для установки нового пароля после перехода по ссылке из email.
    Токен действителен 30 минут после отправки письма.

    Attributes:
        token: Токен восстановления из письма (из query параметра или тела запроса).
        password: Новый пароль (минимум 8 символов, требования безопасности).

    Example:
        ```json
        {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "password": "NewSecurePass123!"
        }
        ```
    """

    token: str = Field(description="Токен восстановления из письма")
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Новый пароль (минимум 8 символов, заглавная/строчная буквы, цифра, спецсимвол)",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Валидатор для проверки пароля на соответствие требованиям безопасности.

        Использует общую утилиту validate_password_strength.

        Args:
            v (str): Пароль для валидации.

        Returns:
            str: Валидный пароль.

        Raises:
            ValueError: Если пароль не соответствует требованиям безопасности.
        """
        validate_password_strength(v)
        return v
