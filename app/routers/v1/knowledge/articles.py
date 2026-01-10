"""
Роутер для работы со статьями базы знаний.

Предоставляет HTTP API для CRUD операций со статьями.
"""

from uuid import UUID

from fastapi import Query

from app.core.dependencies.knowledge import KnowledgeServiceDep
from app.core.security import CurrentUserDep, OptionalCurrentUserDep
from app.routers.base import BaseRouter, ProtectedRouter
from app.schemas import PaginatedDataSchema, PaginationMetaSchema, PaginationParamsSchema
from app.schemas.v1.knowledge import (
    KnowledgeArticleCreateSchema,
    KnowledgeArticleDeletedSchema,
    KnowledgeArticleDetailSchema,
    KnowledgeArticleListItemSchema,
    KnowledgeArticleListResponseSchema,
    KnowledgeArticleResponseSchema,
    KnowledgeArticleUpdateSchema,
    KnowledgeAuthorSchema,
    KnowledgeCategoryListItemSchema,
    KnowledgeGenerateDescriptionSchema,
    KnowledgeGeneratedDescriptionSchema,
    KnowledgeTagListItemSchema,
)


def _article_to_list_schema(article) -> KnowledgeArticleListItemSchema:
    """Преобразует модель статьи в схему для списка."""
    author_schema = KnowledgeAuthorSchema(
        id=article.author.id,
        username=article.author.username,
        full_name=article.author.full_name,
    )

    category_schema = None
    if article.category:
        category_schema = KnowledgeCategoryListItemSchema(
            id=article.category.id,
            name=article.category.name,
            slug=article.category.slug,
            description=article.category.description,
            icon=article.category.icon,
            color=article.category.color,
            order=article.category.order,
            articles_count=0,
        )

    tags_schema = [
        KnowledgeTagListItemSchema(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            color=tag.color,
            articles_count=0,
        )
        for tag in article.tags
    ]

    return KnowledgeArticleListItemSchema(
        id=article.id,
        title=article.title,
        slug=article.slug,
        description=article.description,
        author=author_schema,
        category=category_schema,
        tags=tags_schema,
        is_published=article.is_published,
        is_featured=article.is_featured,
        view_count=article.view_count,
        published_at=article.published_at,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


def _article_to_detail_schema(article) -> KnowledgeArticleDetailSchema:
    """Преобразует модель статьи в детальную схему."""
    author_schema = KnowledgeAuthorSchema(
        id=article.author.id,
        username=article.author.username,
        full_name=article.author.full_name,
    )

    category_schema = None
    if article.category:
        category_schema = KnowledgeCategoryListItemSchema(
            id=article.category.id,
            name=article.category.name,
            slug=article.category.slug,
            description=article.category.description,
            icon=article.category.icon,
            color=article.category.color,
            order=article.category.order,
            articles_count=0,
        )

    tags_schema = [
        KnowledgeTagListItemSchema(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            color=tag.color,
            articles_count=0,
        )
        for tag in article.tags
    ]

    return KnowledgeArticleDetailSchema(
        id=article.id,
        title=article.title,
        slug=article.slug,
        description=article.description,
        content=article.content,
        author=author_schema,
        category=category_schema,
        tags=tags_schema,
        is_published=article.is_published,
        is_featured=article.is_featured,
        view_count=article.view_count,
        published_at=article.published_at,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


class KnowledgeArticleRouter(BaseRouter):
    """
    Роутер для публичного API статей базы знаний.

    Public endpoints:
        GET /knowledge/articles - Получить опубликованные статьи
        GET /knowledge/articles/{slug} - Получить статью по slug
    """

    def __init__(self):
        """Инициализирует KnowledgeArticleRouter."""
        super().__init__(prefix="knowledge/articles", tags=["Knowledge Base - Articles"])

    def configure(self):
        """Настройка endpoint'ов для статей."""

        @self.router.get(
            path="",
            response_model=KnowledgeArticleListResponseSchema,
            description="""\
## 📚 Получить опубликованные статьи

Возвращает опубликованные статьи с пагинацией и фильтрами.

### Query Parameters:
- **page** — Номер страницы (по умолчанию 1)
- **page_size** — Размер страницы (по умолчанию 20)
- **categories** — Фильтр по категориям (UUID через запятую)
- **tags** — Фильтр по тегам (slugs через запятую)
- **featured** — Только закреплённые статьи
- **sort_by** — Сортировка (published_at, view_count, created_at, updated_at)

### Returns:
- Список статей с пагинацией
""",
        )
        async def get_published_articles(
            service: KnowledgeServiceDep,
            page: int = Query(1, ge=1, description="Номер страницы"),
            page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
            categories: str | None = Query(None, description="Фильтр по категориям (UUID через запятую)"),
            tags: str | None = Query(None, description="Фильтр по тегам (slugs через запятую)"),
            featured: bool = Query(False, description="Только закреплённые"),
            author_id: str | None = Query(None, description="Фильтр по автору (UUID)"),
            sort_by: str = Query("published_at", description="Сортировка (published_at, view_count, created_at, updated_at)"),
        ) -> KnowledgeArticleListResponseSchema:
            """Получает опубликованные статьи."""
            # Валидация sort_by
            allowed_sort_fields = {"published_at", "view_count", "created_at", "updated_at"}
            if sort_by not in allowed_sort_fields:
                sort_by = "published_at"

            pagination = PaginationParamsSchema(
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_desc=True,
            )

            tag_slugs = tags.split(",") if tags else None
            category_ids = [UUID(c.strip()) for c in categories.split(",") if c.strip()] if categories else None
            author_uuid = UUID(author_id) if author_id else None

            articles, total = await service.get_published_articles(
                pagination=pagination,
                category_ids=category_ids,
                tag_slugs=tag_slugs,
                featured_only=featured,
                author_id=author_uuid,
            )

            schemas = [_article_to_list_schema(article) for article in articles]

            total_pages = (total + page_size - 1) // page_size

            return KnowledgeArticleListResponseSchema(
                success=True,
                message="Статьи получены",
                data=PaginatedDataSchema(
                    items=schemas,
                    pagination=PaginationMetaSchema(
                        total=total,
                        page=page,
                        page_size=page_size,
                        total_pages=total_pages,
                        has_next=page < total_pages,
                        has_prev=page > 1,
                    ),
                ),
            )

        @self.router.get(
            path="/{slug}",
            response_model=KnowledgeArticleResponseSchema,
            description="""\
## 📖 Получить статью по slug

Возвращает статью с полным контентом.
Автоматически увеличивает счётчик просмотров.

Если пользователь авторизован, он может просматривать свои черновики.

### Path Parameters:
- **slug** — URL-friendly идентификатор статьи

### Returns:
- Полные данные статьи с контентом
""",
        )
        async def get_article_by_slug(
            slug: str,
            service: KnowledgeServiceDep,
            current_user: OptionalCurrentUserDep,
        ) -> KnowledgeArticleResponseSchema:
            """Получает статью по slug."""
            # Если пользователь авторизован, позволяем просматривать его черновики
            current_user_id = current_user.id if current_user else None
            article = await service.get_article_by_slug(
                slug, published_only=True, current_user_id=current_user_id
            )

            # Увеличиваем счётчик просмотров только для опубликованных статей
            if article.is_published:
                await service.increment_article_views(article.id)

            schema = _article_to_detail_schema(article)

            return KnowledgeArticleResponseSchema(
                success=True,
                message="Статья получена",
                data=schema,
            )


class KnowledgeArticleProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для управления статьями.

    Protected endpoints:
        POST /knowledge/articles - Создать статью
        PUT /knowledge/articles/{id} - Обновить статью
        DELETE /knowledge/articles/{id} - Удалить статью
        POST /knowledge/articles/{id}/publish - Опубликовать
        POST /knowledge/articles/{id}/unpublish - Снять с публикации
    """

    def __init__(self):
        """Инициализирует защищённый роутер статей."""
        super().__init__(prefix="knowledge/articles", tags=["Knowledge Base - Articles"])

    def configure(self):
        """Настройка защищённых endpoint'ов."""

        @self.router.post(
            path="",
            response_model=KnowledgeArticleResponseSchema,
            status_code=201,
            description="""\
## ➕ Создать статью

Создаёт новую статью в базе знаний.

### Request Body:
- **title** — Заголовок (обязательно)
- **content** — Контент в Markdown (обязательно)
- **description** — Краткое описание
- **slug** — URL-friendly идентификатор (генерируется автоматически)
- **category_id** — ID категории
- **tag_ids** — Список ID тегов
- **is_published** — Опубликовать сразу
- **is_featured** — Закрепить

### Returns:
- Созданная статья
""",
        )
        async def create_article(
            data: KnowledgeArticleCreateSchema,
            service: KnowledgeServiceDep,
            current_user: CurrentUserDep,
        ) -> KnowledgeArticleResponseSchema:
            """Создаёт статью."""
            article = await service.create_article(
                data=data.model_dump(exclude_unset=True),
                author_id=current_user.id,
            )

            schema = _article_to_detail_schema(article)

            return KnowledgeArticleResponseSchema(
                success=True,
                message="Статья создана",
                data=schema,
            )

        @self.router.get(
            path="/drafts",
            response_model=KnowledgeArticleListResponseSchema,
            description="""\
## 📝 Получить черновики текущего пользователя

Возвращает неопубликованные статьи текущего автора.

### Returns:
- Список черновиков с пагинацией
""",
        )
        async def get_my_drafts(
            service: KnowledgeServiceDep,
            current_user: CurrentUserDep,
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
        ) -> KnowledgeArticleListResponseSchema:
            """Получает черновики текущего пользователя."""
            pagination = PaginationParamsSchema(
                page=page,
                page_size=page_size,
                sort_by="updated_at",
                sort_desc=True,
            )

            articles, total = await service.article_repository.get_by_author(
                author_id=current_user.id,
                pagination=pagination,
                published_only=False,
            )

            # Фильтруем только черновики
            drafts = [a for a in articles if not a.is_published]
            schemas = [_article_to_list_schema(article) for article in drafts]

            total_pages = (len(drafts) + page_size - 1) // page_size if drafts else 0

            return KnowledgeArticleListResponseSchema(
                success=True,
                message="Черновики получены",
                data=PaginatedDataSchema(
                    items=schemas,
                    pagination=PaginationMetaSchema(
                        total=len(drafts),
                        page=page,
                        page_size=page_size,
                        total_pages=total_pages,
                        has_next=page < total_pages,
                        has_prev=page > 1,
                    ),
                ),
            )

        @self.router.put(
            path="/{article_id}",
            response_model=KnowledgeArticleResponseSchema,
            description="""\
## ✏️ Обновить статью

Обновляет данные статьи.

### Path Parameters:
- **article_id** — UUID статьи

### Request Body:
- Любые поля из KnowledgeArticleUpdateSchema

### Returns:
- Обновлённая статья
""",
        )
        async def update_article(
            article_id: UUID,
            data: KnowledgeArticleUpdateSchema,
            service: KnowledgeServiceDep,
        ) -> KnowledgeArticleResponseSchema:
            """Обновляет статью."""
            article = await service.update_article(
                article_id,
                data.model_dump(exclude_unset=True),
            )

            schema = _article_to_detail_schema(article)

            return KnowledgeArticleResponseSchema(
                success=True,
                message="Статья обновлена",
                data=schema,
            )

        @self.router.delete(
            path="/{article_id}",
            response_model=KnowledgeArticleDeletedSchema,
            description="""\
## 🗑️ Удалить статью

Удаляет статью из базы знаний.

### Path Parameters:
- **article_id** — UUID статьи

### Returns:
- Подтверждение удаления
""",
        )
        async def delete_article(
            article_id: UUID,
            service: KnowledgeServiceDep,
        ) -> KnowledgeArticleDeletedSchema:
            """Удаляет статью."""
            await service.delete_article(article_id)

            return KnowledgeArticleDeletedSchema(
                success=True,
                message="Статья успешно удалена",
            )

        @self.router.post(
            path="/{article_id}/publish",
            response_model=KnowledgeArticleResponseSchema,
            description="""\
## 📢 Опубликовать статью

Публикует статью (делает её видимой для всех).

### Path Parameters:
- **article_id** — UUID статьи

### Returns:
- Опубликованная статья
""",
        )
        async def publish_article(
            article_id: UUID,
            service: KnowledgeServiceDep,
        ) -> KnowledgeArticleResponseSchema:
            """Публикует статью."""
            article = await service.publish_article(article_id)
            schema = _article_to_detail_schema(article)

            return KnowledgeArticleResponseSchema(
                success=True,
                message="Статья опубликована",
                data=schema,
            )

        @self.router.post(
            path="/{article_id}/unpublish",
            response_model=KnowledgeArticleResponseSchema,
            description="""\
## 📤 Снять с публикации

Снимает статью с публикации (делает черновиком).

### Path Parameters:
- **article_id** — UUID статьи

### Returns:
- Статья-черновик
""",
        )
        async def unpublish_article(
            article_id: UUID,
            service: KnowledgeServiceDep,
        ) -> KnowledgeArticleResponseSchema:
            """Снимает статью с публикации."""
            article = await service.unpublish_article(article_id)
            schema = _article_to_detail_schema(article)

            return KnowledgeArticleResponseSchema(
                success=True,
                message="Статья снята с публикации",
                data=schema,
            )

        @self.router.post(
            path="/generate-description",
            response_model=KnowledgeGeneratedDescriptionSchema,
            description="""\
## 🤖 Сгенерировать описание

Генерирует краткое описание статьи с помощью ИИ.

### Request Body:
- **title** — Заголовок статьи
- **content** — Содержимое статьи

### Returns:
- Сгенерированное описание (1-2 предложения)

### Требования:
- API ключ OpenRouter должен быть настроен в системных настройках
- LLM модель должна быть выбрана в настройках AI
""",
        )
        async def generate_description(
            data: KnowledgeGenerateDescriptionSchema,
            service: KnowledgeServiceDep,
        ) -> KnowledgeGeneratedDescriptionSchema:
            """Генерирует описание статьи с помощью ИИ."""
            description = await service.generate_description(
                title=data.title,
                content=data.content,
            )

            return KnowledgeGeneratedDescriptionSchema(
                success=True,
                message="Описание сгенерировано",
                data=description,
            )
