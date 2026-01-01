"""
Базовые схемы для health check.

Содержит схемы данных для проверки состояния приложения.
"""

from pydantic import Field

from app.schemas import CommonBaseSchema


class HealthCheckDataSchema(CommonBaseSchema):
    """
    Схема данных для health check.

    Attributes:
        app (str): Статус приложения
        db (str): Статус базы данных
        redis (str): Статус Redis
    """

    app: str = Field(default="ok", description="Статус приложения", examples=["ok"])
    db: str = Field(
        default="ok",
        description="Статус базы данных",
        examples=["ok", "fail", "unknown"],
    )
    redis: str = Field(default="ok", description="Статус Redis", examples=["ok", "fail", "unknown"])
