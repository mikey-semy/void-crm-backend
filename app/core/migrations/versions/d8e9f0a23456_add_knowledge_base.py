"""add knowledge base

Revision ID: d8e9f0a23456
Revises: c7f8a9b12345
Create Date: 2026-01-03 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d8e9f0a23456"
down_revision: Union[str, Sequence[str], None] = "c7f8a9b12345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # =========================================================================
    # 1. Создание таблицы knowledge_categories
    # =========================================================================
    op.create_table(
        "knowledge_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True, comment="Название категории"),
        sa.Column("slug", sa.String(100), nullable=False, unique=True, comment="URL-friendly идентификатор"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание категории"),
        sa.Column("icon", sa.String(50), nullable=True, comment="Название иконки (lucide-react)"),
        sa.Column("color", sa.String(7), nullable=True, comment="HEX цвет для UI"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0", comment="Порядок отображения"),
    )

    op.create_index("ix_knowledge_categories_name", "knowledge_categories", ["name"])
    op.create_index("ix_knowledge_categories_slug", "knowledge_categories", ["slug"])
    op.create_index("ix_knowledge_categories_order", "knowledge_categories", ["order"])

    # =========================================================================
    # 2. Создание таблицы knowledge_tags
    # =========================================================================
    op.create_table(
        "knowledge_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(50), nullable=False, unique=True, comment="Название тега"),
        sa.Column("slug", sa.String(50), nullable=False, unique=True, comment="URL-friendly идентификатор"),
        sa.Column("color", sa.String(7), nullable=True, comment="HEX цвет для UI"),
    )

    op.create_index("ix_knowledge_tags_name", "knowledge_tags", ["name"])
    op.create_index("ix_knowledge_tags_slug", "knowledge_tags", ["slug"])

    # =========================================================================
    # 3. Создание таблицы knowledge_articles
    # =========================================================================
    op.create_table(
        "knowledge_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, comment="Заголовок статьи"),
        sa.Column("slug", sa.String(500), nullable=False, unique=True, comment="URL-friendly идентификатор"),
        sa.Column("description", sa.Text(), nullable=True, comment="Краткое описание для превью"),
        sa.Column("content", sa.Text(), nullable=False, comment="Контент статьи (Markdown)"),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False, comment="ID автора статьи"),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True, comment="ID категории"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false", comment="Опубликована ли статья"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="false", comment="Закреплена ли статья"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0", comment="Количество просмотров"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True, comment="Дата публикации"),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True, comment="Вектор для полнотекстового поиска"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["knowledge_categories.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_knowledge_articles_title", "knowledge_articles", ["title"])
    op.create_index("ix_knowledge_articles_slug", "knowledge_articles", ["slug"])
    op.create_index("ix_knowledge_articles_author_id", "knowledge_articles", ["author_id"])
    op.create_index("ix_knowledge_articles_category_id", "knowledge_articles", ["category_id"])
    op.create_index("ix_knowledge_articles_is_published", "knowledge_articles", ["is_published"])
    op.create_index("ix_knowledge_articles_is_featured", "knowledge_articles", ["is_featured"])
    op.create_index("ix_knowledge_articles_published_at", "knowledge_articles", ["published_at"])

    # =========================================================================
    # 4. Создание связующей таблицы knowledge_article_tags
    # =========================================================================
    op.create_table(
        "knowledge_article_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), nullable=False, comment="ID статьи"),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False, comment="ID тега"),
        sa.ForeignKeyConstraint(["article_id"], ["knowledge_articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["knowledge_tags.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("article_id", "tag_id", name="uq_knowledge_article_tag"),
    )

    op.create_index("ix_knowledge_article_tags_article_id", "knowledge_article_tags", ["article_id"])
    op.create_index("ix_knowledge_article_tags_tag_id", "knowledge_article_tags", ["tag_id"])

    # =========================================================================
    # 5. GIN индекс для полнотекстового поиска
    # =========================================================================
    op.execute("""
        CREATE INDEX ix_knowledge_articles_search_vector
        ON knowledge_articles USING GIN(search_vector)
    """)

    # =========================================================================
    # 6. Функция для обновления search_vector
    # =========================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION knowledge_articles_search_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('russian', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('russian', coalesce(NEW.description, '')), 'B') ||
                setweight(to_tsvector('russian', coalesce(NEW.content, '')), 'C');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)

    # =========================================================================
    # 7. Триггер для автоматического обновления search_vector
    # =========================================================================
    op.execute("""
        CREATE TRIGGER knowledge_articles_search_trigger
        BEFORE INSERT OR UPDATE OF title, description, content
        ON knowledge_articles
        FOR EACH ROW EXECUTE FUNCTION knowledge_articles_search_update();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаление триггера
    op.execute("DROP TRIGGER IF EXISTS knowledge_articles_search_trigger ON knowledge_articles")

    # Удаление функции
    op.execute("DROP FUNCTION IF EXISTS knowledge_articles_search_update()")

    # Удаление таблиц (в обратном порядке из-за FK)
    op.drop_table("knowledge_article_tags")
    op.drop_table("knowledge_articles")
    op.drop_table("knowledge_tags")
    op.drop_table("knowledge_categories")
