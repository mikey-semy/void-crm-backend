"""Схемы запросов для базы знаний."""

import uuid
from typing import Annotated

from pydantic import Field

from app.schemas import BaseRequestSchema


# ==================== КАТЕГОРИИ ====================


class KnowledgeCategoryCreateSchema(BaseRequestSchema):
    """
    Схема создания категории.

    Attributes:
        name: Название категории (обязательно).
        slug: URL-friendly идентификатор (опционально, генерируется автоматически).
        description: Описание категории.
        icon: Название иконки (lucide-react).
        color: HEX цвет для UI.
        order: Порядок отображения.
    """

    name: Annotated[str, Field(min_length=2, max_length=100, description="Название категории")]
    slug: Annotated[str | None, Field(
        None,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly идентификатор"
    )]
    description: str | None = Field(None, description="Описание категории")
    icon: str | None = Field(None, description="Название иконки (lucide-react)")
    color: Annotated[str | None, Field(
        None,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="HEX цвет для UI"
    )]
    order: int = Field(default=0, description="Порядок отображения")


class KnowledgeCategoryUpdateSchema(BaseRequestSchema):
    """
    Схема обновления категории.

    Все поля опциональны.
    """

    name: Annotated[str | None, Field(
        None,
        min_length=2,
        max_length=100,
        description="Название категории"
    )]
    slug: Annotated[str | None, Field(
        None,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly идентификатор"
    )]
    description: str | None = Field(None, description="Описание категории")
    icon: str | None = Field(None, description="Название иконки (lucide-react)")
    color: Annotated[str | None, Field(
        None,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="HEX цвет для UI"
    )]
    order: int | None = Field(None, description="Порядок отображения")


# ==================== ТЕГИ ====================


class KnowledgeTagCreateSchema(BaseRequestSchema):
    """
    Схема создания тега.

    Attributes:
        name: Название тега (обязательно).
        slug: URL-friendly идентификатор (опционально, генерируется автоматически).
        color: HEX цвет для UI.
    """

    name: Annotated[str, Field(min_length=2, max_length=50, description="Название тега")]
    slug: Annotated[str | None, Field(
        None,
        min_length=2,
        max_length=50,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly идентификатор"
    )]
    color: Annotated[str | None, Field(
        None,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="HEX цвет для UI"
    )]


class KnowledgeTagUpdateSchema(BaseRequestSchema):
    """
    Схема обновления тега.

    Все поля опциональны.
    """

    name: Annotated[str | None, Field(
        None,
        min_length=2,
        max_length=50,
        description="Название тега"
    )]
    slug: Annotated[str | None, Field(
        None,
        min_length=2,
        max_length=50,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly идентификатор"
    )]
    color: Annotated[str | None, Field(
        None,
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="HEX цвет для UI"
    )]


# ==================== СТАТЬИ ====================


class KnowledgeArticleCreateSchema(BaseRequestSchema):
    """
    Схема создания статьи.

    Attributes:
        title: Заголовок статьи (обязательно).
        content: Контент в формате Markdown (обязательно).
        slug: URL-friendly идентификатор (опционально, генерируется автоматически).
        description: Краткое описание для превью.
        category_id: ID категории.
        tag_ids: Список ID тегов.
        is_published: Опубликовать сразу.
        is_featured: Закрепить статью.
    """

    title: Annotated[str, Field(min_length=3, max_length=500, description="Заголовок статьи")]
    content: Annotated[str, Field(min_length=10, description="Контент в формате Markdown")]
    slug: Annotated[str | None, Field(
        None,
        min_length=3,
        max_length=500,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly идентификатор"
    )]
    description: Annotated[str | None, Field(
        None,
        max_length=1000,
        description="Краткое описание для превью"
    )]
    category_id: uuid.UUID | None = Field(None, description="ID категории")
    tag_ids: list[uuid.UUID] = Field(default_factory=list, description="Список ID тегов")
    is_published: bool = Field(default=False, description="Опубликовать сразу")
    is_featured: bool = Field(default=False, description="Закрепить статью")


class KnowledgeArticleUpdateSchema(BaseRequestSchema):
    """
    Схема обновления статьи.

    Все поля опциональны.
    """

    title: Annotated[str | None, Field(
        None,
        min_length=3,
        max_length=500,
        description="Заголовок статьи"
    )]
    content: Annotated[str | None, Field(
        None,
        min_length=10,
        description="Контент в формате Markdown"
    )]
    slug: Annotated[str | None, Field(
        None,
        min_length=3,
        max_length=500,
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly идентификатор"
    )]
    description: Annotated[str | None, Field(
        None,
        max_length=1000,
        description="Краткое описание для превью"
    )]
    category_id: uuid.UUID | None = Field(None, description="ID категории")
    tag_ids: list[uuid.UUID] | None = Field(None, description="Список ID тегов")
    is_published: bool | None = Field(None, description="Опубликована ли статья")
    is_featured: bool | None = Field(None, description="Закреплена ли статья")


# ==================== ПОИСК ====================


class KnowledgeSearchQuerySchema(BaseRequestSchema):
    """
    Схема поискового запроса.

    Attributes:
        query: Поисковый запрос (минимум 2 символа).
        category_id: Фильтр по категории.
        tag_slugs: Фильтр по тегам (slugs через запятую).
    """

    query: Annotated[str, Field(min_length=2, max_length=200, description="Поисковый запрос")]
    category_id: uuid.UUID | None = Field(None, description="Фильтр по категории")
    tag_slugs: str | None = Field(None, description="Фильтр по тегам (slugs через запятую)")


# ==================== AI ====================


class KnowledgeGenerateDescriptionSchema(BaseRequestSchema):
    """
    Схема запроса на генерацию описания статьи.

    Attributes:
        title: Заголовок статьи.
        content: Содержимое статьи.
    """

    title: Annotated[str, Field(min_length=3, max_length=500, description="Заголовок статьи")]
    content: Annotated[str, Field(min_length=10, description="Содержимое статьи")]


# ==================== ЧАТ ====================


class KnowledgeChatRequestSchema(BaseRequestSchema):
    """
    Схема запроса к RAG-чату.

    Attributes:
        messages: История сообщений диалога.
        use_context: Использовать контекст из базы знаний.
    """

    messages: list[dict[str, str]] = Field(
        description="История сообщений [{role: 'user'|'assistant', content: '...'}]"
    )
    use_context: bool = Field(default=True, description="Использовать контекст из базы знаний")
