"""
Модуль для работы с куками аутентификации.

Предоставляет класс CookieManager для установки, чтения и удаления
куков с токенами аутентификации. Обеспечивает безопасную работу
с куками через HttpOnly, Secure и SameSite флаги.
"""

import logging
from enum import Enum

from fastapi import Response

from app.core.settings import settings

logger = logging.getLogger(__name__)


class TokenCookieKey(str, Enum):
    """
    Перечисление ключей для куков токенов аутентификации.
    Используется для обеспечения согласованности и предотвращения ошибок при работе с куками.
    """

    ACCESS = "access_token"
    REFRESH = "refresh_token"


class CookieManager:
    """
    Класс для управления куками аутентификации.

    Предоставляет статические методы для установки, чтения и удаления
    куков с токенами. Использует настройки безопасности из конфигурации.
    """

    @staticmethod
    def set_auth_cookies(
        response: Response, access_token: str, refresh_token: str
    ) -> None:
        """
        Устанавливает куки с токенами аутентификации.

        Args:
            response (Response): Ответ FastAPI, в который нужно установить куки.
            access_token (str): Access токен, который нужно сохранить в куке.
            refresh_token (str): Refresh токен, который нужно сохранить в куке.

        Returns:
            None
        """
        CookieManager.set_access_token_cookie(response, access_token)
        CookieManager.set_refresh_token_cookie(response, refresh_token)
        logger.debug(
            "Установлены куки с токенами аутентификации",
            extra={
                "access_token_length": len(access_token),
                "refresh_token_length": len(refresh_token),
            },
        )

    @staticmethod
    def set_access_token_cookie(response: Response, access_token: str) -> None:
        """
        Устанавливает куку с access токеном.

        Args:
            response (Response): Ответ FastAPI, в который нужно установить куку.
            access_token (str): Access токен, который нужно сохранить в куке.

        Returns:
            None
        """
        response.set_cookie(
            key=TokenCookieKey.ACCESS.value,
            value=access_token,
            **settings.access_token_cookie_params,
        )
        logger.debug("Установлена кука с access токеном")

    @staticmethod
    def set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
        """
        Устанавливает куку с refresh токеном.

        Args:
            response (Response): Ответ FastAPI, в который нужно установить куку.
            refresh_token (str): Refresh токен, который нужно сохранить в куке.

        Returns:
            None
        """
        response.set_cookie(
            key=TokenCookieKey.REFRESH.value,
            value=refresh_token,
            **settings.refresh_token_cookie_params,
        )
        logger.debug("Установлена кука с refresh токеном")

    @staticmethod
    def clear_auth_cookies(response: Response) -> None:
        """
        Очищает все куки с токенами аутентификации.

        Args:
            response (Response): Ответ FastAPI, из которого нужно удалить куки.

        Returns:
            None
        """
        CookieManager.clear_access_token_cookie(response)
        CookieManager.clear_refresh_token_cookie(response)
        logger.debug("Очищены куки с токенами аутентификации")

    @staticmethod
    def clear_access_token_cookie(response: Response) -> None:
        """
        Очищает куку с access токеном.

        Args:
            response (Response): Ответ FastAPI, из которого нужно удалить куку.

        Returns:
            None
        """
        # delete_cookie in Starlette/FastAPI accepts only a subset of params.
        # Avoid passing unsupported kwargs like max_age/expires which cause
        # TypeError: unexpected keyword argument 'max_age'.
        allowed = ("path", "domain", "secure", "httponly", "samesite")
        params = {
            k: v for k, v in settings.access_token_cookie_params.items() if k in allowed
        }

        response.delete_cookie(
            key=TokenCookieKey.ACCESS.value,
            **params,
        )
        logger.debug("Очищена кука с access токеном")

    @staticmethod
    def clear_refresh_token_cookie(response: Response) -> None:
        """
        Очищает куку с refresh токеном.

        Args:
            response (Response): Ответ FastAPI, из которого нужно удалить куку.

        Returns:
            None
        """
        allowed = ("path", "domain", "secure", "httponly", "samesite")
        params = {
            k: v
            for k, v in settings.refresh_token_cookie_params.items()
            if k in allowed
        }

        response.delete_cookie(
            key=TokenCookieKey.REFRESH.value,
            **params,
        )
        logger.debug("Очищена кука с refresh токеном")

    @staticmethod
    def get_cookie_settings() -> dict:
        """
        Возвращает текущие настройки куков для отладки.

        Returns:
            dict: Словарь с параметрами куков для access и refresh токенов.
        """
        return {
            "access_token": settings.access_token_cookie_params,
            "refresh_token": settings.refresh_token_cookie_params,
        }
