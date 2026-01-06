"""
Модели для базы знаний.

Содержит модели для категорий, тегов и статей базы знаний.
Поддерживает полнотекстовый поиск через PostgreSQL tsvector.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.v1.users import UserModel


class KnowledgeCategoryModel(BaseModel):
    """
    Модель категории базы знаний.

    Представляет категорию статей (например: "React", "DevOps", "Best Practices").
    Категории плоские (без вложенности).

    Attributes:
        name (str): Название категории.
        slug (str): URL-friendly идентификатор.
        description (str | None): Описание категории.
        icon (str | None): Название иконки (lucide-react).
        color (str | None): HEX цвет для UI.
        order (int): Порядок отображения.
        articles (List[KnowledgeArticleModel]): Статьи в категории.

    Example:
        >>> category = KnowledgeCategoryModel(
        ...     name="React",
        ...     slug="react",
        ...     description="Статьи о React и экосистеме",
        ...     icon="Code",
        ...     color="#61dafb",
        ...     order=1
        ... )
    """

    __tablename__ = "knowledge_categories"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Название категории",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-friendly идентификатор",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание категории",
    )

    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Название иконки (lucide-react)",
    )

    color: Mapped[str | None] = mapped_column(
        String(7),
        nullable=True,
        comment="HEX цвет для UI",
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
        comment="Порядок отображения",
    )

    # Связи
    articles: Mapped[list["KnowledgeArticleModel"]] = relationship(
        "KnowledgeArticleModel",
        back_populates="category",
        order_by="desc(KnowledgeArticleModel.created_at)",
    )

    @property
    def articles_count(self) -> int:
        """Возвращает количество статей в категории."""
        return len(self.articles)

    @property
    def published_articles_count(self) -> int:
        """Возвращает количество опубликованных статей."""
        return sum(1 for article in self.articles if article.is_published)

    def __repr__(self) -> str:
        """Строковое представление модели для отладки."""
        return f"<KnowledgeCategoryModel(name={self.name}, slug={self.slug})>"


class KnowledgeTagModel(BaseModel):
    """
    Модель тега для статей базы знаний.

    Теги используются для гибкой категоризации статей.

    Attributes:
        name (str): Название тега.
        slug (str): URL-friendly идентификатор.
        color (str | None): HEX цвет для UI.

    Example:
        >>> tag = KnowledgeTagModel(
        ...     name="TypeScript",
        ...     slug="typescript",
        ...     color="#3178c6"
        ... )
    """

    __tablename__ = "knowledge_tags"

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Название тега",
    )

    slug: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-friendly идентификатор",
    )

    color: Mapped[str | None] = mapped_column(
        String(7),
        nullable=True,
        comment="HEX цвет для UI",
    )

    # Связи
    articles: Mapped[list["KnowledgeArticleModel"]] = relationship(
        "KnowledgeArticleModel",
        secondary="knowledge_article_tags",
        back_populates="tags",
    )

    @property
    def articles_count(self) -> int:
        """Возвращает количество статей с этим тегом."""
        return len(self.articles)

    def __repr__(self) -> str:
        """Строковое представление модели для отладки."""
        return f"<KnowledgeTagModel(name={self.name}, slug={self.slug})>"


class KnowledgeArticleModel(BaseModel):
    """
    Модель статьи базы знаний.

    Представляет статью с Markdown контентом и поддержкой полнотекстового поиска.

    Attributes:
        title (str): Заголовок статьи.
        slug (str): URL-friendly идентификатор.
        description (str | None): Краткое описание для превью.
        content (str): Контент статьи в формате Markdown.
        author_id (UUID): ID автора статьи.
        category_id (UUID | None): ID категории.
        is_published (bool): Опубликована ли статья.
        is_featured (bool): Закреплена ли статья.
        view_count (int): Количество просмотров.
        published_at (datetime | None): Дата публикации.
        search_vector (Any): PostgreSQL tsvector для полнотекстового поиска.

    Relationships:
        author: Many-to-One связь с UserModel.
        category: Many-to-One связь с KnowledgeCategoryModel.
        tags: Many-to-Many связь с KnowledgeTagModel.

    Example:
        >>> article = KnowledgeArticleModel(
        ...     title="Как настроить ESLint в проекте",
        ...     slug="kak-nastroit-eslint-v-proekte",
        ...     description="Пошаговое руководство по настройке ESLint",
        ...     content="# ESLint\n\nESLint - это...",
        ...     author_id=user.id,
        ...     category_id=category.id,
        ...     is_published=True
        ... )
    """

    __tablename__ = "knowledge_articles"

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="Заголовок статьи",
    )

    slug: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-friendly идентификатор",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Краткое описание для превью",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Контент статьи (Markdown)",
    )

    # Связь с автором
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID автора статьи",
    )

    # Связь с категорией (опционально)
    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID категории",
    )

    # Метаданные
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Опубликована ли статья",
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Закреплена ли статья",
    )

    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Количество просмотров",
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Дата публикации",
    )

    # Полнотекстовый поиск (PostgreSQL)
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        nullable=True,
        comment="Вектор для полнотекстового поиска",
    )

    # Семантический поиск (pgvector/RAG)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
        comment="Вектор эмбеддинга для семантического поиска (RAG)",
    )

    # Связи
    author: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="knowledge_articles",
    )

    category: Mapped["KnowledgeCategoryModel | None"] = relationship(
        "KnowledgeCategoryModel",
        back_populates="articles",
    )

    tags: Mapped[list["KnowledgeTagModel"]] = relationship(
        "KnowledgeTagModel",
        secondary="knowledge_article_tags",
        back_populates="articles",
    )

    @property
    def is_draft(self) -> bool:
        """Проверяет, является ли статья черновиком."""
        return not self.is_published

    def publish(self) -> None:
        """Публикует статью и устанавливает дату публикации."""
        self.is_published = True
        self.published_at = datetime.now(UTC)

    def unpublish(self) -> None:
        """Снимает статью с публикации."""
        self.is_published = False

    def increment_views(self) -> None:
        """Увеличивает счетчик просмотров."""
        self.view_count += 1

    def __repr__(self) -> str:
        """Строковое представление модели для отладки."""
        status = "published" if self.is_published else "draft"
        return f"<KnowledgeArticleModel(title={self.title[:30]}..., status={status})>"


class KnowledgeArticleTagModel(BaseModel):
    """
    Связующая таблица для Many-to-Many связи между статьями и тегами.

    Attributes:
        article_id (UUID): ID статьи.
        tag_id (UUID): ID тега.
    """

    __tablename__ = "knowledge_article_tags"

    article_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID статьи",
    )

    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_tags.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID тега",
    )

    def __repr__(self) -> str:
        """Строковое представление модели для отладки."""
        return f"<KnowledgeArticleTagModel(article_id={self.article_id}, tag_id={self.tag_id})>"
