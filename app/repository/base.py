"""
Базовый репозиторий для profitool-store.
"""

# pylint: disable=not-callable  # func.count() is callable in SQLAlchemy
import logging
import time
from collections.abc import Awaitable, Callable
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
)
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes, lazyload
from sqlalchemy.sql.expression import Executable

from app.models import BaseModel
from app.repository.cache import CacheBackend, NoCacheBackend
from app.repository.monitoring import CompositeQueryHook, LoggingHook, QueryMetrics

if TYPE_CHECKING:
    from app.schemas.pagination import PaginationParamsSchema

# Generic types
M = TypeVar("M", bound=BaseModel)
T = TypeVar("T")


class SessionMixin:
    """
    Миксин для предоставления экземпляра сессии базы данных.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализирует миксин с сессией базы данных.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных.
        """
        self.session = session


class BaseRepository(SessionMixin, Generic[M]):
    """
    Базовый класс для репозиториев с расширенной функциональностью.

    Предоставляет полный набор методов для работы с базой данных с минимизацией
    лишних запросов и оптимизацией производительности.

    ## Основные возможности

    **CRUD операции:**
    - `create_item()` - создание записи
    - `create_with_related()` - создание записи со связанными объектами
    - `get_item_by_id()` - получение по ID
    - `get_item_by_field()` - получение по полю
    - `get_item_by_fields_or()` - получение по нескольким полям (OR)
    - `get_items()` - получение списка
    - `get_items_by_field()` - получение списка по полю
    - `update_item()` - обновление записи
    - `delete_item()` - удаление записи

    **Фильтрация и поиск:**
    - `filter_by()` - фильтрация с операторами (eq, ne, gt, lt, gte, lte, in, not_in, like, ilike, is_null)
    - `filter_by_ordered()` - фильтрация с сортировкой
    - `count_items()` - подсчет с фильтрами
    - `exists_by_field()` - проверка существования

    **SELECT FOR UPDATE (конкурентность):**
    - `get_item_by_id_for_update()` - получение с блокировкой
    - `filter_by_for_update()` - фильтрация с блокировкой

    **Проекции (частичная загрузка):**
    - `project_fields()` - получить несколько полей как словари
    - `project_field()` - получить одно поле как список
    - `project_one()` - получить одну запись с проекцией

    **Кеширование:**
    - `get_item_by_id_cached()` - получение с кешированием

    **Batch операции:**
    - `bulk_create()` - массовое создание
    - `bulk_update()` - массовое обновление
    - `bulk_upsert()` - массовый upsert (ON CONFLICT)

    **Связанные объекты:**
    - `get_items_with_relations()` - получение со связями
    - `get_paginated_items()` - пагинация с сортировкой

    **Утилиты:**
    - `get_or_create()` - получить или создать
    - `update_or_create()` - обновить или создать
    - `delete_by_filters()` - удаление по фильтрам
    - `execute_statement()` - выполнить произвольный запрос

    **Трассировка и хуки:**
    - `add_hook()` - добавить хук для мониторинга
    - `remove_hook()` - удалить хук

    Attributes:
        session (AsyncSession): Асинхронная сессия базы данных.
        model (Type[M]): Тип SQLAlchemy модели.
        cache (CacheBackend): Бэкенд для кеширования.
        enable_tracing (bool): Включена ли трассировка запросов.
        hooks (CompositeQueryHook): Композитный хук для трассировки.

    Class Attributes:
        default_options (List[Any]): Опции загрузки по умолчанию для всех запросов.

    Example:
        >>> # Создание репозитория с кешированием и трассировкой
        >>> class ProductRepository(BaseRepository[ProductModel]):
        ...     default_options = [selectinload(ProductModel.categories)]
        >>>
        >>> from app.repository.cache import RedisCacheBackend
        >>> cache = RedisCacheBackend()
        >>> repo = ProductRepository(
        ...     session,
        ...     ProductModel,
        ...     cache_backend=cache,
        ...     enable_tracing=True
        ... )
        >>>
        >>> # Использование проекций для списка
        >>> products = await repo.project_fields(['id', 'name', 'price'], is_active=True)
    """

    # Default options на уровне класса (переопределяются в наследниках)
    default_options: list[Any] = []

    def __init__(
        self,
        session: AsyncSession,
        model: type[M],
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        """
        Инициализирует BaseRepository с расширенной функциональностью.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных.
            model (Type[M]): Тип SQLAlchemy модели.
            cache_backend (Optional[CacheBackend]): Бэкенд для кеширования.
                По умолчанию NoCacheBackend (кеш отключен).
            enable_tracing (bool): Включить трассировку запросов (по умолчанию False).
                Если True, автоматически добавляется LoggingHook.

        Example:
            >>> from app.repository.cache import RedisCacheBackend
            >>> cache = RedisCacheBackend()
            >>> repo = ProductRepository(session, ProductModel,
            ...                          cache_backend=cache,
            ...                          enable_tracing=True)
        """
        super().__init__(session)
        self.model = model
        self.logger = logging.getLogger(self.__class__.__name__)

        # Кеширование
        self.cache = cache_backend or NoCacheBackend()

        # Трассировка запросов
        self.enable_tracing = enable_tracing
        self.hooks = CompositeQueryHook()
        if enable_tracing:
            self.hooks.add(LoggingHook())

    async def create_item(
        self,
        data: dict[str, Any],
        commit: bool = True,
        options: list[Any] | None = None,
        refresh: bool = True,
    ) -> M:
        """
        Создает новую запись в базе данных.

        Args:
            data (Dict[str, Any]): Данные для создания записи.
            commit (bool): Если True - делает commit после создания.
                Если False - только flush (для использования в транзакциях).
            options (Optional[List[Any]]): Опции загрузки relationships (selectinload, joinedload).
            refresh (bool): Выполнять ли refresh созданной записи (по умолчанию True).

        Returns:
            M: Созданная SQLAlchemy модель.

        Raises:
            SQLAlchemyError: Если произошла ошибка при создании.

        Example:
            >>> await repo.create_item(
                >>> data,
                >>> options=[selectinload(self.model.relation)],
                >>> refresh=False
            >>> )
            >>> # insert + select с eager load, без лишнего refresh
        """
        try:
            instance = self.model(**data)
            self.session.add(instance)
            await self.session.flush()  # Отправляем в БД, но транзакция остается открытой

            if commit:
                await self.session.commit()  # Коммитим транзакцию

            if options:
                stmt = select(self.model).where(self.model.id == instance.id).options(*options)
                result = await self.session.execute(stmt)
                instance = result.scalar_one()
            elif refresh:
                await self.session.refresh(instance)  # Обновляем поля (id, created_at и т.д.)

            self.logger.info(
                "Создана запись %s",
                self.model.__name__,
                extra={
                    "model": self.model.__name__,
                    "id": getattr(instance, "id", None),
                },
            )
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при создании %s: %s", self.model.__name__, e)
            raise

    async def create_with_related(
        self,
        main_data: dict[str, Any],
        related_items: list[tuple[type[BaseModel], dict[str, Any]]],
    ) -> M:
        """
        Создает основную запись и связанные записи в одной транзакции.

        Атомарная операция: либо создаются ВСЕ записи, либо НИ ОДНА.
        После flush основной записи её ID доступен для связанных записей.

        Args:
            main_data: Данные для основной записи (self.model).
            related_items: Список кортежей (Model, data) для связанных записей.
                Example: [(UserRoleModel, {"role_code": "user"})]

        Returns:
            M: Созданная основная SQLAlchemy модель с актуальными данными.

        Raises:
            SQLAlchemyError: При ошибках работы с БД (откатывает все операции).

        Example:
            >>> # Создать пользователя и роль в одной транзакции
            >>> user = await repo.create_with_related(
            ...     main_data={"username": "john", "email": "j@ex.com"},
            ...     related_items=[
            ...         (UserRoleModel, {"user_id": None, "role_code": "user"})
            ...     ]
            ... )
            >>> # user_id будет автоматически подставлен после flush
        """
        try:
            # 1. Создаём основную запись БЕЗ commit (add + flush)
            main_instance = self.model(**main_data)
            self.session.add(main_instance)
            await self.session.flush()  # Генерирует ID основной записи

            # 2. Создаём связанные записи в той же транзакции
            for related_model, related_data in related_items:
                # Автоматически подставляем ID основной записи для FK полей со значением None
                # Копируем данные, чтобы не изменять оригинал
                filled_data = related_data.copy()

                # Ищем поля с None, которые заканчиваются на _id (потенциальные FK)
                for field_name, field_value in list(filled_data.items()):
                    if field_value is None and field_name.endswith("_id"):
                        # Проверяем, есть ли такое поле в related_model
                        if hasattr(related_model, field_name):
                            # Подставляем ID основной записи
                            filled_data[field_name] = main_instance.id

                related_instance = related_model(**filled_data)
                self.session.add(related_instance)

            # 3. Flush для сохранения, но транзакция остается открытой
            await self.session.flush()

            # 4. Refresh для получения актуальных данных ДО commit
            await self.session.refresh(main_instance)

            # 5. Commit для финализации ВСЕХ записей одновременно
            await self.session.commit()

            self.logger.info(
                "Создана запись %s с %d связанными записями",
                self.model.__name__,
                len(related_items),
                extra={
                    "model": self.model.__name__,
                    "id": main_instance.id,
                    "related_count": len(related_items),
                },
            )

            return main_instance

        except SQLAlchemyError as e:
            # Откатываем ВСЮ транзакцию (main + related)
            await self.session.rollback()
            self.logger.error(
                "Ошибка при создании %s с связанными записями: %s",
                self.model.__name__,
                str(e),
                exc_info=True,
            )
            raise

    async def get_item_by_id(self, item_id: UUID, options: list[Any] | None = None) -> M | None:
        """
        Получает запись по ID.

        Args:
            item_id (UUID): ID записи.
            options (Optional[List[Any]]): Опции для загрузки связей (selectinload, joinedload).

        Returns:
            Optional[M]: SQLAlchemy модель или None, если не найдена.

        Example:
            >>> await repo.get_item_by_id(
                >>> item_id,
                >>> options=[selectinload(self.model.children)]
            >>> )
        """
        try:
            statement = select(self.model).where(self.model.id == item_id)
            if options:
                for option in options:
                    statement = statement.options(option)
            result = await self.session.execute(statement)
            return result.scalar()
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при получении %s по ID %s: %s", self.model.__name__, item_id, e)
            return None

    async def get_item_by_field(self, field_name: str, field_value: Any, options: list[Any] | None = None) -> M | None:
        """
        Получает запись по указанному полю.

        Args:
            field_name (str): Название поля.
            field_value (Any): Значение поля.
            options (Optional[List[Any]]): Опции для загрузки связей.

        Returns:
            Optional[M]: SQLAlchemy модель или None, если не найдена.

        Example:
            >>> await repo.get_item_by_field(
                >>> "code",
                >>> code,
                >>> options=[selectinload(self.model.tags)]
            >>> )
        """
        try:
            if not hasattr(self.model, field_name):
                raise ValueError(f"Поле '{field_name}' не существует в модели {self.model.__name__}")

            field = getattr(self.model, field_name)
            statement = select(self.model).where(field == field_value)
            if options:
                for option in options:
                    statement = statement.options(option)
            result = await self.session.execute(statement)
            return result.scalar()
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при получении %s по полю %s=%s: %s",
                self.model.__name__,
                field_name,
                field_value,
                e,
            )
            return None

    async def get_item_by_fields_or(self, **field_values: Any) -> M | None:
        """
        Получает запись по нескольким полям с OR-логикой.

        Выполняет поиск записи, где ХОТЯ БЫ ОДНО из указанных полей
        совпадает с переданным значением (field1=value1 OR field2=value2).

        Args:
            **field_values: Пары поле=значение для поиска.

        Returns:
            Optional[M]: SQLAlchemy модель или None, если не найдена.

        Raises:
            ValueError: Если передано поле, не существующее в модели.

        Example:
            >>> # Найти пользователя по email ИЛИ username
            >>> user = await repo.get_item_by_fields_or(
            ...     email="test@example.com",
            ...     username="testuser"
            ... )
        """
        try:
            from sqlalchemy import or_

            if not field_values:
                return None

            # Проверяем существование полей и строим OR-условия
            conditions = []
            for field_name, field_value in field_values.items():
                if not hasattr(self.model, field_name):
                    raise ValueError(f"Поле '{field_name}' не существует в модели {self.model.__name__}")
                field = getattr(self.model, field_name)
                conditions.append(field == field_value)

            statement = select(self.model).where(or_(*conditions))
            result = await self.session.execute(statement)
            return result.scalar()

        except SQLAlchemyError as e:
            self.logger.error("Ошибка при получении %s по полям OR: %s", self.model.__name__, e)
            return None

    async def get_items(
        self,
        limit: int | None = None,
        offset: int | None = None,
        options: list[Any] | None = None,
    ) -> list[M]:
        """
        Получает список всех записей.

        Args:
            limit (Optional[int]): Лимит записей.
            offset (Optional[int]): Смещение.
            options (Optional[List[Any]]): Опции для загрузки связей.

        Returns:
            List[M]: Список SQLAlchemy моделей.

        Example:
            >>> await repo.get_items(
                >>> options=[selectinload(self.model.relation)],
                >>> limit=50
            >>> )
        """
        try:
            statement = select(self.model)

            # Применяем default_options и переданные options
            statement = self._apply_default_options(statement, options)

            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            result = await self.session.execute(statement)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при получении списка %s: %s", self.model.__name__, e)
            return []

    async def get_items_by_field(
        self,
        field_name: str,
        field_value: Any,
        limit: int | None = None,
        offset: int | None = None,
        options: list[Any] | None = None,
    ) -> list[M]:
        """
        Получает список записей по указанному полю.

        Args:
            field_name (str): Название поля.
            field_value (Any): Значение поля.
            limit (Optional[int]): Лимит записей.
            offset (Optional[int]): Смещение.
            options (Optional[List[Any]]): Опции для загрузки связей.

        Returns:
            List[M]: Список SQLAlchemy моделей.

        Example:
            >>> await repo.get_items_by_field(
                >>> "category_id",
                >>> cid,
                >>> options=[selectinload(self.model.images)]
            >>> )
        """
        try:
            if not hasattr(self.model, field_name):
                raise ValueError(f"Поле '{field_name}' не существует в модели {self.model.__name__}")

            field = getattr(self.model, field_name)
            statement = select(self.model).where(field == field_value)

            if options:
                for option in options:
                    statement = statement.options(option)

            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            result = await self.session.execute(statement)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при получении списка %s по полю %s=%s: %s",
                self.model.__name__,
                field_name,
                field_value,
                e,
            )
            return []

    async def update_item(
        self,
        item_id: UUID,
        data: dict[str, Any],
        options: list[Any] | None = None,
        refresh: bool = True,
    ) -> M | None:
        """
        Обновляет запись по ID.

        Args:
            item_id (UUID): ID записи.
            data (Dict[str, Any]): Данные для обновления.
            options (Optional[List[Any]]): Опции загрузки relationships (selectinload, joinedload).
            refresh (bool): Выполнять ли refresh после commit (по умолчанию True).

        Returns:
            Optional[M]: Обновленная SQLAlchemy модель или None, если не найдена.

        Raises:
            SQLAlchemyError: Если произошла ошибка при обновлении.

        Example:
            >>> await repo.update_item(
                >>> item_id,
                >>> data,
                >>> options=[selectinload(self.model.relation)],
                >>> refresh=False
            >>> )
        """
        try:
            instance = await self.get_item_by_id(item_id)
            if not instance:
                return None

            for key, value in data.items():
                if hasattr(instance, key) and key != "id":  # Не обновляем ID
                    setattr(instance, key, value)
                    # Помечаем JSONB поля как измененные для SQLAlchemy
                    if key in ("json_value", "metadata"):
                        attributes.flag_modified(instance, key)

            await self.session.commit()

            if options:
                stmt = select(self.model).where(self.model.id == item_id).options(*options)
                result = await self.session.execute(stmt)
                instance = result.scalar_one()
            elif refresh:
                await self.session.refresh(instance)

            self.logger.info(
                "Обновлена запись %s",
                self.model.__name__,
                extra={"model": self.model.__name__, "id": item_id},
            )
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при обновлении %s с ID %s: %s", self.model.__name__, item_id, e)
            raise

    async def delete_item(self, item_id: UUID) -> bool:
        """
        Удаляет запись по ID.

        Args:
            item_id (UUID): ID записи.

        Returns:
            bool: True, если запись удалена, False, если не найдена.

        Raises:
            SQLAlchemyError: Если произошла ошибка при удалении.
        """
        try:
            instance = await self.get_item_by_id(item_id)
            if not instance:
                return False

            await self.session.delete(instance)
            await self.session.commit()

            self.logger.info(
                "Удалена запись %s",
                self.model.__name__,
                extra={"model": self.model.__name__, "id": item_id},
            )
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при удалении %s с ID %s: %s", self.model.__name__, item_id, e)
            raise

    async def bulk_get_by_ids(self, ids: list[UUID]) -> list[M]:
        """
        Массовое получение записей по списку ID.

        Args:
            ids (List[UUID]): Список ID записей для получения.

        Returns:
            List[M]: Список найденных моделей.

        Raises:
            SQLAlchemyError: Если произошла ошибка при получении.

        Example:
            >>> # Получить несколько продуктов
            >>> products = await repo.bulk_get_by_ids([uuid1, uuid2, uuid3])
            >>> print(f"Найдено {len(products)} записей")
        """
        try:
            statement = select(self.model).where(self.model.id.in_(ids))
            result = await self.session.execute(statement)
            items = result.scalars().all()

            self.logger.info(
                "Массовое получение %s: найдено %d записей из %d запрошенных",
                self.model.__name__,
                len(items),
                len(ids),
            )
            return list(items)
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при массовом получении %s: %s", self.model.__name__, e)
            raise

    async def bulk_delete_by_ids(self, ids: list[UUID]) -> int:
        """
        Массовое удаление записей по списку ID.

        Args:
            ids (List[UUID]): Список ID записей для удаления.

        Returns:
            int: Количество удалённых записей.

        Raises:
            SQLAlchemyError: Если произошла ошибка при удалении.

        Example:
            >>> # Удалить несколько продуктов
            >>> deleted_count = await repo.bulk_delete_by_ids([uuid1, uuid2, uuid3])
            >>> print(f"Удалено {deleted_count} записей")
        """
        try:
            statement = delete(self.model).where(self.model.id.in_(ids))
            result = await self.session.execute(statement)
            await self.session.commit()

            deleted_count = result.rowcount
            self.logger.info(
                "Массовое удаление %s: удалено %d записей",
                self.model.__name__,
                deleted_count,
            )
            return deleted_count
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при массовом удалении %s: %s", self.model.__name__, e)
            raise

    async def count_items(self, **filters) -> int:
        """
        Подсчитывает количество записей с фильтрами.

        Args:
            **filters: Фильтры для подсчета (поддерживает операторы как в filter_by).

        Returns:
            int: Количество записей.

        Example:
            >>> # Простой подсчет
            >>> count = await repo.count_items(is_active=True)
            >>>
            >>> # С операторами
            >>> count = await repo.count_items(sort_order__gte=10, parent_id__is_null=True)
        """
        try:
            statement = select(func.count()).select_from(self.model)

            # Используем централизованную логику фильтрации
            conditions = self._build_filter_conditions(**filters)
            if conditions:
                statement = statement.where(and_(*conditions))

            result = await self.session.execute(statement)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при подсчете %s: %s", self.model.__name__, e)
            return 0

    async def exists_by_field(self, field_name: str, field_value: Any) -> bool:
        """
        Проверяет существование записи по полю.

        Args:
            field_name (str): Название поля.
            field_value (Any): Значение поля.

        Returns:
            bool: True, если запись существует, False иначе.

        Example (минимум запросов):
            exists = await repo.exists_by_field("code", code)
        """
        try:
            if not hasattr(self.model, field_name):
                return False

            field = getattr(self.model, field_name)
            statement = select(exists().where(field == field_value))
            result = await self.session.execute(statement)
            return bool(result.scalar())
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при проверке существования %s по полю %s=%s: %s",
                self.model.__name__,
                field_name,
                field_value,
                e,
            )
            return False

    async def bulk_create(self, models: list[M | dict[str, Any]], refresh: bool = True) -> list[M]:
        """
        Массовое создание записей в базе данных.

        Args:
            models (List[M | Dict[str, Any]]): Список моделей SQLAlchemy или словарей для добавления.
            refresh (bool): Делать refresh созданных моделей (по умолчанию True).

        Returns:
            List[M]: Список добавленных SQLAlchemy моделей.

        Raises:
            SQLAlchemyError: Если произошла ошибка при массовом добавлении.

        Example:
            >>> categories = [
            ...     CategoryModel(name="Инструменты", code="tools"),
            ...     {"name": "Электрика", "code": "electric"},
            ... ]
            >>> created = await repo.bulk_create(categories)
        """
        try:
            instances: list[M] = []
            for item in models:
                if isinstance(item, dict):
                    instances.append(self.model(**item))
                else:
                    instances.append(item)

            self.session.add_all(instances)
            await self.session.commit()

            if refresh:
                for model in instances:
                    await self.session.refresh(model)

            self.logger.info(
                "Создано %s записей %s",
                len(instances),
                self.model.__name__,
                extra={"model": self.model.__name__, "count": len(instances)},
            )
            return instances
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при массовом создании %s: %s", self.model.__name__, e)
            raise

    async def bulk_update(self, models: list[M], refresh: bool = True) -> list[M]:
        """
        Массовое обновление записей в базе данных.

        Args:
            models (List[M]): Список моделей SQLAlchemy для обновления.
            refresh (bool): Делать refresh каждой модели после commit (по умолчанию True).

        Returns:
            List[M]: Список обновленных SQLAlchemy моделей.

        Raises:
            SQLAlchemyError: Если произошла ошибка при массовом обновлении.

        Example:
            >>> categories = await repo.get_items_by_field("is_active", False)
            >>> for cat in categories:
            ...     cat.is_active = True
            >>> updated = await repo.bulk_update(categories)
        """
        try:
            await self.session.commit()

            if refresh:
                for model in models:
                    await self.session.refresh(model)

            self.logger.info(
                "Обновлено %s записей %s",
                len(models),
                self.model.__name__,
                extra={"model": self.model.__name__, "count": len(models)},
            )
            return models
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при массовом обновлении %s: %s", self.model.__name__, e)
            raise

    async def get_or_create(
        self,
        filters: dict[str, Any],
        defaults: dict[str, Any] | None = None,
        refresh: bool = True,
    ) -> tuple[M, bool]:
        """
        Получает запись по фильтрам или создает новую, если не существует.

        Args:
            filters (Dict[str, Any]): Словарь фильтров для поиска записи (поддерживает операторы).
            defaults (Optional[Dict[str, Any]]): Данные по умолчанию для новой записи.

        Returns:
            Tuple[M, bool]: Кортеж (модель, создана), где created=True если запись создана.

        Args:
            refresh (bool): Делать refresh созданной записи (по умолчанию True).

        Raises:
            SQLAlchemyError: Если произошла ошибка при получении или создании.

        Example:
            >>> category, created = await repo.get_or_create(
            ...     {"code": "tools"},
            ...     {"name": "Инструменты", "is_active": True}
            ... )
            >>> if created:
            ...     print("Категория создана")
        """
        try:
            # Строим запрос с использованием централизованной логики фильтрации
            statement = select(self.model)
            conditions = self._build_filter_conditions(**filters)

            if conditions:
                statement = statement.where(and_(*conditions))

            result = await self.session.execute(statement)
            instance = result.scalar()

            if instance:
                return instance, False

            # Создаем новую запись (только простые фильтры без операторов для создания)
            create_data = {}
            for key, value in filters.items():
                # Используем только фильтры без операторов для создания объекта
                if "__" not in key:
                    create_data[key] = value

            create_data.update(defaults or {})
            instance = self.model(**create_data)
            self.session.add(instance)
            await self.session.commit()
            if refresh:
                await self.session.refresh(instance)

            self.logger.info(
                "Создана новая запись %s",
                self.model.__name__,
                extra={"model": self.model.__name__, "filters": filters},
            )
            return instance, True

        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при get_or_create %s: %s", self.model.__name__, e)
            raise

    async def update_or_create(
        self, filters: dict[str, Any], defaults: dict[str, Any], refresh: bool = True
    ) -> tuple[M, bool]:
        """
        Обновляет запись по фильтрам или создает новую, если не существует.

        Args:
            filters (Dict[str, Any]): Словарь фильтров для поиска записи (поддерживает операторы).
            defaults (Dict[str, Any]): Данные для обновления или создания.

        Returns:
            Tuple[M, bool]: Кортеж (модель, создана), где created=True если запись создана.

        Args:
            refresh (bool): Делать refresh изменённой/созданной записи (по умолчанию True).

        Raises:
            SQLAlchemyError: Если произошла ошибка при обновлении или создании.

        Example:
            >>> category, created = await repo.update_or_create(
            ...     {"code": "tools"},
            ...     {"name": "Инструменты обновленные", "is_active": True}
            ... )
        """
        try:
            # Строим запрос с использованием централизованной логики фильтрации
            statement = select(self.model)
            conditions = self._build_filter_conditions(**filters)

            if conditions:
                statement = statement.where(and_(*conditions))

            result = await self.session.execute(statement)
            instance = result.scalar()

            if instance:
                # Обновляем существующую запись
                for key, value in defaults.items():
                    if hasattr(instance, key) and key != "id":
                        setattr(instance, key, value)

                await self.session.commit()
                if refresh:
                    await self.session.refresh(instance)

                self.logger.info(
                    "Обновлена запись %s",
                    self.model.__name__,
                    extra={"model": self.model.__name__, "filters": filters},
                )
                return instance, False

            # Создаем новую запись (только простые фильтры без операторов)
            create_data = {}
            for key, value in filters.items():
                # Используем только фильтры без операторов для создания объекта
                if "__" not in key:
                    create_data[key] = value

            create_data.update(defaults)
            instance = self.model(**create_data)
            self.session.add(instance)
            await self.session.commit()
            if refresh:
                await self.session.refresh(instance)

            self.logger.info(
                "Создана новая запись %s",
                self.model.__name__,
                extra={"model": self.model.__name__, "filters": filters},
            )
            return instance, True

        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при update_or_create %s: %s", self.model.__name__, e)
            raise

    def _apply_filter_condition(self, field, operator: str, value):
        """
        Применяет условие фильтрации к полю.

        Централизованная логика для применения операторов фильтрации.
        Используется во всех методах фильтрации для соблюдения DRY.

        Args:
            field: SQLAlchemy поле модели
            operator: Оператор фильтрации (eq, ne, gt, lt, gte, lte, in, not_in, like, ilike, is_null)
            value: Значение для фильтрации

        Returns:
            SQLAlchemy условие или None если оператор неизвестен
        """
        if operator == "eq":
            return field == value
        elif operator == "ne":
            return field != value
        elif operator == "gt":
            return field > value
        elif operator == "lt":
            return field < value
        elif operator == "gte":
            return field >= value
        elif operator == "lte":
            return field <= value
        elif operator == "in":
            return field.in_(value)
        elif operator == "not_in":
            return ~field.in_(value)
        elif operator == "like":
            return field.like(value)
        elif operator == "ilike":
            return field.ilike(value)
        elif operator == "is_null":
            if value:
                return field.is_(None)
            else:
                return field.isnot(None)
        else:
            self.logger.warning("Неизвестный оператор '%s'", operator)
            return None

    def _build_filter_conditions(self, **kwargs) -> list:
        """
        Строит список условий фильтрации из kwargs.

        Централизованный парсинг фильтров для переиспользования
        во всех методах фильтрации.

        Args:
            **kwargs: Параметры фильтрации в формате field__operator=value

        Returns:
            List: Список SQLAlchemy условий для WHERE
        """
        conditions = []

        for key, value in kwargs.items():
            # Исключаем служебные параметры
            if key in ("limit", "offset"):
                continue

            if "__" in key:
                field_name, operator = key.rsplit("__", 1)
            else:
                field_name, operator = key, "eq"

            if not hasattr(self.model, field_name):
                self.logger.warning(
                    "Поле '%s' не существует в модели %s",
                    field_name,
                    self.model.__name__,
                )
                continue

            field = getattr(self.model, field_name)
            condition = self._apply_filter_condition(field, operator, value)

            if condition is not None:
                conditions.append(condition)

        return conditions

    async def filter_by(self, options: list[Any] | None = None, **kwargs) -> list[M]:
        """
        Фильтрует записи по указанным параметрам с поддержкой операторов.

        Операторы фильтрации:
        | Оператор  | Описание                    | Example                         |
        |-----------|-----------------------------|---------------------------------|
        | eq        | Равно (=)                   | field__eq=value                 |
        | ne        | Не равно (!=)               | field__ne=value                 |
        | gt        | Больше (>)                  | field__gt=value                 |
        | lt        | Меньше (<)                  | field__lt=value                 |
        | gte       | Больше или равно (>=)       | field__gte=value                |
        | lte       | Меньше или равно (<=)       | field__lte=value                |
        | in        | В списке                    | field__in=[value1, value2]      |
        | not_in    | Не в списке                 | field__not_in=[value1, value2]  |
        | like      | LIKE (с учетом регистра)    | field__like="%value%"           |
        | ilike     | ILIKE (без учета регистра)  | field__ilike="%value%"          |
        | is_null   | IS NULL / IS NOT NULL       | field__is_null=True             |

        Args:
            options (Optional[List[Any]]): Список опций для загрузки связей.
            **kwargs: Параметры фильтрации в формате field__operator=value.

        Returns:
            List[M]: Список отфильтрованных SQLAlchemy моделей.

        Example:
            >>> # Простая фильтрация
            >>> active_cats = await repo.filter_by(is_active=True)
            >>>
            >>> # С операторами
            >>> categories = await repo.filter_by(
            ...     name__ilike="%инструмент%",
            ...     sort_order__gte=10,
            ...     parent_id__is_null=True
            ... )
        """
        try:
            statement = select(self.model)
            conditions = self._build_filter_conditions(**kwargs)

            if conditions:
                statement = statement.where(and_(*conditions))

            # Применяем default_options и переданные options
            statement = self._apply_default_options(statement, options)

            # Пагинация
            limit = kwargs.get("limit")
            offset = kwargs.get("offset")
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            if self.enable_tracing:
                return await self._execute_with_hooks(
                    "select",
                    self.execute_and_return_scalars,
                    statement,
                    query_params=kwargs,  # Передаем параметры фильтрации для логирования
                )
            else:
                return await self.execute_and_return_scalars(statement)

        except (SQLAlchemyError, AttributeError) as e:
            self.logger.error("Ошибка при фильтрации %s: %s", self.model.__name__, e)
            return []

    async def filter_by_ordered(
        self,
        order_by: str,
        ascending: bool = True,
        options: list[Any] | None = None,
        **kwargs,
    ) -> list[M]:
        """
        Фильтрует записи с сортировкой.

        Комбинирует возможности filter_by с ORDER BY для случаев,
        когда нужна и фильтрация, и сортировка результатов.

        Args:
            order_by (str): Поле для сортировки.
            ascending (bool): True для ASC, False для DESC. По умолчанию True.
            **kwargs: Параметры фильтрации (те же, что в filter_by).
            options (Optional[List[Any]]): Список опций для загрузки связей.

        Returns:
            List[M]: Отсортированный список отфильтрованных SQLAlchemy моделей.

        Example:
            >>> # Активные категории, отсортированные по sort_order
            >>> categories = await repo.filter_by_ordered(
            ...     "sort_order",
            ...     is_active=True,
            ...     parent_id__is_null=True
            ... )
            >>>
            >>> # Категории с порядком >= 10, отсортированные по имени (DESC)
            >>> categories = await repo.filter_by_ordered(
            ...     "name",
            ...     ascending=False,
            ...     sort_order__gte=10
            ... )
        """
        try:
            statement = select(self.model)
            conditions = self._build_filter_conditions(**kwargs)

            if conditions:
                statement = statement.where(and_(*conditions))

            if options:
                for option in options:
                    statement = statement.options(option)

            # Добавляем сортировку
            if not hasattr(self.model, order_by):
                self.logger.warning(
                    "Поле '%s' для сортировки не существует в модели %s",
                    order_by,
                    self.model.__name__,
                )
            else:
                order_field = getattr(self.model, order_by)
                if ascending:
                    statement = statement.order_by(order_field)
                else:
                    statement = statement.order_by(order_field.desc())

            # Пагинация
            limit = kwargs.get("limit")
            offset = kwargs.get("offset")
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            return await self.execute_and_return_scalars(statement)

        except (SQLAlchemyError, AttributeError) as e:
            self.logger.error("Ошибка при фильтрации с сортировкой %s: %s", self.model.__name__, e)
            return []

    async def execute_statement(self, statement: Executable) -> Any:
        """
        Выполняет произвольный SQL-запрос (SELECT).

        Args:
            statement (Executable): SQLAlchemy запрос для выполнения.

        Returns:
            Any: Результат выполнения запроса.

        Example:
            >>> from sqlalchemy import select
            >>> stmt = select(CategoryModel).where(
            ...     CategoryModel.name.ilike("%инструмент%")
            ... ).order_by(CategoryModel.sort_order)
            >>> result = await repo.execute_statement(stmt)
            >>> categories = list(result.scalars().all())
        """
        try:
            result = await self.session.execute(statement)
            return result
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при выполнении запроса: %s", e)
            raise

    async def delete_by_filters(self, **filters) -> int:
        """
        Удаляет записи по фильтрам.

        Args:
            **filters: Фильтры для удаления (поддерживает операторы как в filter_by).

        Returns:
            int: Количество удаленных записей.

        Raises:
            SQLAlchemyError: Если произошла ошибка при удалении.

        Example:
            >>> # Удалить неактивные категории
            >>> deleted_count = await repo.delete_by_filters(is_active=False)
            >>>
            >>> # С операторами
            >>> deleted_count = await repo.delete_by_filters(sort_order__lt=10)
        """
        try:
            statement = delete(self.model)

            # Используем централизованную логику фильтрации
            conditions = self._build_filter_conditions(**filters)
            if conditions:
                # delete() требует where() с условиями через and_
                for condition in conditions:
                    statement = statement.where(condition)

            result: CursorResult[Any] = await self.session.execute(statement)
            await self.session.commit()

            deleted_count = result.rowcount
            self.logger.info(
                "Удалено %s записей %s",
                deleted_count,
                self.model.__name__,
                extra={"model": self.model.__name__, "filters": filters},
            )
            return deleted_count

        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при удалении %s по фильтрам: %s", self.model.__name__, e)
            raise

    async def execute_and_return_scalars(self, statement: Executable) -> list[M]:
        """
        Выполняет statement и возвращает список моделей.

        Базовый метод для выполнения SELECT запросов с автоматическим
        логированием и обработкой ошибок.

        Args:
            statement: SQLAlchemy statement для выполнения

        Returns:
            List[M]: Список моделей

        Raises:
            SQLAlchemyError: При ошибке выполнения запроса
        """
        try:
            result = await self.session.execute(statement)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при выполнении запроса %s: %s", self.model.__name__, e)
            raise

    async def execute_and_return_scalar(self, statement: Executable) -> M | None:
        """
        Выполняет statement и возвращает одну модель.

        Базовый метод для выполнения SELECT запросов, возвращающих одну запись.

        Args:
            statement: SQLAlchemy statement для выполнения

        Returns:
            Optional[M]: Модель или None

        Raises:
            SQLAlchemyError: При ошибке выполнения запроса
        """
        try:
            result = await self.session.execute(statement)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при выполнении запроса %s: %s", self.model.__name__, e)
            raise

    async def get_items_with_relations(self, relation_options: list, **filters) -> list[M]:
        """
        Получает записи с загрузкой связанных объектов.

        Базовый метод для запросов с selectinload/joinedload.

        Args:
            relation_options: Список options для загрузки связей (selectinload, joinedload)
            **filters: Фильтры как в filter_by

        Returns:
            List[M]: Список моделей с загруженными связями

        Example:
            >>> options = [selectinload(ProductModel.categories)]
            >>> products = await repo.get_items_with_relations(options, is_active=True)
        """
        try:
            stmt = select(self.model)

            # Добавляем relation options
            for option in relation_options:
                stmt = stmt.options(option)

            # Применяем фильтры используя централизованную логику
            conditions = self._build_filter_conditions(**filters)
            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Пагинация
            limit = filters.get("limit")
            offset = filters.get("offset")
            if offset is not None:
                stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)

            return await self.execute_and_return_scalars(stmt)

        except (SQLAlchemyError, AttributeError) as e:
            self.logger.error("Ошибка при получении %s с связями: %s", self.model.__name__, e)
            return []

    async def get_paginated_items(
        self,
        pagination: "PaginationParamsSchema",
        statement: Any | None = None,
        options: list[Any] | None = None,
    ) -> tuple[list[M], int]:
        """
        Получает список записей с пагинацией и сортировкой.

        Args:
            pagination (PaginationParamsSchema): Параметры пагинации и сортировки.
            statement (Optional[Select]): Базовый SQL-запрос. Если None, выбирает все записи.

        Returns:
            Tuple[List[M], int]: Список записей и общее количество.

        Example:
            >>> from app.schemas.v1.pagination import PaginationParamsSchema
            >>> pagination = PaginationParamsSchema(page=1, page_size=20, sort_by="created_at", sort_desc=True)
            >>> items, total = await repo.get_paginated_items(pagination)
        """
        try:
            from sqlalchemy import asc, desc

            if statement is None:
                statement = select(self.model)

            # Применяем default_options и переданные options
            statement = self._apply_default_options(statement, options)

            # 1. Считаем общее количество (до пагинации)
            # Используем count() от подзапроса для корректного подсчета с join/group by
            count_stmt = select(func.count()).select_from(statement.subquery())
            total_result = await self.session.execute(count_stmt)
            total = total_result.scalar() or 0

            # 2. Применяем сортировку
            if hasattr(self.model, pagination.sort_by):
                sort_column = getattr(self.model, pagination.sort_by)
                statement = statement.order_by(desc(sort_column) if pagination.sort_desc else asc(sort_column))
            else:
                self.logger.warning(
                    "Поле сортировки '%s' не найдено в модели %s. Используется сортировка по умолчанию.",
                    pagination.sort_by,
                    self.model.__name__,
                )
                # Fallback to default sort (e.g. created_at desc) if available
                if hasattr(self.model, "created_at"):
                    statement = statement.order_by(desc(self.model.created_at))

            # 3. Применяем пагинацию
            offset = (pagination.page - 1) * pagination.page_size
            statement = statement.offset(offset).limit(pagination.page_size)

            # 4. Выполняем запрос
            result = await self.session.execute(statement)
            items = list(result.scalars().all())

            return items, total

        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при получении пагинированного списка %s: %s",
                self.model.__name__,
                e,
            )
            return [], 0

    # ============================================================================
    # UTILITY METHODS (hooks, caching, default options)
    # ============================================================================

    def add_hook(self, hook) -> None:
        """
        Добавить хук для трассировки запросов.

        Args:
            hook (QueryHook): Хук для добавления.

        Example:
            >>> from app.repository.monitoring import DetailedLoggingHook
            >>> repo.add_hook(DetailedLoggingHook())
        """
        self.hooks.add(hook)

    def remove_hook(self, hook) -> bool:
        """
        Удалить хук трассировки.

        Args:
            hook (QueryHook): Хук для удаления.

        Returns:
            bool: True если хук был удален.
        """
        return self.hooks.remove(hook)

    def _apply_default_options(self, stmt, options: list[Any] | None = None, override_defaults: bool = False):
        """
        Применить default options и переданные options к statement.

        Args:
            stmt: SQLAlchemy statement.
            options (Optional[List[Any]]): Дополнительные опции.
            override_defaults (bool): Игнорировать default_options если True.

        Returns:
            Statement с примененными options.

        Example:
            >>> stmt = select(self.model)
            >>> stmt = self._apply_default_options(stmt, [joinedload(Model.relation)])
        """
        if not override_defaults and self.default_options:
            for option in self.default_options:
                stmt = stmt.options(option)

        if options:
            for option in options:
                stmt = stmt.options(option)

        return stmt

    async def _execute_with_hooks(
        self,
        query_type: str,
        exec_func: Callable[..., Awaitable[T]],
        *args,
        query_params: dict[str, Any] | None = None,
        **kwargs,
    ) -> T:
        """
        Выполнить функцию с трассировкой через hooks.

        Args:
            query_type (str): Тип запроса (select, insert, update, delete).
            func: Асинхронная функция для выполнения.
            *args: Позиционные аргументы для функции.
            query_params (Optional[Dict]): Параметры запроса для логирования (не передаются в функцию).
            **kwargs: Именованные аргументы для функции.

        Returns:
            Результат выполнения функции.
        """
        start_time = time.time()
        error = None
        result = None
        rows_affected = 0

        # Если query_params не переданы, используем kwargs как параметры (если это имеет смысл)
        params_to_log = query_params if query_params is not None else kwargs

        try:
            # Before hook
            await self.hooks.before_execute(query_type, self.model.__name__, params_to_log)

            # Выполнение
            result = await exec_func(*args, **kwargs)

            # Подсчёт затронутых строк
            if hasattr(result, "__len__"):
                rows_affected = len(result)
            elif hasattr(result, "rowcount"):
                rows_affected = result.rowcount
            else:
                rows_affected = 1 if result else 0

            return result

        except Exception as e:
            error = str(e)
            raise
        finally:
            # After hook
            execution_time_ms = (time.time() - start_time) * 1000
            metrics = QueryMetrics(
                query_type=query_type,
                model_name=self.model.__name__,
                execution_time_ms=execution_time_ms,
                rows_affected=rows_affected,
                query_params=params_to_log,
                cache_hit=False,  # TODO: Передавать информацию о кеше
                error=error,
            )
            await self.hooks.after_execute(metrics)

        return result

    # ============================================================================
    # SELECT FOR UPDATE (Pessimistic Locking)
    # ============================================================================

    async def get_item_by_id_for_update(
        self,
        item_id: UUID,
        nowait: bool = False,
        skip_locked: bool = False,
        options: list[Any] | None = None,
    ) -> M | None:
        """
        Получить запись по ID с блокировкой FOR UPDATE.

        Используется для конкурентных операций, когда нужно гарантировать,
        что запись не будет изменена другой транзакцией.

        Note:
            Метод автоматически отключает eager loading (lazy="joined")
            для корректной работы FOR UPDATE с nullable relationships.

        Args:
            item_id (UUID): ID записи.
            nowait (bool): Не ждать, если запись заблокирована (вызвать ошибку).
            skip_locked (bool): Пропустить заблокированные записи.
            options (Optional[List[Any]]): Опции для загрузки связей.

        Returns:
            Optional[M]: SQLAlchemy модель или None.

        Raises:
            SQLAlchemyError: Если запись заблокирована и nowait=True.

        Example:
            >>> # Получить продукт с блокировкой
            >>> product = await repo.get_item_by_id_for_update(product_id)
            >>> product.quantity -= 1
            >>> await session.commit()  # Блокировка снимается автоматически
        """
        try:
            statement = select(self.model).where(self.model.id == item_id)

            # Для FOR UPDATE отключаем eager loading (lazy="joined"),
            # так как PostgreSQL не поддерживает FOR UPDATE с LEFT OUTER JOIN
            statement = statement.options(lazyload("*"))

            # Применяем пользовательские options (если переданы)
            if options:
                for option in options:
                    statement = statement.options(option)

            # Добавляем FOR UPDATE
            statement = statement.with_for_update(nowait=nowait, skip_locked=skip_locked)

            if self.enable_tracing:
                result = await self._execute_with_hooks("select_for_update", self.execute_and_return_scalar, statement)
            else:
                result = await self.execute_and_return_scalar(statement)

            return result

        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при получении %s по ID %s с блокировкой: %s",
                self.model.__name__,
                item_id,
                e,
            )
            raise

    async def filter_by_for_update(
        self,
        nowait: bool = False,
        skip_locked: bool = False,
        options: list[Any] | None = None,
        **kwargs,
    ) -> list[M]:
        """
        Фильтр записей с блокировкой FOR UPDATE.

        Note:
            Метод автоматически отключает eager loading (lazy="joined")
            для корректной работы FOR UPDATE с nullable relationships.

        Args:
            nowait (bool): Не ждать, если записи заблокированы.
            skip_locked (bool): Пропустить заблокированные записи.
            options (Optional[List[Any]]): Опции для загрузки связей.
            **kwargs: Фильтры (те же что в filter_by).

        Returns:
            List[M]: Список заблокированных записей.

        Example:
            >>> # Заблокировать все активные продукты
            >>> products = await repo.filter_by_for_update(
            ...     is_active=True,
            ...     skip_locked=True
            ... )
        """
        try:
            statement = select(self.model)
            conditions = self._build_filter_conditions(**kwargs)

            if conditions:
                statement = statement.where(and_(*conditions))

            # Для FOR UPDATE отключаем eager loading (lazy="joined"),
            # так как PostgreSQL не поддерживает FOR UPDATE с LEFT OUTER JOIN
            statement = statement.options(lazyload("*"))

            # Применяем пользовательские options (если переданы)
            if options:
                for option in options:
                    statement = statement.options(option)

            # Добавляем FOR UPDATE
            statement = statement.with_for_update(nowait=nowait, skip_locked=skip_locked)

            # Пагинация
            limit = kwargs.get("limit")
            offset = kwargs.get("offset")
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            if self.enable_tracing:
                return await self._execute_with_hooks("filter_for_update", self.execute_and_return_scalars, statement)
            else:
                return await self.execute_and_return_scalars(statement)

        except SQLAlchemyError as e:
            self.logger.error("Ошибка при фильтрации %s с блокировкой: %s", self.model.__name__, e)
            return []

    # ============================================================================
    # PROJECTIONS (Частичная загрузка полей)
    # ============================================================================

    async def project_fields(self, fields: list[str], **filters) -> list[dict[str, Any]]:
        """
        Получить только указанные поля без загрузки полной модели.

        Возвращает список словарей вместо моделей SQLAlchemy.
        Значительно экономит память и время при работе с большими выборками.

        Args:
            fields (List[str]): Список полей для выборки.
            **filters: Фильтры (те же что в filter_by).

        Returns:
            List[Dict[str, Any]]: Список словарей с указанными полями.

        Example:
            >>> # Получить только name и code
            >>> categories = await repo.project_fields(['name', 'code'], is_active=True)
            >>> # [{"name": "Инструменты", "code": "tools"}, ...]
        """
        try:
            # Проверяем существование полей
            columns = []
            for field_name in fields:
                if not hasattr(self.model, field_name):
                    raise ValueError(f"Поле '{field_name}' не существует в модели {self.model.__name__}")
                columns.append(getattr(self.model, field_name))

            # Строим запрос с выбором конкретных полей
            statement = select(*columns)

            # Фильтры
            conditions = self._build_filter_conditions(**filters)
            if conditions:
                statement = statement.where(and_(*conditions))

            # Пагинация
            limit = filters.get("limit")
            offset = filters.get("offset")
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            result = await self.session.execute(statement)
            rows = result.all()

            # Преобразуем в словари
            return [dict(zip(fields, row, strict=False)) for row in rows]

        except (SQLAlchemyError, ValueError) as e:
            self.logger.error("Ошибка при проекции полей %s: %s", self.model.__name__, e)
            return []

    async def project_field(self, field_name: str, **filters) -> list[Any]:
        """
        Получить список значений одного поля.

        Args:
            field_name (str): Название поля.
            **filters: Фильтры (те же что в filter_by).

        Returns:
            List[Any]: Список значений поля.

        Example:
            >>> # Получить только IDs
            >>> ids = await repo.project_field('id', parent_id__is_null=True)
            >>> # [UUID('...'), UUID('...'), ...]
        """
        try:
            if not hasattr(self.model, field_name):
                raise ValueError(f"Поле '{field_name}' не существует в модели {self.model.__name__}")

            field = getattr(self.model, field_name)
            statement = select(field)

            # Фильтры
            conditions = self._build_filter_conditions(**filters)
            if conditions:
                statement = statement.where(and_(*conditions))

            # Пагинация
            limit = filters.get("limit")
            offset = filters.get("offset")
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            result = await self.session.execute(statement)
            return list(result.scalars().all())

        except (SQLAlchemyError, ValueError) as e:
            self.logger.error(
                "Ошибка при получении поля %s.%s: %s",
                self.model.__name__,
                field_name,
                e,
            )
            return []

    async def project_one(self, fields: list[str], **filters) -> dict[str, Any] | None:
        """
        Получить одну запись с проекцией полей.

        Args:
            fields (List[str]): Список полей для выборки.
            **filters: Фильтры (те же что в filter_by).

        Returns:
            Optional[Dict[str, Any]]: Словарь с полями или None.

        Example:
            >>> category = await repo.project_one(['name', 'code'], code="tools")
            >>> # {"name": "Инструменты", "code": "tools"}
        """
        results = await self.project_fields(fields, limit=1, **filters)
        return results[0] if results else None

    # ============================================================================
    # CACHING
    # ============================================================================

    async def get_item_by_id_cached(
        self,
        item_id: UUID,
        use_cache: bool = True,
        cache_ttl: int = 300,
        options: list[Any] | None = None,
    ) -> M | None:
        """
        Получить запись по ID с кешированием.

        Args:
            item_id (UUID): ID записи.
            use_cache (bool): Использовать кеш (по умолчанию True).
            cache_ttl (int): TTL кеша в секундах (по умолчанию 300 = 5 минут).
            options (Optional[List[Any]]): Опции для загрузки связей.

        Returns:
            Optional[M]: SQLAlchemy модель или None.
        """
        cache_key = self.cache.build_key(self.model.__name__, "get_by_id", item_id)

        # Попытка получить из кеша
        if use_cache:
            cached_value = await self.cache.get(cache_key)
            if cached_value is not None:
                self.logger.debug("Cache HIT for %s", cache_key)
                return cached_value

        # Запрос в БД
        item = await self.get_item_by_id(item_id, options)

        # Сохранить в кеш
        if use_cache and item is not None:
            await self.cache.set(cache_key, item, cache_ttl)

        return item

    async def get_item_by_field_cached(
        self,
        field_name: str,
        field_value: Any,
        use_cache: bool = True,
        cache_ttl: int = 300,
        options: list[Any] | None = None,
    ) -> M | None:
        """
        Получить запись по полю с кешированием.

        Args:
            field_name (str): Название поля.
            field_value (Any): Значение поля.
            use_cache (bool): Использовать кеш (по умолчанию True).
            cache_ttl (int): TTL кеша в секундах (по умолчанию 300 = 5 минут).
            options (Optional[List[Any]]): Опции для загрузки связей.

        Returns:
            Optional[M]: SQLAlchemy модель или None.

        Example:
            >>> setting = await repo.get_item_by_field_cached(
            ...     "key", "site_name", cache_ttl=3600
            ... )
        """
        cache_key = self.cache.build_key(self.model.__name__, f"get_by_{field_name}", str(field_value))

        # Попытка получить из кеша
        if use_cache:
            cached_value = await self.cache.get(cache_key)
            if cached_value is not None:
                self.logger.debug("Cache HIT for %s", cache_key)
                return cached_value

        # Запрос в БД
        item = await self.get_item_by_field(field_name, field_value, options)

        # Сохранить в кеш
        if use_cache and item is not None:
            await self.cache.set(cache_key, item, cache_ttl)

        return item

    async def _invalidate_cache(self, pattern_suffix: str = "*") -> int:
        """
        Инвалидировать кеш для модели.

        Args:
            pattern_suffix (str): Суффикс паттерна (по умолчанию "*" - все ключи).

        Returns:
            int: Количество удаленных ключей.
        """
        pattern = f"{self.model.__name__}:{pattern_suffix}"
        return await self.cache.invalidate_pattern(pattern)

    # ============================================================================
    # BATCH UPSERT (ON CONFLICT DO UPDATE)
    # ============================================================================

    async def bulk_upsert(
        self,
        items: list[dict[str, Any]],
        conflict_columns: list[str],
        update_columns: list[str] | None = None,
    ) -> int:
        """
        Массовый upsert (insert-or-update) записей.

        Использует PostgreSQL ON CONFLICT DO UPDATE.
        Если запись с conflict_columns существует - обновляет, иначе создаёт.

        Args:
            items (List[Dict]): Список словарей с данными.
            conflict_columns (List[str]): Поля для определения конфликта (unique keys).
            update_columns (Optional[List[str]]): Поля для обновления.
                Если None, обновляются все поля кроме conflict_columns.

        Returns:
            int: Количество затронутых строк.

        Raises:
            SQLAlchemyError: При ошибке выполнения.

        Example:
            >>> categories = [
            ...     {"code": "tools", "name": "Инструменты", "sort_order": 1},
            ...     {"code": "electric", "name": "Электрика", "sort_order": 2},
            ... ]
            >>> count = await repo.bulk_upsert(
            ...     categories,
            ...     conflict_columns=['code'],
            ...     update_columns=['name', 'sort_order']
            ... )
        """
        if not items:
            return 0

        try:
            # Определяем поля для обновления
            if update_columns is None:
                # Все поля кроме conflict_columns
                sample = items[0]
                update_columns = [k for k in sample.keys() if k not in conflict_columns]

            # PostgreSQL INSERT ... ON CONFLICT
            stmt = pg_insert(self.model).values(items)

            # ON CONFLICT DO UPDATE
            update_dict = {col: stmt.excluded[col] for col in update_columns}

            stmt = stmt.on_conflict_do_update(index_elements=conflict_columns, set_=update_dict)

            await self.session.execute(stmt)
            await self.session.commit()

            # Принудительно инвалидируем объекты в сессии, так как expire_on_commit=False
            # Это гарантирует, что последующие запросы получат свежие данные
            self.session.expire_all()

            # Используем len(items) вместо rowcount для точности
            count = len(items)
            self.logger.info("Bulk upsert: %d строк для %s", count, self.model.__name__)

            # Инвалидация кеша
            await self._invalidate_cache()

            return count

        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при bulk_upsert %s: %s", self.model.__name__, e)
            raise
