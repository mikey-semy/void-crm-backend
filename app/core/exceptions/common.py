"""
Общие исключения для API.

Содержит базовые исключения, которые могут использоваться в различных частях приложения.
"""

from typing import Any

from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_502_BAD_GATEWAY,
)

from .base import BaseAPIException


class NotFoundError(BaseAPIException):
    """
    Исключение для случая, когда запрашиваемый ресурс не найден.

    Attributes:
        status_code (int): HTTP_404_NOT_FOUND.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "not_found".
    """

    def __init__(
        self,
        detail: str = "Ресурс не найден",
        field: str | None = None,
        value: Any | None = None,
        extra: dict[Any, Any] | None = None,
    ):
        """
        Инициализация исключения NotFoundError.

        Args:
            detail (str): Сообщение об ошибке.
            field (str, optional): Название поля, по которому искали.
            value (Any, optional): Значение, которое не было найдено.
            extra (Dict, optional): Дополнительные данные.
        """
        if extra is None:
            extra = {}

        if field and value:
            extra.update({"field": field, "value": value})

        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            detail=detail,
            error_type="not_found",
            extra=extra,
        )


class BadRequestError(BaseAPIException):
    """
    Исключение для некорректных запросов.

    Attributes:
        status_code (int): HTTP_400_BAD_REQUEST.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "bad_request".
    """

    def __init__(
        self,
        detail: str = "Некорректный запрос",
        extra: dict[Any, Any] | None = None,
    ):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            detail=detail,
            error_type="bad_request",
            extra=extra,
        )


class ConflictError(BaseAPIException):
    """
    Исключение для конфликтов данных (например, дублирование уникальных полей).

    Attributes:
        status_code (int): HTTP_409_CONFLICT.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "conflict".
    """

    def __init__(
        self,
        detail: str = "Конфликт данных",
        extra: dict[Any, Any] | None = None,
    ):
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            detail=detail,
            error_type="conflict",
            extra=extra,
        )


class ForbiddenError(BaseAPIException):
    """
    Исключение для случая, когда доступ запрещен.

    Attributes:
        status_code (int): HTTP_403_FORBIDDEN.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "forbidden".
    """

    def __init__(
        self,
        detail: str = "Доступ запрещен",
        extra: dict[Any, Any] | None = None,
    ):
        super().__init__(
            status_code=HTTP_403_FORBIDDEN,
            detail=detail,
            error_type="forbidden",
            extra=extra,
        )


class ExternalAPIError(BaseAPIException):
    """
    Исключение для ошибок при обращении к внешним API.

    Attributes:
        status_code (int): HTTP_502_BAD_GATEWAY.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "external_api_error".
    """

    def __init__(
        self,
        detail: str = "Ошибка при обращении к внешнему API",
        extra: dict[Any, Any] | None = None,
    ):
        super().__init__(
            status_code=HTTP_502_BAD_GATEWAY,
            detail=detail,
            error_type="external_api_error",
            extra=extra,
        )


class ValidationError(BaseAPIException):
    """
    Исключение для ошибок валидации данных.

    Attributes:
        status_code (int): HTTP_422_UNPROCESSABLE_ENTITY.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "validation_error".
    """

    def __init__(
        self,
        detail: str = "Ошибка валидации данных",
        field: str | None = None,
        message: str | None = None,
        extra: dict[Any, Any] | None = None,
    ):
        """
        Инициализация исключения ValidationError.

        Args:
            detail (str): Общее сообщение об ошибке.
            field (str, optional): Название поля с ошибкой.
            message (str, optional): Сообщение об ошибке для поля.
            extra (Dict, optional): Дополнительные данные.
        """
        if extra is None:
            extra = {}

        if field:
            extra["field"] = field
        if message:
            extra["message"] = message

        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_type="validation_error",
            extra=extra,
        )
