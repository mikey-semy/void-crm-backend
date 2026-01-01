"""Схемы WebSocket сообщений для чек-листа."""

from typing import Any, Literal

from pydantic import Field

from app.schemas.websocket import WebSocketMessageSchema


class TaskUpdatedSchema(WebSocketMessageSchema):
    """
    Схема сообщения об обновлении задачи.

    Attributes:
        type: "task:updated"
        data: Данные обновленной задачи
    """

    type: Literal["task:updated"] = "task:updated"
    data: dict[str, Any] = Field(description="Данные обновленной задачи")


class TaskCreatedSchema(WebSocketMessageSchema):
    """
    Схема сообщения о создании задачи.

    Attributes:
        type: "task:created"
        data: Данные созданной задачи
    """

    type: Literal["task:created"] = "task:created"
    data: dict[str, Any] = Field(description="Данные созданной задачи")


class TaskDeletedSchema(WebSocketMessageSchema):
    """
    Схема сообщения об удалении задачи.

    Attributes:
        type: "task:deleted"
        data: ID удаленной задачи
    """

    type: Literal["task:deleted"] = "task:deleted"
    data: dict[str, str] = Field(description="ID удаленной задачи")


class CategoryUpdatedSchema(WebSocketMessageSchema):
    """
    Схема сообщения об обновлении категории.

    Attributes:
        type: "category:updated"
        data: Данные обновленной категории
    """

    type: Literal["category:updated"] = "category:updated"
    data: dict[str, Any] = Field(description="Данные обновленной категории")
