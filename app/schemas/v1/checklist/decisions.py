"""Схемы для полей решений задач чек-листа."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas import BaseRequestSchema, BaseResponseSchema, CommonBaseSchema


# ==================== Типы ====================

DecisionFieldType = Literal["text", "number", "select", "boolean", "date", "time"]
AssigneeType = Literal["partner1", "partner2", "both"]


# ==================== Опция выбора ====================


class SelectOptionSchema(CommonBaseSchema):
    """Схема опции для select-поля."""

    value: str = Field(description="Значение опции")
    label: str = Field(description="Отображаемый текст")


# ==================== Правила валидации ====================


class ValidationRulesSchema(CommonBaseSchema):
    """Схема правил валидации поля."""

    min: float | None = Field(None, description="Минимальное значение (для number)")
    max: float | None = Field(None, description="Максимальное значение (для number)")
    min_length: int | None = Field(None, description="Минимальная длина (для text)")
    max_length: int | None = Field(None, description="Максимальная длина (для text)")
    pattern: str | None = Field(None, description="Regex паттерн (для text)")


# ==================== Базовые схемы полей ====================


class DecisionFieldBaseSchema(CommonBaseSchema):
    """Базовая схема поля решения."""

    field_key: str = Field(description="Уникальный ключ поля (snake_case)")
    field_type: DecisionFieldType = Field(description="Тип поля")
    label: str = Field(description="Человекочитаемая метка")
    description: str | None = Field(None, description="Подсказка для заполнения")
    options: list[SelectOptionSchema] | None = Field(None, description="Опции для select")
    is_required: bool = Field(False, description="Обязательное поле")
    order: int = Field(0, description="Порядок отображения")
    validation_rules: ValidationRulesSchema | None = Field(None, description="Правила валидации")


class DecisionFieldSchema(CommonBaseSchema):
    """Схема поля решения с ID и значением."""

    id: UUID = Field(description="ID поля")
    task_id: UUID = Field(description="ID задачи")
    field_key: str = Field(description="Уникальный ключ поля")
    field_type: DecisionFieldType = Field(description="Тип поля")
    label: str = Field(description="Человекочитаемая метка")
    description: str | None = Field(None, description="Подсказка для заполнения")
    options: list[SelectOptionSchema] | None = Field(None, description="Опции для select")
    is_required: bool = Field(False, description="Обязательное поле")
    order: int = Field(0, description="Порядок отображения")
    validation_rules: ValidationRulesSchema | None = Field(None, description="Правила валидации")
    value: Any | None = Field(None, description="Текущее значение")
    filled_by: AssigneeType | None = Field(None, description="Кто заполнил")
    filled_at: datetime | None = Field(None, description="Когда заполнено")


class DecisionFieldListItemSchema(CommonBaseSchema):
    """Схема элемента списка полей решений."""

    id: UUID = Field(description="ID поля")
    task_id: UUID = Field(description="ID задачи")
    field_key: str = Field(description="Уникальный ключ поля")
    field_type: DecisionFieldType = Field(description="Тип поля")
    label: str = Field(description="Человекочитаемая метка")
    description: str | None = Field(None, description="Подсказка")
    options: list[SelectOptionSchema] | None = Field(None, description="Опции для select")
    is_required: bool = Field(False, description="Обязательное поле")
    order: int = Field(0, description="Порядок отображения")
    value: Any | None = Field(None, description="Текущее значение")
    filled_by: AssigneeType | None = Field(None, description="Кто заполнил")
    filled_at: datetime | None = Field(None, description="Когда заполнено")


# ==================== Схемы запросов ====================


class DecisionFieldCreateSchema(BaseRequestSchema):
    """Схема создания поля решения."""

    field_key: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    field_type: DecisionFieldType
    label: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    options: list[SelectOptionSchema] | None = None
    is_required: bool = False
    order: int = 0
    validation_rules: ValidationRulesSchema | None = None

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[SelectOptionSchema] | None, info) -> list[SelectOptionSchema] | None:
        """Валидация: options обязательны для select."""
        if info.data.get("field_type") == "select" and not v:
            raise ValueError("options required for select field type")
        return v


class DecisionFieldUpdateSchema(BaseRequestSchema):
    """Схема обновления поля решения."""

    label: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    options: list[SelectOptionSchema] | None = None
    is_required: bool | None = None
    order: int | None = None
    validation_rules: ValidationRulesSchema | None = None


class DecisionValueUpdateSchema(BaseRequestSchema):
    """Схема обновления значения решения."""

    value: Any = Field(description="Значение поля")
    filled_by: AssigneeType | None = Field(None, description="Кто заполняет")


class BulkDecisionValueItem(CommonBaseSchema):
    """Элемент массового обновления значений."""

    field_id: UUID = Field(description="ID поля")
    value: Any = Field(description="Значение")
    filled_by: AssigneeType | None = Field(None, description="Кто заполняет")


class BulkDecisionValuesUpdateSchema(BaseRequestSchema):
    """Схема массового обновления значений решений."""

    values: list[BulkDecisionValueItem] = Field(description="Список значений для обновления")


# ==================== Схемы ответов ====================


class DecisionFieldResponseSchema(BaseResponseSchema):
    """Ответ с одним полем решения."""

    data: DecisionFieldSchema


class DecisionFieldListResponseSchema(BaseResponseSchema):
    """Ответ со списком полей решений."""

    data: list[DecisionFieldListItemSchema]


# ==================== Схемы для страницы решений ====================


class TaskDecisionSummarySchema(CommonBaseSchema):
    """Сводка решений по одной задаче."""

    task_id: UUID = Field(description="ID задачи")
    task_title: str = Field(description="Название задачи")
    task_status: str = Field(description="Статус задачи")
    notes: str | None = Field(None, description="Комментарии к задаче")
    assignee: AssigneeType | None = Field(None, description="Ответственный")
    completed_at: datetime | None = Field(None, description="Дата завершения")
    fields: list[DecisionFieldListItemSchema] = Field(description="Поля решений")
    filled_count: int = Field(description="Количество заполненных полей")
    total_count: int = Field(description="Общее количество полей")
    is_complete: bool = Field(description="Все обязательные поля заполнены")


class CategoryDecisionSummarySchema(CommonBaseSchema):
    """Сводка решений по категории."""

    category_id: UUID = Field(description="ID категории")
    category_title: str = Field(description="Название категории")
    category_icon: str | None = Field(None, description="Иконка категории")
    category_color: str | None = Field(None, description="Цвет категории")
    tasks: list[TaskDecisionSummarySchema] = Field(description="Задачи с решениями")
    filled_count: int = Field(description="Всего заполненных полей в категории")
    total_count: int = Field(description="Всего полей в категории")
    progress_percentage: float = Field(description="Процент заполненности")


class PartnershipDecisionsSummarySchema(CommonBaseSchema):
    """Полная сводка решений партнёрства."""

    categories: list[CategoryDecisionSummarySchema] = Field(description="Категории с решениями")
    total_filled: int = Field(description="Всего заполненных полей")
    total_fields: int = Field(description="Всего полей решений")
    overall_progress: float = Field(description="Общий процент заполненности")


class PartnershipDecisionsResponseSchema(BaseResponseSchema):
    """Ответ со сводкой решений."""

    data: PartnershipDecisionsSummarySchema
