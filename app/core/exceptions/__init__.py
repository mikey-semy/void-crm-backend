from .base import BaseAPIException
from .common import (
    BadRequestError,
    ConflictError,
    ExternalAPIError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from .dependencies import ServiceUnavailableException
from .handlers import register_exception_handlers
from .rate_limits import RateLimitExceededError
from .health import ServiceUnavailableError
from .users import (
    UserNotFoundError,
    UserExistsError,
    UserCreationError,
    UserInactiveError,
    UserEmailConflictError,
    UserPhoneConflictError
)

from .auth import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidEmailFormatError,
    InvalidPasswordError,
    InvalidCurrentPasswordError,
    WeakPasswordError,
    TokenError,
    TokenMissingError,
    TokenExpiredError,
    TokenInvalidError,
    InvalidUserDataError,
    PasswordChangeFailedError,
    InvalidResetTokenError,
    ResetTokenExpiredError,
    UserNotFoundForResetError,
)

from .register import (
    EmailVerificationError,
    RoleAssignmentError,
    UserAlreadyExistsError,
)
__all__ = [
    # Base
    "BaseAPIException",
    # Rate Limits
    "RateLimitExceededError",
    # Common
    "NotFoundError",
    "BadRequestError",
    "ConflictError",
    "ForbiddenError",
    "ExternalAPIError",
    "ValidationError",
    # Handlers
    "register_exception_handlers",
    # Dependencies
    "ServiceUnavailableException",
    # Health
    "ServiceUnavailableError",
    # Users
    "UserNotFoundError",
    "UserExistsError",
    "UserCreationError",
    "UserInactiveError",
    "UserEmailConflictError",
    "UserPhoneConflictError",
    # Auth
    "AuthenticationError",
    "InvalidCredentialsError",
    "InvalidEmailFormatError",
    "InvalidPasswordError",
    "InvalidCurrentPasswordError",
    "WeakPasswordError",
    "TokenError",
    "TokenMissingError",
    "TokenExpiredError",
    "TokenInvalidError",
    "InvalidUserDataError",
    "PasswordChangeFailedError",
    "InvalidResetTokenError",
    "ResetTokenExpiredError",
    "UserNotFoundForResetError",

    # Registration
    "UserAlreadyExistsError",
    "EmailVerificationError",
    "RoleAssignmentError",
]
