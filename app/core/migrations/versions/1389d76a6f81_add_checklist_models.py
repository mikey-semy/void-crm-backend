"""add checklist models

Revision ID: 1389d76a6f81
Revises:
Create Date: 2026-01-01 19:57:32.435946

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1389d76a6f81"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создание ENUM типов с проверкой существования
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_status_enum AS ENUM ('pending', 'in_progress', 'completed', 'skipped');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_priority_enum AS ENUM ('critical', 'high', 'medium', 'low');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE task_assignee_enum AS ENUM ('partner1', 'partner2', 'both');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Определяем ENUM типы для использования в таблице
    task_status_enum = postgresql.ENUM(
        "pending", "in_progress", "completed", "skipped", name="task_status_enum", create_type=False
    )
    task_priority_enum = postgresql.ENUM(
        "critical", "high", "medium", "low", name="task_priority_enum", create_type=False
    )
    task_assignee_enum = postgresql.ENUM("partner1", "partner2", "both", name="task_assignee_enum", create_type=False)

    # Создание таблицы checklist_categories
    op.create_table(
        "checklist_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, comment="Название категории"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание категории"),
        sa.Column("icon", sa.String(50), nullable=True, comment="Название иконки (lucide-react)"),
        sa.Column("color", sa.String(7), nullable=True, comment="HEX цвет для UI"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0", comment="Порядок отображения"),
    )

    # Создание индексов для checklist_categories
    op.create_index("ix_checklist_categories_title", "checklist_categories", ["title"])
    op.create_index("ix_checklist_categories_order", "checklist_categories", ["order"])

    # Создание таблицы checklist_tasks
    op.create_table(
        "checklist_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, comment="Название задачи"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание задачи"),
        sa.Column("status", task_status_enum, nullable=False, server_default="pending", comment="Статус задачи"),
        sa.Column("priority", task_priority_enum, nullable=False, server_default="medium", comment="Приоритет задачи"),
        sa.Column("assignee", task_assignee_enum, nullable=True, comment="Назначенный исполнитель"),
        sa.Column("notes", sa.Text(), nullable=True, comment="Заметки к задаче"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0", comment="Порядок отображения в категории"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True, comment="Время завершения задачи"),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False, comment="ID категории задачи"),
        sa.ForeignKeyConstraint(["category_id"], ["checklist_categories.id"], ondelete="CASCADE"),
    )

    # Создание индексов для checklist_tasks
    op.create_index("ix_checklist_tasks_status", "checklist_tasks", ["status"])
    op.create_index("ix_checklist_tasks_priority", "checklist_tasks", ["priority"])
    op.create_index("ix_checklist_tasks_order", "checklist_tasks", ["order"])
    op.create_index("ix_checklist_tasks_category_id", "checklist_tasks", ["category_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Удаление таблиц
    op.drop_table("checklist_tasks")
    op.drop_table("checklist_categories")

    # Удаление ENUM типов
    op.execute("DROP TYPE IF EXISTS task_assignee_enum")
    op.execute("DROP TYPE IF EXISTS task_priority_enum")
    op.execute("DROP TYPE IF EXISTS task_status_enum")
