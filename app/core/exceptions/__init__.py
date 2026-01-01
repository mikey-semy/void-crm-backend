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
]
