"""
Роутер для работы с тегами базы знаний.

Предоставляет HTTP API для CRUD операций с тегами.
"""

from uuid import UUID

from app.core.dependencies.knowledge import KnowledgeServiceDep
from app.routers.base import BaseRouter, ProtectedRouter
from app.schemas.v1.knowledge import (
    KnowledgeTagCreateSchema,
    KnowledgeTagDeletedSchema,
    KnowledgeTagListItemSchema,
    KnowledgeTagListResponseSchema,
    KnowledgeTagResponseSchema,
    KnowledgeTagUpdateSchema,
)


class KnowledgeTagRouter(BaseRouter):
    """
    Роутер для API тегов базы знаний.

    Public endpoints:
        GET /knowledge/tags - Получить все теги
        GET /knowledge/tags/popular - Получить популярные теги
        GET /knowledge/tags/{slug} - Получить тег по slug
    """

    def __init__(self):
        """Инициализирует KnowledgeTagRouter."""
        super().__init__(prefix="knowledge/tags", tags=["Knowledge Base - Tags"])

    def configure(self):
        """Настройка endpoint'ов для тегов."""

        @self.router.get(
            path="",
            response_model=KnowledgeTagListResponseSchema,
            description="""\
## 🏷️ Получить все теги

Возвращает все теги базы знаний с количеством статей.

### Returns:
- Список всех тегов с articles_count
""",
        )
        async def get_all_tags(
            service: KnowledgeServiceDep,
        ) -> KnowledgeTagListResponseSchema:
            """Получает все теги с количеством статей."""
            tags_data = await service.get_all_tags_with_counts()

            schemas = [
                KnowledgeTagListItemSchema(
                    id=item["tag"].id,
                    name=item["tag"].name,
                    slug=item["tag"].slug,
                    color=item["tag"].color,
                    articles_count=item["articles_count"],
                )
                for item in tags_data
            ]

            return KnowledgeTagListResponseSchema(
                success=True,
                message="Теги получены",
                data=schemas,
            )

        @self.router.get(
            path="/popular",
            response_model=KnowledgeTagListResponseSchema,
            description="""\
## 🔥 Получить популярные теги

Возвращает теги, отсортированные по количеству статей.

### Query Parameters:
- **limit** — Максимальное количество тегов (по умолчанию 20)

### Returns:
- Список популярных тегов с articles_count
""",
        )
        async def get_popular_tags(
            service: KnowledgeServiceDep,
            limit: int = 20,
        ) -> KnowledgeTagListResponseSchema:
            """Получает популярные теги."""
            tags_data = await service.get_popular_tags(limit)

            schemas = []
            for item in tags_data:
                tag = item["tag"]
                schema = KnowledgeTagListItemSchema(
                    id=tag.id,
                    name=tag.name,
                    slug=tag.slug,
                    color=tag.color,
                    articles_count=item["articles_count"],
                )
                schemas.append(schema)

            return KnowledgeTagListResponseSchema(
                success=True,
                message="Популярные теги получены",
                data=schemas,
            )

        @self.router.get(
            path="/{slug}",
            response_model=KnowledgeTagResponseSchema,
            description="""\
## 🏷️ Получить тег по slug

Возвращает тег по его URL-friendly идентификатору.

### Path Parameters:
- **slug** — URL-friendly идентификатор тега

### Returns:
- Данные тега
""",
        )
        async def get_tag_by_slug(
            slug: str,
            service: KnowledgeServiceDep,
        ) -> KnowledgeTagResponseSchema:
            """Получает тег по slug."""
            tag = await service.get_tag_by_slug(slug)

            schema = KnowledgeTagListItemSchema(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                color=tag.color,
                articles_count=0,  # Количество загружается отдельно при необходимости
            )

            return KnowledgeTagResponseSchema(
                success=True,
                message="Тег получен",
                data=schema,
            )


class KnowledgeTagProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для управления тегами.

    Protected endpoints:
        POST /knowledge/tags - Создать тег
        PUT /knowledge/tags/{id} - Обновить тег
        DELETE /knowledge/tags/{id} - Удалить тег
    """

    def __init__(self):
        """Инициализирует защищённый роутер тегов."""
        super().__init__(prefix="knowledge/tags", tags=["Knowledge Base - Tags"])

    def configure(self):
        """Настройка защищённых endpoint'ов."""

        @self.router.post(
            path="",
            response_model=KnowledgeTagResponseSchema,
            status_code=201,
            description="""\
## ➕ Создать тег

Создаёт новый тег.

### Request Body:
- **name** — Название тега (обязательно)
- **slug** — URL-friendly идентификатор (опционально)
- **color** — HEX цвет для UI

### Returns:
- Созданный тег
""",
        )
        async def create_tag(
            data: KnowledgeTagCreateSchema,
            service: KnowledgeServiceDep,
        ) -> KnowledgeTagResponseSchema:
            """Создаёт тег."""
            tag = await service.create_tag(data.model_dump(exclude_unset=True))

            schema = KnowledgeTagListItemSchema(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                color=tag.color,
                articles_count=0,
            )

            return KnowledgeTagResponseSchema(
                success=True,
                message="Тег создан",
                data=schema,
            )

        @self.router.put(
            path="/{tag_id}",
            response_model=KnowledgeTagResponseSchema,
            description="""\
## ✏️ Обновить тег

Обновляет данные тега.

### Path Parameters:
- **tag_id** — UUID тега

### Request Body:
- Любые поля из KnowledgeTagUpdateSchema

### Returns:
- Обновлённый тег
""",
        )
        async def update_tag(
            tag_id: UUID,
            data: KnowledgeTagUpdateSchema,
            service: KnowledgeServiceDep,
        ) -> KnowledgeTagResponseSchema:
            """Обновляет тег."""
            tag = await service.update_tag(
                tag_id,
                data.model_dump(exclude_unset=True),
            )

            schema = KnowledgeTagListItemSchema(
                id=tag.id,
                name=tag.name,
                slug=tag.slug,
                color=tag.color,
                articles_count=0,  # Количество загружается отдельно при необходимости
            )

            return KnowledgeTagResponseSchema(
                success=True,
                message="Тег обновлён",
                data=schema,
            )

        @self.router.delete(
            path="/{tag_id}",
            response_model=KnowledgeTagDeletedSchema,
            description="""\
## 🗑️ Удалить тег

Удаляет тег. Связи со статьями будут удалены.

### Path Parameters:
- **tag_id** — UUID тега

### Returns:
- Подтверждение удаления
""",
        )
        async def delete_tag(
            tag_id: UUID,
            service: KnowledgeServiceDep,
        ) -> KnowledgeTagDeletedSchema:
            """Удаляет тег."""
            await service.delete_tag(tag_id)

            return KnowledgeTagDeletedSchema(
                success=True,
                message="Тег успешно удалён",
            )
