"""
Схемы API версии 1.

Экспортирует все схемы для версии API v1.
"""

# Common (из base.py)
from .base import (
    BaseRequestSchema,
    BaseResponseSchema,
    BaseSchema,
    CommonBaseSchema,
    ErrorResponseSchema,
    ErrorSchema,
)
# Health
from .health import (
    HealthCheckDataSchema,
    HealthCheckResponseSchema,
)
# Pagination
from .pagination import (
    BaseSortFields,
    PaginatedDataSchema,
    PaginatedResponseSchema,
    PaginationMetaSchema,
    PaginationParamsSchema,
    SearchParamsSchema,
    SortFieldRegistry,
    SortFields,
    SortOption,
)

# Auth
from .v1.auth import (
    CurrentUserResponseSchema,
    ForgotPasswordRequestSchema,
    LoginRequestSchema,
    LogoutDataSchema,
    LogoutResponseSchema,
    PasswordResetConfirmDataSchema,
    PasswordResetConfirmRequestSchema,
    PasswordResetConfirmResponseSchema,
    PasswordResetDataSchema,
    PasswordResetResponseSchema,
    RefreshTokenRequestSchema,
    TokenDataSchema,
    TokenResponseSchema,
    UserCredentialsSchema,
    UserCurrentSchema,
)

# Users
from .v1.users import (
    PasswordChangedSchema,
    UserActivateResponseSchema,
    UserBaseSchema,
    UserCreateSchema,
    UserDeletedSchema,
    UserDeleteResponseSchema,
    UserDetailSchema,
    UserFilterSchema,
    UserListItemSchema,
    UserListResponseSchema,
    UserPasswordChangedResponseSchema,
    UserPasswordChangeSchema,
    UserPasswordResetByAdminSchema,
    UserPublicProfileResponseSchema,
    UserPublicProfileSchema,
    UserResponseSchema,
    UserUpdateSchema,
    UsersListResponseSchema,
    ProfileResponseSchema,
)
__all__ = [
    # Common
    "CommonBaseSchema",
    "BaseSchema",
    "BaseRequestSchema",
    "BaseResponseSchema",
    "ErrorSchema",
    "ErrorResponseSchema",

    # Pagination
    "SortOption",
    "BaseSortFields",
    "SortFields",
    "SortFieldRegistry",
    "PaginationParamsSchema",
    "SearchParamsSchema",
    "PaginationMetaSchema",
    "PaginatedDataSchema",
    "PaginatedResponseSchema",

    # Health
    "HealthCheckDataSchema",
    "HealthCheckResponseSchema",

    # Auth
    "CurrentUserResponseSchema",
    "ForgotPasswordRequestSchema",
    "LoginRequestSchema",
    "LogoutDataSchema",
    "LogoutResponseSchema",
    "PasswordResetConfirmDataSchema",
    "PasswordResetConfirmRequestSchema",
    "PasswordResetConfirmResponseSchema",
    "PasswordResetDataSchema",
    "PasswordResetResponseSchema",
    "RefreshTokenRequestSchema",
    "TokenDataSchema",
    "TokenResponseSchema",
    "UserCredentialsSchema",
    "UserCurrentSchema",

    # Users
    "UserBaseSchema",
    "UserListItemSchema",
    "UserDetailSchema",
    "UserDeletedSchema",
    "PasswordChangedSchema",
    "UserCreateSchema",
    "UserUpdateSchema",
    "UserPasswordChangeSchema",
    "UserPasswordResetByAdminSchema",
    "UserFilterSchema",
    "UserResponseSchema",
    "UserListResponseSchema",
    "UserDeleteResponseSchema",
    "UserActivateResponseSchema",
    "UserPasswordChangedResponseSchema",
    "UserPublicProfileSchema",
    "UserPublicProfileResponseSchema",
    "UsersListResponseSchema",
    "ProfileResponseSchema",
]
