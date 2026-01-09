"""
Роутер для поиска по базе знаний.

Поддерживает два режима:
- Полнотекстовый поиск через PostgreSQL tsvector
- Семантический поиск (RAG) через OpenRouter embeddings + pgvector
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
    Роутер для поиска по базе знаний.

    Public endpoints:
        GET /knowledge/search - Поиск по статьям (полнотекстовый или семантический)
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
## 🔍 Поиск по статьям

Поддерживает два режима поиска:

### Полнотекстовый поиск (semantic=false, по умолчанию)
- Использует PostgreSQL tsvector с поддержкой русского языка
- Ищет точные совпадения слов в заголовках, описаниях и контенте
- Быстрый, не требует внешних API

### Семантический поиск / RAG (semantic=true)
- Использует OpenRouter embeddings + pgvector
- Ищет по смыслу запроса, а не по точным словам
- Требует настроенный API ключ в системных настройках
- Статьи должны быть проиндексированы (embedding != null)

### Query Parameters:
- **q** — Поисковый запрос (минимум 2 символа)
- **semantic** — Использовать семантический поиск (по умолчанию false)
- **page** — Номер страницы (по умолчанию 1)
- **page_size** — Размер страницы (по умолчанию 20)
- **categories** — Фильтр по категориям (UUID через запятую)
- **tags** — Фильтр по тегам (slugs через запятую)

### Example:
```
GET /api/v1/knowledge/search?q=react+hooks
GET /api/v1/knowledge/search?q=как+настроить+docker&semantic=true
```
""",
        )
        async def search_articles(
            service: KnowledgeServiceDep,
            current_user: OptionalCurrentUserDep,
            q: str = Query(..., min_length=2, max_length=200, description="Поисковый запрос"),
            semantic: bool = Query(False, description="Использовать семантический поиск (RAG)"),
            page: int = Query(1, ge=1, description="Номер страницы"),
            page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
            categories: str | None = Query(None, description="Фильтр по категориям (UUID через запятую)"),
            tags: str | None = Query(None, description="Фильтр по тегам (slugs через запятую)"),
        ) -> KnowledgeSearchResponseSchema:
            """Выполняет поиск по статьям."""
            pagination = PaginationParamsSchema(
                page=page,
                page_size=page_size,
                sort_by="relevance",
                sort_desc=True,
            )

            tag_slugs = tags.split(",") if tags else None
            category_ids = [UUID(c.strip()) for c in categories.split(",") if c.strip()] if categories else None

            # Если пользователь авторизован, показываем ему также его черновики
            current_user_id = current_user.id if current_user else None

            if semantic:
                # Семантический поиск через RAG
                articles, total = await service.semantic_search_public(
                    query=q,
                    pagination=pagination,
                    category_ids=category_ids,
                )
                search_type = "семантический"
            else:
                # Полнотекстовый поиск
                articles, total = await service.search_articles(
                    query=q,
                    pagination=pagination,
                    category_ids=category_ids,
                    tag_slugs=tag_slugs,
                    current_user_id=current_user_id,
                )
                search_type = "полнотекстовый"

            schemas = [_article_to_list_schema(article) for article in articles]

            total_pages = (total + page_size - 1) // page_size

            return KnowledgeSearchResponseSchema(
                success=True,
                message=f"Найдено {total} статей ({search_type} поиск)",
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
