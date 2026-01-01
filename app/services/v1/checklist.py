"""
Сервис для бизнес-логики работы с чек-листом партнёрства.

Модуль предоставляет ChecklistService для управления категориями и задачами чек-листа:
- CRUD операции для категорий и задач
- Получение всех категорий с задачами
- Обновление статуса задач с автоматическим проставлением completed_at
- Подсчёт статистики выполнения

КРИТИЧНО: Сервис возвращает только SQLAlchemy модели (ChecklistCategoryModel, ChecklistTaskModel),
конвертация в Pydantic схемы происходит на уровне Router!
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.v1 import ChecklistCategoryModel, ChecklistTaskModel
from app.repository.v1.checklist import ChecklistCategoryRepository, ChecklistTaskRepository
from app.services.base import BaseService


class ChecklistService(BaseService):
    """
    Сервис для управления чек-листом партнёрства.

    Реализует бизнес-логику работы с категориями и задачами чек-листа:
    - Создание/обновление категорий и задач
    - Получение всех категорий с задачами
    - Обновление статуса задач с автоматической установкой времени завершения
    - Валидация данных перед сохранением

    Attributes:
        category_repository: Репозиторий для работы с категориями
        task_repository: Репозиторий для работы с задачами
        logger: Логгер для отслеживания операций

    Example:
        >>> async with AsyncSession() as session:
        ...     service = ChecklistService(session)
        ...     # Получение всех категорий с задачами
        ...     categories = await service.get_all_categories_with_tasks()
        ...
        ...     # Обновление статуса задачи
        ...     task = await service.update_task_status(task_id, "completed")
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует ChecklistService.

        Args:
            session: Асинхронная сессия SQLAlchemy для работы с БД
        """
        super().__init__(session)
        self.category_repository = ChecklistCategoryRepository(session)
        self.task_repository = ChecklistTaskRepository(session)

    # ==================== КАТЕГОРИИ ====================

    async def get_all_categories_with_tasks(self) -> list[ChecklistCategoryModel]:
        """
        Получает все категории чек-листа с задачами.

        Использует кеширование на уровне репозитория.
        Категории отсортированы по order, задачи также по order.

        Returns:
            list[ChecklistCategoryModel]: Список всех категорий с загруженными задачами

        Example:
            >>> categories = await service.get_all_categories_with_tasks()
            >>> for category in categories:
            ...     print(f"{category.title}: {category.progress_percentage}%")
        """
        categories = await self.category_repository.get_all_categories_with_tasks()
        self.logger.debug("Получено %d категорий с задачами", len(categories))
        return categories

    async def get_category_by_id(self, category_id: UUID) -> ChecklistCategoryModel:
        """
        Получает категорию по ID с задачами.

        Args:
            category_id: UUID категории

        Returns:
            ChecklistCategoryModel: Категория с задачами

        Raises:
            NotFoundError: Если категория не найдена

        Example:
            >>> category = await service.get_category_by_id(uuid)
        """
        category = await self.category_repository.get_category_with_tasks(category_id)
        if not category:
            self.logger.error("Категория не найдена: %s", category_id)
            raise NotFoundError(detail="Категория не найдена", field="category_id", value=str(category_id))

        self.logger.debug("Получена категория: %s", category.title)
        return category

    async def create_category(self, data: dict) -> ChecklistCategoryModel:
        """
        Создает новую категорию чек-листа.

        Args:
            data: Словарь с данными категории
                - title (str): Название категории
                - description (str, optional): Описание
                - icon (str, optional): Название иконки
                - color (str, optional): HEX цвет
                - order (int, optional): Порядок отображения

        Returns:
            ChecklistCategoryModel: Созданная категория

        Example:
            >>> category = await service.create_category({
            ...     "title": "Финансы",
            ...     "icon": "DollarSign",
            ...     "color": "#10b981",
            ...     "order": 1
            ... })
        """
        category = await self.category_repository.create_item(data)
        self.logger.info(
            "Создана категория: %s (id=%s, order=%s)",
            category.title,
            category.id,
            category.order,
        )
        return category

    async def update_category(self, category_id: UUID, data: dict) -> ChecklistCategoryModel:
        """
        Обновляет категорию чек-листа.

        Args:
            category_id: UUID категории
            data: Словарь с обновляемыми полями

        Returns:
            ChecklistCategoryModel: Обновленная категория

        Raises:
            NotFoundError: Если категория не найдена

        Example:
            >>> updated = await service.update_category(
            ...     category_id,
            ...     {"title": "Финансы и ценообразование"}
            ... )
        """
        category = await self.category_repository.update_item(category_id, data)
        if not category:
            self.logger.error("Категория для обновления не найдена: %s", category_id)
            raise NotFoundError(detail="Категория не найдена", field="category_id", value=str(category_id))

        self.logger.info("Обновлена категория: %s", category_id)
        return category

    async def delete_category(self, category_id: UUID) -> bool:
        """
        Удаляет категорию чек-листа.

        Задачи категории также будут удалены (CASCADE).

        Args:
            category_id: UUID категории

        Returns:
            bool: True если категория удалена

        Raises:
            NotFoundError: Если категория не найдена

        Example:
            >>> await service.delete_category(category_id)
        """
        result = await self.category_repository.delete_item(category_id)
        if not result:
            self.logger.error("Категория для удаления не найдена: %s", category_id)
            raise NotFoundError(detail="Категория не найдена", field="category_id", value=str(category_id))

        self.logger.info("Удалена категория: %s", category_id)
        return result

    # ==================== ЗАДАЧИ ====================

    async def get_task_by_id(self, task_id: UUID) -> ChecklistTaskModel:
        """
        Получает задачу по ID.

        Args:
            task_id: UUID задачи

        Returns:
            ChecklistTaskModel: Задача

        Raises:
            NotFoundError: Если задача не найдена

        Example:
            >>> task = await service.get_task_by_id(uuid)
        """
        task = await self.task_repository.get_item_by_id(task_id)
        if not task:
            self.logger.error("Задача не найдена: %s", task_id)
            raise NotFoundError(detail="Задача не найдена", field="task_id", value=str(task_id))

        self.logger.debug("Получена задача: %s", task.title)
        return task

    async def get_tasks_by_category(self, category_id: UUID) -> list[ChecklistTaskModel]:
        """
        Получает все задачи категории.

        Args:
            category_id: UUID категории

        Returns:
            list[ChecklistTaskModel]: Список задач, отсортированных по order

        Example:
            >>> tasks = await service.get_tasks_by_category(category_id)
        """
        tasks = await self.task_repository.get_tasks_by_category(category_id)
        self.logger.debug("Получено %d задач для категории %s", len(tasks), category_id)
        return tasks

    async def create_task(self, data: dict) -> ChecklistTaskModel:
        """
        Создает новую задачу чек-листа.

        Проверяет существование категории перед созданием.

        Args:
            data: Словарь с данными задачи
                - title (str): Название задачи
                - description (str, optional): Описание
                - status (str, optional): Статус (по умолчанию "pending")
                - priority (str, optional): Приоритет (по умолчанию "medium")
                - assignee (str, optional): Исполнитель
                - notes (str, optional): Заметки
                - order (int, optional): Порядок отображения
                - category_id (UUID): ID категории

        Returns:
            ChecklistTaskModel: Созданная задача

        Raises:
            NotFoundError: Если категория не найдена

        Example:
            >>> task = await service.create_task({
            ...     "title": "Определить базовые расценки",
            ...     "category_id": finance_category_id,
            ...     "priority": "critical",
            ...     "assignee": "both"
            ... })
        """
        # Проверка существования категории
        category = await self.category_repository.get_item_by_id(data["category_id"])
        if not category:
            self.logger.error("Категория не найдена: %s", data["category_id"])
            raise NotFoundError(detail="Категория не найдена", field="category_id", value=str(data["category_id"]))

        task = await self.task_repository.create_item(data)
        self.logger.info(
            "Создана задача: %s (id=%s, category=%s, priority=%s)",
            task.title,
            task.id,
            task.category_id,
            task.priority,
        )
        return task

    async def update_task(self, task_id: UUID, data: dict) -> ChecklistTaskModel:
        """
        Обновляет задачу чек-листа.

        Автоматически устанавливает completed_at при изменении статуса на "completed".
        Сбрасывает completed_at при изменении статуса обратно на "pending" или "in_progress".

        Args:
            task_id: UUID задачи
            data: Словарь с обновляемыми полями

        Returns:
            ChecklistTaskModel: Обновленная задача

        Raises:
            NotFoundError: Если задача не найдена

        Example:
            >>> # Обновление статуса и заметок
            >>> updated = await service.update_task(
            ...     task_id,
            ...     {"status": "completed", "notes": "Прайс-лист согласован"}
            ... )
        """
        # Автоматическая установка/сброс completed_at при изменении статуса
        if "status" in data:
            if data["status"] == "completed":
                data["completed_at"] = datetime.now(UTC)
            elif data["status"] in ("pending", "in_progress"):
                data["completed_at"] = None

        task = await self.task_repository.update_item(task_id, data)
        if not task:
            self.logger.error("Задача для обновления не найдена: %s", task_id)
            raise NotFoundError(detail="Задача не найдена", field="task_id", value=str(task_id))

        self.logger.info("Обновлена задача: %s (status=%s)", task_id, task.status)
        return task

    async def update_task_status(self, task_id: UUID, status: str) -> ChecklistTaskModel:
        """
        Быстрое обновление только статуса задачи.

        Используется для WebSocket обновлений.
        Автоматически устанавливает completed_at.

        Args:
            task_id: UUID задачи
            status: Новый статус (pending, in_progress, completed, skipped)

        Returns:
            ChecklistTaskModel: Обновленная задача

        Raises:
            NotFoundError: Если задача не найдена
            ValidationError: Если статус невалидный

        Example:
            >>> task = await service.update_task_status(task_id, "completed")
        """
        # Валидация статуса
        valid_statuses = ("pending", "in_progress", "completed", "skipped")
        if status not in valid_statuses:
            self.logger.error("Невалидный статус: %s", status)
            raise ValidationError(
                field="status",
                message=f"Статус должен быть одним из: {', '.join(valid_statuses)}",
            )

        return await self.update_task(task_id, {"status": status})

    async def delete_task(self, task_id: UUID) -> bool:
        """
        Удаляет задачу чек-листа.

        Args:
            task_id: UUID задачи

        Returns:
            bool: True если задача удалена

        Raises:
            NotFoundError: Если задача не найдена

        Example:
            >>> await service.delete_task(task_id)
        """
        result = await self.task_repository.delete_item(task_id)
        if not result:
            self.logger.error("Задача для удаления не найдена: %s", task_id)
            raise NotFoundError(detail="Задача не найдена", field="task_id", value=str(task_id))

        self.logger.info("Удалена задача: %s", task_id)
        return result

    # ==================== СТАТИСТИКА ====================

    async def get_statistics(self) -> dict:
        """
        Получает статистику по чек-листу.

        Returns:
            dict: Статистика с количеством задач по статусам

        Example:
            >>> stats = await service.get_statistics()
            >>> # {"pending": 15, "in_progress": 3, "completed": 8, "skipped": 1}
        """
        stats = await self.task_repository.count_by_status()
        self.logger.debug("Получена статистика: %s", stats)
        return stats
