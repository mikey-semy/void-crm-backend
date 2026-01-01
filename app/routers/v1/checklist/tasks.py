"""
Роутер для работы с задачами чек-листа.

Предоставляет HTTP API для CRUD операций с задачами чек-листа.
"""

from uuid import UUID

from app.core.dependencies.checklist import ChecklistServiceDep
from app.core.dependencies.websocket import WebSocketManagerDep
from app.routers.base import BaseRouter
from app.schemas.v1.checklist import (
    ChecklistTaskAssigneeUpdateSchema,
    ChecklistTaskCreateSchema,
    ChecklistTaskListItemSchema,
    ChecklistTaskListResponseSchema,
    ChecklistTaskNotesUpdateSchema,
    ChecklistTaskResponseSchema,
    ChecklistTaskStatusUpdateSchema,
    ChecklistTaskUpdateSchema,
)


class ChecklistTaskRouter(BaseRouter):
    """
    Роутер для API задач чек-листа.

    Endpoints:
        GET /checklist/tasks/{id} - Получить задачу
        GET /checklist/categories/{category_id}/tasks - Получить задачи категории
        POST /checklist/tasks - Создать задачу
        PUT /checklist/tasks/{id} - Обновить задачу
        PATCH /checklist/tasks/{id}/status - Обновить статус задачи
        DELETE /checklist/tasks/{id} - Удалить задачу
    """

    def __init__(self):
        """Инициализирует ChecklistTaskRouter."""
        super().__init__(prefix="checklist/tasks", tags=["Checklist - Tasks"])

    def configure(self):
        """Настройка endpoint'ов для задач."""

        @self.router.get(
            path="/{task_id}",
            response_model=ChecklistTaskResponseSchema,
            description="""\
## 📝 Получить задачу

Возвращает одну задачу чек-листа по ID.

### Path Parameters:
- **task_id** — UUID задачи

### Returns:
- Задача чек-листа
""",
        )
        async def get_task(
            task_id: UUID,
            service: ChecklistServiceDep,
        ) -> ChecklistTaskResponseSchema:
            """Получает задачу чек-листа."""
            task = await service.get_task_by_id(task_id)
            schema = ChecklistTaskListItemSchema.model_validate(task)

            return ChecklistTaskResponseSchema(success=True, message="Задача получена", data=schema)

        @self.router.post(
            path="",
            response_model=ChecklistTaskResponseSchema,
            status_code=201,
            description="""\
## ➕ Создать задачу

Создаёт новую задачу чек-листа.

### Request Body:
- **title** — Название задачи (обязательно)
- **description** — Описание задачи
- **status** — Статус (pending, in_progress, completed, skipped)
- **priority** — Приоритет (critical, high, medium, low)
- **assignee** — Исполнитель (partner1, partner2, both)
- **notes** — Заметки
- **order** — Порядок отображения
- **category_id** — UUID категории (обязательно)

### Returns:
- Созданная задача
""",
        )
        async def create_task(
            data: ChecklistTaskCreateSchema,
            service: ChecklistServiceDep,
            ws_manager: WebSocketManagerDep,
        ) -> ChecklistTaskResponseSchema:
            """Создаёт новую задачу чек-листа."""
            task = await service.create_task(data.model_dump())
            schema = ChecklistTaskListItemSchema.model_validate(task)

            # Отправляем событие всем подключенным клиентам
            await ws_manager.broadcast(
                {
                    "type": "task:created",
                    "data": schema.model_dump(mode="json"),
                }
            )

            return ChecklistTaskResponseSchema(success=True, message="Задача создана", data=schema)

        @self.router.put(
            path="/{task_id}",
            response_model=ChecklistTaskResponseSchema,
            description="""\
## ✏️ Обновить задачу

Обновляет существующую задачу чек-листа.
Автоматически устанавливает completed_at при изменении статуса на "completed".

### Path Parameters:
- **task_id** — UUID задачи

### Request Body:
- **title** — Новое название
- **description** — Новое описание
- **status** — Новый статус
- **priority** — Новый приоритет
- **assignee** — Новый исполнитель
- **notes** — Новые заметки
- **order** — Новый порядок

### Returns:
- Обновлённая задача
""",
        )
        async def update_task(
            task_id: UUID,
            data: ChecklistTaskUpdateSchema,
            service: ChecklistServiceDep,
            ws_manager: WebSocketManagerDep,
        ) -> ChecklistTaskResponseSchema:
            """Обновляет задачу чек-листа."""
            update_data = data.model_dump(exclude_unset=True)
            task = await service.update_task(task_id, update_data)
            schema = ChecklistTaskListItemSchema.model_validate(task)

            # Отправляем событие всем подключенным клиентам
            await ws_manager.broadcast(
                {
                    "type": "task:updated",
                    "data": schema.model_dump(mode="json"),
                }
            )

            return ChecklistTaskResponseSchema(success=True, message="Задача обновлена", data=schema)

        @self.router.patch(
            path="/{task_id}/status",
            response_model=ChecklistTaskResponseSchema,
            description="""\
## 🔄 Обновить статус задачи

Быстрое обновление только статуса задачи.
Автоматически устанавливает completed_at при статусе "completed".

### Path Parameters:
- **task_id** — UUID задачи

### Request Body:
- **status** — Новый статус (pending, in_progress, completed, skipped)

### Returns:
- Обновлённая задача
""",
        )
        async def update_task_status(
            task_id: UUID,
            data: ChecklistTaskStatusUpdateSchema,
            service: ChecklistServiceDep,
            ws_manager: WebSocketManagerDep,
        ) -> ChecklistTaskResponseSchema:
            """Обновляет статус задачи чек-листа."""
            task = await service.update_task_status(task_id, data.status)
            schema = ChecklistTaskListItemSchema.model_validate(task)

            # Отправляем событие всем подключенным клиентам
            await ws_manager.broadcast(
                {
                    "type": "task:updated",
                    "data": schema.model_dump(mode="json"),
                }
            )

            return ChecklistTaskResponseSchema(success=True, message="Статус задачи обновлён", data=schema)

        @self.router.patch(
            path="/{task_id}/notes",
            response_model=ChecklistTaskResponseSchema,
            description="""\
## 📝 Обновить заметки задачи

Быстрое обновление только заметок задачи.

### Path Parameters:
- **task_id** — UUID задачи

### Request Body:
- **notes** — Новые заметки

### Returns:
- Обновлённая задача
""",
        )
        async def update_task_notes(
            task_id: UUID,
            data: ChecklistTaskNotesUpdateSchema,
            service: ChecklistServiceDep,
            ws_manager: WebSocketManagerDep,
        ) -> ChecklistTaskResponseSchema:
            """Обновляет заметки задачи чек-листа."""
            task = await service.update_task(task_id, {"notes": data.notes})
            schema = ChecklistTaskListItemSchema.model_validate(task)

            # Отправляем событие всем подключенным клиентам
            await ws_manager.broadcast(
                {
                    "type": "task:updated",
                    "data": schema.model_dump(mode="json"),
                }
            )

            return ChecklistTaskResponseSchema(success=True, message="Заметки задачи обновлены", data=schema)

        @self.router.patch(
            path="/{task_id}/assignee",
            response_model=ChecklistTaskResponseSchema,
            description="""\
## 👤 Обновить исполнителя задачи

Быстрое обновление только исполнителя задачи.

### Path Parameters:
- **task_id** — UUID задачи

### Request Body:
- **assignee** — Новый исполнитель (partner1, partner2, both)

### Returns:
- Обновлённая задача
""",
        )
        async def update_task_assignee(
            task_id: UUID,
            data: ChecklistTaskAssigneeUpdateSchema,
            service: ChecklistServiceDep,
            ws_manager: WebSocketManagerDep,
        ) -> ChecklistTaskResponseSchema:
            """Обновляет исполнителя задачи чек-листа."""
            task = await service.update_task(task_id, {"assignee": data.assignee})
            schema = ChecklistTaskListItemSchema.model_validate(task)

            # Отправляем событие всем подключенным клиентам
            await ws_manager.broadcast(
                {
                    "type": "task:updated",
                    "data": schema.model_dump(mode="json"),
                }
            )

            return ChecklistTaskResponseSchema(success=True, message="Исполнитель задачи обновлён", data=schema)

        @self.router.delete(
            path="/{task_id}",
            response_model=ChecklistTaskListResponseSchema,
            description="""\
## 🗑️ Удалить задачу

Удаляет задачу чек-листа.

### Path Parameters:
- **task_id** — UUID задачи

### Returns:
- Пустой список
""",
        )
        async def delete_task(
            task_id: UUID,
            service: ChecklistServiceDep,
            ws_manager: WebSocketManagerDep,
        ) -> ChecklistTaskListResponseSchema:
            """Удаляет задачу чек-листа."""
            await service.delete_task(task_id)

            # Отправляем событие всем подключенным клиентам
            await ws_manager.broadcast(
                {
                    "type": "task:deleted",
                    "data": {"id": str(task_id)},
                }
            )

            return ChecklistTaskListResponseSchema(success=True, message="Задача удалена", data=[])


class ChecklistCategoryTaskRouter(BaseRouter):
    """
    Роутер для получения задач по категории.

    Endpoints:
        GET /checklist/categories/{category_id}/tasks - Получить задачи категории
    """

    def __init__(self):
        """Инициализирует ChecklistCategoryTaskRouter."""
        super().__init__(prefix="checklist/categories", tags=["Checklist - Tasks"])

    def configure(self):
        """Настройка endpoint'ов для задач категории."""

        @self.router.get(
            path="/{category_id}/tasks",
            response_model=ChecklistTaskListResponseSchema,
            description="""\
## 📝 Получить задачи категории

Возвращает все задачи указанной категории, отсортированные по order.

### Path Parameters:
- **category_id** — UUID категории

### Returns:
- Список задач категории
""",
        )
        async def get_tasks_by_category(
            category_id: UUID,
            service: ChecklistServiceDep,
        ) -> ChecklistTaskListResponseSchema:
            """Получает задачи категории."""
            tasks = await service.get_tasks_by_category(category_id)
            schemas = [ChecklistTaskListItemSchema.model_validate(task) for task in tasks]

            return ChecklistTaskListResponseSchema(success=True, message="Задачи получены", data=schemas)
