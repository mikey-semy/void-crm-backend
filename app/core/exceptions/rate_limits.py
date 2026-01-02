"""Исключения для ограничения частоты запросов."""

from typing import Any

from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from .base import BaseAPIException


class RateLimitExceededError(BaseAPIException):
    """
    Исключение, возникающее при превышении лимита запросов.

    Attributes:
        detail (str): Сообщение об ошибке.
        error_type (str): Тип ошибки.
        status_code (int): HTTP_429_TOO_MANY_REQUESTS.
        extra (Dict[str, Any]): Дополнительная информация об ошибке.
    """

    def __init__(
        self,
        detail: str = "Слишком много запросов. Пожалуйста, повторите попытку позже.",
        error_type: str = "rate_limit_exceeded",
        reset_time: int | None = None,
        extra: dict[str, Any] | None = None,
    ):
        """
        Инициализирует исключение RateLimitExceededError.

        Args:
            detail: Сообщение об ошибке.
            error_type: Тип ошибки.
            reset_time: Время в секундах до сброса ограничения.
            extra: Дополнительная информация об ошибке.
        """
        _extra = extra or {}
        if reset_time is not None:
            _extra["reset_time"] = reset_time

        super().__init__(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_type=error_type,
            extra=_extra,
        )
