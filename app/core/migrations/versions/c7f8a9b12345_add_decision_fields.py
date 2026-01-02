"""add decision fields

Revision ID: c7f8a9b12345
Revises: acc24a810883
Create Date: 2026-01-02 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c7f8a9b12345"
down_revision: Union[str, Sequence[str], None] = "acc24a810883"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создание ENUM типа для типов полей решений
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE decision_field_type_enum AS ENUM (
                'text', 'number', 'select', 'boolean', 'date', 'time'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    decision_field_type_enum = postgresql.ENUM(
        "text", "number", "select", "boolean", "date", "time",
        name="decision_field_type_enum",
        create_type=False
    )

    # Используем существующий ENUM task_assignee_enum
    task_assignee_enum = postgresql.ENUM(
        "partner1", "partner2", "both",
        name="task_assignee_enum",
        create_type=False
    )

    # Создание таблицы task_decision_fields
    op.create_table(
        "task_decision_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="ID задачи"
        ),
        sa.Column(
            "field_key",
            sa.String(100),
            nullable=False,
            comment="Уникальный ключ поля (snake_case)"
        ),
        sa.Column(
            "field_type",
            decision_field_type_enum,
            nullable=False,
            comment="Тип поля"
        ),
        sa.Column(
            "label",
            sa.String(255),
            nullable=False,
            comment="Человекочитаемая метка поля"
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Подсказка для заполнения"
        ),
        sa.Column(
            "options",
            postgresql.JSONB(),
            nullable=True,
            comment="Опции для select [{value, label}]"
        ),
        sa.Column(
            "is_required",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Обязательное поле"
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Порядок отображения"
        ),
        sa.Column(
            "validation_rules",
            postgresql.JSONB(),
            nullable=True,
            comment="Правила валидации {min, max, pattern}"
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["checklist_tasks.id"],
            ondelete="CASCADE"
        ),
        sa.UniqueConstraint("task_id", "field_key", name="uq_task_decision_field_key"),
    )

    # Индексы для task_decision_fields
    op.create_index(
        "ix_task_decision_fields_task_id",
        "task_decision_fields",
        ["task_id"]
    )
    op.create_index(
        "ix_task_decision_fields_order",
        "task_decision_fields",
        ["order"]
    )

    # Создание таблицы task_decision_values
    op.create_table(
        "task_decision_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "field_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
            comment="ID поля решения"
        ),
        sa.Column(
            "value",
            postgresql.JSONB(),
            nullable=False,
            comment="Значение поля (универсальное хранение)"
        ),
        sa.Column(
            "filled_by",
            task_assignee_enum,
            nullable=True,
            comment="Кто заполнил"
        ),
        sa.Column(
            "filled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Когда заполнено"
        ),
        sa.ForeignKeyConstraint(
            ["field_id"],
            ["task_decision_fields.id"],
            ondelete="CASCADE"
        ),
    )

    # Индекс для task_decision_values
    op.create_index(
        "ix_task_decision_values_field_id",
        "task_decision_values",
        ["field_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Удаление таблиц
    op.drop_table("task_decision_values")
    op.drop_table("task_decision_fields")

    # Удаление ENUM типа
    op.execute("DROP TYPE IF EXISTS decision_field_type_enum")
