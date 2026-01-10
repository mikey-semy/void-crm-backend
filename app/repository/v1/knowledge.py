"""Репозиторий для работы с базой знаний.

Этот модуль предоставляет операции с базой данных для управления
статьями, категориями и тегами базы знаний.

Наследуется от BaseRepository и реализует специфичные методы,
включая полнотекстовый поиск через PostgreSQL tsvector.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.v1 import (
    KnowledgeArticleChunkModel,
    KnowledgeArticleModel,
    KnowledgeArticleTagModel,
    KnowledgeCategoryModel,
    KnowledgeChatMessageModel,
    KnowledgeChatSessionModel,
    KnowledgeTagModel,
)
from app.repository.base import BaseRepository
from app.repository.cache import CacheBackend

if TYPE_CHECKING:
    from app.schemas.pagination import PaginationParamsSchema


class KnowledgeCategoryRepository(BaseRepository[KnowledgeCategoryModel]):
    """Репозиторий для операций с категориями базы знаний.

    Предоставляет методы для работы с категориями статей.
    Стандартные CRUD операции наследуются от BaseRepository.

    Специфичные методы:
    - get_all_ordered() - получение всех категорий отсортированных по order
    - get_by_slug() - получение категории по slug
    - get_with_articles_count() - получение категорий с подсчётом статей
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        """Инициализация репозитория категорий.

        Args:
            session: Асинхронная SQLAlchemy сессия для операций с БД.
            cache_backend: Бэкенд для кеширования.
            enable_tracing: Включить трассировку запросов.
        """
        super().__init__(session, KnowledgeCategoryModel, cache_backend, enable_tracing)

    async def get_all_ordered(self) -> list[KnowledgeCategoryModel]:
        """Получить все категории, отсортированные по order.

        Returns:
            Список категорий.
        """
        return await self.filter_by_ordered("order", ascending=True)

    async def get_by_slug(self, slug: str) -> KnowledgeCategoryModel | None:
        """Получить категорию по slug.

        Args:
            slug: URL-friendly идентификатор.

        Returns:
            KnowledgeCategoryModel или None.
        """
        return await self.get_item_by_field("slug", slug)

    async def get_with_articles_count(self) -> list[dict[str, Any]]:
        """Получить категории с количеством опубликованных статей.

        Returns:
            Список словарей с данными категорий и articles_count.
        """
        stmt = (
            select(
                KnowledgeCategoryModel,
                func.count(KnowledgeArticleModel.id).filter(
                    KnowledgeArticleModel.is_published == True  # noqa: E712
                ).label("articles_count"),
            )
            .outerjoin(KnowledgeArticleModel)
            .group_by(KnowledgeCategoryModel.id)
            .order_by(KnowledgeCategoryModel.order)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "category": row[0],
                "articles_count": row[1] or 0,
            }
            for row in rows
        ]


class KnowledgeTagRepository(BaseRepository[KnowledgeTagModel]):
    """Репозиторий для операций с тегами базы знаний.

    Предоставляет методы для работы с тегами статей.
    Стандартные CRUD операции наследуются от BaseRepository.

    Специфичные методы:
    - get_by_slug() - получение тега по slug
    - get_popular() - получение популярных тегов
    - get_by_slugs() - получение тегов по списку slugs
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        """Инициализация репозитория тегов.

        Args:
            session: Асинхронная SQLAlchemy сессия для операций с БД.
            cache_backend: Бэкенд для кеширования.
            enable_tracing: Включить трассировку запросов.
        """
        super().__init__(session, KnowledgeTagModel, cache_backend, enable_tracing)

    async def get_by_slug(self, slug: str) -> KnowledgeTagModel | None:
        """Получить тег по slug.

        Args:
            slug: URL-friendly идентификатор.

        Returns:
            KnowledgeTagModel или None.
        """
        return await self.get_item_by_field("slug", slug)

    async def get_by_slugs(self, slugs: list[str]) -> list[KnowledgeTagModel]:
        """Получить теги по списку slugs.

        Args:
            slugs: Список URL-friendly идентификаторов.

        Returns:
            Список тегов.
        """
        if not slugs:
            return []

        return await self.filter_by(slug__in=slugs)

    async def get_all_with_counts(self) -> list[dict[str, Any]]:
        """Получить все теги с количеством статей.

        Returns:
            Список словарей с тегами и их articles_count.
        """
        stmt = (
            select(
                KnowledgeTagModel,
                func.count(KnowledgeArticleTagModel.article_id).label("articles_count"),
            )
            .outerjoin(KnowledgeArticleTagModel)
            .group_by(KnowledgeTagModel.id)
            .order_by(KnowledgeTagModel.name)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "tag": row[0],
                "articles_count": row[1] or 0,
            }
            for row in rows
        ]

    async def get_popular(self, limit: int = 20) -> list[dict[str, Any]]:
        """Получить популярные теги по количеству статей.

        Args:
            limit: Максимальное количество тегов.

        Returns:
            Список словарей с тегами и их articles_count.
        """
        stmt = (
            select(
                KnowledgeTagModel,
                func.count(KnowledgeArticleTagModel.article_id).label("articles_count"),
            )
            .outerjoin(KnowledgeArticleTagModel)
            .group_by(KnowledgeTagModel.id)
            .order_by(text("articles_count DESC"))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "tag": row[0],
                "articles_count": row[1] or 0,
            }
            for row in rows
        ]


class KnowledgeArticleRepository(BaseRepository[KnowledgeArticleModel]):
    """Репозиторий для операций со статьями базы знаний.

    Предоставляет методы для работы со статьями, включая полнотекстовый поиск.
    Стандартные CRUD операции наследуются от BaseRepository.

    Специфичные методы:
    - get_by_slug() - получение статьи по slug с связями
    - get_published() - получение опубликованных статей с пагинацией
    - full_text_search() - полнотекстовый поиск по статьям
    - increment_view_count() - увеличение счётчика просмотров
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        """Инициализация репозитория статей.

        Args:
            session: Асинхронная SQLAlchemy сессия для операций с БД.
            cache_backend: Бэкенд для кеширования.
            enable_tracing: Включить трассировку запросов.
        """
        super().__init__(session, KnowledgeArticleModel, cache_backend, enable_tracing)

    async def get_by_slug(
        self,
        slug: str,
        published_only: bool = True,
        current_user_id: UUID | None = None,
    ) -> KnowledgeArticleModel | None:
        """Получить статью по slug с категорией, тегами и автором.

        Args:
            slug: URL-friendly идентификатор.
            published_only: Только опубликованные статьи.
            current_user_id: ID текущего пользователя для просмотра своих черновиков.

        Returns:
            KnowledgeArticleModel с загруженными связями или None.
        """
        stmt = (
            select(KnowledgeArticleModel)
            .where(KnowledgeArticleModel.slug == slug)
            .options(
                selectinload(KnowledgeArticleModel.category),
                selectinload(KnowledgeArticleModel.tags),
                selectinload(KnowledgeArticleModel.author),
            )
        )

        if published_only:
            # Если есть current_user_id, показываем опубликованные ИЛИ черновики этого пользователя
            if current_user_id:
                stmt = stmt.where(
                    or_(
                        KnowledgeArticleModel.is_published == True,  # noqa: E712
                        KnowledgeArticleModel.author_id == current_user_id,
                    )
                )
            else:
                stmt = stmt.where(KnowledgeArticleModel.is_published == True)  # noqa: E712

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_relations(
        self,
        article_id: UUID,
    ) -> KnowledgeArticleModel | None:
        """Получить статью по ID с категорией, тегами и автором.

        Args:
            article_id: UUID статьи.

        Returns:
            KnowledgeArticleModel с загруженными связями или None.
        """
        stmt = (
            select(KnowledgeArticleModel)
            .where(KnowledgeArticleModel.id == article_id)
            .options(
                selectinload(KnowledgeArticleModel.category),
                selectinload(KnowledgeArticleModel.tags),
                selectinload(KnowledgeArticleModel.author),
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_published(
        self,
        pagination: "PaginationParamsSchema",
        category_ids: list[UUID] | None = None,
        tag_slugs: list[str] | None = None,
        featured_only: bool = False,
        author_id: UUID | None = None,
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """Получить опубликованные статьи с пагинацией и фильтрами.

        Args:
            pagination: Параметры пагинации.
            category_ids: Фильтр по категориям (статья должна принадлежать хотя бы одной).
            tag_slugs: Фильтр по тегам (статья должна иметь хотя бы один из тегов).
            featured_only: Только закреплённые статьи.
            author_id: Фильтр по автору.

        Returns:
            Кортеж (список статей, общее количество).
        """
        stmt = (
            select(KnowledgeArticleModel)
            .where(KnowledgeArticleModel.is_published == True)  # noqa: E712
            .options(
                selectinload(KnowledgeArticleModel.category),
                selectinload(KnowledgeArticleModel.tags),
                selectinload(KnowledgeArticleModel.author),
            )
        )

        if category_ids:
            stmt = stmt.where(KnowledgeArticleModel.category_id.in_(category_ids))

        if featured_only:
            stmt = stmt.where(KnowledgeArticleModel.is_featured == True)  # noqa: E712

        if author_id:
            stmt = stmt.where(KnowledgeArticleModel.author_id == author_id)

        if tag_slugs:
            # Подзапрос для фильтрации по тегам
            stmt = stmt.where(
                KnowledgeArticleModel.id.in_(
                    select(KnowledgeArticleTagModel.article_id)
                    .join(KnowledgeTagModel)
                    .where(KnowledgeTagModel.slug.in_(tag_slugs))
                )
            )

        return await self.get_paginated_items(pagination, stmt)

    async def full_text_search(
        self,
        query: str,
        pagination: "PaginationParamsSchema",
        category_ids: list[UUID] | None = None,
        tag_slugs: list[str] | None = None,
        current_user_id: UUID | None = None,
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """Полнотекстовый поиск по статьям.

        Использует PostgreSQL tsvector и ts_rank для ранжирования результатов.
        Веса: title (A), description (B), content (C).

        Показывает:
        - Все опубликованные статьи
        - Черновики текущего пользователя (если current_user_id передан)

        Args:
            query: Поисковый запрос.
            pagination: Параметры пагинации.
            category_ids: Фильтр по категориям (статья должна принадлежать хотя бы одной).
            tag_slugs: Фильтр по тегам.
            current_user_id: ID текущего пользователя для показа его черновиков.

        Returns:
            Кортеж (список статей, общее количество).
        """
        from sqlalchemy import or_

        # Создаём tsquery из поискового запроса
        search_query = func.plainto_tsquery("russian", query)

        # Условие видимости: опубликовано ИЛИ автор = текущий пользователь
        if current_user_id:
            visibility_condition = or_(
                KnowledgeArticleModel.is_published == True,  # noqa: E712
                KnowledgeArticleModel.author_id == current_user_id,
            )
        else:
            visibility_condition = KnowledgeArticleModel.is_published == True  # noqa: E712

        # Базовый запрос с полнотекстовым поиском
        stmt = (
            select(
                KnowledgeArticleModel,
                func.ts_rank(
                    KnowledgeArticleModel.search_vector,
                    search_query,
                ).label("rank"),
            )
            .where(visibility_condition)
            .where(KnowledgeArticleModel.search_vector.op("@@")(search_query))
            .options(
                selectinload(KnowledgeArticleModel.category),
                selectinload(KnowledgeArticleModel.tags),
                selectinload(KnowledgeArticleModel.author),
            )
        )

        if category_ids:
            stmt = stmt.where(KnowledgeArticleModel.category_id.in_(category_ids))

        if tag_slugs:
            stmt = stmt.where(
                KnowledgeArticleModel.id.in_(
                    select(KnowledgeArticleTagModel.article_id)
                    .join(KnowledgeTagModel)
                    .where(KnowledgeTagModel.slug.in_(tag_slugs))
                )
            )

        # Подсчёт общего количества
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Сортировка по релевантности (rank) и пагинация
        stmt = stmt.order_by(text("rank DESC"))
        offset = (pagination.page - 1) * pagination.page_size
        stmt = stmt.offset(offset).limit(pagination.page_size)

        result = await self.session.execute(stmt)
        rows = result.all()

        # Извлекаем только модели (без rank)
        articles = [row[0] for row in rows]

        return articles, total

    async def increment_view_count(self, article_id: UUID) -> None:
        """Увеличить счётчик просмотров статьи.

        Args:
            article_id: UUID статьи.
        """
        article = await self.get_item_by_id(article_id)
        if article:
            article.increment_views()
            await self.session.commit()

    async def get_by_author(
        self,
        author_id: UUID,
        pagination: "PaginationParamsSchema",
        published_only: bool = False,
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """Получить статьи автора с пагинацией.

        Args:
            author_id: UUID автора.
            pagination: Параметры пагинации.
            published_only: Только опубликованные статьи.

        Returns:
            Кортеж (список статей, общее количество).
        """
        stmt = (
            select(KnowledgeArticleModel)
            .where(KnowledgeArticleModel.author_id == author_id)
            .options(
                selectinload(KnowledgeArticleModel.author),
                selectinload(KnowledgeArticleModel.category),
                selectinload(KnowledgeArticleModel.tags),
            )
        )

        if published_only:
            stmt = stmt.where(KnowledgeArticleModel.is_published == True)  # noqa: E712

        return await self.get_paginated_items(pagination, stmt)

    async def set_tags(self, article_id: UUID, tag_ids: list[UUID]) -> None:
        """Установить теги для статьи (заменяет существующие).

        Args:
            article_id: UUID статьи.
            tag_ids: Список UUID тегов.
        """
        from sqlalchemy import delete

        # Удаляем существующие связи
        await self.session.execute(
            delete(KnowledgeArticleTagModel).where(
                KnowledgeArticleTagModel.article_id == article_id
            )
        )

        # Создаём новые связи
        for tag_id in tag_ids:
            link = KnowledgeArticleTagModel(
                article_id=article_id,
                tag_id=tag_id,
            )
            self.session.add(link)

        await self.session.flush()

    async def update_embedding(
        self,
        article_id: UUID,
        embedding: list[float],
    ) -> None:
        """Обновить эмбеддинг статьи.

        Args:
            article_id: UUID статьи.
            embedding: Вектор эмбеддинга.
        """
        article = await self.get_item_by_id(article_id)
        if article:
            article.embedding = embedding
            await self.session.commit()

    async def find_similar(
        self,
        embedding: list[float],
        limit: int = 5,
        threshold: float = 0.7,
        exclude_id: UUID | None = None,
    ) -> list[KnowledgeArticleModel]:
        """Найти похожие статьи по эмбеддингу (косинусное сходство).

        Использует pgvector для векторного поиска.

        Args:
            embedding: Вектор запроса.
            limit: Максимальное количество результатов.
            threshold: Минимальное сходство (0-1).
            exclude_id: UUID статьи для исключения из результатов.

        Returns:
            Список похожих статей, отсортированных по сходству.
        """
        from sqlalchemy import Float, cast
        from sqlalchemy.dialects.postgresql import ARRAY
        from sqlalchemy.dialects.postgresql import array as pg_array

        # Преобразуем embedding в PostgreSQL массив
        embedding_array = pg_array(embedding, type_=Float)

        # Косинусное расстояние: 1 - cosine_similarity
        # pgvector использует <=> для косинусного расстояния
        # Мы хотим similarity, поэтому: 1 - distance
        stmt = (
            select(
                KnowledgeArticleModel,
                (
                    1 - func.power(
                        func.sum(
                            func.unnest(KnowledgeArticleModel.embedding)
                            * func.unnest(cast(embedding_array, ARRAY(Float)))
                        ),
                        1,
                    )
                    / (
                        func.sqrt(
                            func.sum(
                                func.power(func.unnest(KnowledgeArticleModel.embedding), 2)
                            )
                        )
                        * func.sqrt(
                            func.sum(
                                func.power(func.unnest(cast(embedding_array, ARRAY(Float))), 2)
                            )
                        )
                    )
                ).label("similarity"),
            )
            .where(KnowledgeArticleModel.is_published == True)  # noqa: E712
            .where(KnowledgeArticleModel.embedding.isnot(None))
            .options(
                selectinload(KnowledgeArticleModel.category),
                selectinload(KnowledgeArticleModel.tags),
                selectinload(KnowledgeArticleModel.author),
            )
            .group_by(KnowledgeArticleModel.id)
            .order_by(text("similarity DESC"))
            .limit(limit)
        )

        if exclude_id:
            stmt = stmt.where(KnowledgeArticleModel.id != exclude_id)

        result = await self.session.execute(stmt)
        rows = result.all()

        # Фильтруем по threshold и возвращаем только модели
        return [row[0] for row in rows if row[1] >= threshold]

    async def semantic_search(
        self,
        embedding: list[float],
        pagination: "PaginationParamsSchema",
        category_id: UUID | None = None,
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """Семантический поиск по статьям с использованием эмбеддингов.

        Более простой подход с использованием raw SQL для pgvector.

        Args:
            embedding: Вектор запроса.
            pagination: Параметры пагинации.
            category_id: Фильтр по категории.

        Returns:
            Кортеж (список статей, общее количество).
        """
        from sqlalchemy import text as sql_text

        # Преобразуем embedding в строку для SQL
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        # Raw SQL для pgvector cosine similarity
        # Используем 1 - (embedding <=> query) для similarity
        base_where = "is_published = true AND embedding IS NOT NULL"
        if category_id:
            base_where += f" AND category_id = '{category_id}'"

        # Подсчёт общего количества
        count_sql = sql_text(f"""
            SELECT COUNT(*)
            FROM knowledge_articles
            WHERE {base_where}
        """)
        count_result = await self.session.execute(count_sql)
        total = count_result.scalar() or 0

        # Основной запрос с пагинацией
        offset = (pagination.page - 1) * pagination.page_size
        search_sql = sql_text(f"""
            SELECT id
            FROM knowledge_articles
            WHERE {base_where}
            ORDER BY embedding <=> '{embedding_str}'::vector
            LIMIT {pagination.page_size} OFFSET {offset}
        """)

        result = await self.session.execute(search_sql)
        article_ids = [row[0] for row in result.all()]

        if not article_ids:
            return [], total

        # Загружаем полные объекты с связями
        stmt = (
            select(KnowledgeArticleModel)
            .where(KnowledgeArticleModel.id.in_(article_ids))
            .options(
                selectinload(KnowledgeArticleModel.category),
                selectinload(KnowledgeArticleModel.tags),
                selectinload(KnowledgeArticleModel.author),
            )
        )

        result = await self.session.execute(stmt)
        articles_map = {a.id: a for a in result.scalars().all()}

        # Возвращаем в порядке релевантности
        articles = [articles_map[aid] for aid in article_ids if aid in articles_map]

        return articles, total

    async def clear_all_embeddings(self) -> int:
        """Сбросить все эмбеддинги статей.

        Используется при смене модели эмбеддингов.

        Returns:
            Количество обновлённых статей.
        """
        from sqlalchemy import update

        stmt = (
            update(KnowledgeArticleModel)
            .where(KnowledgeArticleModel.embedding.isnot(None))
            .values(embedding=None)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount or 0

    async def count_with_embeddings(self) -> int:
        """Подсчитать количество статей с эмбеддингами.

        Returns:
            Количество статей с эмбеддингами.
        """
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(KnowledgeArticleModel)
            .where(KnowledgeArticleModel.embedding.isnot(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0


class KnowledgeChatSessionRepository(BaseRepository[KnowledgeChatSessionModel]):
    """Репозиторий для операций с сессиями чата базы знаний.

    Предоставляет методы для работы с чат-сессиями и их сообщениями.
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        """Инициализация репозитория сессий чата."""
        super().__init__(session, KnowledgeChatSessionModel, cache_backend, enable_tracing)

    async def get_user_sessions(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[KnowledgeChatSessionModel]:
        """Получить сессии чата пользователя.

        Args:
            user_id: UUID пользователя.
            limit: Максимальное количество сессий.

        Returns:
            Список сессий, отсортированных по дате обновления.
        """
        stmt = (
            select(KnowledgeChatSessionModel)
            .where(KnowledgeChatSessionModel.user_id == user_id)
            .order_by(KnowledgeChatSessionModel.updated_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_session_key(
        self,
        session_key: str,
    ) -> KnowledgeChatSessionModel | None:
        """Получить сессию по ключу (для анонимных пользователей).

        Args:
            session_key: Ключ сессии.

        Returns:
            Сессия или None.
        """
        stmt = (
            select(KnowledgeChatSessionModel)
            .where(KnowledgeChatSessionModel.session_key == session_key)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_sessions_by_key(
        self,
        session_key: str,
        limit: int = 20,
    ) -> list[KnowledgeChatSessionModel]:
        """Получить сессии чата по ключу (для анонимных).

        Args:
            session_key: Ключ сессии.
            limit: Максимальное количество сессий.

        Returns:
            Список сессий.
        """
        stmt = (
            select(KnowledgeChatSessionModel)
            .where(KnowledgeChatSessionModel.session_key == session_key)
            .order_by(KnowledgeChatSessionModel.updated_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_messages(
        self,
        session_id: UUID,
    ) -> KnowledgeChatSessionModel | None:
        """Получить сессию с сообщениями.

        Args:
            session_id: UUID сессии.

        Returns:
            Сессия с загруженными сообщениями или None.
        """
        stmt = (
            select(KnowledgeChatSessionModel)
            .where(KnowledgeChatSessionModel.id == session_id)
            .options(selectinload(KnowledgeChatSessionModel.messages))
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class KnowledgeChatMessageRepository(BaseRepository[KnowledgeChatMessageModel]):
    """Репозиторий для операций с сообщениями чата базы знаний."""

    def __init__(
        self,
        session: AsyncSession,
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        """Инициализация репозитория сообщений чата."""
        super().__init__(session, KnowledgeChatMessageModel, cache_backend, enable_tracing)

    async def get_session_messages(
        self,
        session_id: UUID,
        limit: int = 50,
    ) -> list[KnowledgeChatMessageModel]:
        """Получить сообщения сессии.

        Args:
            session_id: UUID сессии.
            limit: Максимальное количество сообщений.

        Returns:
            Список сообщений в хронологическом порядке.
        """
        stmt = (
            select(KnowledgeChatMessageModel)
            .where(KnowledgeChatMessageModel.session_id == session_id)
            .order_by(KnowledgeChatMessageModel.created_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class KnowledgeArticleChunkRepository(BaseRepository[KnowledgeArticleChunkModel]):
    """Репозиторий для операций с чанками статей базы знаний.

    Предоставляет методы для работы с фрагментами статей,
    включая семантический поиск по чанкам.

    Специфичные методы:
    - get_article_chunks() - получение всех чанков статьи
    - delete_article_chunks() - удаление всех чанков статьи
    - semantic_search_chunks() - семантический поиск по чанкам
    - update_chunk_embedding() - обновление эмбеддинга чанка
    """

    def __init__(
        self,
        session: AsyncSession,
        cache_backend: CacheBackend | None = None,
        enable_tracing: bool = False,
    ):
        """Инициализация репозитория чанков."""
        super().__init__(session, KnowledgeArticleChunkModel, cache_backend, enable_tracing)

    async def get_article_chunks(
        self,
        article_id: UUID,
    ) -> list[KnowledgeArticleChunkModel]:
        """Получить все чанки статьи, отсортированные по индексу.

        Args:
            article_id: UUID статьи.

        Returns:
            Список чанков в порядке индекса.
        """
        stmt = (
            select(KnowledgeArticleChunkModel)
            .where(KnowledgeArticleChunkModel.article_id == article_id)
            .order_by(KnowledgeArticleChunkModel.chunk_index)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_article_chunks(self, article_id: UUID) -> int:
        """Удалить все чанки статьи.

        Args:
            article_id: UUID статьи.

        Returns:
            Количество удалённых чанков.
        """
        from sqlalchemy import delete

        stmt = delete(KnowledgeArticleChunkModel).where(
            KnowledgeArticleChunkModel.article_id == article_id
        )
        result = await self.session.execute(stmt)
        await self.session.flush()

        return result.rowcount or 0

    async def update_chunk_embedding(
        self,
        chunk_id: UUID,
        embedding: list[float],
    ) -> None:
        """Обновить эмбеддинг чанка.

        Args:
            chunk_id: UUID чанка.
            embedding: Вектор эмбеддинга.
        """
        chunk = await self.get_item_by_id(chunk_id)
        if chunk:
            chunk.embedding = embedding
            await self.session.flush()

    async def semantic_search_chunks(
        self,
        embedding: list[float],
        limit: int = 10,
        category_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Семантический поиск по чанкам статей.

        Возвращает чанки с информацией о родительской статье.

        Args:
            embedding: Вектор запроса.
            limit: Максимальное количество результатов.
            category_id: Фильтр по категории статьи.

        Returns:
            Список словарей с чанком, статьёй и расстоянием.
        """
        from sqlalchemy import text as sql_text

        # Преобразуем embedding в строку для SQL
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        # Базовые условия
        where_clauses = ["c.embedding IS NOT NULL", "a.is_published = true"]
        if category_id:
            where_clauses.append(f"a.category_id = '{category_id}'")

        where_sql = " AND ".join(where_clauses)

        # Запрос с JOIN на статьи для фильтрации по published
        search_sql = sql_text(f"""
            SELECT
                c.id as chunk_id,
                c.article_id,
                c.chunk_index,
                c.title as chunk_title,
                c.content,
                c.token_count,
                a.title as article_title,
                a.slug as article_slug,
                c.embedding <=> '{embedding_str}'::vector as distance
            FROM knowledge_article_chunks c
            JOIN knowledge_articles a ON c.article_id = a.id
            WHERE {where_sql}
            ORDER BY distance
            LIMIT {limit}
        """)

        result = await self.session.execute(search_sql)
        rows = result.all()

        return [
            {
                "chunk_id": row[0],
                "article_id": row[1],
                "chunk_index": row[2],
                "chunk_title": row[3],
                "content": row[4],
                "token_count": row[5],
                "article_title": row[6],
                "article_slug": row[7],
                "distance": row[8],
            }
            for row in rows
        ]

    async def count_chunks_with_embeddings(self) -> int:
        """Подсчитать количество чанков с эмбеддингами.

        Returns:
            Количество чанков с эмбеддингами.
        """
        stmt = (
            select(func.count())
            .select_from(KnowledgeArticleChunkModel)
            .where(KnowledgeArticleChunkModel.embedding.isnot(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def clear_all_chunk_embeddings(self) -> int:
        """Сбросить все эмбеддинги чанков.

        Returns:
            Количество обновлённых чанков.
        """
        from sqlalchemy import update

        stmt = (
            update(KnowledgeArticleChunkModel)
            .where(KnowledgeArticleChunkModel.embedding.isnot(None))
            .values(embedding=None)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount or 0
