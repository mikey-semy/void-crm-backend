"""add pgvector extension, embeddings column and user API keys table

Revision ID: e1f2a3b4c5d6
Revises: d8e9f0a23456
Create Date: 2026-01-03 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d8e9f0a23456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. Add embedding column to knowledge_articles as vector type
    # Using 1536 dimensions (OpenAI text-embedding-3-small default)
    op.execute(
        "ALTER TABLE knowledge_articles ADD COLUMN embedding vector(1536)"
    )

    # 3. Create user_api_keys table
    op.create_table(
        "user_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(50), nullable=False),  # openrouter, openai
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
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

    # 4. Create indexes for user_api_keys
    op.create_index(
        "ix_user_api_keys_user_id",
        "user_api_keys",
        ["user_id"],
    )
    op.create_index(
        "ix_user_api_keys_provider",
        "user_api_keys",
        ["provider"],
    )

    # 5. Create HNSW index for vector similarity search (cosine distance)
    # This is much faster than ivfflat for approximate nearest neighbor search
    op.execute(
        """
        CREATE INDEX ix_knowledge_articles_embedding
        ON knowledge_articles
        USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_knowledge_articles_embedding")
    op.drop_index("ix_user_api_keys_provider", table_name="user_api_keys")
    op.drop_index("ix_user_api_keys_user_id", table_name="user_api_keys")

    # Drop user_api_keys table
    op.drop_table("user_api_keys")

    # Drop embedding column
    op.drop_column("knowledge_articles", "embedding")

    # Note: We don't drop the pgvector extension as it might be used by other tables
