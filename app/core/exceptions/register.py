"""
Исключения для процесса регистрации пользователей.

Все исключения наследуются от BaseAPIException и автоматически
конвертируются в HTTP responses через global exception handler.
"""

from typing import Any
from uuid import UUID

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.core.exceptions.base import BaseAPIException


class UserAlreadyExistsError(BaseAPIException):
    """
    Исключение когда пользователь с таким email/username уже существует.

    HTTP Status: 409 Conflict
    """

    def __init__(
        self,
        field: str,
        value: str,
        detail: str | None = None,
        extra: dict[Any, Any] | None = None,
    ):
        """
        Args:
            field: Поле, по которому найден дубликат (email, username).
            value: Значение поля.
            detail: Дополнительное описание ошибки.
            extra: Дополнительные данные для клиента.
        """
        if extra is None:
            extra = {}

        extra["field"] = field
        extra["value"] = value

        if not detail:
            detail = f"Пользователь с {field}='{value}' уже зарегистрирован"

        super().__init__(
            status_code=HTTP_409_CONFLICT,
            detail=detail,
            error_type="user_already_exists",
            extra=extra,
        )


class WeakPasswordError(BaseAPIException):
    """
    Исключение когда пароль не соответствует требованиям безопасности.

    HTTP Status: 400 Bad Request
    """

    def __init__(
        self,
        requirements: list[str] | None = None,
        detail: str | None = None,
        extra: dict[Any, Any] | None = None,
    ):
        """
        Args:
            requirements: Список несоблюдённых требований.
            detail: Описание ошибки.
            extra: Дополнительные данные.
        """
        if extra is None:
            extra = {}

        if requirements:
            extra["requirements"] = requirements

        if not detail:
            detail = "Пароль не соответствует требованиям безопасности"

        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            detail=detail,
            error_type="weak_password",
            extra=extra,
        )


class UserCreationError(BaseAPIException):
    """
    Исключение при ошибке создания пользователя.

    HTTP Status: 500 Internal Server Error
    """

    def __init__(
        self,
        reason: str | None = None,
        detail: str | None = None,
        extra: dict[Any, Any] | None = None,
    ):
        """
        Args:
            reason: Причина ошибки.
            detail: Описание ошибки.
            extra: Дополнительные данные.
        """
        if extra is None:
            extra = {}

        if reason:
            extra["reason"] = reason

        if not detail:
            detail = "Не удалось создать пользователя"

        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_type="user_creation_error",
            extra=extra,
        )


class RoleAssignmentError(BaseAPIException):
    """
    Исключение при ошибке присвоения роли пользователю.

    HTTP Status: 500 Internal Server Error
    """

    def __init__(
        self,
        user_id: UUID | None = None,
        role_code: str | None = None,
        detail: str | None = None,
        extra: dict[Any, Any] | None = None,
    ):
        """
        Args:
            user_id: ID пользователя.
            role_code: Код роли (buyer, admin).
            detail: Описание ошибки.
            extra: Дополнительные данные.
        """
        if extra is None:
            extra = {}

        if user_id:
            extra["user_id"] = str(user_id)

        if role_code:
            extra["role_code"] = role_code

        if not detail:
            detail = f"Не удалось присвоить роль '{role_code}' пользователю"

        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_type="role_assignment_error",
            extra=extra,
        )


class EmailVerificationError(BaseAPIException):
    """
    Исключение при ошибке верификации email.

    HTTP Status: 400 Bad Request
    """

    def __init__(
        self,
        token: str | None = None,
        detail: str | None = None,
        extra: dict[Any, Any] | None = None,
    ):
        """
        Args:
            token: Токен верификации.
            detail: Описание ошибки.
            extra: Дополнительные данные.
        """
        if extra is None:
            extra = {}

        if token:
            # НЕ отправляем токен клиенту в целях безопасности
            extra["token_provided"] = True

        if not detail:
            detail = "Неверный или истёкший токен верификации email"

        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            detail=detail,
            error_type="email_verification_error",
            extra=extra,
        )
