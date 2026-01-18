"""
Роутер для работы с полями решений задач чек-листа.

Предоставляет HTTP API для:
- CRUD операций с полями решений
- Обновления значений решений
- Получения сводки решений партнёрства
"""

from uuid import UUID

from app.core.dependencies.checklist import DecisionServiceDep
from app.routers.base import ProtectedRouter
from app.schemas.v1.checklist import (
    BulkDecisionValuesUpdateSchema,
    DecisionFieldCreateSchema,
    DecisionFieldListItemSchema,
    DecisionFieldListResponseSchema,
    DecisionFieldResponseSchema,
    DecisionFieldSchema,
    DecisionFieldUpdateSchema,
    DecisionValueUpdateSchema,
    PartnershipDecisionsResponseSchema,
    PartnershipDecisionsSummarySchema,
)


class DecisionFieldRouter(ProtectedRouter):
    """
    Роутер для API полей решений задач.

    Endpoints:
        GET /checklist/tasks/{task_id}/decision-fields - Получить поля решений задачи
        POST /checklist/tasks/{task_id}/decision-fields - Создать поле решения
        PUT /checklist/decision-fields/{field_id} - Обновить поле решения
        DELETE /checklist/decision-fields/{field_id} - Удалить поле решения
        PATCH /checklist/decision-fields/{field_id}/value - Обновить значение
        PATCH /checklist/tasks/{task_id}/decision-values - Массовое обновление
    """

    def __init__(self):
        """Инициализирует DecisionFieldRouter."""
        super().__init__(prefix="checklist", tags=["Checklist - Decisions"])

    def configure(self):
        """Настройка endpoint'ов для полей решений."""

        @self.router.get(
            path="/tasks/{task_id}/decision-fields",
            response_model=DecisionFieldListResponseSchema,
            description="""\
## Получить поля решений задачи

Возвращает все поля решений для указанной задачи с их текущими значениями.

### Path Parameters:
- **task_id** — UUID задачи

### Returns:
- Список полей решений с их значениями
""",
        )
        async def get_task_decision_fields(
            task_id: UUID,
            service: DecisionServiceDep,
        ) -> DecisionFieldListResponseSchema:
            """Получает все поля решений задачи."""
            fields = await service.get_fields_by_task(task_id)
            schemas = [
                DecisionFieldListItemSchema(
                    id=f.id,
                    task_id=f.task_id,
                    field_key=f.field_key,
                    field_type=f.field_type,
                    label=f.label,
                    description=f.description,
                    options=f.options,
                    is_required=f.is_required,
                    order=f.order,
                    value=f.value.value if f.value else None,
                    filled_by=f.value.filled_by if f.value else None,
                    filled_at=f.value.filled_at if f.value else None,
                )
                for f in fields
            ]

            return DecisionFieldListResponseSchema(
                success=True,
                message="Поля решений получены",
                data=schemas,
            )

        @self.router.post(
            path="/tasks/{task_id}/decision-fields",
            response_model=DecisionFieldResponseSchema,
            status_code=201,
            description="""\
## Создать поле решения

Создаёт новое поле решения для задачи.

### Path Parameters:
- **task_id** — UUID задачи

### Request Body:
- **field_key** — Уникальный ключ поля (snake_case)
- **field_type** — Тип поля (text, number, select, boolean, date, time)
- **label** — Человекочитаемая метка
- **description** — Подсказка для заполнения
- **options** — Опции для select (массив {value, label})
- **is_required** — Обязательное поле
- **order** — Порядок отображения
- **validation_rules** — Правила валидации {min, max, pattern}

### Returns:
- Созданное поле решения
""",
        )
        async def create_decision_field(
            task_id: UUID,
            data: DecisionFieldCreateSchema,
            service: DecisionServiceDep,
        ) -> DecisionFieldResponseSchema:
            """Создаёт новое поле решения для задачи."""
            field = await service.create_field(task_id, data.model_dump())
            schema = DecisionFieldSchema(
                id=field.id,
                task_id=field.task_id,
                field_key=field.field_key,
                field_type=field.field_type,
                label=field.label,
                description=field.description,
                options=field.options,
                is_required=field.is_required,
                order=field.order,
                validation_rules=field.validation_rules,
                value=None,
                filled_by=None,
                filled_at=None,
            )

            return DecisionFieldResponseSchema(
                success=True,
                message="Поле решения создано",
                data=schema,
            )

        @self.router.put(
            path="/decision-fields/{field_id}",
            response_model=DecisionFieldResponseSchema,
            description="""\
## Обновить поле решения

Обновляет существующее поле решения.

### Path Parameters:
- **field_id** — UUID поля решения

### Request Body:
- **label** — Новая метка
- **description** — Новая подсказка
- **options** — Новые опции для select
- **is_required** — Обязательность поля
- **order** — Новый порядок
- **validation_rules** — Новые правила валидации

### Returns:
- Обновлённое поле решения
""",
        )
        async def update_decision_field(
            field_id: UUID,
            data: DecisionFieldUpdateSchema,
            service: DecisionServiceDep,
        ) -> DecisionFieldResponseSchema:
            """Обновляет поле решения."""
            update_data = data.model_dump(exclude_unset=True)
            field = await service.update_field(field_id, update_data)
            schema = DecisionFieldSchema(
                id=field.id,
                task_id=field.task_id,
                field_key=field.field_key,
                field_type=field.field_type,
                label=field.label,
                description=field.description,
                options=field.options,
                is_required=field.is_required,
                order=field.order,
                validation_rules=field.validation_rules,
                value=field.value.value if field.value else None,
                filled_by=field.value.filled_by if field.value else None,
                filled_at=field.value.filled_at if field.value else None,
            )

            return DecisionFieldResponseSchema(
                success=True,
                message="Поле решения обновлено",
                data=schema,
            )

        @self.router.delete(
            path="/decision-fields/{field_id}",
            response_model=DecisionFieldListResponseSchema,
            description="""\
## Удалить поле решения

Удаляет поле решения и его значение (CASCADE).

### Path Parameters:
- **field_id** — UUID поля решения

### Returns:
- Пустой список
""",
        )
        async def delete_decision_field(
            field_id: UUID,
            service: DecisionServiceDep,
        ) -> DecisionFieldListResponseSchema:
            """Удаляет поле решения."""
            await service.delete_field(field_id)

            return DecisionFieldListResponseSchema(
                success=True,
                message="Поле решения удалено",
                data=[],
            )

        @self.router.patch(
            path="/decision-fields/{field_id}/value",
            response_model=DecisionFieldResponseSchema,
            description="""\
## Обновить значение поля решения

Обновляет или создаёт значение для поля решения.
Валидирует значение согласно типу поля и правилам.

### Path Parameters:
- **field_id** — UUID поля решения

### Request Body:
- **value** — Значение поля (тип зависит от field_type)
- **filled_by** — Кто заполнил (partner1, partner2, both)

### Returns:
- Обновлённое поле с новым значением
""",
        )
        async def update_decision_value(
            field_id: UUID,
            data: DecisionValueUpdateSchema,
            service: DecisionServiceDep,
        ) -> DecisionFieldResponseSchema:
            """Обновляет значение поля решения."""
            field = await service.update_value(field_id, data.value, data.filled_by)
            schema = DecisionFieldSchema(
                id=field.id,
                task_id=field.task_id,
                field_key=field.field_key,
                field_type=field.field_type,
                label=field.label,
                description=field.description,
                options=field.options,
                is_required=field.is_required,
                order=field.order,
                validation_rules=field.validation_rules,
                value=field.value.value if field.value else None,
                filled_by=field.value.filled_by if field.value else None,
                filled_at=field.value.filled_at if field.value else None,
            )

            return DecisionFieldResponseSchema(
                success=True,
                message="Значение обновлено",
                data=schema,
            )

        @self.router.patch(
            path="/tasks/{task_id}/decision-values",
            response_model=DecisionFieldListResponseSchema,
            description="""\
## Массовое обновление значений решений

Обновляет несколько значений полей решений за один запрос.

### Path Parameters:
- **task_id** — UUID задачи

### Request Body:
- **values** — Массив [{field_id, value, filled_by}, ...]

### Returns:
- Список обновлённых полей
""",
        )
        async def bulk_update_decision_values(
            task_id: UUID,
            data: BulkDecisionValuesUpdateSchema,
            service: DecisionServiceDep,
        ) -> DecisionFieldListResponseSchema:
            """Массовое обновление значений решений."""
            values = [
                {
                    "field_id": v.field_id,
                    "value": v.value,
                    "filled_by": v.filled_by,
                }
                for v in data.values
            ]
            fields = await service.bulk_update_values(task_id, values)
            schemas = [
                DecisionFieldListItemSchema(
                    id=f.id,
                    task_id=f.task_id,
                    field_key=f.field_key,
                    field_type=f.field_type,
                    label=f.label,
                    description=f.description,
                    options=f.options,
                    is_required=f.is_required,
                    order=f.order,
                    value=f.value.value if f.value else None,
                    filled_by=f.value.filled_by if f.value else None,
                    filled_at=f.value.filled_at if f.value else None,
                )
                for f in fields
            ]

            return DecisionFieldListResponseSchema(
                success=True,
                message="Значения обновлены",
                data=schemas,
            )


class PartnershipDecisionsRouter(ProtectedRouter):
    """
    Роутер для страницы "Решения партнёрства".

    Endpoints:
        GET /partnership-decisions - Получить сводку всех решений
    """

    def __init__(self):
        """Инициализирует PartnershipDecisionsRouter."""
        super().__init__(prefix="partnership-decisions", tags=["Partnership Decisions"])

    def configure(self):
        """Настройка endpoint'ов для сводки решений."""

        @self.router.get(
            path="",
            response_model=PartnershipDecisionsResponseSchema,
            description="""\
## Сводка решений партнёрства

Возвращает все заполненные решения, сгруппированные по категориям чек-листа.
Показывает только задачи с полями решений.

### Query Parameters:
- **include_empty** — Включать задачи без заполненных полей (default: false)

### Returns:
- Список категорий с задачами и их решениями
- Общий процент заполненности
""",
        )
        async def get_partnership_decisions(
            service: DecisionServiceDep,
            include_empty: bool = False,
        ) -> PartnershipDecisionsResponseSchema:
            """Получает сводку решений партнёрства."""
            summary = await service.get_decisions_summary(include_empty=include_empty)

            return PartnershipDecisionsResponseSchema(
                success=True,
                message="Решения партнёрства получены",
                data=PartnershipDecisionsSummarySchema(**summary),
            )

        @self.router.get(
            path="/summary",
            response_model=PartnershipDecisionsResponseSchema,
            description="""\
## Сводка завершённых задач партнёрства

Возвращает все завершённые задачи (status='completed') с их данными:
- Комментарии (notes)
- Ответственный (assignee)
- Дата завершения (completed_at)
- Поля решений (decision_fields), если есть

### Returns:
- Список категорий с завершёнными задачами
- Общий процент заполненности полей решений
""",
        )
        async def get_partnership_summary(
            service: DecisionServiceDep,
        ) -> PartnershipDecisionsResponseSchema:
            """Получает сводку всех завершённых задач партнёрства."""
            summary = await service.get_completed_tasks_summary()

            return PartnershipDecisionsResponseSchema(
                success=True,
                message="Сводка завершённых задач получена",
                data=PartnershipDecisionsSummarySchema(**summary),
            )
