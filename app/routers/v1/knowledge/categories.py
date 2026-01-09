"""
Роутер для работы с категориями базы знаний.

Предоставляет HTTP API для CRUD операций с категориями.
"""

from uuid import UUID

from app.core.dependencies.knowledge import KnowledgeServiceDep
from app.routers.base import BaseRouter, ProtectedRouter
from app.schemas.v1.knowledge import (
    KnowledgeCategoryCreateSchema,
    KnowledgeCategoryDeletedSchema,
    KnowledgeCategoryListItemSchema,
    KnowledgeCategoryListResponseSchema,
    KnowledgeCategoryResponseSchema,
    KnowledgeCategoryUpdateSchema,
)


class KnowledgeCategoryRouter(BaseRouter):
    """
    Роутер для API категорий базы знаний.

    Public endpoints:
        GET /knowledge/categories - Получить все категории с количеством статей

    Protected endpoints:
        POST /knowledge/categories - Создать категорию
        PUT /knowledge/categories/{id} - Обновить категорию
        DELETE /knowledge/categories/{id} - Удалить категорию
    """

    def __init__(self):
        """Инициализирует KnowledgeCategoryRouter."""
        super().__init__(prefix="knowledge/categories", tags=["Knowledge Base - Categories"])

    def configure(self):
        """Настройка endpoint'ов для категорий."""

        @self.router.get(
            path="",
            response_model=KnowledgeCategoryListResponseSchema,
            description="""\
## 📂 Получить все категории базы знаний

Возвращает все категории с количеством опубликованных статей,
отсортированные по order.

### Returns:
- Список категорий с articles_count
""",
        )
        async def get_all_categories(
            service: KnowledgeServiceDep,
        ) -> KnowledgeCategoryListResponseSchema:
            """Получает все категории базы знаний."""
            categories_data = await service.get_categories_with_count()

            schemas = []
            for item in categories_data:
                category = item["category"]
                schema = KnowledgeCategoryListItemSchema(
                    id=category.id,
                    name=category.name,
                    slug=category.slug,
                    description=category.description,
                    icon=category.icon,
                    color=category.color,
                    order=category.order,
                    articles_count=item["articles_count"],
                )
                schemas.append(schema)

            return KnowledgeCategoryListResponseSchema(
                success=True,
                message="Категории получены",
                data=schemas,
            )

        @self.router.get(
            path="/{slug}",
            response_model=KnowledgeCategoryResponseSchema,
            description="""\
## 📂 Получить категорию по slug

Возвращает категорию по её URL-friendly идентификатору.

### Path Parameters:
- **slug** — URL-friendly идентификатор категории

### Returns:
- Данные категории
""",
        )
        async def get_category_by_slug(
            slug: str,
            service: KnowledgeServiceDep,
        ) -> KnowledgeCategoryResponseSchema:
            """Получает категорию по slug."""
            category = await service.get_category_by_slug(slug)

            # Получаем количество статей через отдельный запрос
            # чтобы избежать lazy loading relationships
            schema = KnowledgeCategoryListItemSchema(
                id=category.id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                icon=category.icon,
                color=category.color,
                order=category.order,
                articles_count=0,  # Количество загружается отдельно при необходимости
            )

            return KnowledgeCategoryResponseSchema(
                success=True,
                message="Категория получена",
                data=schema,
            )


class KnowledgeCategoryProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для управления категориями.

    Protected endpoints:
        POST /knowledge/categories - Создать категорию
        PUT /knowledge/categories/{id} - Обновить категорию
        DELETE /knowledge/categories/{id} - Удалить категорию
    """

    def __init__(self):
        """Инициализирует защищённый роутер категорий."""
        super().__init__(prefix="knowledge/categories", tags=["Knowledge Base - Categories"])

    def configure(self):
        """Настройка защищённых endpoint'ов."""

        @self.router.post(
            path="",
            response_model=KnowledgeCategoryResponseSchema,
            status_code=201,
            description="""\
## ➕ Создать категорию

Создаёт новую категорию базы знаний.

### Request Body:
- **name** — Название категории (обязательно)
- **slug** — URL-friendly идентификатор (опционально, генерируется автоматически)
- **description** — Описание категории
- **icon** — Название иконки (lucide-react)
- **color** — HEX цвет для UI
- **order** — Порядок отображения

### Returns:
- Созданная категория
""",
        )
        async def create_category(
            data: KnowledgeCategoryCreateSchema,
            service: KnowledgeServiceDep,
        ) -> KnowledgeCategoryResponseSchema:
            """Создаёт категорию базы знаний."""
            category = await service.create_category(data.model_dump(exclude_unset=True))

            schema = KnowledgeCategoryListItemSchema(
                id=category.id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                icon=category.icon,
                color=category.color,
                order=category.order,
                articles_count=0,
            )

            return KnowledgeCategoryResponseSchema(
                success=True,
                message="Категория создана",
                data=schema,
            )

        @self.router.put(
            path="/{category_id}",
            response_model=KnowledgeCategoryResponseSchema,
            description="""\
## ✏️ Обновить категорию

Обновляет данные категории.

### Path Parameters:
- **category_id** — UUID категории

### Request Body:
- Любые поля из KnowledgeCategoryUpdateSchema

### Returns:
- Обновлённая категория
""",
        )
        async def update_category(
            category_id: UUID,
            data: KnowledgeCategoryUpdateSchema,
            service: KnowledgeServiceDep,
        ) -> KnowledgeCategoryResponseSchema:
            """Обновляет категорию базы знаний."""
            category = await service.update_category(
                category_id,
                data.model_dump(exclude_unset=True),
            )

            schema = KnowledgeCategoryListItemSchema(
                id=category.id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                icon=category.icon,
                color=category.color,
                order=category.order,
                articles_count=0,  # Количество загружается при необходимости
            )

            return KnowledgeCategoryResponseSchema(
                success=True,
                message="Категория обновлена",
                data=schema,
            )

        @self.router.delete(
            path="/{category_id}",
            response_model=KnowledgeCategoryDeletedSchema,
            description="""\
## 🗑️ Удалить категорию

Удаляет категорию. Статьи категории останутся, но потеряют связь с категорией.

### Path Parameters:
- **category_id** — UUID категории

### Returns:
- Подтверждение удаления
""",
        )
        async def delete_category(
            category_id: UUID,
            service: KnowledgeServiceDep,
        ) -> KnowledgeCategoryDeletedSchema:
            """Удаляет категорию базы знаний."""
            await service.delete_category(category_id)

            return KnowledgeCategoryDeletedSchema(
                success=True,
                message="Категория успешно удалена",
            )
