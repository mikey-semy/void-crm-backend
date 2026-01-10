"""Базовые схемы для MCP API базы знаний."""

import uuid

from pydantic import Field

from app.schemas import CommonBaseSchema


# ==================== СТАТЬИ ====================


class MCPArticleSnippetSchema(CommonBaseSchema):
    """
    Краткая информация о статье для MCP.

    Attributes:
        id: ID статьи.
        title: Заголовок статьи.
        slug: URL-friendly идентификатор.
        description: Краткое описание.
        category_name: Название категории.
        tags: Список названий тегов.
        relevance_score: Релевантность для семантического поиска.
    """

    id: uuid.UUID = Field(description="ID статьи")
    title: str = Field(description="Заголовок статьи")
    slug: str = Field(description="URL-friendly идентификатор")
    description: str | None = Field(None, description="Краткое описание")
    category_name: str | None = Field(None, description="Название категории")
    tags: list[str] = Field(default_factory=list, description="Список тегов")
    relevance_score: float | None = Field(None, description="Релевантность (0-1)")


class MCPArticleContentSchema(CommonBaseSchema):
    """
    Полный контент статьи для MCP.

    Attributes:
        id: ID статьи.
        title: Заголовок статьи.
        slug: URL-friendly идентификатор.
        description: Краткое описание.
        content: Полный контент в Markdown.
        category_name: Название категории.
        tags: Список названий тегов.
        author: Имя автора.
        created_at: Дата создания (ISO формат).
        updated_at: Дата обновления (ISO формат).
    """

    id: uuid.UUID = Field(description="ID статьи")
    title: str = Field(description="Заголовок статьи")
    slug: str = Field(description="URL-friendly идентификатор")
    description: str | None = Field(None, description="Краткое описание")
    content: str = Field(description="Контент в формате Markdown")
    category_name: str | None = Field(None, description="Название категории")
    tags: list[str] = Field(default_factory=list, description="Список тегов")
    author: str = Field(description="Имя автора")
    created_at: str = Field(description="Дата создания (ISO)")
    updated_at: str = Field(description="Дата обновления (ISO)")


# ==================== КАТЕГОРИИ ====================


class MCPCategoryItemSchema(CommonBaseSchema):
    """
    Категория для MCP.

    Attributes:
        id: ID категории.
        name: Название категории.
        slug: URL-friendly идентификатор.
        description: Описание категории.
        icon: Иконка категории.
        articles_count: Количество статей.
    """

    id: uuid.UUID = Field(description="ID категории")
    name: str = Field(description="Название категории")
    slug: str = Field(description="URL-friendly идентификатор")
    description: str | None = Field(None, description="Описание категории")
    icon: str | None = Field(None, description="Иконка категории")
    articles_count: int = Field(default=0, description="Количество статей")


# ==================== ТЕГИ ====================


class MCPTagItemSchema(CommonBaseSchema):
    """
    Тег для MCP.

    Attributes:
        id: ID тега.
        name: Название тега.
        slug: URL-friendly идентификатор.
        articles_count: Количество статей.
    """

    id: uuid.UUID = Field(description="ID тега")
    name: str = Field(description="Название тега")
    slug: str = Field(description="URL-friendly идентификатор")
    articles_count: int = Field(default=0, description="Количество статей")


# ==================== СНИППЕТЫ ====================


class MCPSnippetItemSchema(CommonBaseSchema):
    """
    Сниппет кода из статьи.

    Attributes:
        article_id: ID статьи-источника.
        article_title: Заголовок статьи.
        article_slug: Slug статьи.
        language: Язык программирования.
        code: Код сниппета.
    """

    article_id: uuid.UUID = Field(description="ID статьи")
    article_title: str = Field(description="Заголовок статьи")
    article_slug: str = Field(description="Slug статьи")
    language: str = Field(description="Язык программирования")
    code: str = Field(description="Код сниппета")


# ==================== ОПЕРАЦИИ ====================


class MCPSuccessDataSchema(CommonBaseSchema):
    """
    Данные успешной операции.

    Attributes:
        message: Сообщение об успехе.
    """

    message: str = Field(description="Сообщение")


class MCPIndexDataSchema(CommonBaseSchema):
    """
    Данные результата индексации.

    Attributes:
        message: Сообщение о результате.
        indexed_count: Количество проиндексированных статей.
    """

    message: str = Field(description="Сообщение")
    indexed_count: int = Field(description="Количество проиндексированных статей")