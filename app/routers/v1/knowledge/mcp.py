"""
MCP API роутер для интеграции базы знаний с Claude Code.

Предоставляет API для MCP сервера с аутентификацией через X-API-Key.
Поддерживает семантический поиск (RAG) и полный CRUD.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Header, Query
from pydantic import BaseModel, Field

from app.core.dependencies.knowledge import KnowledgeServiceDep
from app.routers.base import ApiKeyProtectedRouter
from app.schemas import PaginationParamsSchema

# ==================== MCP SCHEMAS ====================


class MCPSearchRequest(BaseModel):
    """Запрос семантического поиска."""

    query: str = Field(..., min_length=2, max_length=500, description="Поисковый запрос")
    category_id: UUID | None = Field(None, description="Фильтр по категории")
    limit: int = Field(10, ge=1, le=50, description="Максимум результатов")
    use_semantic: bool = Field(True, description="Использовать семантический поиск (RAG)")


class MCPArticleSnippet(BaseModel):
    """Краткая информация о статье для MCP."""

    id: UUID
    title: str
    slug: str
    description: str | None
    category_name: str | None
    tags: list[str]
    relevance_score: float | None = None


class MCPSearchResponse(BaseModel):
    """Ответ семантического поиска."""

    success: bool = True
    query: str
    total: int
    articles: list[MCPArticleSnippet]


class MCPArticleContent(BaseModel):
    """Полный контент статьи для MCP."""

    id: UUID
    title: str
    slug: str
    description: str | None
    content: str
    category_name: str | None
    tags: list[str]
    author: str
    created_at: str
    updated_at: str


class MCPArticleResponse(BaseModel):
    """Ответ с полным контентом статьи."""

    success: bool = True
    article: MCPArticleContent


class MCPCategoryItem(BaseModel):
    """Категория для MCP."""

    id: UUID
    name: str
    slug: str
    description: str | None
    icon: str | None
    articles_count: int


class MCPCategoriesResponse(BaseModel):
    """Список категорий."""

    success: bool = True
    categories: list[MCPCategoryItem]


class MCPTagItem(BaseModel):
    """Тег для MCP."""

    id: UUID
    name: str
    slug: str
    articles_count: int


class MCPTagsResponse(BaseModel):
    """Список тегов."""

    success: bool = True
    tags: list[MCPTagItem]


class MCPSnippetItem(BaseModel):
    """Сниппет кода из статьи."""

    article_id: UUID
    article_title: str
    article_slug: str
    language: str
    code: str


class MCPSnippetsResponse(BaseModel):
    """Список сниппетов кода."""

    success: bool = True
    tag: str
    snippets: list[MCPSnippetItem]


class MCPCreateArticleRequest(BaseModel):
    """Запрос на создание статьи через MCP."""

    title: str = Field(..., min_length=3, max_length=500)
    content: str = Field(..., min_length=10)
    description: str | None = Field(None, max_length=1000)
    category_id: UUID | None = None
    tag_ids: list[UUID] = Field(default_factory=list)
    is_published: bool = False


class MCPUpdateArticleRequest(BaseModel):
    """Запрос на обновление статьи через MCP."""

    title: str | None = Field(None, min_length=3, max_length=500)
    content: str | None = Field(None, min_length=10)
    description: str | None = None
    category_id: UUID | None = None
    tag_ids: list[UUID] | None = None
    is_published: bool | None = None


class MCPSuccessResponse(BaseModel):
    """Простой успешный ответ."""

    success: bool = True
    message: str


class MCPIndexResponse(BaseModel):
    """Ответ на индексацию статей."""

    success: bool = True
    message: str
    indexed_count: int


# ==================== API KEY DEPENDENCY ====================


ApiKeyHeader = Annotated[
    str,
    Header(
        alias="X-API-Key",
        description="API ключ пользователя (OpenRouter ключ для RAG)",
    ),
]


# ==================== MCP ROUTER ====================


class KnowledgeMCPRouter(ApiKeyProtectedRouter):
    """
    MCP API роутер для интеграции с Claude Code.

    Endpoints:
        POST /knowledge/mcp/search - Семантический поиск (RAG)
        GET /knowledge/mcp/article/{slug} - Получить статью
        GET /knowledge/mcp/categories - Список категорий
        GET /knowledge/mcp/tags - Популярные теги
        GET /knowledge/mcp/snippets - Сниппеты по тегу
        POST /knowledge/mcp/articles - Создать статью
        PUT /knowledge/mcp/articles/{id} - Обновить статью
        DELETE /knowledge/mcp/articles/{id} - Удалить статью
        POST /knowledge/mcp/index - Индексировать статьи для RAG
    """

    def __init__(self):
        """Инициализирует MCP роутер."""
        super().__init__(prefix="knowledge/mcp", tags=["Knowledge Base - MCP"])

    def configure(self):
        """Настройка MCP endpoint'ов."""

        @self.router.post(
            path="/search",
            response_model=MCPSearchResponse,
            description="""\
## 🔍 Семантический поиск (RAG)

Поиск статей по смыслу запроса через OpenRouter embeddings.
Использует pgvector для векторного поиска.

### Request Body:
- **query** — Поисковый запрос (2-500 символов)
- **category_id** — Фильтр по категории (опционально)
- **limit** — Максимум результатов (1-50, по умолчанию 10)
- **use_semantic** — Использовать RAG (по умолчанию true)

### Headers:
- **X-API-Key** — OpenRouter API ключ пользователя

### Returns:
- Список релевантных статей с рангом похожести
""",
        )
        async def mcp_search(
            request: MCPSearchRequest,
            service: KnowledgeServiceDep,
            api_key: ApiKeyHeader,
        ) -> MCPSearchResponse:
            """Семантический поиск по базе знаний."""
            pagination = PaginationParamsSchema(
                page=1,
                page_size=request.limit,
            )

            if request.use_semantic:
                # Семантический поиск через RAG
                articles, total = await service.semantic_search(
                    query=request.query,
                    api_key=api_key,
                    pagination=pagination,
                    category_id=request.category_id,
                )
            else:
                # Полнотекстовый поиск
                articles, total = await service.search_articles(
                    query=request.query,
                    pagination=pagination,
                    category_id=request.category_id,
                )

            snippets = [
                MCPArticleSnippet(
                    id=article.id,
                    title=article.title,
                    slug=article.slug,
                    description=article.description,
                    category_name=article.category.name if article.category else None,
                    tags=[tag.name for tag in article.tags],
                    relevance_score=None,  # TODO: добавить score из pgvector
                )
                for article in articles
            ]

            return MCPSearchResponse(
                query=request.query,
                total=total,
                articles=snippets,
            )

        @self.router.get(
            path="/article/{slug}",
            response_model=MCPArticleResponse,
            description="""\
## 📖 Получить статью по slug

Возвращает полный контент статьи для чтения.

### Path Parameters:
- **slug** — URL-friendly идентификатор статьи

### Returns:
- Полные данные статьи включая Markdown контент
""",
        )
        async def mcp_get_article(
            slug: str,
            service: KnowledgeServiceDep,
        ) -> MCPArticleResponse:
            """Получает статью по slug."""
            article = await service.get_article_by_slug(slug, published_only=True)

            return MCPArticleResponse(
                article=MCPArticleContent(
                    id=article.id,
                    title=article.title,
                    slug=article.slug,
                    description=article.description,
                    content=article.content,
                    category_name=article.category.name if article.category else None,
                    tags=[tag.name for tag in article.tags],
                    author=article.author.full_name or article.author.username,
                    created_at=article.created_at.isoformat(),
                    updated_at=article.updated_at.isoformat(),
                )
            )

        @self.router.get(
            path="/categories",
            response_model=MCPCategoriesResponse,
            description="""\
## 📁 Список категорий

Возвращает все категории с количеством статей.

### Returns:
- Список категорий с метаданными
""",
        )
        async def mcp_list_categories(
            service: KnowledgeServiceDep,
        ) -> MCPCategoriesResponse:
            """Получает список категорий."""
            categories_data = await service.get_categories_with_count()

            categories = [
                MCPCategoryItem(
                    id=cat["category"].id,
                    name=cat["category"].name,
                    slug=cat["category"].slug,
                    description=cat["category"].description,
                    icon=cat["category"].icon,
                    articles_count=cat["articles_count"],
                )
                for cat in categories_data
            ]

            return MCPCategoriesResponse(categories=categories)

        @self.router.get(
            path="/tags",
            response_model=MCPTagsResponse,
            description="""\
## 🏷️ Популярные теги

Возвращает популярные теги с количеством статей.

### Query Parameters:
- **limit** — Максимум тегов (по умолчанию 20)

### Returns:
- Список тегов отсортированных по популярности
""",
        )
        async def mcp_list_tags(
            service: KnowledgeServiceDep,
            limit: int = Query(20, ge=1, le=100),
        ) -> MCPTagsResponse:
            """Получает популярные теги."""
            tags_data = await service.get_popular_tags(limit)

            tags = [
                MCPTagItem(
                    id=tag["tag"].id,
                    name=tag["tag"].name,
                    slug=tag["tag"].slug,
                    articles_count=tag["articles_count"],
                )
                for tag in tags_data
            ]

            return MCPTagsResponse(tags=tags)

        @self.router.get(
            path="/snippets",
            response_model=MCPSnippetsResponse,
            description="""\
## 💻 Сниппеты кода по тегу

Извлекает все блоки кода из статей с указанным тегом.
Полезно для получения примеров кода по технологии.

### Query Parameters:
- **tag** — Slug тега (например: "typescript", "docker")
- **limit** — Максимум сниппетов (по умолчанию 20)

### Returns:
- Список сниппетов с указанием языка и источника
""",
        )
        async def mcp_get_snippets(
            service: KnowledgeServiceDep,
            tag: str = Query(..., description="Slug тега"),
            limit: int = Query(20, ge=1, le=100),
        ) -> MCPSnippetsResponse:
            """Получает сниппеты кода по тегу."""
            import re

            # Получаем статьи с тегом
            pagination = PaginationParamsSchema(page=1, page_size=limit)
            articles, _ = await service.get_published_articles(
                pagination=pagination,
                tag_slugs=[tag],
            )

            snippets = []
            # Regex для извлечения блоков кода из Markdown
            code_block_pattern = re.compile(
                r"```(\w+)?\n(.*?)```",
                re.DOTALL,
            )

            for article in articles:
                matches = code_block_pattern.findall(article.content)
                for language, code in matches:
                    snippets.append(
                        MCPSnippetItem(
                            article_id=article.id,
                            article_title=article.title,
                            article_slug=article.slug,
                            language=language or "text",
                            code=code.strip(),
                        )
                    )
                    if len(snippets) >= limit:
                        break
                if len(snippets) >= limit:
                    break

            return MCPSnippetsResponse(tag=tag, snippets=snippets)

        @self.router.post(
            path="/articles",
            response_model=MCPArticleResponse,
            status_code=201,
            description="""\
## ➕ Создать статью

Создаёт новую статью в базе знаний через MCP.

### Request Body:
- **title** — Заголовок (обязательно)
- **content** — Контент в Markdown (обязательно)
- **description** — Краткое описание
- **category_id** — ID категории
- **tag_ids** — Список ID тегов
- **is_published** — Опубликовать сразу (по умолчанию false)

### Headers:
- **X-API-Key** — OpenRouter API ключ пользователя

### Returns:
- Созданная статья
""",
        )
        async def mcp_create_article(
            request: MCPCreateArticleRequest,
            service: KnowledgeServiceDep,
            api_key: ApiKeyHeader,
        ) -> MCPArticleResponse:
            """Создаёт статью через MCP."""
            # TODO: Получить user_id из API key
            # Пока используем системного пользователя
            from uuid import uuid4

            # Временно: создаём статью без автора
            # В продакшене нужно связать API key с пользователем
            article = await service.create_article(
                data=request.model_dump(exclude_unset=True),
                author_id=uuid4(),  # TODO: получить из API key
            )

            # Индексируем для RAG
            try:
                await service.index_article(article.id, api_key)
            except Exception:
                pass  # Ошибка индексации не критична

            return MCPArticleResponse(
                article=MCPArticleContent(
                    id=article.id,
                    title=article.title,
                    slug=article.slug,
                    description=article.description,
                    content=article.content,
                    category_name=article.category.name if article.category else None,
                    tags=[tag.name for tag in article.tags],
                    author=article.author.full_name or article.author.username if article.author else "System",
                    created_at=article.created_at.isoformat(),
                    updated_at=article.updated_at.isoformat(),
                )
            )

        @self.router.put(
            path="/articles/{article_id}",
            response_model=MCPArticleResponse,
            description="""\
## ✏️ Обновить статью

Обновляет существующую статью через MCP.

### Path Parameters:
- **article_id** — UUID статьи

### Request Body:
- Любые поля из MCPUpdateArticleRequest

### Headers:
- **X-API-Key** — OpenRouter API ключ (для переиндексации)

### Returns:
- Обновлённая статья
""",
        )
        async def mcp_update_article(
            article_id: UUID,
            request: MCPUpdateArticleRequest,
            service: KnowledgeServiceDep,
            api_key: ApiKeyHeader,
        ) -> MCPArticleResponse:
            """Обновляет статью через MCP."""
            article = await service.update_article(
                article_id,
                request.model_dump(exclude_unset=True),
            )

            # Переиндексируем для RAG если изменился контент
            if request.title or request.content or request.description:
                try:
                    await service.index_article(article.id, api_key)
                except Exception:
                    pass

            return MCPArticleResponse(
                article=MCPArticleContent(
                    id=article.id,
                    title=article.title,
                    slug=article.slug,
                    description=article.description,
                    content=article.content,
                    category_name=article.category.name if article.category else None,
                    tags=[tag.name for tag in article.tags],
                    author=article.author.full_name or article.author.username,
                    created_at=article.created_at.isoformat(),
                    updated_at=article.updated_at.isoformat(),
                )
            )

        @self.router.delete(
            path="/articles/{article_id}",
            response_model=MCPSuccessResponse,
            description="""\
## 🗑️ Удалить статью

Удаляет статью из базы знаний.

### Path Parameters:
- **article_id** — UUID статьи

### Returns:
- Подтверждение удаления
""",
        )
        async def mcp_delete_article(
            article_id: UUID,
            service: KnowledgeServiceDep,
        ) -> MCPSuccessResponse:
            """Удаляет статью через MCP."""
            await service.delete_article(article_id)

            return MCPSuccessResponse(
                message=f"Article {article_id} deleted successfully"
            )

        @self.router.post(
            path="/index",
            response_model=MCPIndexResponse,
            description="""\
## 🔄 Индексировать статьи для RAG

Создаёт эмбеддинги для всех опубликованных статей без эмбеддингов.
Используется для первоначальной индексации или обновления.

### Headers:
- **X-API-Key** — OpenRouter API ключ пользователя

### Returns:
- Количество проиндексированных статей
""",
        )
        async def mcp_index_articles(
            service: KnowledgeServiceDep,
            api_key: ApiKeyHeader,
        ) -> MCPIndexResponse:
            """Индексирует все статьи для RAG."""
            count = await service.index_all_articles(api_key)

            return MCPIndexResponse(
                message=f"Indexed {count} articles for semantic search",
                indexed_count=count,
            )

        @self.router.get(
            path="/similar/{article_id}",
            response_model=MCPSearchResponse,
            description="""\
## 🔗 Похожие статьи

Находит статьи похожие на указанную через семантический поиск.

### Path Parameters:
- **article_id** — UUID статьи

### Query Parameters:
- **limit** — Максимум результатов (по умолчанию 5)

### Headers:
- **X-API-Key** — OpenRouter API ключ

### Returns:
- Список похожих статей
""",
        )
        async def mcp_similar_articles(
            article_id: UUID,
            service: KnowledgeServiceDep,
            api_key: ApiKeyHeader,
            limit: int = Query(5, ge=1, le=20),
        ) -> MCPSearchResponse:
            """Находит похожие статьи."""
            articles = await service.find_similar_articles(
                article_id=article_id,
                api_key=api_key,
                limit=limit,
            )

            snippets = [
                MCPArticleSnippet(
                    id=article.id,
                    title=article.title,
                    slug=article.slug,
                    description=article.description,
                    category_name=article.category.name if article.category else None,
                    tags=[tag.name for tag in article.tags],
                )
                for article in articles
            ]

            # Получаем исходную статью для query
            source_article = await service.get_article_by_id(article_id)

            return MCPSearchResponse(
                query=f"Similar to: {source_article.title}",
                total=len(snippets),
                articles=snippets,
            )
