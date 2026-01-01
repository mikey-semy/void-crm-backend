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
from .health import (
    HealthCheckDataSchema,
    HealthCheckResponseSchema,
)
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
]
