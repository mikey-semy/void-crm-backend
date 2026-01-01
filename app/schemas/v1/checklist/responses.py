"""Схемы ответов для чек-листа."""

from app.schemas.base import BaseResponseSchema

from .base import (
    ChecklistCategoryListItemSchema,
    ChecklistCategoryWithTasksSchema,
    ChecklistTaskListItemSchema,
)


class ChecklistCategoryResponseSchema(BaseResponseSchema):
    """
    Схема ответа с одной категорией чек-листа.

    Attributes:
        data: Информация о категории.
    """

    data: ChecklistCategoryListItemSchema


class ChecklistCategoryListResponseSchema(BaseResponseSchema):
    """
    Схема ответа со списком категорий чек-листа.

    Attributes:
        data: Список категорий.
    """

    data: list[ChecklistCategoryListItemSchema]


class ChecklistCategoryWithTasksResponseSchema(BaseResponseSchema):
    """
    Схема ответа с категорией и её задачами.

    Attributes:
        data: Категория с задачами.
    """

    data: ChecklistCategoryWithTasksSchema


class ChecklistAllCategoriesWithTasksResponseSchema(BaseResponseSchema):
    """
    Схема ответа со всеми категориями и задачами.

    Attributes:
        data: Список всех категорий с задачами.
    """

    data: list[ChecklistCategoryWithTasksSchema]


class ChecklistTaskResponseSchema(BaseResponseSchema):
    """
    Схема ответа с одной задачей чек-листа.

    Attributes:
        data: Информация о задаче.
    """

    data: ChecklistTaskListItemSchema


class ChecklistTaskListResponseSchema(BaseResponseSchema):
    """
    Схема ответа со списком задач чек-листа.

    Attributes:
        data: Список задач.
    """

    data: list[ChecklistTaskListItemSchema]


class ChecklistTaskDeleteResponseSchema(BaseResponseSchema):
    """
    Схема ответа при удалении задачи.

    Attributes:
        data: Информация об удалённой задаче.
    """

    data: ChecklistTaskListItemSchema
