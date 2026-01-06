"""Базовые схемы для базы знаний."""

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas import BaseSchema, CommonBaseSchema


# ==================== КАТЕГОРИИ ====================


class KnowledgeCategoryBaseSchema(BaseSchema):
    """
    Базовая схема категории базы знаний.

    Attributes:
        name: Название категории.
        slug: URL-friendly идентификатор.
        description: Описание категории.
        icon: Название иконки (lucide-react).
        color: HEX цвет для UI.
        order: Порядок отображения.
    """

    name: str = Field(description="Название категории")
    slug: str = Field(description="URL-friendly идентификатор")
    description: str | None = Field(None, description="Описание категории")
    icon: str | None = Field(None, description="Название иконки (lucide-react)")
    color: str | None = Field(None, description="HEX цвет для UI")
    order: int = Field(default=0, description="Порядок отображения")


class KnowledgeCategoryListItemSchema(CommonBaseSchema):
    """
    Схема элемента списка категорий.

    Attributes:
        id: ID категории.
        name: Название категории.
        slug: URL-friendly идентификатор.
        description: Описание категории.
        icon: Название иконки.
        color: HEX цвет.
        order: Порядок отображения.
        articles_count: Количество статей в категории.
    """

    id: uuid.UUID = Field(description="ID категории")
    name: str = Field(description="Название категории")
    slug: str = Field(description="URL-friendly идентификатор")
    description: str | None = Field(None, description="Описание категории")
    icon: str | None = Field(None, description="Название иконки")
    color: str | None = Field(None, description="HEX цвет")
    order: int = Field(description="Порядок отображения")
    articles_count: int = Field(default=0, description="Количество статей")


# ==================== ТЕГИ ====================


class KnowledgeTagBaseSchema(BaseSchema):
    """
    Базовая схема тега.

    Attributes:
        name: Название тега.
        slug: URL-friendly идентификатор.
        color: HEX цвет для UI.
    """

    name: str = Field(description="Название тега")
    slug: str = Field(description="URL-friendly идентификатор")
    color: str | None = Field(None, description="HEX цвет для UI")


class KnowledgeTagListItemSchema(CommonBaseSchema):
    """
    Схема элемента списка тегов.

    Attributes:
        id: ID тега.
        name: Название тега.
        slug: URL-friendly идентификатор.
        color: HEX цвет.
        articles_count: Количество статей с этим тегом.
    """

    id: uuid.UUID = Field(description="ID тега")
    name: str = Field(description="Название тега")
    slug: str = Field(description="URL-friendly идентификатор")
    color: str | None = Field(None, description="HEX цвет")
    articles_count: int = Field(default=0, description="Количество статей")


# ==================== АВТОР ====================


class KnowledgeAuthorSchema(CommonBaseSchema):
    """
    Схема автора статьи (краткая информация).

    Attributes:
        id: ID автора.
        username: Имя пользователя.
        full_name: Полное имя.
    """

    id: uuid.UUID = Field(description="ID автора")
    username: str = Field(description="Имя пользователя")
    full_name: str | None = Field(None, description="Полное имя")


# ==================== СТАТЬИ ====================


class KnowledgeArticleBaseSchema(BaseSchema):
    """
    Базовая схема статьи.

    Attributes:
        title: Заголовок статьи.
        slug: URL-friendly идентификатор.
        description: Краткое описание.
        content: Контент в формате Markdown.
        is_published: Опубликована ли статья.
        is_featured: Закреплена ли статья.
    """

    title: str = Field(description="Заголовок статьи")
    slug: str = Field(description="URL-friendly идентификатор")
    description: str | None = Field(None, description="Краткое описание")
    content: str = Field(description="Контент в формате Markdown")
    is_published: bool = Field(default=False, description="Опубликована ли статья")
    is_featured: bool = Field(default=False, description="Закреплена ли статья")


class KnowledgeArticleListItemSchema(CommonBaseSchema):
    """
    Схема элемента списка статей (без полного контента).

    Attributes:
        id: ID статьи.
        title: Заголовок статьи.
        slug: URL-friendly идентификатор.
        description: Краткое описание.
        author: Информация об авторе.
        category: Категория статьи.
        tags: Список тегов.
        is_published: Опубликована ли статья.
        is_featured: Закреплена ли статья.
        view_count: Количество просмотров.
        published_at: Дата публикации.
        created_at: Дата создания.
    """

    id: uuid.UUID = Field(description="ID статьи")
    title: str = Field(description="Заголовок статьи")
    slug: str = Field(description="URL-friendly идентификатор")
    description: str | None = Field(None, description="Краткое описание")
    author: KnowledgeAuthorSchema = Field(description="Информация об авторе")
    category: KnowledgeCategoryListItemSchema | None = Field(None, description="Категория статьи")
    tags: list[KnowledgeTagListItemSchema] = Field(default_factory=list, description="Список тегов")
    is_published: bool = Field(description="Опубликована ли статья")
    is_featured: bool = Field(description="Закреплена ли статья")
    view_count: int = Field(default=0, description="Количество просмотров")
    published_at: datetime | None = Field(None, description="Дата публикации")
    created_at: datetime = Field(description="Дата создания")


class KnowledgeArticleDetailSchema(KnowledgeArticleListItemSchema):
    """
    Схема детальной информации о статье (с полным контентом).

    Attributes:
        content: Полный контент в формате Markdown.
        updated_at: Дата последнего обновления.
    """

    content: str = Field(description="Контент в формате Markdown")
    updated_at: datetime = Field(description="Дата последнего обновления")
