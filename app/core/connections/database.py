"""
Модуль для работы с базой данных.

Предоставляет классы для управления подключением к PostgreSQL через SQLAlchemy:
- DatabaseClient: Singleton клиент для управления глобальным подключением к базе данных
- DatabaseContextManager: Контекстный менеджер для автоматического управления сессиями БД
- AsyncSessionFactory: Фабрика для создания асинхронных сессий

Модуль использует настройки подключения из конфигурации приложения и реализует
базовые интерфейсы из модуля base.py.
"""

import asyncio
import weakref
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.connections.base import BaseClient, BaseContextManager
from app.core.settings import Settings, settings


class DatabaseClient(BaseClient):
    """
    Singleton клиент для работы с базой данных.

    Реализует паттерн Singleton для обеспечения единого глобального подключения
    к PostgreSQL через SQLAlchemy. Управляет жизненным циклом engine и session factory.

    Attributes:
        _instance (Optional[DatabaseClient]): Единственный экземпляр класса
        _initialized (bool): Флаг инициализации
        _settings (Settings): Конфигурация с параметрами подключения к БД
        _engine (Optional[AsyncEngine]): Глобальный асинхронный движок SQLAlchemy
        _session_factory (Optional[async_sessionmaker]): Глобальная фабрика сессий
        _lock (asyncio.Lock): Блокировка для thread-safe инициализации
        logger (logging.Logger): Логгер для записи событий
    """

    _instance: Optional["DatabaseClient"] = None
    _initialized: bool = False
    _lock = asyncio.Lock()
    _instance_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, *args, **kwargs) -> "DatabaseClient":
        """
        Реализация паттерна Singleton.

        Args:
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы

        Returns:
            DatabaseClient: Единственный экземпляр класса
        """
        if cls._instance is None:
            async with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(*args, **kwargs)
        return cls._instance

    def __init__(self, _settings: Settings = settings) -> None:
        """
        Инициализирует клиент базы данных (только один раз).

        Args:
            _settings (Settings, optional): Конфигурация приложения.
                По умолчанию используется глобальная конфигурация.
        """
        if self._initialized:
            return

        super().__init__()
        self._settings = _settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker | None = None
        self._initialized = True

    async def connect(self) -> async_sessionmaker:
        """
        Создает глобальное подключение к базе данных (если еще не создано).

        Устанавливает соединение с PostgreSQL и создает движок SQLAlchemy
        с фабрикой сессий. Использует блокировку для thread-safe инициализации.

        Returns:
            async_sessionmaker: Фабрика для создания асинхронных сессий

        Raises:
            SQLAlchemyError: При ошибке подключения к базе данных

        Usage:
            ```python
            db_client = await DatabaseClient.get_instance()
            session_factory = await db_client.connect()
            async with session_factory() as session:
                # Работа с сессией
                result = await session.execute(query)
            ```
        """
        if self._session_factory is not None:
            return self._session_factory

        async with self._lock:
            # Double-check locking pattern
            if self._session_factory is not None:
                return self._session_factory

            self.logger.debug("Инициализация глобального подключения к базе данных...")

            self._engine = create_async_engine(
                url=self._settings.database_url,
                **self._settings.engine_params,
            )

            self._session_factory = async_sessionmaker(bind=self._engine, **self._settings.session_params)

            # Создаём расширение pgvector (если ещё не создано)
            await self._ensure_pgvector_extension()

            self.logger.info("Глобальное подключение к базе данных установлено")

        return self._session_factory

    async def close(self) -> None:
        """
        Закрывает глобальное подключение к базе данных.

        Безопасно закрывает все соединения в пуле и освобождает ресурсы движка.
        Сбрасывает singleton для возможности повторной инициализации.

        Usage:
            ```python
            db_client = await DatabaseClient.get_instance()
            try:
                session_factory = await db_client.connect()
                # Работа с базой данных
            finally:
                await db_client.close()
            ```
        """
        async with self._lock:
            if self._engine:
                self.logger.debug("Закрытие глобального подключения к базе данных...")
                await self._engine.dispose()
                self._engine = None
                self._session_factory = None
                self.logger.info("Глобальное подключение к базе данных закрыто")

                # Сброс singleton для возможности повторной инициализации
                DatabaseClient._instance = None
                DatabaseClient._initialized = False

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """
        Получение фабрики сессий.

        Returns:
            async_sessionmaker: Фабрика для создания сессий

        Raises:
            RuntimeError: Если база данных не была инициализирована
        """
        if self._session_factory is None:
            raise RuntimeError("База данных не инициализирована. Вызовите connect() перед использованием.")
        return self._session_factory

    def get_engine(self) -> AsyncEngine:
        """
        Получение текущего движка базы данных.

        Returns:
            AsyncEngine: асинхронный движок SQLAlchemy

        Raises:
            RuntimeError: если движок еще не инициализирован (connect не вызывался)
        """
        if self._engine is None:
            raise RuntimeError("База данных не инициализирована. Вызовите connect() перед использованием.")
        return self._engine

    @property
    def is_connected(self) -> bool:
        """Проверяет, установлено ли подключение к базе данных."""
        return self._engine is not None

    async def _health_check_probe(self) -> None:
        session_factory = self.get_session_factory()
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))

    async def _ensure_pgvector_extension(self) -> None:
        """Создаёт расширение pgvector если оно ещё не установлено."""
        if self._engine is None:
            return

        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            self.logger.info("Расширение pgvector готово")
        except Exception as e:
            self.logger.warning("Не удалось создать расширение pgvector: %s", e)


class DatabaseContextManager(BaseContextManager[AsyncSession]):
    """
    Контекстный менеджер для сессий базы данных.

    Упрощает работу с сессиями SQLAlchemy, автоматически управляя
    жизненным циклом сессии. Использует глобальный DatabaseClient
    для получения фабрики сессий.

    Attributes:
        session (AsyncSession | None): Текущая активная сессия SQLAlchemy
        _session_weakref (weakref.ref | None): Слабая ссылка на сессию для отслеживания
        logger (logging.Logger): Логгер для записи событий
    """

    def __init__(self) -> None:
        """Инициализирует контекстный менеджер базы данных."""
        super().__init__()
        self.session: AsyncSession | None = None
        self._session_weakref: weakref.ref | None = None

    async def connect(self) -> AsyncSession:
        """
        Создает новую сессию базы данных из глобальной фабрики.

        Returns:
            AsyncSession: Асинхронная сессия SQLAlchemy для работы с базой данных

        Raises:
            RuntimeError: Если глобальное подключение не инициализировано

        Usage:
            ```python
            db_manager = DatabaseContextManager()
            session = await db_manager.connect()
            # Работа с сессией
            result = await session.execute(query)
            # Фиксация изменений
            await db_manager.commit()
            # Закрытие сессии
            await db_manager.close()
            ```
        """
        # Получаем глобальную фабрику сессий через singleton
        db_client = await DatabaseClient.get_instance()
        session_factory = await db_client.connect()

        self.session = session_factory()
        # Создаём слабую ссылку для отслеживания удаления объекта
        self._session_weakref = weakref.ref(self.session)
        self.logger.debug("Создана новая сессия базы данных")

        return self.session

    async def close(self, do_rollback: bool = False) -> None:
        """
        Закрывает текущую сессию базы данных и принудительно освобождает память.

        Args:
            do_rollback (bool, optional): Флаг, указывающий, нужно ли выполнить
                откат транзакции перед закрытием сессии. По умолчанию False.

        Note:
            Если do_rollback=True, все незафиксированные изменения будут отменены.
            Если do_rollback=False, незафиксированные изменения останутся в сессии,
            но не будут применены к базе данных.

            После закрытия вызывается сборщик мусора для немедленного освобождения памяти.

        Usage:
            ```python
            # Закрытие сессии без отката транзакции
            await db_manager.close()

            # Закрытие сессии с откатом транзакции
            await db_manager.close(do_rollback=True)
            ```
        """
        if self.session:
            session_id = id(self.session)
            try:
                if do_rollback:
                    await self.session.rollback()
                    self.logger.debug("Выполнен откат транзакции")
            finally:
                # Закрываем сессию SQLAlchemy
                await self.session.close()

                # Явно удаляем все ссылки на объект сессии
                self.session = None
                self._session_weakref = None

                # НЕ вызываем gc.collect() на каждый запрос - это замедляет работу!
                # GC запускается автоматически когда нужно

                self.logger.debug("Сессия базы данных закрыта (id=%s)", session_id)

    async def commit(self) -> None:
        """
        Фиксирует изменения в базе данных.

        Применяет все изменения, сделанные в текущей транзакции.

        Raises:
            RuntimeError: Если сессия не была инициализирована

        Usage:
            ```python
            # Создание новой записи
            new_user = User(username="john_doe")
            session.add(new_user)

            # Фиксация изменений
            await db_manager.commit()
            ```
        """
        if not self.session:
            raise RuntimeError("Сессия не инициализирована. Вызовите connect() сначала.")

        await self.session.commit()
        self.logger.debug("Изменения зафиксированы в базе данных")

    async def rollback(self) -> None:
        """
        Откатывает текущую транзакцию.

        Raises:
            RuntimeError: Если сессия не была инициализирована

        Usage:
            ```python
            try:
                # Операции с базой данных
                session.add(new_record)
                await db_manager.commit()
            except Exception:
                await db_manager.rollback()
                raise
            ```
        """
        if not self.session:
            raise RuntimeError("Сессия не инициализирована. Вызовите connect() сначала.")

        await self.session.rollback()
        self.logger.debug("Транзакция откачена")

    def is_session_alive(self) -> bool:
        """
        Проверяет, жива ли сессия (существует ли объект в памяти).

        Returns:
            bool: True если сессия активна, False если удалена

        Usage:
            ```python
            if db_manager.is_session_alive():
                print("Сессия активна")
            else:
                print("Сессия удалена из памяти")
            ```
        """
        if self._session_weakref is None:
            return False
        # Слабая ссылка вернёт None если объект был удалён сборщиком мусора
        return self._session_weakref() is not None


async def get_session_factory(_settings: Settings = settings) -> async_sessionmaker:
    """
    Утилитарная функция для получения глобальной фабрики сессий.

    Returns:
        async_sessionmaker: Глобальная фабрика сессий

    Usage:
        ```python
        session_factory = await get_session_factory()
        async with session_factory() as session:
            # Работа с сессией
            pass
        ```
    """
    client = await DatabaseClient.get_instance()
    return await client.connect()


async def close_database_connection(_settings: Settings = settings) -> None:
    """
    Утилитарная функция для закрытия глобального подключения к базе данных.

    Используется при завершении работы приложения.

    Usage:
        ```python
        # При завершении работы приложения
        await close_database_connection()
        ```
    """
    client = await DatabaseClient.get_instance()
    await client.close()


async def get_db_session(
    _settings: Settings = settings,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Утилитарная функция для получения асинхронной сессии базы данных.

    Returns:
        AsyncGenerator[AsyncSession, None]: Асинхронный генератор сессий

    Usage:
        ```python
        async for session in get_db_session():
            # Работа с сессией
            pass
        ```
    """
    manager = DatabaseContextManager()
    try:
        session = await manager.connect()
        yield session
    except Exception:
        await manager.rollback()
        raise
    finally:
        await manager.close()
