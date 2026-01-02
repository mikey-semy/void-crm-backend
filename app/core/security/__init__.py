"""
Модуль безопасности для работы с аутентификацией.

Содержит менеджеры для:
- Токенов (JWT)
- Паролей (хеширование и валидация)
- Куки (установка и очистка)
- Аутентификации (защита роутеров)
"""

from .auth import (
    AuthenticationManager,
    CurrentAdminDep,
    CurrentUserDep,
    CurrentUserOrApiKeyDep,
    get_current_admin,
    get_current_user,
    get_current_user_or_api_key,
)
from .cookie_manager import CookieManager, TokenCookieKey
from .encryption import EncryptionService, get_encryption_service
from .password_manager import PasswordManager
from .token_manager import TokenManager, TokenType

__all__ = [
    "TokenManager",
    "TokenType",
    "PasswordManager",
    "CookieManager",
    "TokenCookieKey",
    "EncryptionService",
    "get_encryption_service",
    "AuthenticationManager",
    "get_current_user",
    "get_current_admin",
    "get_current_user_or_api_key",
    "CurrentUserDep",
    "CurrentAdminDep",
    "CurrentUserOrApiKeyDep",
]
