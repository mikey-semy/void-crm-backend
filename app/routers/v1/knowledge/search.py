"""
Роутер для полнотекстового поиска по базе знаний.

Использует PostgreSQL tsvector для эффективного поиска.
"""

from uuid import UUID

from fastapi import Query

from app.core.dependencies.knowledge import KnowledgeServiceDep
from app.core.security import OptionalCurrentUserDep
from app.routers.base import BaseRouter
from app.schemas import PaginatedDataSchema, PaginationMetaSchema, PaginationParamsSchema
from app.schemas.v1.knowledge import (
    KnowledgeArticleListItemSchema,
    KnowledgeAuthorSchema,
    KnowledgeCategoryListItemSchema,
    KnowledgeSearchResponseSchema,
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


class KnowledgeSearchRouter(BaseRouter):
    """
    Роутер для полнотекстового поиска по базе знаний.

    Public endpoints:
        GET /knowledge/search - Полнотекстовый поиск по статьям
    """

    def __init__(self):
        """Инициализирует KnowledgeSearchRouter."""
        super().__init__(prefix="knowledge/search", tags=["Knowledge Base - Search"])

    def configure(self):
        """Настройка endpoint'ов для поиска."""

        @self.router.get(
            path="",
            response_model=KnowledgeSearchResponseSchema,
            description="""\
## 🔍 Полнотекстовый поиск по статьям

Выполняет полнотекстовый поиск по заголовкам, описаниям и контенту статей.
Использует PostgreSQL tsvector с поддержкой русского языка.

Результаты отсортированы по релевантности (ts_rank).

### Query Parameters:
- **q** — Поисковый запрос (минимум 2 символа, обязательно)
- **page** — Номер страницы (по умолчанию 1)
- **page_size** — Размер страницы (по умолчанию 20)
- **category_id** — Фильтр по категории
- **tags** — Фильтр по тегам (slugs через запятую)

### Returns:
- Результаты поиска с пагинацией, отсортированные по релевантности

### Example:
```
GET /api/v1/knowledge/search?q=react+hooks&page=1&page_size=10
GET /api/v1/knowledge/search?q=typescript&category_id=<uuid>&tags=frontend,best-practices
```
""",
        )
        async def search_articles(
            service: KnowledgeServiceDep,
            current_user: OptionalCurrentUserDep,
            q: str = Query(..., min_length=2, max_length=200, description="Поисковый запрос"),
            page: int = Query(1, ge=1, description="Номер страницы"),
            page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
            category_id: UUID | None = Query(None, description="Фильтр по категории"),
            tags: str | None = Query(None, description="Фильтр по тегам (slugs через запятую)"),
        ) -> KnowledgeSearchResponseSchema:
            """Выполняет полнотекстовый поиск."""
            pagination = PaginationParamsSchema(
                page=page,
                page_size=page_size,
                sort_by="relevance",
                sort_desc=True,
            )

            tag_slugs = tags.split(",") if tags else None

            # Если пользователь авторизован, показываем ему также его черновики
            current_user_id = current_user.id if current_user else None

            articles, total = await service.search_articles(
                query=q,
                pagination=pagination,
                category_id=category_id,
                tag_slugs=tag_slugs,
                current_user_id=current_user_id,
            )

            schemas = [_article_to_list_schema(article) for article in articles]

            total_pages = (total + page_size - 1) // page_size

            return KnowledgeSearchResponseSchema(
                success=True,
                message=f"Найдено {total} статей по запросу '{q}'",
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
