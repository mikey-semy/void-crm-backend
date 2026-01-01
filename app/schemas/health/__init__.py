"""
Схемы для health check endpoints.

Exports:
    - HealthCheckDataSchema: Данные статусов сервисов
    - HealthCheckResponseSchema: Полный ответ health check
"""

from .base import HealthCheckDataSchema
from .responses import HealthCheckResponseSchema

__all__ = [
    # Base schemas
    "HealthCheckDataSchema",
    # Response schemas
    "HealthCheckResponseSchema",
]
