"""
Схемы ответов для health check endpoints.
"""

from pydantic import Field

from app.schemas import BaseResponseSchema

from .base import HealthCheckDataSchema


class HealthCheckResponseSchema(BaseResponseSchema):
    """
    Схема ответа для health check endpoint.

    Attributes:
        success (bool): Успешность проверки
        message (str): Сообщение о статусе
        data (HealthCheckDataSchema): Детальные статусы сервисов
    """

    data: HealthCheckDataSchema = Field(..., description="Детальные статусы всех проверяемых сервисов")
