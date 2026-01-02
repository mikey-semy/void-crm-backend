"""Схемы для аутентификации и авторизации."""

from .base import (
    LogoutDataSchema,
    PasswordChangeDataSchema,
    PasswordResetConfirmDataSchema,
    PasswordResetDataSchema,
    TokenDataSchema,
    UserCredentialsSchema,
    UserCurrentSchema,
    UserSchema,
)
from .requests import (
    AuthSchema,
    ForgotPasswordRequestSchema,
    ForgotPasswordSchema,
    LoginRequestSchema,
    PasswordChangeRequestSchema,
    PasswordResetConfirmRequestSchema,
    PasswordResetConfirmSchema,
    RefreshTokenRequestSchema,
)
from .responses import (
    CurrentUserResponseSchema,
    LogoutResponseSchema,
    PasswordChangeResponseSchema,
    PasswordResetConfirmResponseSchema,
    PasswordResetResponseSchema,
    TokenResponseSchema,
)

__all__ = [
    # Base
    "LogoutDataSchema",
    "PasswordChangeDataSchema",
    "PasswordResetConfirmDataSchema",
    "PasswordResetDataSchema",
    "TokenDataSchema",
    "UserCredentialsSchema",
    "UserCurrentSchema",
    "UserSchema",
    # Requests
    "AuthSchema",
    "ForgotPasswordRequestSchema",
    "ForgotPasswordSchema",
    "LoginRequestSchema",
    "PasswordChangeRequestSchema",
    "PasswordResetConfirmRequestSchema",
    "PasswordResetConfirmSchema",
    "RefreshTokenRequestSchema",
    # Responses
    "CurrentUserResponseSchema",
    "LogoutResponseSchema",
    "PasswordChangeResponseSchema",
    "PasswordResetConfirmResponseSchema",
    "PasswordResetResponseSchema",
    "TokenResponseSchema",
]
