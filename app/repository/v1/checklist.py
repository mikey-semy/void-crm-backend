"""Репозиторий для работы с чек-листом партнёрства.

Этот модуль предоставляет операции с базой данных для управления
категориями и задачами чек-листа формализации партнёрства.

Наследуется от BaseRepository и реализует только специфичные методы,
все стандартные CRUD операции уже есть в базовом классе.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.v1 import ChecklistCategoryModel, ChecklistTaskModel
from app.repository.base import BaseRepository
from app.repository.cache import CacheBackend


class ChecklistCategoryRepository(BaseRepository[ChecklistCategoryModel]):
    """Репозиторий для операций с категориями чек-листа.

    Предоставляет методы для работы с категориями чек-листа.
    Стандартные CRUD операции наследуются от BaseRepository.

    Специфичные методы:
    - get_all_categories_with_tasks() - получение всех категорий с задачами
    - get_category_with_tasks() - получение категории с задачами по ID
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        """Инициализация репозитория категорий чек-листа.

        Args:
            session: Асинхронная SQLAlchemy сессия для операций с БД.
            cache_backend: Бэкенд для кеширования.
            enable_tracing: Включить трассировку запросов.
        """
        super().__init__(session, ChecklistCategoryModel, cache_backend, enable_tracing)

    async def get_all_categories_with_tasks(self) -> list[ChecklistCategoryModel]:
        """Получить все категории с задачами.

        Использует selectinload для eager loading связи tasks,
        чтобы избежать N+1 запросов. Категории отсортированы по order.
        Использует кеширование (TTL 5 минут).

        Returns:
            Список экземпляров ChecklistCategoryModel с загруженными задачами.

        Example:
            >>> repo = ChecklistCategoryRepository(session)
            >>> categories = await repo.get_all_categories_with_tasks()
            >>> for category in categories:
            ...     print(f"{category.title}: {category.progress_percentage}%")
        """
        cache_key = self.cache.build_key("ChecklistCategoryModel", "all_with_tasks")

        # Try cache
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # DB query
        stmt = (
            select(ChecklistCategoryModel)
            .options(selectinload(ChecklistCategoryModel.tasks))
            .order_by(ChecklistCategoryModel.order)
        )

        result = await self.session.execute(stmt)
        categories = list(result.scalars().all())

        # Set cache (5 минут, так как чек-лист часто обновляется)
        if categories:
            await self.cache.set(cache_key, categories, ttl=300)

        return categories

    async def get_category_with_tasks(self, category_id: UUID) -> ChecklistCategoryModel | None:
        """Получить категорию по ID с загруженными задачами.

        Загружает связь tasks через selectinload для избежания lazy loading.
        Задачи отсортированы по order.

        Args:
            category_id: UUID категории.

        Returns:
            ChecklistCategoryModel с подгруженными задачами или None если не найдено.

        Example:
            >>> category = await repo.get_category_with_tasks(uuid)
            >>> if category:
            ...     for task in category.tasks:
            ...         print(f"  - {task.title}: {task.status}")
        """
        stmt = (
            select(ChecklistCategoryModel)
            .where(ChecklistCategoryModel.id == category_id)
            .options(selectinload(ChecklistCategoryModel.tasks))
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_item(
        self,
        data: dict[str, Any],
        commit: bool = True,
        options: list[Any] | None = None,
        refresh: bool = True,
    ) -> ChecklistCategoryModel:
        """Создать категорию и автоматически сбросить кеш.

        Args:
            data: Данные для создания категории.
            commit: Если True - делает commit после создания.
            options: Опции загрузки relationships.
            refresh: Выполнять ли refresh созданной записи.

        Returns:
            ChecklistCategoryModel: Созданная категория.

        Raises:
            SQLAlchemyError: Если произошла ошибка при создании.
        """
        item = await super().create_item(data, commit, options, refresh)
        await self._invalidate_cache()
        return item

    async def update_item(
        self,
        item_id: UUID,
        data: dict[str, Any],
        options: list[Any] | None = None,
        refresh: bool = True,
    ) -> ChecklistCategoryModel | None:
        """Обновить категорию и автоматически сбросить кеш.

        Args:
            item_id: UUID категории.
            data: Словарь с данными для обновления.
            options: Дополнительные параметры для обновления.
            refresh: Флаг для обновления объекта в памяти.

        Returns:
            Обновленная категория или None если не найдено.
        """
        item = await super().update_item(item_id, data, options, refresh)
        await self._invalidate_cache()
        return item

    async def delete_item(self, item_id: UUID) -> bool:
        """Удалить категорию и сбросить кеш.

        Args:
            item_id: UUID категории.

        Returns:
            True если категория найдена и удалена, False если не найдено.
        """
        result = await super().delete_item(item_id)
        if result:
            await self._invalidate_cache()
        return result


class ChecklistTaskRepository(BaseRepository[ChecklistTaskModel]):
    """Репозиторий для операций с задачами чек-листа.

    Предоставляет методы для работы с задачами.
    Стандартные CRUD операции (фильтрация, подсчёт, обновление) наследуются от BaseRepository.

    Все методы используют существующий функционал BaseRepository:
    - filter_by_ordered() - для фильтрации с сортировкой
    - count_items() - для подсчёта с фильтрами
    - update_item() - для обновления с кешем
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        """Инициализация репозитория задач чек-листа.

        Args:
            session: Асинхронная SQLAlchemy сессия для операций с БД.
            cache_backend: Бэкенд для кеширования.
            enable_tracing: Включить трассировку запросов.
        """
        super().__init__(session, ChecklistTaskModel, cache_backend, enable_tracing)

    # Все остальные методы уже реализованы в BaseRepository:
    # - get_items_by_field(field="category_id", value=category_id) - получение задач по категории
    # - filter_by_ordered("order", status="pending") - получение задач по статусу
    # - filter_by_ordered("order", assignee="partner1") - получение задач по исполнителю
    # - filter_by_ordered("order", priority="critical") - получение критических задач
    # - count_items(status="completed") - подсчёт задач по статусу
    # - update_item(task_id, {"status": "completed", "completed_at": datetime.now(UTC)})
    # - delete_item(task_id) - удаление задачи

    async def create_item(
        self,
        data: dict[str, Any],
        commit: bool = True,
        options: list[Any] | None = None,
        refresh: bool = True,
    ) -> ChecklistTaskModel:
        """Создать задачу и автоматически сбросить кеш.

        Args:
            data: Данные для создания задачи.
            commit: Если True - делает commit после создания.
            options: Опции загрузки relationships.
            refresh: Выполнять ли refresh созданной записи.

        Returns:
            ChecklistTaskModel: Созданная задача.

        Raises:
            SQLAlchemyError: Если произошла ошибка при создании.
        """
        item = await super().create_item(data, commit, options, refresh)
        await self._invalidate_cache()
        return item

    async def update_item(
        self,
        item_id: UUID,
        data: dict[str, Any],
        options: list[Any] | None = None,
        refresh: bool = True,
    ) -> ChecklistTaskModel | None:
        """Обновить задачу и автоматически сбросить кеш.

        Args:
            item_id: UUID задачи.
            data: Словарь с данными для обновления.
            options: Дополнительные параметры для обновления.
            refresh: Флаг для обновления объекта в памяти.

        Returns:
            Обновленная задача или None если не найдено.
        """
        item = await super().update_item(item_id, data, options, refresh)
        await self._invalidate_cache()
        return item

    async def delete_item(self, item_id: UUID) -> bool:
        """Удалить задачу и сбросить кеш.

        Args:
            item_id: UUID задачи.

        Returns:
            True если задача найдена и удалена, False если не найдено.
        """
        result = await super().delete_item(item_id)
        if result:
            await self._invalidate_cache()
        return result
