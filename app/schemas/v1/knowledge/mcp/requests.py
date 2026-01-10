"""Схемы запросов для MCP API базы знаний."""

from uuid import UUID

from pydantic import Field

from app.schemas import BaseRequestSchema


class MCPSearchRequestSchema(BaseRequestSchema):
    """
    Запрос семантического поиска.

    Attributes:
        query: Поисковый запрос.
        category_id: Фильтр по категории.
        limit: Максимум результатов.
        use_semantic: Использовать семантический поиск.
    """

    query: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Поисковый запрос",
    )
    category_id: UUID | None = Field(None, description="Фильтр по категории")
    limit: int = Field(10, ge=1, le=50, description="Максимум результатов")
    use_semantic: bool = Field(True, description="Использовать семантический поиск (RAG)")


class MCPCreateArticleRequestSchema(BaseRequestSchema):
    """
    Запрос на создание статьи через MCP.

    Attributes:
        title: Заголовок статьи.
        content: Контент в Markdown.
        description: Краткое описание.
        category_id: ID категории.
        tag_ids: Список ID тегов.
        is_published: Опубликовать сразу.
    """

    title: str = Field(..., min_length=3, max_length=500, description="Заголовок статьи")
    content: str = Field(..., min_length=10, description="Контент в Markdown")
    description: str | None = Field(None, max_length=1000, description="Краткое описание")
    category_id: UUID | None = Field(None, description="ID категории")
    tag_ids: list[UUID] = Field(default_factory=list, description="Список ID тегов")
    is_published: bool = Field(False, description="Опубликовать сразу")


class MCPUpdateArticleRequestSchema(BaseRequestSchema):
    """
    Запрос на обновление статьи через MCP.

    Attributes:
        title: Заголовок статьи.
        content: Контент в Markdown.
        description: Краткое описание.
        category_id: ID категории.
        tag_ids: Список ID тегов.
        is_published: Статус публикации.
    """

    title: str | None = Field(None, min_length=3, max_length=500, description="Заголовок статьи")
    content: str | None = Field(None, min_length=10, description="Контент в Markdown")
    description: str | None = Field(None, max_length=1000, description="Краткое описание")
    category_id: UUID | None = Field(None, description="ID категории")
    tag_ids: list[UUID] | None = Field(None, description="Список ID тегов")
    is_published: bool | None = Field(None, description="Статус публикации")