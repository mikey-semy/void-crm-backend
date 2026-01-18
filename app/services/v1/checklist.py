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
from app.models.v1 import (
    ChecklistCategoryModel,
    ChecklistTaskModel,
    TaskDecisionFieldModel,
    TaskDecisionValueModel,
)
from app.repository.v1.checklist import (
    ChecklistCategoryRepository,
    ChecklistTaskRepository,
    DecisionFieldRepository,
    DecisionValueRepository,
)
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


class DecisionService(BaseService):
    """
    Сервис для управления полями решений задач чек-листа.

    Реализует бизнес-логику работы с полями решений:
    - CRUD для полей решений
    - Обновление значений полей
    - Валидация значений согласно типу поля
    - Получение сводки решений по категориям

    Attributes:
        field_repository: Репозиторий для работы с полями решений
        value_repository: Репозиторий для работы со значениями
        category_repository: Репозиторий для категорий (для сводки)
        logger: Логгер для отслеживания операций

    Example:
        >>> async with AsyncSession() as session:
        ...     service = DecisionService(session)
        ...     fields = await service.get_fields_by_task(task_id)
        ...     await service.update_value(field_id, 3000, "both")
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует DecisionService.

        Args:
            session: Асинхронная сессия SQLAlchemy для работы с БД
        """
        super().__init__(session)
        self.field_repository = DecisionFieldRepository(session)
        self.value_repository = DecisionValueRepository(session)
        self.category_repository = ChecklistCategoryRepository(session)

    # ==================== ПОЛЯ РЕШЕНИЙ ====================

    async def get_fields_by_task(self, task_id: UUID) -> list[TaskDecisionFieldModel]:
        """
        Получает все поля решений задачи с их значениями.

        Args:
            task_id: UUID задачи

        Returns:
            list[TaskDecisionFieldModel]: Список полей с загруженными значениями
        """
        fields = await self.field_repository.get_fields_by_task(task_id)
        self.logger.debug("Получено %d полей решений для задачи %s", len(fields), task_id)
        return fields

    async def create_field(self, task_id: UUID, data: dict) -> TaskDecisionFieldModel:
        """
        Создает новое поле решения для задачи.

        Args:
            task_id: UUID задачи
            data: Словарь с данными поля:
                - field_key (str): Уникальный ключ (snake_case)
                - field_type (str): Тип поля
                - label (str): Метка поля
                - description (str, optional): Подсказка
                - options (list, optional): Опции для select
                - is_required (bool, optional): Обязательное поле
                - order (int, optional): Порядок

        Returns:
            TaskDecisionFieldModel: Созданное поле

        Raises:
            ValidationError: Если поле с таким field_key уже существует
        """
        # Проверка уникальности field_key в рамках задачи
        existing = await self.field_repository.get_by_task_and_key(
            task_id, data["field_key"]
        )
        if existing:
            self.logger.error(
                "Поле с ключом %s уже существует для задачи %s",
                data["field_key"],
                task_id,
            )
            raise ValidationError(
                field="field_key",
                message=f"Поле с ключом '{data['field_key']}' уже существует",
            )

        data["task_id"] = task_id
        field = await self.field_repository.create_item(data)
        self.logger.info(
            "Создано поле решения: %s (id=%s, task=%s)",
            field.field_key,
            field.id,
            task_id,
        )
        return field

    async def update_field(self, field_id: UUID, data: dict) -> TaskDecisionFieldModel:
        """
        Обновляет поле решения.

        Args:
            field_id: UUID поля
            data: Словарь с обновляемыми полями

        Returns:
            TaskDecisionFieldModel: Обновлённое поле

        Raises:
            NotFoundError: Если поле не найдено
        """
        field = await self.field_repository.update_item(field_id, data)
        if not field:
            self.logger.error("Поле решения не найдено: %s", field_id)
            raise NotFoundError(
                detail="Поле решения не найдено",
                field="field_id",
                value=str(field_id),
            )

        self.logger.info("Обновлено поле решения: %s", field_id)
        return field

    async def delete_field(self, field_id: UUID) -> bool:
        """
        Удаляет поле решения (и его значение каскадно).

        Args:
            field_id: UUID поля

        Returns:
            bool: True если удалено

        Raises:
            NotFoundError: Если поле не найдено
        """
        result = await self.field_repository.delete_item(field_id)
        if not result:
            self.logger.error("Поле решения для удаления не найдено: %s", field_id)
            raise NotFoundError(
                detail="Поле решения не найдено",
                field="field_id",
                value=str(field_id),
            )

        self.logger.info("Удалено поле решения: %s", field_id)
        return result

    # ==================== ЗНАЧЕНИЯ РЕШЕНИЙ ====================

    async def update_value(
        self,
        field_id: UUID,
        value: any,
        filled_by: str | None = None,
    ) -> TaskDecisionFieldModel:
        """
        Обновляет значение поля решения.

        Валидирует значение согласно типу поля и правилам валидации.
        Создаёт или обновляет запись в task_decision_values.

        Args:
            field_id: UUID поля решения
            value: Значение для сохранения
            filled_by: Кто заполнил (partner1, partner2, both)

        Returns:
            TaskDecisionFieldModel: Поле с обновлённым значением

        Raises:
            NotFoundError: Если поле не найдено
            ValidationError: Если значение не валидно
        """
        # Получаем поле с текущим значением
        field = await self.field_repository.get_field_with_value(field_id)
        if not field:
            self.logger.error("Поле решения не найдено: %s", field_id)
            raise NotFoundError(
                detail="Поле решения не найдено",
                field="field_id",
                value=str(field_id),
            )

        # Валидация значения
        self._validate_value(field, value)

        # Upsert значения
        await self.value_repository.upsert_value(field_id, value, filled_by)

        # Возвращаем обновлённое поле
        updated_field = await self.field_repository.get_field_with_value(field_id)
        self.logger.info("Обновлено значение поля %s: %s", field.field_key, value)
        return updated_field

    async def bulk_update_values(
        self,
        task_id: UUID,
        values: list[dict],
    ) -> list[TaskDecisionFieldModel]:
        """
        Массовое обновление значений решений.

        Args:
            task_id: UUID задачи
            values: Список [{field_id, value, filled_by}, ...]

        Returns:
            list[TaskDecisionFieldModel]: Обновлённые поля
        """
        for item in values:
            await self.update_value(
                item["field_id"],
                item["value"],
                item.get("filled_by"),
            )

        self.logger.info("Массово обновлено %d значений для задачи %s", len(values), task_id)
        return await self.get_fields_by_task(task_id)

    def _validate_value(self, field: TaskDecisionFieldModel, value: any) -> None:
        """
        Валидация значения согласно типу и правилам поля.

        Args:
            field: Поле решения
            value: Значение для валидации

        Raises:
            ValidationError: Если значение не валидно
        """
        if value is None:
            if field.is_required:
                raise ValidationError(
                    field=field.field_key,
                    message="Обязательное поле",
                )
            return

        field_type = field.field_type
        rules = field.validation_rules or {}

        if field_type == "text":
            if not isinstance(value, str):
                raise ValidationError(
                    field=field.field_key,
                    message="Ожидается строка",
                )
            if rules.get("min_length") and len(value) < rules["min_length"]:
                raise ValidationError(
                    field=field.field_key,
                    message=f"Минимум {rules['min_length']} символов",
                )
            if rules.get("max_length") and len(value) > rules["max_length"]:
                raise ValidationError(
                    field=field.field_key,
                    message=f"Максимум {rules['max_length']} символов",
                )

        elif field_type == "number":
            if not isinstance(value, (int, float)):
                raise ValidationError(
                    field=field.field_key,
                    message="Ожидается число",
                )
            if rules.get("min") is not None and value < rules["min"]:
                raise ValidationError(
                    field=field.field_key,
                    message=f"Минимум {rules['min']}",
                )
            if rules.get("max") is not None and value > rules["max"]:
                raise ValidationError(
                    field=field.field_key,
                    message=f"Максимум {rules['max']}",
                )

        elif field_type == "select":
            valid_values = [opt["value"] for opt in (field.options or [])]
            if value not in valid_values:
                raise ValidationError(
                    field=field.field_key,
                    message=f"Значение должно быть одним из: {', '.join(valid_values)}",
                )

        elif field_type == "boolean":
            if not isinstance(value, bool):
                raise ValidationError(
                    field=field.field_key,
                    message="Ожидается boolean",
                )

    # ==================== СВОДКА РЕШЕНИЙ ====================

    async def get_decisions_summary(self, include_empty: bool = False) -> dict:
        """
        Получить сводку всех решений по категориям.

        Args:
            include_empty: Включать задачи без заполненных полей

        Returns:
            dict: Сводка решений с прогрессом
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Загружаем все категории с задачами и полями решений
        stmt = (
            select(ChecklistCategoryModel)
            .options(
                selectinload(ChecklistCategoryModel.tasks)
                .selectinload(ChecklistTaskModel.decision_fields)
                .selectinload(TaskDecisionFieldModel.value)
            )
            .order_by(ChecklistCategoryModel.order)
        )

        result = await self.session.execute(stmt)
        categories = list(result.scalars().all())

        summary = {
            "categories": [],
            "total_filled": 0,
            "total_fields": 0,
            "overall_progress": 0.0,
        }

        for category in categories:
            category_data = {
                "category_id": category.id,
                "category_title": category.title,
                "category_icon": category.icon,
                "category_color": category.color,
                "tasks": [],
                "filled_count": 0,
                "total_count": 0,
                "progress_percentage": 0.0,
            }

            for task in category.tasks:
                if not task.decision_fields:
                    continue  # Пропускаем задачи без полей решений

                filled = sum(1 for f in task.decision_fields if f.value is not None)
                total = len(task.decision_fields)

                # Пропускаем пустые, если не запрошено include_empty
                if not include_empty and filled == 0:
                    continue

                task_data = {
                    "task_id": task.id,
                    "task_title": task.title,
                    "task_status": task.status,
                    "fields": [self._field_to_dict(f) for f in task.decision_fields],
                    "filled_count": filled,
                    "total_count": total,
                    "is_complete": task.decision_fields_required_filled,
                }

                category_data["tasks"].append(task_data)
                category_data["filled_count"] += filled
                category_data["total_count"] += total

            # Пропускаем пустые категории
            if not category_data["tasks"]:
                continue

            if category_data["total_count"] > 0:
                category_data["progress_percentage"] = round(
                    (category_data["filled_count"] / category_data["total_count"]) * 100, 2
                )

            summary["categories"].append(category_data)
            summary["total_filled"] += category_data["filled_count"]
            summary["total_fields"] += category_data["total_count"]

        if summary["total_fields"] > 0:
            summary["overall_progress"] = round(
                (summary["total_filled"] / summary["total_fields"]) * 100, 2
            )

        self.logger.debug(
            "Получена сводка решений: %d категорий, прогресс %.1f%%",
            len(summary["categories"]),
            summary["overall_progress"],
        )
        return summary

    async def get_completed_tasks_summary(self) -> dict:
        """
        Получить сводку всех завершённых задач с их решениями.

        Возвращает только задачи со статусом 'completed', включая:
        - Комментарии (notes)
        - Ответственного (assignee)
        - Дату завершения (completed_at)
        - Поля решений (decision_fields), если есть

        Returns:
            dict: Сводка завершённых задач с прогрессом
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Загружаем все категории с завершёнными задачами и полями решений
        stmt = (
            select(ChecklistCategoryModel)
            .options(
                selectinload(ChecklistCategoryModel.tasks)
                .selectinload(ChecklistTaskModel.decision_fields)
                .selectinload(TaskDecisionFieldModel.value)
            )
            .order_by(ChecklistCategoryModel.order)
        )

        result = await self.session.execute(stmt)
        categories = list(result.scalars().all())

        summary = {
            "categories": [],
            "total_filled": 0,
            "total_fields": 0,
            "overall_progress": 0.0,
        }

        for category in categories:
            category_data = {
                "category_id": category.id,
                "category_title": category.title,
                "category_icon": category.icon,
                "category_color": category.color,
                "tasks": [],
                "filled_count": 0,
                "total_count": 0,
                "progress_percentage": 0.0,
            }

            for task in category.tasks:
                # Показываем только завершённые задачи
                if task.status != "completed":
                    continue

                # Подсчёт заполненных полей решений
                filled = sum(1 for f in task.decision_fields if f.value is not None)
                total = len(task.decision_fields)

                task_data = {
                    "task_id": task.id,
                    "task_title": task.title,
                    "task_status": task.status,
                    "notes": task.notes,
                    "assignee": task.assignee,
                    "completed_at": task.completed_at,
                    "fields": [self._field_to_dict(f) for f in task.decision_fields],
                    "filled_count": filled,
                    "total_count": total,
                    "is_complete": task.decision_fields_required_filled if task.decision_fields else True,
                }

                category_data["tasks"].append(task_data)
                category_data["filled_count"] += filled
                category_data["total_count"] += total

            # Пропускаем категории без завершённых задач
            if not category_data["tasks"]:
                continue

            if category_data["total_count"] > 0:
                category_data["progress_percentage"] = round(
                    (category_data["filled_count"] / category_data["total_count"]) * 100, 2
                )

            summary["categories"].append(category_data)
            summary["total_filled"] += category_data["filled_count"]
            summary["total_fields"] += category_data["total_count"]

        if summary["total_fields"] > 0:
            summary["overall_progress"] = round(
                (summary["total_filled"] / summary["total_fields"]) * 100, 2
            )

        self.logger.debug(
            "Получена сводка завершённых задач: %d категорий, прогресс %.1f%%",
            len(summary["categories"]),
            summary["overall_progress"],
        )
        return summary

    def _field_to_dict(self, field: TaskDecisionFieldModel) -> dict:
        """Конвертация поля в словарь для ответа."""
        return {
            "id": field.id,
            "task_id": field.task_id,
            "field_key": field.field_key,
            "field_type": field.field_type,
            "label": field.label,
            "description": field.description,
            "options": field.options,
            "is_required": field.is_required,
            "order": field.order,
            "value": field.value.value if field.value else None,
            "filled_by": field.value.filled_by if field.value else None,
            "filled_at": field.value.filled_at if field.value else None,
        }
