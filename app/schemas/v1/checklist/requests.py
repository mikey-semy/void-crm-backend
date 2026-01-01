"""Схемы запросов для чек-листа."""

import uuid
from typing import Literal

from pydantic import Field

from app.schemas.base import BaseRequestSchema


class ChecklistCategoryCreateSchema(BaseRequestSchema):
    """
    Схема создания категории чек-листа.

    Attributes:
        title: Название категории.
        description: Описание категории.
        icon: Название иконки.
        color: HEX цвет.
        order: Порядок отображения.
    """

    title: str = Field(min_length=2, max_length=255, description="Название категории")
    description: str | None = Field(None, max_length=1000, description="Описание категории")
    icon: str | None = Field(None, max_length=50, description="Название иконки")
    color: str | None = Field(None, max_length=7, description="HEX цвет (#RRGGBB)")
    order: int = Field(0, description="Порядок отображения")


class ChecklistCategoryUpdateSchema(BaseRequestSchema):
    """
    Схема обновления категории чек-листа.

    Attributes:
        title: Новое название.
        description: Новое описание.
        icon: Новая иконка.
        color: Новый цвет.
        order: Новый порядок.
    """

    title: str | None = Field(None, min_length=2, max_length=255, description="Новое название")
    description: str | None = Field(None, max_length=1000, description="Новое описание")
    icon: str | None = Field(None, max_length=50, description="Новая иконка")
    color: str | None = Field(None, max_length=7, description="Новый цвет")
    order: int | None = Field(None, description="Новый порядок")


class ChecklistTaskCreateSchema(BaseRequestSchema):
    """
    Схема создания задачи чек-листа.

    Attributes:
        title: Название задачи.
        description: Описание задачи.
        status: Статус задачи.
        priority: Приоритет задачи.
        assignee: Назначенный исполнитель.
        notes: Заметки к задаче.
        order: Порядок отображения.
        category_id: ID категории.
    """

    title: str = Field(min_length=2, max_length=500, description="Название задачи")
    description: str | None = Field(None, max_length=5000, description="Описание задачи")
    status: Literal["pending", "in_progress", "completed", "skipped"] = Field("pending", description="Статус задачи")
    priority: Literal["critical", "high", "medium", "low"] = Field("medium", description="Приоритет задачи")
    assignee: Literal["partner1", "partner2", "both"] | None = Field(None, description="Назначенный исполнитель")
    notes: str | None = Field(None, max_length=5000, description="Заметки к задаче")
    order: int = Field(0, description="Порядок отображения")
    category_id: uuid.UUID = Field(description="ID категории")


class ChecklistTaskUpdateSchema(BaseRequestSchema):
    """
    Схема обновления задачи чек-листа.

    Attributes:
        title: Новое название.
        description: Новое описание.
        status: Новый статус.
        priority: Новый приоритет.
        assignee: Новый исполнитель.
        notes: Новые заметки.
        order: Новый порядок.
    """

    title: str | None = Field(None, min_length=2, max_length=500, description="Новое название")
    description: str | None = Field(None, max_length=5000, description="Новое описание")
    status: Literal["pending", "in_progress", "completed", "skipped"] | None = Field(None, description="Новый статус")
    priority: Literal["critical", "high", "medium", "low"] | None = Field(None, description="Новый приоритет")
    assignee: Literal["partner1", "partner2", "both"] | None = Field(None, description="Новый исполнитель")
    notes: str | None = Field(None, max_length=5000, description="Новые заметки")
    order: int | None = Field(None, description="Новый порядок")


class ChecklistTaskStatusUpdateSchema(BaseRequestSchema):
    """
    Схема для быстрого обновления статуса задачи.

    Используется для WebSocket и быстрых обновлений.

    Attributes:
        status: Новый статус задачи.
    """

    status: Literal["pending", "in_progress", "completed", "skipped"] = Field(description="Новый статус задачи")


class ChecklistTaskNotesUpdateSchema(BaseRequestSchema):
    """
    Схема для быстрого обновления заметок задачи.

    Attributes:
        notes: Новые заметки к задаче.
    """

    notes: str = Field(max_length=5000, description="Новые заметки к задаче")


class ChecklistTaskAssigneeUpdateSchema(BaseRequestSchema):
    """
    Схема для быстрого обновления исполнителя задачи.

    Attributes:
        assignee: Новый исполнитель задачи.
    """

    assignee: Literal["partner1", "partner2", "both"] = Field(description="Новый исполнитель задачи")
