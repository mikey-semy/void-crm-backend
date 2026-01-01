"""Схемы для чек-листа партнёрства."""

from .base import (
    ChecklistCategoryBaseSchema,
    ChecklistCategoryListItemSchema,
    ChecklistCategoryWithTasksSchema,
    ChecklistTaskBaseSchema,
    ChecklistTaskListItemSchema,
)
from .requests import (
    ChecklistCategoryCreateSchema,
    ChecklistCategoryUpdateSchema,
    ChecklistTaskAssigneeUpdateSchema,
    ChecklistTaskCreateSchema,
    ChecklistTaskNotesUpdateSchema,
    ChecklistTaskStatusUpdateSchema,
    ChecklistTaskUpdateSchema,
)
from .responses import (
    ChecklistAllCategoriesWithTasksResponseSchema,
    ChecklistCategoryListResponseSchema,
    ChecklistCategoryResponseSchema,
    ChecklistCategoryWithTasksResponseSchema,
    ChecklistTaskDeleteResponseSchema,
    ChecklistTaskListResponseSchema,
    ChecklistTaskResponseSchema,
)

__all__ = [
    # Base schemas
    "ChecklistCategoryBaseSchema",
    "ChecklistCategoryListItemSchema",
    "ChecklistCategoryWithTasksSchema",
    "ChecklistTaskBaseSchema",
    "ChecklistTaskListItemSchema",
    # Request schemas
    "ChecklistCategoryCreateSchema",
    "ChecklistCategoryUpdateSchema",
    "ChecklistTaskCreateSchema",
    "ChecklistTaskUpdateSchema",
    "ChecklistTaskStatusUpdateSchema",
    "ChecklistTaskNotesUpdateSchema",
    "ChecklistTaskAssigneeUpdateSchema",
    # Response schemas
    "ChecklistCategoryResponseSchema",
    "ChecklistCategoryListResponseSchema",
    "ChecklistCategoryWithTasksResponseSchema",
    "ChecklistAllCategoriesWithTasksResponseSchema",
    "ChecklistTaskResponseSchema",
    "ChecklistTaskListResponseSchema",
    "ChecklistTaskDeleteResponseSchema",
]
