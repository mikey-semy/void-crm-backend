"""add knowledge_article_chunks table for granular RAG search

Revision ID: g3h4i5j6k7l8
Revises: f2a3b4c5d6e7
Create Date: 2026-01-10 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "g3h4i5j6k7l8"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create knowledge_article_chunks table
    op.create_table(
        "knowledge_article_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "article_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_articles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
            comment="Порядковый номер чанка в статье",
        ),
        sa.Column(
            "title",
            sa.String(500),
            nullable=True,
            comment="Заголовок секции (из Markdown)",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Содержимое чанка",
        ),
        sa.Column(
            "token_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Приблизительное количество токенов",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # 2. Add vector column for embedding (1536 dimensions for OpenAI)
    op.execute(
        "ALTER TABLE knowledge_article_chunks ADD COLUMN embedding vector(1536)"
    )

    # 3. Create indexes
    op.create_index(
        "ix_knowledge_article_chunks_article_id",
        "knowledge_article_chunks",
        ["article_id"],
    )
    op.create_index(
        "ix_knowledge_article_chunks_chunk_index",
        "knowledge_article_chunks",
        ["chunk_index"],
    )

    # 4. Create HNSW index for vector similarity search (cosine distance)
    op.execute(
        """
        CREATE INDEX ix_knowledge_article_chunks_embedding
        ON knowledge_article_chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_knowledge_article_chunks_embedding")
    op.drop_index(
        "ix_knowledge_article_chunks_chunk_index",
        table_name="knowledge_article_chunks",
    )
    op.drop_index(
        "ix_knowledge_article_chunks_article_id",
        table_name="knowledge_article_chunks",
    )

    # Drop table
    op.drop_table("knowledge_article_chunks")