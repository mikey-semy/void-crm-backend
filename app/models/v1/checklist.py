"""
Модели для чек-листа партнёрства.

Содержит модели для категорий и задач чек-листа формализации партнёрства
веб-студии. Поддерживает отслеживание статусов, заметок, назначение исполнителей
и приоритезацию задач.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    pass


class ChecklistCategoryModel(BaseModel):
    """
    Модель категории чек-листа партнёрства.

    Представляет категорию задач (например: "Финансы", "Коммуникации", "Технический стек").
    Каждая категория содержит набор связанных задач и имеет порядок отображения.

    Attributes:
        title (str): Название категории (например: "Финансы и ценообразование").
        description (str | None): Описание категории (например: "Прайс-лист, распределение дохода").
        icon (str | None): Название иконки для UI (например: "DollarSign", "MessageSquare").
        color (str | None): HEX цвет для UI (например: "#10b981").
        order (int): Порядок отображения категории (начиная с 1).
        tasks (List[ChecklistTaskModel]): Список задач в категории.

    Relationships:
        tasks: One-to-Many связь с ChecklistTaskModel (задачи категории).

    Properties:
        tasks_count: Количество задач в категории.
        completed_tasks_count: Количество завершённых задач.
        progress_percentage: Процент выполнения категории.

    Example:
        >>> category = ChecklistCategoryModel(
        ...     title="Финансы и ценообразование",
        ...     description="Прайс-лист, распределение дохода, система оплат",
        ...     icon="DollarSign",
        ...     color="#10b981",
        ...     order=1
        ... )
        >>> category.tasks_count
        10
        >>> category.progress_percentage
        30.0
    """

    __tablename__ = "checklist_categories"

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Название категории",
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
    tasks: Mapped[list["ChecklistTaskModel"]] = relationship(
        "ChecklistTaskModel",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="ChecklistTaskModel.order",
    )

    @property
    def tasks_count(self) -> int:
        """Возвращает общее количество задач в категории."""
        return len(self.tasks)

    @property
    def completed_tasks_count(self) -> int:
        """Возвращает количество завершённых задач."""
        return sum(1 for task in self.tasks if task.status == "completed")

    @property
    def progress_percentage(self) -> float:
        """Возвращает процент выполнения категории."""
        if self.tasks_count == 0:
            return 0.0
        return round((self.completed_tasks_count / self.tasks_count) * 100, 2)

    def __repr__(self) -> str:
        """Строковое представление модели для отладки."""
        return f"<ChecklistCategoryModel(title={self.title}, tasks={self.tasks_count})>"


class ChecklistTaskModel(BaseModel):
    """
    Модель задачи чек-листа партнёрства.

    Представляет отдельную задачу в рамках категории чек-листа. Поддерживает
    отслеживание статуса выполнения, приоритета, назначение исполнителей и заметки.

    Attributes:
        title (str): Название задачи (например: "Определить базовые расценки").
        description (str | None): Детальное описание задачи.
        status (str): Статус задачи (pending, in_progress, completed, skipped).
        priority (str): Приоритет задачи (critical, high, medium, low).
        assignee (str | None): Назначенный исполнитель (partner1, partner2, both, None).
        notes (str | None): Заметки к задаче.
        order (int): Порядок отображения задачи в категории.
        completed_at (datetime | None): Время завершения задачи.
        category_id (UUID): Внешний ключ на ChecklistCategoryModel.
        category (ChecklistCategoryModel): Связь с категорией.

    Relationships:
        category: Many-to-One связь с ChecklistCategoryModel (категория задачи).

    Properties:
        is_completed: Проверяет, завершена ли задача.
        is_pending: Проверяет, находится ли задача в ожидании.
        is_in_progress: Проверяет, выполняется ли задача.

    Example:
        >>> task = ChecklistTaskModel(
        ...     title="Определить базовые расценки на типовые проекты",
        ...     description="Лендинг, интернет-магазин, корпоративный сайт",
        ...     status="pending",
        ...     priority="critical",
        ...     assignee="both",
        ...     order=1,
        ...     category_id=category.id
        ... )
        >>> task.is_pending
        True
        >>> task.mark_completed()
        >>> task.is_completed
        True
    """

    __tablename__ = "checklist_tasks"

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Название задачи",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание задачи",
    )

    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "in_progress",
            "completed",
            "skipped",
            name="task_status_enum",
        ),
        nullable=False,
        default="pending",
        index=True,
        comment="Статус задачи",
    )

    priority: Mapped[str] = mapped_column(
        Enum(
            "critical",
            "high",
            "medium",
            "low",
            name="task_priority_enum",
        ),
        nullable=False,
        default="medium",
        index=True,
        comment="Приоритет задачи",
    )

    assignee: Mapped[str | None] = mapped_column(
        Enum(
            "partner1",
            "partner2",
            "both",
            name="task_assignee_enum",
        ),
        nullable=True,
        comment="Назначенный исполнитель",
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Заметки к задаче",
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True,
        comment="Порядок отображения в категории",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время завершения задачи",
    )

    # Связь с категорией
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("checklist_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID категории задачи",
    )

    category: Mapped["ChecklistCategoryModel"] = relationship(
        "ChecklistCategoryModel",
        back_populates="tasks",
    )

    @property
    def is_completed(self) -> bool:
        """Проверяет, завершена ли задача."""
        return self.status == "completed"

    @property
    def is_pending(self) -> bool:
        """Проверяет, находится ли задача в ожидании."""
        return self.status == "pending"

    @property
    def is_in_progress(self) -> bool:
        """Проверяет, выполняется ли задача."""
        return self.status == "in_progress"

    def mark_completed(self) -> None:
        """Отмечает задачу как завершённую и устанавливает время завершения."""
        from datetime import UTC, datetime

        self.status = "completed"
        self.completed_at = datetime.now(UTC)

    def mark_in_progress(self) -> None:
        """Отмечает задачу как выполняемую."""
        self.status = "in_progress"

    def mark_pending(self) -> None:
        """Возвращает задачу в статус ожидания."""
        self.status = "pending"
        self.completed_at = None

    def __repr__(self) -> str:
        """Строковое представление модели для отладки."""
        return f"<ChecklistTaskModel(title={self.title[:30]}..., status={self.status})>"
