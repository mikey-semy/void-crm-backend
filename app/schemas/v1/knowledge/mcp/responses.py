"""Схемы ответов для MCP API базы знаний."""

from pydantic import Field

from app.schemas import BaseResponseSchema

from .base import (
    MCPArticleContentSchema,
    MCPArticleSnippetSchema,
    MCPCategoryItemSchema,
    MCPIndexDataSchema,
    MCPSnippetItemSchema,
    MCPSuccessDataSchema,
    MCPTagItemSchema,
)


# ==================== ПОИСК ====================


class MCPSearchResponseSchema(BaseResponseSchema):
    """
    Ответ семантического поиска.

    Attributes:
        query: Исходный запрос.
        total: Общее количество найденных статей.
        articles: Список найденных статей.
    """

    query: str = Field(description="Поисковый запрос")
    total: int = Field(description="Всего найдено")
    articles: list[MCPArticleSnippetSchema] = Field(
        default_factory=list,
        description="Список статей",
    )


# ==================== СТАТЬИ ====================


class MCPArticleResponseSchema(BaseResponseSchema):
    """
    Ответ с полным контентом статьи.

    Attributes:
        article: Данные статьи.
    """

    article: MCPArticleContentSchema = Field(description="Данные статьи")


# ==================== КАТЕГОРИИ ====================


class MCPCategoriesResponseSchema(BaseResponseSchema):
    """
    Список категорий.

    Attributes:
        categories: Список категорий.
    """

    categories: list[MCPCategoryItemSchema] = Field(
        default_factory=list,
        description="Список категорий",
    )


# ==================== ТЕГИ ====================


class MCPTagsResponseSchema(BaseResponseSchema):
    """
    Список тегов.

    Attributes:
        tags: Список тегов.
    """

    tags: list[MCPTagItemSchema] = Field(
        default_factory=list,
        description="Список тегов",
    )


# ==================== СНИППЕТЫ ====================


class MCPSnippetsResponseSchema(BaseResponseSchema):
    """
    Список сниппетов кода.

    Attributes:
        tag: Тег для фильтрации.
        snippets: Список сниппетов.
    """

    tag: str = Field(description="Тег фильтрации")
    snippets: list[MCPSnippetItemSchema] = Field(
        default_factory=list,
        description="Список сниппетов",
    )


# ==================== ОПЕРАЦИИ ====================


class MCPSuccessResponseSchema(BaseResponseSchema):
    """
    Простой успешный ответ.

    Attributes:
        data: Данные ответа.
    """

    data: MCPSuccessDataSchema = Field(description="Данные ответа")


class MCPIndexResponseSchema(BaseResponseSchema):
    """
    Ответ на индексацию статей.

    Attributes:
        data: Данные результата индексации.
    """

    data: MCPIndexDataSchema = Field(description="Данные индексации")