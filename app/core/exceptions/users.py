"""
Классы исключений для модуля users.

Этот модуль содержит классы исключений,
которые могут быть вызваны при работе с пользователями.

Включают в себя:
- UserNotFoundError: Исключение, которое вызывается, когда пользователь не найден.
- UserExistsError: Исключение, которое вызывается, когда пользователь с таким именем или email уже существует.
- UserCreationError: Исключение при ошибке создания пользователя.
"""

from typing import Any

from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from .base import BaseAPIException


class UserNotFoundError(BaseAPIException):
    """
    Исключение для ненайденного пользователя.

    Возникает, когда запрашиваемый пользователь не найден в базе данных.

    Attributes:
        field (Optional[str]): Поле, по которому искали пользователя.
        value (Any): Значение поля, по которому искали пользователя.
        detail (Optional[str]): Подробное сообщение об ошибке.
    """

    def __init__(
        self,
        field: str | None = None,
        value: Any = None,
        detail: str | None = None,
    ):
        """
        Инициализирует исключение UserNotFoundError.

        Args:
            field (Optional[str]): Поле, по которому искали пользователя.
            value (Any): Значение поля, по которому искали пользователя.
            detail (Optional[str]): Подробное сообщение об ошибке.
        """
        message = detail or "Пользователь не найден"
        if field and value is not None:
            message = f"Пользователь с {field}={value} не найден"

        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            detail=message,
            error_type="user_not_found",
            extra={"field": field, "value": value} if field else None,
        )


class UserExistsError(BaseAPIException):
    """
    Исключение для существующего пользователя.

    Возникает при попытке создать пользователя с данными, которые уже существуют в системе.

    Attributes:
        detail (str): Подробное сообщение об ошибке.
        field (str): Поле, по которому обнаружен дубликат.
        value (Any): Значение поля, которое уже существует.
    """

    def __init__(self, field: str, value: Any):
        """
        Инициализирует исключение UserExistsError.

        Args:
            field (str): Поле, по которому обнаружен дубликат.
            value (Any): Значение поля, которое уже существует.
        """
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            detail=f"Пользователь с {field}={value} уже существует",
            error_type="user_exists",
            extra={"field": field, "value": value},
        )


class UserCreationError(BaseAPIException):
    """
    Исключение при ошибке создания пользователя.

    Возникает, когда не удается создать пользователя из-за внутренней ошибки системы,
    проблем с базой данных или некорректных входных данных, которые не были
    обработаны на уровне валидации.

    Attributes:
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки - "user_creation_error".
        status_code (int): HTTP-код ответа - 500 (Internal Server Error).
        extra (Optional[Dict[str, Any]]): Дополнительная информация об ошибке.
    """

    def __init__(
        self,
        detail: str = "Не удалось создать пользователя. Пожалуйста, попробуйте позже.",
        extra: dict[str, Any] | None = None,
    ):
        """
        Инициализирует исключение UserCreationError.

        Args:
            detail (str): Подробное сообщение об ошибке. По умолчанию предоставляется
                          общее сообщение, но рекомендуется указывать более конкретную причину.
            extra (Optional[Dict[str, Any]]): Дополнительная информация об ошибке, которая может быть полезна
                          для отладки, но не отображается в ответе клиенту.

        Examples:
            >>> raise UserCreationError("Ошибка при хешировании пароля")
            >>> raise UserCreationError("Ошибка при сохранении в базу данных", {"db_error": "Duplicate key"})
        """
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_type="user_creation_error",
            extra=extra or {},
        )


class UserInactiveError(BaseAPIException):
    """
    Исключение для неактивного пользователя.

    Возникает, когда пользователь пытается аутентифицироваться,
    но его аккаунт деактивирован.

    Attributes:
        detail (str): "Аккаунт деактивирован".
        error_type (str): "user_inactive".
    """

    def __init__(self, detail: str = "Аккаунт деактивирован"):
        """
        Инициализирует исключение UserInactiveError.

        Args:
            detail (str): Подробное сообщение об ошибке.
        """
        super().__init__(
            status_code=HTTP_403_FORBIDDEN,
            detail=detail,
            error_type="user_inactive",
        )


class UserEmailConflictError(BaseAPIException):
    """
    Исключение для конфликта email при обновлении профиля.

    Возникает, когда пользователь пытается изменить email на уже занятый.

    HTTP Status: 409 Conflict

    Attributes:
        email (str): Email, который уже занят.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): "user_email_conflict".
    """

    def __init__(
        self,
        email: str,
        detail: str | None = None,
        extra: dict[Any, Any] | None = None,
    ):
        """
        Инициализирует исключение UserEmailConflictError.

        Args:
            email (str): Email, который уже занят другим пользователем.
            detail (Optional[str]): Дополнительное описание ошибки.
            extra (Optional[Dict[Any, Any]]): Дополнительные данные.

        Example:
            >>> raise UserEmailConflictError(email="user@example.com")
        """
        if extra is None:
            extra = {}

        extra["email"] = email

        if not detail:
            detail = f"Email '{email}' уже используется другим пользователем"

        super().__init__(
            status_code=HTTP_409_CONFLICT,
            detail=detail,
            error_type="user_email_conflict",
            extra=extra,
        )


class UserPhoneConflictError(BaseAPIException):
    """
    Исключение для конфликта телефона при обновлении профиля.

    Возникает, когда пользователь пытается изменить телефон на уже занятый.

    HTTP Status: 409 Conflict

    Attributes:
        phone (str): Телефон, который уже занят.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): "user_phone_conflict".
    """

    def __init__(
        self,
        phone: str,
        detail: str | None = None,
        extra: dict[Any, Any] | None = None,
    ):
        """
        Инициализирует исключение UserPhoneConflictError.

        Args:
            phone (str): Телефон, который уже занят другим пользователем.
            detail (Optional[str]): Дополнительное описание ошибки.
            extra (Optional[Dict[Any, Any]]): Дополнительные данные.

        Example:
            >>> raise UserPhoneConflictError(phone="+79991234567")
        """
        if extra is None:
            extra = {}

        extra["phone"] = phone

        if not detail:
            detail = f"Телефон '{phone}' уже используется другим пользователем"

        super().__init__(
            status_code=HTTP_409_CONFLICT,
            detail=detail,
            error_type="user_phone_conflict",
            extra=extra,
        )
