"""Базовые схемы для WebSocket сообщений."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class WebSocketMessageSchema(BaseModel):
    """
    Базовая схема WebSocket сообщения.

    Attributes:
        type: Тип сообщения
        data: Данные сообщения
        message: Опциональное текстовое сообщение
    """

    type: str = Field(description="Тип сообщения")
    data: dict[str, Any] | None = Field(None, description="Данные сообщения")
    message: str | None = Field(None, description="Текстовое сообщение")


class ConnectionEstablishedSchema(WebSocketMessageSchema):
    """
    Схема сообщения при установке соединения.

    Attributes:
        type: "connection:established"
        message: Сообщение о подключении
    """

    type: Literal["connection:established"] = "connection:established"
    message: str = "Подключено"


class HeartbeatResponseSchema(WebSocketMessageSchema):
    """
    Схема ответа на heartbeat.

    Attributes:
        type: "pong"
        message: "Connection alive"
    """

    type: Literal["pong"] = "pong"
    message: str = "Connection alive"
