"""
Сервис для бизнес-логики работы с базой знаний.

Модуль предоставляет KnowledgeService для управления статьями, категориями и тегами:
- CRUD операции для статей, категорий и тегов
- Полнотекстовый поиск по статьям
- Семантический поиск (RAG) через OpenRouter embeddings
- Публикация/снятие с публикации статей
- Управление тегами статей
- Автогенерация slug из заголовка

КРИТИЧНО: Сервис возвращает только SQLAlchemy модели,
конвертация в Pydantic схемы происходит на уровне Router!
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.integrations.ai import OpenRouterClient
from app.core.settings import settings
from app.core.utils import generate_slug
from app.models.v1 import (
    KnowledgeArticleModel,
    KnowledgeCategoryModel,
    KnowledgeTagModel,
)
from app.repository.v1.knowledge import (
    KnowledgeArticleRepository,
    KnowledgeCategoryRepository,
    KnowledgeTagRepository,
)
from app.services.base import BaseService

if TYPE_CHECKING:
    from app.schemas.pagination import PaginationParamsSchema


class KnowledgeService(BaseService):
    """
    Сервис для управления базой знаний.

    Реализует бизнес-логику работы со статьями, категориями и тегами:
    - Создание/обновление/удаление статей
    - Публикация и снятие с публикации
    - Полнотекстовый поиск
    - Управление категориями и тегами

    Attributes:
        article_repository: Репозиторий для работы со статьями
        category_repository: Репозиторий для работы с категориями
        tag_repository: Репозиторий для работы с тегами
        logger: Логгер для отслеживания операций

    Example:
        >>> async with AsyncSession() as session:
        ...     service = KnowledgeService(session)
        ...     # Создание статьи
        ...     article = await service.create_article(
        ...         data={"title": "Как настроить ESLint", "content": "..."},
        ...         author_id=user_id
        ...     )
        ...
        ...     # Полнотекстовый поиск
        ...     articles, total = await service.search_articles(
        ...         query="ESLint",
        ...         pagination=PaginationParamsSchema()
        ...     )
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует KnowledgeService.

        Args:
            session: Асинхронная сессия SQLAlchemy для работы с БД
        """
        super().__init__(session)
        self.article_repository = KnowledgeArticleRepository(session)
        self.category_repository = KnowledgeCategoryRepository(session)
        self.tag_repository = KnowledgeTagRepository(session)
        self._ai_settings = settings.ai

    def _get_openrouter_client(self, api_key: str) -> OpenRouterClient:
        """
        Создаёт клиент OpenRouter для работы с эмбеддингами.

        Args:
            api_key: API ключ OpenRouter пользователя

        Returns:
            Настроенный OpenRouterClient
        """
        return OpenRouterClient(
            api_key=api_key,
            base_url=self._ai_settings.OPENROUTER_BASE_URL,
            site_url=self._ai_settings.OPENROUTER_SITE_URL,
            app_name=self._ai_settings.OPENROUTER_APP_NAME,
            timeout=self._ai_settings.OPENROUTER_TIMEOUT,
            default_embedding_model=self._ai_settings.RAG_DEFAULT_MODEL,
        )

    # ==================== СТАТЬИ ====================

    async def get_article_by_slug(
        self,
        slug: str,
        published_only: bool = True,
        current_user_id: UUID | None = None,
    ) -> KnowledgeArticleModel:
        """
        Получает статью по slug.

        Args:
            slug: URL-friendly идентификатор
            published_only: Только опубликованные статьи
            current_user_id: ID текущего пользователя для просмотра своих черновиков

        Returns:
            KnowledgeArticleModel: Статья с категорией, тегами и автором

        Raises:
            NotFoundError: Если статья не найдена
        """
        article = await self.article_repository.get_by_slug(
            slug, published_only, current_user_id
        )
        if not article:
            self.logger.error("Статья не найдена: %s", slug)
            raise NotFoundError(detail="Статья не найдена", field="slug", value=slug)

        self.logger.debug("Получена статья: %s", article.title)
        return article

    async def get_article_by_id(self, article_id: UUID) -> KnowledgeArticleModel:
        """
        Получает статью по ID.

        Args:
            article_id: UUID статьи

        Returns:
            KnowledgeArticleModel: Статья с категорией, тегами и автором

        Raises:
            NotFoundError: Если статья не найдена
        """
        article = await self.article_repository.get_by_id_with_relations(article_id)
        if not article:
            self.logger.error("Статья не найдена: %s", article_id)
            raise NotFoundError(
                detail="Статья не найдена",
                field="article_id",
                value=str(article_id),
            )

        return article

    async def get_published_articles(
        self,
        pagination: "PaginationParamsSchema",
        category_id: UUID | None = None,
        tag_slugs: list[str] | None = None,
        featured_only: bool = False,
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """
        Получает опубликованные статьи с фильтрами и пагинацией.

        Args:
            pagination: Параметры пагинации
            category_id: Фильтр по категории
            tag_slugs: Фильтр по тегам
            featured_only: Только закреплённые статьи

        Returns:
            Кортеж (список статей, общее количество)
        """
        articles, total = await self.article_repository.get_published(
            pagination=pagination,
            category_id=category_id,
            tag_slugs=tag_slugs,
            featured_only=featured_only,
        )

        self.logger.debug(
            "Получено %d статей (всего: %d)",
            len(articles),
            total,
        )

        return articles, total

    async def search_articles(
        self,
        query: str,
        pagination: "PaginationParamsSchema",
        category_id: UUID | None = None,
        tag_slugs: list[str] | None = None,
        current_user_id: UUID | None = None,
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """
        Полнотекстовый поиск по статьям.

        Показывает все опубликованные статьи + черновики текущего пользователя.

        Args:
            query: Поисковый запрос
            pagination: Параметры пагинации
            category_id: Фильтр по категории
            tag_slugs: Фильтр по тегам
            current_user_id: ID текущего пользователя для показа его черновиков

        Returns:
            Кортеж (список статей, общее количество)
        """
        if not query or len(query.strip()) < 2:
            raise ValidationError(
                detail="Поисковый запрос должен содержать минимум 2 символа",
                field="query",
                value=query,
            )

        articles, total = await self.article_repository.full_text_search(
            query=query.strip(),
            pagination=pagination,
            category_id=category_id,
            tag_slugs=tag_slugs,
            current_user_id=current_user_id,
        )

        self.logger.info(
            "Поиск '%s': найдено %d статей",
            query,
            total,
        )

        return articles, total

    async def create_article(
        self,
        data: dict[str, Any],
        author_id: UUID,
    ) -> KnowledgeArticleModel:
        """
        Создаёт новую статью.

        Args:
            data: Данные статьи
                - title (str): Заголовок
                - content (str): Контент в Markdown
                - description (str, optional): Краткое описание
                - slug (str, optional): URL-friendly идентификатор
                - category_id (UUID, optional): ID категории
                - tag_ids (list[UUID], optional): Список ID тегов
                - is_published (bool, optional): Опубликовать сразу
                - is_featured (bool, optional): Закрепить
            author_id: UUID автора

        Returns:
            KnowledgeArticleModel: Созданная статья

        Raises:
            ValidationError: Если slug уже существует
        """
        # Генерируем slug если не указан
        slug = data.get("slug") or generate_slug(data["title"])

        # Проверяем уникальность slug
        existing = await self.article_repository.get_item_by_field("slug", slug)
        if existing:
            # Добавляем суффикс для уникальности
            base_slug = slug
            counter = 1
            while existing:
                slug = f"{base_slug}-{counter}"
                existing = await self.article_repository.get_item_by_field("slug", slug)
                counter += 1

        # Извлекаем tag_ids для отдельной обработки
        tag_ids = data.pop("tag_ids", [])

        # Подготавливаем данные для создания
        article_data = {
            **data,
            "slug": slug,
            "author_id": author_id,
        }

        # Если публикуем сразу, устанавливаем дату
        if article_data.get("is_published"):
            article_data["published_at"] = datetime.now(UTC)

        # Создаём статью
        article = await self.article_repository.create_item(article_data)

        # Добавляем теги
        if tag_ids:
            await self.article_repository.set_tags(article.id, tag_ids)
            await self.session.commit()

        # Перезагружаем статью с связями
        article = await self.article_repository.get_by_id_with_relations(article.id)

        self.logger.info(
            "Создана статья: %s (id=%s, slug=%s)",
            article.title,
            article.id,
            article.slug,
        )

        return article

    async def update_article(
        self,
        article_id: UUID,
        data: dict[str, Any],
    ) -> KnowledgeArticleModel:
        """
        Обновляет статью.

        Args:
            article_id: UUID статьи
            data: Данные для обновления

        Returns:
            KnowledgeArticleModel: Обновлённая статья

        Raises:
            NotFoundError: Если статья не найдена
            ValidationError: Если slug уже существует
        """
        article = await self.get_article_by_id(article_id)

        # Если обновляется slug, проверяем уникальность
        if "slug" in data and data["slug"] != article.slug:
            existing = await self.article_repository.get_item_by_field("slug", data["slug"])
            if existing:
                raise ValidationError(
                    detail="Статья с таким slug уже существует",
                    field="slug",
                    value=data["slug"],
                )

        # Обрабатываем теги отдельно
        tag_ids = data.pop("tag_ids", None)

        # Обновляем статью
        if data:
            article = await self.article_repository.update_item(article_id, data)

        # Обновляем теги если переданы
        if tag_ids is not None:
            await self.article_repository.set_tags(article_id, tag_ids)
            await self.session.commit()

        # Перезагружаем с связями
        article = await self.article_repository.get_by_id_with_relations(article_id)

        self.logger.info("Обновлена статья: %s (id=%s)", article.title, article.id)

        return article

    async def delete_article(self, article_id: UUID) -> bool:
        """
        Удаляет статью.

        Args:
            article_id: UUID статьи

        Returns:
            bool: True если удалено

        Raises:
            NotFoundError: Если статья не найдена
        """
        article = await self.get_article_by_id(article_id)
        result = await self.article_repository.delete_item(article_id)

        self.logger.info("Удалена статья: %s (id=%s)", article.title, article_id)

        return result

    async def publish_article(self, article_id: UUID) -> KnowledgeArticleModel:
        """
        Публикует статью.

        Args:
            article_id: UUID статьи

        Returns:
            KnowledgeArticleModel: Опубликованная статья

        Raises:
            NotFoundError: Если статья не найдена
        """
        article = await self.get_article_by_id(article_id)
        article.publish()
        await self.session.commit()

        self.logger.info("Опубликована статья: %s (id=%s)", article.title, article_id)

        return article

    async def unpublish_article(self, article_id: UUID) -> KnowledgeArticleModel:
        """
        Снимает статью с публикации.

        Args:
            article_id: UUID статьи

        Returns:
            KnowledgeArticleModel: Статья-черновик

        Raises:
            NotFoundError: Если статья не найдена
        """
        article = await self.get_article_by_id(article_id)
        article.unpublish()
        await self.session.commit()

        self.logger.info("Снята с публикации статья: %s (id=%s)", article.title, article_id)

        return article

    async def increment_article_views(self, article_id: UUID) -> None:
        """
        Увеличивает счётчик просмотров статьи.

        Args:
            article_id: UUID статьи
        """
        await self.article_repository.increment_view_count(article_id)

    # ==================== RAG (СЕМАНТИЧЕСКИЙ ПОИСК) ====================

    async def index_article(
        self,
        article_id: UUID,
        api_key: str,
        model: str = "openai/text-embedding-3-small",
    ) -> KnowledgeArticleModel:
        """
        Создаёт эмбеддинг для статьи и сохраняет в БД.

        Эмбеддинг создаётся из комбинации заголовка, описания и контента.
        Используется для семантического поиска (RAG).

        Args:
            article_id: UUID статьи
            api_key: API ключ OpenRouter пользователя
            model: Модель для эмбеддингов

        Returns:
            KnowledgeArticleModel: Статья с обновлённым эмбеддингом

        Raises:
            NotFoundError: Если статья не найдена
            ExternalServiceError: При ошибке OpenRouter API

        Example:
            >>> article = await service.index_article(
            ...     article_id=uuid,
            ...     api_key="sk-or-..."
            ... )
        """
        article = await self.get_article_by_id(article_id)

        # Формируем текст для эмбеддинга
        text_parts = [article.title]
        if article.description:
            text_parts.append(article.description)
        text_parts.append(article.content)
        text = "\n\n".join(text_parts)

        # Создаём эмбеддинг через OpenRouter
        client = self._get_openrouter_client(api_key)
        embedding = await client.create_embedding(text=text, model=model)

        # Сохраняем в БД
        await self.article_repository.update_embedding(article_id, embedding)

        self.logger.info(
            "Создан эмбеддинг для статьи: %s (id=%s, dimension=%d)",
            article.title,
            article_id,
            len(embedding),
        )

        # Возвращаем обновлённую статью
        return await self.get_article_by_id(article_id)

    async def index_all_articles(
        self,
        api_key: str,
        model: str = "openai/text-embedding-3-small",
    ) -> int:
        """
        Создаёт эмбеддинги для всех опубликованных статей без эмбеддинга.

        Args:
            api_key: API ключ OpenRouter пользователя
            model: Модель для эмбеддингов

        Returns:
            int: Количество проиндексированных статей

        Example:
            >>> count = await service.index_all_articles(api_key="sk-or-...")
            >>> print(f"Проиндексировано {count} статей")
        """
        # Получаем все статьи без эмбеддингов
        articles = await self.article_repository.get_items_by_filter(
            is_published=True,
            embedding=None,
        )

        if not articles:
            self.logger.info("Все статьи уже проиндексированы")
            return 0

        # Готовим тексты для batch обработки
        texts = []
        for article in articles:
            text_parts = [article.title]
            if article.description:
                text_parts.append(article.description)
            text_parts.append(article.content)
            texts.append("\n\n".join(text_parts))

        # Создаём эмбеддинги батчами
        client = self._get_openrouter_client(api_key)
        embeddings = await client.create_embeddings_batch(texts=texts, model=model)

        # Сохраняем эмбеддинги
        for article, embedding in zip(articles, embeddings, strict=True):
            await self.article_repository.update_embedding(article.id, embedding)

        self.logger.info("Проиндексировано %d статей", len(articles))

        return len(articles)

    async def semantic_search(
        self,
        query: str,
        api_key: str,
        pagination: "PaginationParamsSchema",
        category_id: UUID | None = None,
        model: str = "openai/text-embedding-3-small",
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """
        Семантический поиск по статьям через RAG.

        Создаёт эмбеддинг запроса и ищет похожие статьи по косинусному расстоянию.

        Args:
            query: Поисковый запрос
            api_key: API ключ OpenRouter пользователя
            pagination: Параметры пагинации
            category_id: Фильтр по категории
            model: Модель для эмбеддингов

        Returns:
            Кортеж (список статей, общее количество)

        Raises:
            ValidationError: Если запрос слишком короткий
            ExternalServiceError: При ошибке OpenRouter API

        Example:
            >>> articles, total = await service.semantic_search(
            ...     query="Как настроить Docker?",
            ...     api_key="sk-or-...",
            ...     pagination=PaginationParamsSchema()
            ... )
        """
        if not query or len(query.strip()) < 2:
            raise ValidationError(
                detail="Поисковый запрос должен содержать минимум 2 символа",
                field="query",
                value=query,
            )

        # Создаём эмбеддинг запроса
        client = self._get_openrouter_client(api_key)
        query_embedding = await client.create_embedding(text=query.strip(), model=model)

        # Ищем похожие статьи
        articles, total = await self.article_repository.semantic_search(
            embedding=query_embedding,
            pagination=pagination,
            category_id=category_id,
        )

        self.logger.info(
            "Семантический поиск '%s': найдено %d статей",
            query,
            total,
        )

        return articles, total

    async def find_similar_articles(
        self,
        article_id: UUID,
        api_key: str,
        limit: int = 5,
        model: str = "openai/text-embedding-3-small",
    ) -> list[KnowledgeArticleModel]:
        """
        Находит похожие статьи на основе эмбеддинга.

        Args:
            article_id: UUID исходной статьи
            api_key: API ключ OpenRouter (используется если нет эмбеддинга)
            limit: Максимальное количество результатов
            model: Модель для эмбеддингов

        Returns:
            Список похожих статей

        Raises:
            NotFoundError: Если статья не найдена
        """
        article = await self.get_article_by_id(article_id)

        # Если нет эмбеддинга, создаём его
        if not article.embedding:
            article = await self.index_article(article_id, api_key, model)

        # Ищем похожие статьи
        similar = await self.article_repository.find_similar(
            embedding=article.embedding,
            limit=limit,
            exclude_id=article_id,
        )

        self.logger.debug(
            "Найдено %d похожих статей для '%s'",
            len(similar),
            article.title,
        )

        return similar

    # ==================== КАТЕГОРИИ ====================

    async def get_all_categories(self) -> list[KnowledgeCategoryModel]:
        """
        Получает все категории, отсортированные по order.

        Returns:
            Список категорий
        """
        return await self.category_repository.get_all_ordered()

    async def get_categories_with_count(self) -> list[dict[str, Any]]:
        """
        Получает категории с количеством опубликованных статей.

        Returns:
            Список словарей с категориями и articles_count
        """
        return await self.category_repository.get_with_articles_count()

    async def get_category_by_id(self, category_id: UUID) -> KnowledgeCategoryModel:
        """
        Получает категорию по ID.

        Args:
            category_id: UUID категории

        Returns:
            KnowledgeCategoryModel

        Raises:
            NotFoundError: Если категория не найдена
        """
        category = await self.category_repository.get_item_by_id(category_id)
        if not category:
            raise NotFoundError(
                detail="Категория не найдена",
                field="category_id",
                value=str(category_id),
            )
        return category

    async def get_category_by_slug(self, slug: str) -> KnowledgeCategoryModel:
        """
        Получает категорию по slug.

        Args:
            slug: URL-friendly идентификатор

        Returns:
            KnowledgeCategoryModel

        Raises:
            NotFoundError: Если категория не найдена
        """
        category = await self.category_repository.get_by_slug(slug)
        if not category:
            raise NotFoundError(
                detail="Категория не найдена",
                field="slug",
                value=slug,
            )
        return category

    async def create_category(self, data: dict[str, Any]) -> KnowledgeCategoryModel:
        """
        Создаёт новую категорию.

        Args:
            data: Данные категории

        Returns:
            KnowledgeCategoryModel
        """
        # Генерируем slug если не указан
        if not data.get("slug"):
            data["slug"] = generate_slug(data["name"])

        category = await self.category_repository.create_item(data)

        self.logger.info(
            "Создана категория: %s (id=%s)",
            category.name,
            category.id,
        )

        return category

    async def update_category(
        self,
        category_id: UUID,
        data: dict[str, Any],
    ) -> KnowledgeCategoryModel:
        """
        Обновляет категорию.

        Args:
            category_id: UUID категории
            data: Данные для обновления

        Returns:
            KnowledgeCategoryModel

        Raises:
            NotFoundError: Если категория не найдена
        """
        await self.get_category_by_id(category_id)
        category = await self.category_repository.update_item(category_id, data)

        self.logger.info("Обновлена категория: %s (id=%s)", category.name, category.id)

        return category

    async def delete_category(self, category_id: UUID) -> bool:
        """
        Удаляет категорию.

        Args:
            category_id: UUID категории

        Returns:
            bool: True если удалено

        Raises:
            NotFoundError: Если категория не найдена
        """
        category = await self.get_category_by_id(category_id)
        result = await self.category_repository.delete_item(category_id)

        self.logger.info("Удалена категория: %s (id=%s)", category.name, category_id)

        return result

    # ==================== ТЕГИ ====================

    async def get_all_tags(self) -> list[KnowledgeTagModel]:
        """
        Получает все теги.

        Returns:
            Список тегов
        """
        return await self.tag_repository.get_items()

    async def get_popular_tags(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Получает популярные теги с количеством статей.

        Args:
            limit: Максимальное количество тегов

        Returns:
            Список словарей с тегами и articles_count
        """
        return await self.tag_repository.get_popular(limit)

    async def get_tag_by_id(self, tag_id: UUID) -> KnowledgeTagModel:
        """
        Получает тег по ID.

        Args:
            tag_id: UUID тега

        Returns:
            KnowledgeTagModel

        Raises:
            NotFoundError: Если тег не найден
        """
        tag = await self.tag_repository.get_item_by_id(tag_id)
        if not tag:
            raise NotFoundError(
                detail="Тег не найден",
                field="tag_id",
                value=str(tag_id),
            )
        return tag

    async def get_tag_by_slug(self, slug: str) -> KnowledgeTagModel:
        """
        Получает тег по slug.

        Args:
            slug: URL-friendly идентификатор

        Returns:
            KnowledgeTagModel

        Raises:
            NotFoundError: Если тег не найден
        """
        tag = await self.tag_repository.get_by_slug(slug)
        if not tag:
            raise NotFoundError(
                detail="Тег не найден",
                field="slug",
                value=slug,
            )
        return tag

    async def create_tag(self, data: dict[str, Any]) -> KnowledgeTagModel:
        """
        Создаёт новый тег.

        Args:
            data: Данные тега

        Returns:
            KnowledgeTagModel
        """
        # Генерируем slug если не указан
        if not data.get("slug"):
            data["slug"] = generate_slug(data["name"])

        tag = await self.tag_repository.create_item(data)

        self.logger.info("Создан тег: %s (id=%s)", tag.name, tag.id)

        return tag

    async def update_tag(
        self,
        tag_id: UUID,
        data: dict[str, Any],
    ) -> KnowledgeTagModel:
        """
        Обновляет тег.

        Args:
            tag_id: UUID тега
            data: Данные для обновления

        Returns:
            KnowledgeTagModel

        Raises:
            NotFoundError: Если тег не найден
        """
        await self.get_tag_by_id(tag_id)
        tag = await self.tag_repository.update_item(tag_id, data)

        self.logger.info("Обновлён тег: %s (id=%s)", tag.name, tag.id)

        return tag

    async def delete_tag(self, tag_id: UUID) -> bool:
        """
        Удаляет тег.

        Args:
            tag_id: UUID тега

        Returns:
            bool: True если удалено

        Raises:
            NotFoundError: Если тег не найден
        """
        tag = await self.get_tag_by_id(tag_id)
        result = await self.tag_repository.delete_item(tag_id)

        self.logger.info("Удалён тег: %s (id=%s)", tag.name, tag_id)

        return result
