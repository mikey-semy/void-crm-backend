"""
Роутер для работы с категориями чек-листа.

Предоставляет HTTP API для CRUD операций с категориями чек-листа.
"""

from uuid import UUID

from app.core.dependencies.checklist import ChecklistServiceDep
from app.routers.base import ProtectedRouter
from app.schemas.v1.checklist import (
    ChecklistAllCategoriesWithTasksResponseSchema,
    ChecklistCategoryCreateSchema,
    ChecklistCategoryListItemSchema,
    ChecklistCategoryListResponseSchema,
    ChecklistCategoryResponseSchema,
    ChecklistCategoryUpdateSchema,
    ChecklistCategoryWithTasksResponseSchema,
    ChecklistCategoryWithTasksSchema,
)


class ChecklistCategoryRouter(ProtectedRouter):
    """
    Роутер для API категорий чек-листа.

    Endpoints:
        GET /checklist/categories - Получить все категории с задачами
        GET /checklist/categories/{id} - Получить категорию с задачами
        POST /checklist/categories - Создать категорию
        PUT /checklist/categories/{id} - Обновить категорию
        DELETE /checklist/categories/{id} - Удалить категорию
    """

    def __init__(self):
        """Инициализирует ChecklistCategoryRouter."""
        super().__init__(prefix="checklist/categories", tags=["Checklist - Categories"])

    def configure(self):
        """Настройка endpoint'ов для категорий."""

        @self.router.get(
            path="",
            response_model=ChecklistAllCategoriesWithTasksResponseSchema,
            description="""\
## 📋 Получить все категории чек-листа с задачами

Возвращает все категории чек-листа с загруженными задачами,
отсортированные по order.

### Returns:
- Список категорий с задачами, прогрессом выполнения
""",
        )
        async def get_all_categories_with_tasks(
            service: ChecklistServiceDep,
        ) -> ChecklistAllCategoriesWithTasksResponseSchema:
            """Получает все категории чек-листа с задачами."""
            categories = await service.get_all_categories_with_tasks()
            schemas = [ChecklistCategoryWithTasksSchema.model_validate(cat) for cat in categories]

            return ChecklistAllCategoriesWithTasksResponseSchema(
                success=True, message="Категории чек-листа получены", data=schemas
            )

        @self.router.get(
            path="/{category_id}",
            response_model=ChecklistCategoryWithTasksResponseSchema,
            description="""\
## 📂 Получить категорию с задачами

Возвращает одну категорию чек-листа со всеми её задачами.

### Path Parameters:
- **category_id** — UUID категории

### Returns:
- Категория с задачами
""",
        )
        async def get_category_with_tasks(
            category_id: UUID,
            service: ChecklistServiceDep,
        ) -> ChecklistCategoryWithTasksResponseSchema:
            """Получает категорию чек-листа с задачами."""
            category = await service.get_category_by_id(category_id)
            schema = ChecklistCategoryWithTasksSchema.model_validate(category)

            return ChecklistCategoryWithTasksResponseSchema(success=True, message="Категория получена", data=schema)

        @self.router.post(
            path="",
            response_model=ChecklistCategoryResponseSchema,
            status_code=201,
            description="""\
## ➕ Создать категорию чек-листа

Создаёт новую категорию чек-листа.

### Request Body:
- **title** — Название категории (обязательно)
- **description** — Описание категории
- **icon** — Название иконки (lucide-react)
- **color** — HEX цвет для UI
- **order** — Порядок отображения

### Returns:
- Созданная категория
""",
        )
        async def create_category(
            data: ChecklistCategoryCreateSchema,
            service: ChecklistServiceDep,
        ) -> ChecklistCategoryResponseSchema:
            """Создаёт новую категорию чек-листа."""
            category = await service.create_category(data.model_dump())
            schema = ChecklistCategoryListItemSchema.model_validate(category)

            return ChecklistCategoryResponseSchema(success=True, message="Категория создана", data=schema)

        @self.router.put(
            path="/{category_id}",
            response_model=ChecklistCategoryResponseSchema,
            description="""\
## ✏️ Обновить категорию чек-листа

Обновляет существующую категорию чек-листа.

### Path Parameters:
- **category_id** — UUID категории

### Request Body:
- **title** — Новое название
- **description** — Новое описание
- **icon** — Новая иконка
- **color** — Новый цвет
- **order** — Новый порядок

### Returns:
- Обновлённая категория
""",
        )
        async def update_category(
            category_id: UUID,
            data: ChecklistCategoryUpdateSchema,
            service: ChecklistServiceDep,
        ) -> ChecklistCategoryResponseSchema:
            """Обновляет категорию чек-листа."""
            update_data = data.model_dump(exclude_unset=True)
            category = await service.update_category(category_id, update_data)
            schema = ChecklistCategoryListItemSchema.model_validate(category)

            return ChecklistCategoryResponseSchema(success=True, message="Категория обновлена", data=schema)

        @self.router.delete(
            path="/{category_id}",
            response_model=ChecklistCategoryListResponseSchema,
            description="""\
## 🗑️ Удалить категорию чек-листа

Удаляет категорию и все её задачи (CASCADE).

### Path Parameters:
- **category_id** — UUID категории

### Returns:
- Пустой список
""",
        )
        async def delete_category(
            category_id: UUID,
            service: ChecklistServiceDep,
        ) -> ChecklistCategoryListResponseSchema:
            """Удаляет категорию чек-листа."""
            await service.delete_category(category_id)

            return ChecklistCategoryListResponseSchema(success=True, message="Категория удалена", data=[])
