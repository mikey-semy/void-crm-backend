"""Базовые схемы для чек-листа партнёрства."""

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema, CommonBaseSchema


class ChecklistCategoryBaseSchema(BaseSchema):
    """
    Базовая схема категории чек-листа.

    Attributes:
        title: Название категории.
        description: Описание категории.
        icon: Название иконки (lucide-react).
        color: HEX цвет для UI.
        order: Порядок отображения.
    """

    title: str = Field(description="Название категории")
    description: str | None = Field(None, description="Описание категории")
    icon: str | None = Field(None, description="Название иконки (lucide-react)")
    color: str | None = Field(None, description="HEX цвет для UI")
    order: int = Field(description="Порядок отображения")


class ChecklistCategoryListItemSchema(CommonBaseSchema):
    """
    Схема элемента списка категорий чек-листа.

    Attributes:
        id: ID категории.
        title: Название категории.
        description: Описание категории.
        icon: Название иконки.
        color: HEX цвет.
        order: Порядок отображения.
        tasks_count: Количество задач в категории.
        completed_tasks_count: Количество завершённых задач.
        progress_percentage: Процент выполнения.
    """

    id: uuid.UUID = Field(description="ID категории")
    title: str = Field(description="Название категории")
    description: str | None = Field(None, description="Описание категории")
    icon: str | None = Field(None, description="Название иконки")
    color: str | None = Field(None, description="HEX цвет")
    order: int = Field(description="Порядок отображения")
    tasks_count: int = Field(default=0, description="Количество задач")
    completed_tasks_count: int = Field(default=0, description="Количество завершённых задач")
    progress_percentage: float = Field(default=0.0, description="Процент выполнения")


class ChecklistTaskBaseSchema(BaseSchema):
    """
    Базовая схема задачи чек-листа.

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

    title: str = Field(description="Название задачи")
    description: str | None = Field(None, description="Описание задачи")
    status: str = Field(description="Статус задачи")
    priority: str = Field(description="Приоритет задачи")
    assignee: str | None = Field(None, description="Назначенный исполнитель")
    notes: str | None = Field(None, description="Заметки к задаче")
    order: int = Field(description="Порядок отображения")
    category_id: uuid.UUID = Field(description="ID категории")


class ChecklistTaskListItemSchema(CommonBaseSchema):
    """
    Схема элемента списка задач чек-листа.

    Attributes:
        id: ID задачи.
        title: Название задачи.
        description: Описание задачи.
        status: Статус задачи.
        priority: Приоритет задачи.
        assignee: Назначенный исполнитель.
        notes: Заметки к задаче.
        order: Порядок отображения.
        category_id: ID категории.
        completed_at: Время завершения задачи.
    """

    id: uuid.UUID = Field(description="ID задачи")
    title: str = Field(description="Название задачи")
    description: str | None = Field(None, description="Описание задачи")
    status: str = Field(description="Статус задачи")
    priority: str = Field(description="Приоритет задачи")
    assignee: str | None = Field(None, description="Назначенный исполнитель")
    notes: str | None = Field(None, description="Заметки к задаче")
    order: int = Field(description="Порядок отображения")
    category_id: uuid.UUID = Field(description="ID категории")
    completed_at: datetime | None = Field(None, description="Время завершения задачи")


class ChecklistCategoryWithTasksSchema(CommonBaseSchema):
    """
    Схема категории с задачами.

    Attributes:
        id: ID категории.
        title: Название категории.
        description: Описание категории.
        icon: Название иконки.
        color: HEX цвет.
        order: Порядок отображения.
        tasks: Список задач категории.
        tasks_count: Количество задач.
        completed_tasks_count: Количество завершённых задач.
        progress_percentage: Процент выполнения.
    """

    id: uuid.UUID = Field(description="ID категории")
    title: str = Field(description="Название категории")
    description: str | None = Field(None, description="Описание категории")
    icon: str | None = Field(None, description="Название иконки")
    color: str | None = Field(None, description="HEX цвет")
    order: int = Field(description="Порядок отображения")
    tasks: list[ChecklistTaskListItemSchema] = Field(default_factory=list, description="Список задач")
    tasks_count: int = Field(default=0, description="Количество задач")
    completed_tasks_count: int = Field(default=0, description="Количество завершённых задач")
    progress_percentage: float = Field(default=0.0, description="Процент выполнения")
