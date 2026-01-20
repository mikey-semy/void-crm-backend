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
from app.core.security.encryption import get_encryption_service
from app.core.settings import settings
from app.core.utils import generate_slug
from app.core.utils.chunking import chunk_article
from app.models.v1 import (
    KnowledgeArticleChunkModel,
    KnowledgeArticleModel,
    KnowledgeCategoryModel,
    KnowledgeTagModel,
    SystemSettingsKeys,
)
from app.repository.v1.knowledge import (
    KnowledgeArticleChunkRepository,
    KnowledgeArticleRepository,
    KnowledgeCategoryRepository,
    KnowledgeTagRepository,
)
from app.repository.v1.system_settings import SystemSettingsRepository
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
        self.chunk_repository = KnowledgeArticleChunkRepository(session)
        self.system_settings_repository = SystemSettingsRepository(session)
        self._ai_settings = settings.ai
        self._encryption = get_encryption_service()

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

    async def _get_system_api_key(self) -> str | None:
        """
        Получает расшифрованный API ключ из системных настроек.

        Returns:
            Расшифрованный API ключ или None
        """
        encrypted = await self.system_settings_repository.get_value(
            SystemSettingsKeys.RAG_API_KEY,
            "",
        )
        if not encrypted:
            return None

        return self._encryption.decrypt(encrypted)

    async def _get_embedding_model(self) -> str:
        """
        Получает модель эмбеддингов из системных настроек.

        Returns:
            ID модели эмбеддингов
        """
        return await self.system_settings_repository.get_value(
            SystemSettingsKeys.RAG_EMBEDDING_MODEL,
            self._ai_settings.RAG_DEFAULT_MODEL,
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
        category_ids: list[UUID] | None = None,
        tag_slugs: list[str] | None = None,
        featured_only: bool = False,
        author_id: UUID | None = None,
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """
        Получает опубликованные статьи с фильтрами и пагинацией.

        Args:
            pagination: Параметры пагинации
            category_ids: Фильтр по категориям (статья должна принадлежать хотя бы одной)
            tag_slugs: Фильтр по тегам
            featured_only: Только закреплённые статьи
            author_id: Фильтр по автору

        Returns:
            Кортеж (список статей, общее количество)
        """
        articles, total = await self.article_repository.get_published(
            pagination=pagination,
            category_ids=category_ids,
            tag_slugs=tag_slugs,
            featured_only=featured_only,
            author_id=author_id,
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
        category_ids: list[UUID] | None = None,
        tag_slugs: list[str] | None = None,
        current_user_id: UUID | None = None,
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """
        Полнотекстовый поиск по статьям.

        Показывает все опубликованные статьи + черновики текущего пользователя.

        Args:
            query: Поисковый запрос
            pagination: Параметры пагинации
            category_ids: Фильтр по категориям (статья должна принадлежать хотя бы одной)
            tag_slugs: Фильтр по тегам
            current_user_id: ID текущего пользователя для показа его черновиков

        Returns:
            Кортеж (список статей, общее количество)
        """
        if not query or len(query.strip()) < 2:
            raise ValidationError(
                detail="Поисковый запрос должен содержать минимум 2 символа",
                field="query",
            )

        articles, total = await self.article_repository.full_text_search(
            query=query.strip(),
            pagination=pagination,
            category_ids=category_ids,
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

        # Если статья опубликована и изменился контент - отправляем на переиндексацию
        content_fields = {"title", "content", "description"}
        if article.is_published and content_fields & set(data.keys()):
            try:
                from app.core.messaging.publisher import publish_article_indexing

                await publish_article_indexing(article_id)
                self.logger.info(
                    "Задача на переиндексацию статьи отправлена в очередь: %s", article_id
                )
            except Exception as e:
                self.logger.error(
                    "Ошибка отправки задачи переиндексации в очередь %s: %s", article_id, e
                )

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
        Публикует статью и отправляет задачу на индексацию для RAG в очередь.

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

        # Отправляем задачу на индексацию в очередь RabbitMQ
        try:
            from app.core.messaging.publisher import publish_article_indexing

            await publish_article_indexing(article_id)
            self.logger.info(
                "Задача на индексацию статьи отправлена в очередь: %s", article_id
            )
        except Exception as e:
            # Не прерываем публикацию из-за ошибки отправки в очередь
            self.logger.error(
                "Ошибка отправки задачи индексации в очередь %s: %s", article_id, e
            )

        # Перезагружаем с связями
        return await self.article_repository.get_by_id_with_relations(article_id)

    async def unpublish_article(self, article_id: UUID) -> KnowledgeArticleModel:
        """
        Снимает статью с публикации и очищает эмбеддинги.

        Args:
            article_id: UUID статьи

        Returns:
            KnowledgeArticleModel: Статья-черновик

        Raises:
            NotFoundError: Если статья не найдена
        """
        article = await self.get_article_by_id(article_id)
        article.unpublish()

        # Очищаем эмбеддинг статьи (чтобы не попадала в поиск)
        article.embedding = None

        await self.session.commit()

        # Удаляем чанки статьи (они больше не нужны для неопубликованной статьи)
        try:
            deleted_count = await self.chunk_repository.delete_article_chunks(article_id)
            if deleted_count > 0:
                self.logger.info(
                    "Удалено %d чанков статьи: %s", deleted_count, article_id
                )
        except Exception as e:
            self.logger.error(
                "Ошибка удаления чанков статьи %s: %s", article_id, e
            )

        self.logger.info("Снята с публикации статья: %s (id=%s)", article.title, article_id)

        # Перезагружаем с связями
        return await self.article_repository.get_by_id_with_relations(article_id)

    async def increment_article_views(self, article_id: UUID) -> None:
        """
        Увеличивает счётчик просмотров статьи.

        Args:
            article_id: UUID статьи
        """
        await self.article_repository.increment_view_count(article_id)

    async def generate_description(
        self,
        title: str,
        content: str,
    ) -> str:
        """
        Генерирует описание статьи с помощью ИИ.

        Args:
            title: Заголовок статьи
            content: Содержимое статьи

        Returns:
            Сгенерированное описание (1-2 предложения)

        Raises:
            ValidationError: Если API ключ не настроен или LLM модель не выбрана
        """
        api_key = await self._get_system_api_key()
        if not api_key:
            raise ValidationError(
                detail="API ключ OpenRouter не настроен",
                field="api_key",
            )

        llm_model = await self.system_settings_repository.get_value(
            SystemSettingsKeys.AI_LLM_MODEL,
            "",
        )
        if not llm_model:
            raise ValidationError(
                detail="LLM модель не настроена",
                field="llm_model",
            )

        client = self._get_openrouter_client(api_key)

        # Ограничиваем контент для экономии токенов
        truncated_content = content[:3000] if len(content) > 3000 else content

        prompt = f"""Напиши краткое описание для статьи базы знаний.
Описание должно быть на русском языке, 1-2 предложения, без кавычек.
Описание должно кратко передавать суть статьи и привлекать читателя.

Заголовок: {title}

Содержимое:
{truncated_content}

Описание:"""

        description = await client.complete(
            prompt=prompt,
            model=llm_model,
            max_tokens=200,
            temperature=0.7,
        )

        # Убираем лишние кавычки и пробелы
        description = description.strip().strip('"\'')

        self.logger.info("Сгенерировано описание для статьи: %s", title[:50])

        return description

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
        force: bool = False,
    ) -> dict[str, int]:
        """
        Создаёт эмбеддинги для всех опубликованных статей.

        Args:
            api_key: API ключ OpenRouter пользователя
            model: Модель для эмбеддингов
            force: Принудительная переиндексация (сброс всех эмбеддингов)

        Returns:
            dict: Статистика индексации:
                - indexed_count: количество проиндексированных статей
                - total_published: общее количество опубликованных статей
                - cleared_count: количество сброшенных эмбеддингов (при force=True)

        Example:
            >>> result = await service.index_all_articles(api_key="sk-or-...", force=True)
            >>> print(f"Проиндексировано {result['indexed_count']} статей")
        """
        result = {
            "indexed_count": 0,
            "total_published": 0,
            "cleared_count": 0,
        }

        # Если force - сбрасываем все эмбеддинги
        if force:
            cleared = await self.article_repository.clear_all_embeddings()
            result["cleared_count"] = cleared
            self.logger.info("Сброшено %d эмбеддингов статей", cleared)

            # Также сбрасываем эмбеддинги чанков
            chunks_cleared = await self.chunk_repository.clear_all_chunk_embeddings()
            self.logger.info("Сброшено %d эмбеддингов чанков", chunks_cleared)

        # Получаем все опубликованные статьи без эмбеддингов
        articles = await self.article_repository.filter_by(
            is_published=True,
            embedding__is_null=True,
        )

        # Подсчитываем общее количество опубликованных статей
        result["total_published"] = await self.article_repository.count_items(
            is_published=True
        )

        if not articles:
            self.logger.info("Все статьи уже проиндексированы")
            return result

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

        # Сохраняем эмбеддинги статей
        for article, embedding in zip(articles, embeddings, strict=True):
            await self.article_repository.update_embedding(article.id, embedding)

        result["indexed_count"] = len(articles)
        self.logger.info("Проиндексировано %d статей", len(articles))

        # Создаём и индексируем чанки для каждой статьи
        for article in articles:
            try:
                # Создаём чанки
                await self.create_article_chunks(article.id)
                # Индексируем чанки
                await self.index_article_chunks(article.id, api_key, model)
                self.logger.info("Чанки статьи %s проиндексированы", article.id)
            except Exception as e:
                self.logger.error(
                    "Ошибка при индексации чанков статьи %s: %s", article.id, e
                )

        return result

    async def semantic_search_public(
        self,
        query: str,
        pagination: "PaginationParamsSchema",
        category_ids: list[UUID] | None = None,
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """
        Публичный семантический поиск по статьям через RAG.

        Использует API ключ и модель из системных настроек.
        Для использования на фронтенде без передачи ключа.

        Args:
            query: Поисковый запрос
            pagination: Параметры пагинации
            category_ids: Фильтр по категориям

        Returns:
            Кортеж (список статей, общее количество)

        Raises:
            ValidationError: Если запрос слишком короткий или API ключ не настроен
        """
        if not query or len(query.strip()) < 2:
            raise ValidationError(
                detail="Поисковый запрос должен содержать минимум 2 символа",
                field="query",
                value=query,
            )

        # Получаем API ключ из системных настроек
        api_key = await self._get_system_api_key()
        if not api_key:
            raise ValidationError(
                detail="Семантический поиск недоступен: API ключ не настроен",
                field="api_key",
            )

        model = await self._get_embedding_model()

        # Создаём эмбеддинг запроса
        client = self._get_openrouter_client(api_key)
        query_embedding = await client.create_embedding(text=query.strip(), model=model)

        # Ищем похожие статьи
        # Берём первую категорию если передан список (для совместимости)
        category_id = category_ids[0] if category_ids else None

        articles, total = await self.article_repository.semantic_search(
            embedding=query_embedding,
            pagination=pagination,
            category_id=category_id,
        )

        self.logger.info(
            "Публичный семантический поиск '%s': найдено %d статей",
            query,
            total,
        )

        return articles, total

    async def hybrid_search_public(
        self,
        query: str,
        pagination: "PaginationParamsSchema",
        category_ids: list[UUID] | None = None,
        full_text_weight: float = 1.0,
        semantic_weight: float = 1.0,
        rrf_k: int = 60,
        similarity_threshold: float = 0.5,
    ) -> tuple[list[KnowledgeArticleModel], int, list[dict]]:
        """
        Публичный гибридный поиск по статьям (FTS + semantic с RRF).

        Комбинирует полнотекстовый и семантический поиск через
        Reciprocal Rank Fusion. Использует API ключ из системных настроек.

        Args:
            query: Поисковый запрос
            pagination: Параметры пагинации
            category_ids: Фильтр по категориям
            full_text_weight: Вес FTS в RRF (default 1.0)
            semantic_weight: Вес семантического поиска в RRF (default 1.0)
            rrf_k: Параметр RRF, влияет на сглаживание (default 60)
            similarity_threshold: Минимальный порог схожести 0-1 (default 0.5)

        Returns:
            Кортеж (список статей, общее количество, метаданные скоринга)

        Raises:
            ValidationError: Если запрос слишком короткий или API ключ не настроен
        """
        if not query or len(query.strip()) < 2:
            raise ValidationError(
                detail="Поисковый запрос должен содержать минимум 2 символа",
                field="query",
                value=query,
            )

        # Получаем API ключ из системных настроек
        api_key = await self._get_system_api_key()
        if not api_key:
            # Fallback: если API ключ не настроен, используем только FTS
            self.logger.warning(
                "API ключ не настроен, гибридный поиск использует только FTS"
            )
            articles, total = await self.search_articles(
                query=query,
                pagination=pagination,
                category_ids=category_ids,
            )
            return articles, total, []

        model = await self._get_embedding_model()

        # Создаём эмбеддинг запроса
        client = self._get_openrouter_client(api_key)
        query_embedding = await client.create_embedding(text=query.strip(), model=model)

        # Берём первую категорию если передан список (для совместимости)
        category_id = category_ids[0] if category_ids else None

        # Выполняем гибридный поиск
        articles, total, scoring_metadata = await self.article_repository.hybrid_search(
            query=query.strip(),
            embedding=query_embedding,
            pagination=pagination,
            category_id=category_id,
            full_text_weight=full_text_weight,
            semantic_weight=semantic_weight,
            rrf_k=rrf_k,
            similarity_threshold=similarity_threshold,
        )

        self.logger.info(
            "Гибридный поиск '%s': найдено %d статей (FTS weight=%.1f, semantic weight=%.1f)",
            query,
            total,
            full_text_weight,
            semantic_weight,
        )

        return articles, total, scoring_metadata

    async def semantic_search(
        self,
        query: str,
        api_key: str,
        pagination: "PaginationParamsSchema",
        category_id: UUID | None = None,
        model: str = "openai/text-embedding-3-small",
    ) -> tuple[list[KnowledgeArticleModel], int]:
        """
        Семантический поиск по статьям через RAG (с явным API ключом).

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
            Список словарей с катег��риями и articles_count
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

    async def get_all_tags_with_counts(self) -> list[dict[str, Any]]:
        """
        Получает все теги с количеством статей.

        Returns:
            Список словарей с тегами и articles_count
        """
        return await self.tag_repository.get_all_with_counts()

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

    # ==================== ЧАНКИНГ СТАТЕЙ ====================

    async def create_article_chunks(
        self,
        article_id: UUID,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> list[KnowledgeArticleChunkModel]:
        """
        Разбивает статью на чанки и сохраняет в БД.

        Args:
            article_id: UUID статьи
            chunk_size: Размер чанка в токенах
            chunk_overlap: Перекрытие чанков в токенах

        Returns:
            Список созданных чанков
        """
        article = await self.get_article_by_id(article_id)

        # Удаляем старые чанки
        await self.chunk_repository.delete_article_chunks(article_id)

        # Разбиваем статью на чанки
        text_chunks = chunk_article(
            content=article.content,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        if not text_chunks:
            self.logger.warning("Статья %s не содержит контента для чанкинга", article_id)
            return []

        # Создаём записи в БД
        chunks: list[KnowledgeArticleChunkModel] = []
        for text_chunk in text_chunks:
            chunk = await self.chunk_repository.create_item({
                "article_id": article_id,
                "chunk_index": text_chunk.index,
                "title": text_chunk.title,
                "content": text_chunk.content,
                "token_count": text_chunk.token_count,
            })
            chunks.append(chunk)

        await self.session.commit()

        self.logger.info(
            "Создано %d чанков для статьи: %s",
            len(chunks),
            article.title,
        )

        return chunks

    async def index_article_chunks(
        self,
        article_id: UUID,
        api_key: str,
        model: str = "openai/text-embedding-3-small",
    ) -> int:
        """
        Создаёт эмбеддинги для всех чанков статьи.

        Args:
            article_id: UUID статьи
            api_key: API ключ OpenRouter
            model: Модель для эмбеддингов

        Returns:
            Количество проиндексированных чанков
        """
        chunks = await self.chunk_repository.get_article_chunks(article_id)

        if not chunks:
            self.logger.warning("Статья %s не имеет чанков для индексации", article_id)
            return 0

        # Собираем тексты для batch обработки
        texts = []
        for chunk in chunks:
            # Добавляем заголовок секции к контенту для лучшего контекста
            if chunk.title:
                texts.append(f"{chunk.title}\n\n{chunk.content}")
            else:
                texts.append(chunk.content)

        # Создаём эмбеддинги
        client = self._get_openrouter_client(api_key)
        embeddings = await client.create_embeddings_batch(texts=texts, model=model)

        # Сохраняем эмбеддинги
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            await self.chunk_repository.update_chunk_embedding(chunk.id, embedding)

        await self.session.commit()

        self.logger.info(
            "Проиндексировано %d чанков для статьи %s",
            len(chunks),
            article_id,
        )

        return len(chunks)

    async def semantic_search_chunks(
        self,
        query: str,
        limit: int = 10,
        category_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Семантический поиск по чанкам статей.

        Возвращает наиболее релевантные фрагменты статей.

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            category_id: Фильтр по категории

        Returns:
            Список словарей с чанками и информацией о статьях
        """
        if not query or len(query.strip()) < 2:
            raise ValidationError(
                detail="Поисковый запрос должен содержать минимум 2 символа",
                field="query",
            )

        api_key = await self._get_system_api_key()
        if not api_key:
            raise ValidationError(
                detail="Семантический поиск недоступен: API ключ не настроен",
                field="api_key",
            )

        model = await self._get_embedding_model()

        # Создаём эмбеддинг запроса
        client = self._get_openrouter_client(api_key)
        query_embedding = await client.create_embedding(text=query.strip(), model=model)

        # Ищем похожие чанки
        results = await self.chunk_repository.semantic_search_chunks(
            embedding=query_embedding,
            limit=limit,
            category_id=category_id,
        )

        self.logger.info(
            "Семантический поиск по чанкам '%s': найдено %d результатов",
            query,
            len(results),
        )

        return results

    # ==================== RAG ЧАТ ====================

    async def extract_search_query(
        self,
        messages: list[dict[str, str]],
        api_key: str,
        llm_model: str,
    ) -> str | None:
        """
        Извлекает оптимальный поисковый запрос из истории диалога с помощью LLM.

        LLM анализирует диалог и формирует запрос для семантического поиска,
        учитывая контекст предыдущих сообщений и уточняющие вопросы.

        Args:
            messages: История сообщений [{role: 'user'|'assistant', content: '...'}]
            api_key: API ключ OpenRouter
            llm_model: Модель LLM для анализа

        Returns:
            Оптимальный поисковый запрос или None если поиск не нужен
        """
        if not messages:
            return None

        # Берём только последние сообщения для экономии токенов
        recent_messages = messages[-6:]

        # Формируем историю для промпта
        history = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in recent_messages
        )

        prompt = f"""Проанализируй историю диалога и определи, нужен ли поиск по базе знаний.

ИСТОРИЯ ДИАЛОГА:
{history}

ЗАДАЧА:
1. Если последнее сообщение пользователя - приветствие или общая фраза (привет, как дела, спасибо) - ответь: NONE
2. Если пользователь задаёт уточняющий вопрос (дальше, ещё, продолжи, подробнее) - сформируй запрос на основе предыдущего контекста диалога
3. Если пользователь задаёт новый вопрос - извлеки ключевые слова для поиска

ВАЖНО: Верни ТОЛЬКО поисковый запрос (3-10 слов) или слово NONE. Без объяснений.

ОТВЕТ:"""

        client = self._get_openrouter_client(api_key)

        try:
            response = await client.complete(
                prompt=prompt,
                model=llm_model,
                max_tokens=50,
                temperature=0.1,
            )

            result = response.strip()

            if result.upper() == "NONE" or len(result) < 3:
                return None

            self.logger.debug("LLM извлёк поисковый запрос: %s", result)
            return result

        except Exception as e:
            self.logger.warning("Ошибка извлечения запроса через LLM: %s", e)
            # Fallback: используем последнее сообщение пользователя
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    return msg.get("content", "")[:200]
            return None

    async def chat(
        self,
        messages: list[dict[str, str]],
        use_context: bool = True,
    ) -> dict[str, Any]:
        """
        RAG-чат с контекстом из базы знаний.

        Анализирует диалог, извлекает поисковый запрос через LLM,
        ищет релевантные чанки и генерирует ответ.

        Поддерживает:
        - Динамическую подгрузку контекста (LLM может запросить больше информации)
        - Уточняющие вопросы (AI предлагает варианты для уточнения)

        Args:
            messages: История сообщений [{role: 'user'|'assistant', content: '...'}]
            use_context: Использовать контекст из базы знаний

        Returns:
            Словарь с ответом, источниками, моделью и метаданными

        Raises:
            ValidationError: Если API ключ не настроен или нет сообщений
        """
        if not messages:
            raise ValidationError(
                detail="Сообщения не указаны",
                field="messages",
            )

        # Получаем API ключ и модель
        api_key = await self._get_system_api_key()
        if not api_key:
            raise ValidationError(
                detail="API ключ не настроен. Обратитесь к администратору.",
                field="api_key",
            )

        llm_model = await self.system_settings_repository.get_value(
            SystemSettingsKeys.AI_LLM_MODEL,
            "anthropic/claude-3-haiku",
        )

        sources: list[dict[str, Any]] = []
        context_text = ""
        additional_context_loaded = False
        needs_clarification = False
        clarification_options: list[str] = []

        # Извлекаем поисковый запрос через LLM
        if use_context:
            search_query = await self.extract_search_query(messages, api_key, llm_model)

            if search_query:
                self.logger.info("Поисковый запрос: %s", search_query)

                try:
                    # Поиск по чанкам
                    chunks = await self.semantic_search_chunks(
                        query=search_query,
                        limit=10,
                    )

                    if chunks:
                        # Группируем чанки по статьям
                        context_parts = []
                        seen_articles: dict[str, int] = {}

                        for chunk in chunks:
                            article_id = str(chunk["article_id"])

                            if article_id not in seen_articles:
                                idx = len(seen_articles) + 1
                                seen_articles[article_id] = idx
                                sources.append({
                                    "id": article_id,
                                    "title": chunk["article_title"],
                                    "slug": chunk["article_slug"],
                                })

                            idx = seen_articles[article_id]
                            chunk_title = (
                                chunk.get("chunk_title") or chunk["article_title"]
                            )
                            context_parts.append(
                                f"[Статья {idx}] ### {chunk_title}\n{chunk['content']}"
                            )

                        context_text = "\n\n---\n\n".join(context_parts)
                        self.logger.info(
                            "Найдено %d чанков из %d статей",
                            len(chunks),
                            len(seen_articles),
                        )

                except Exception as e:
                    self.logger.warning("Семантический поиск недоступен: %s", e)

        # Формируем системный промпт
        system_prompt = self._build_chat_system_prompt(context_text, sources)

        # Формируем сообщения для LLM
        llm_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages[-10:]:
            llm_messages.append({"role": msg["role"], "content": msg["content"]})

        # Генерируем ответ
        client = self._get_openrouter_client(api_key)
        response = await client.chat(
            messages=llm_messages,
            model=llm_model,
            temperature=0.7,
            max_tokens=4000,
        )

        # Парсим ответ на наличие запросов доп. контекста и уточнений
        parsed = self._parse_chat_response_extended(response.content, sources)
        content = parsed["content"]
        used_sources = parsed["sources"]

        # Проверяем, нужен ли дополнительный контекст
        if parsed.get("needs_more_context") and use_context:
            additional_query = parsed.get("additional_query", "")
            if additional_query:
                self.logger.info(
                    "LLM запросил дополнительный контекст: %s", additional_query
                )
                try:
                    # Загружаем дополнительные чанки
                    extra_chunks = await self.semantic_search_chunks(
                        query=additional_query,
                        limit=5,
                    )

                    if extra_chunks:
                        additional_context_loaded = True

                        # Добавляем новые источники
                        extra_context_parts = []
                        for chunk in extra_chunks:
                            article_id = str(chunk["article_id"])

                            if article_id not in {str(s["id"]) for s in sources}:
                                sources.append({
                                    "id": article_id,
                                    "title": chunk["article_title"],
                                    "slug": chunk["article_slug"],
                                })

                            chunk_title = (
                                chunk.get("chunk_title") or chunk["article_title"]
                            )
                            extra_context_parts.append(
                                f"### {chunk_title}\n{chunk['content']}"
                            )

                        # Генерируем дополненный ответ
                        extra_context = "\n\n---\n\n".join(extra_context_parts)
                        llm_messages.append({
                            "role": "assistant",
                            "content": content,
                        })
                        llm_messages.append({
                            "role": "user",
                            "content": (
                                f"Вот дополнительная информация:\n\n{extra_context}\n\n"
                                "Пожалуйста, дополни свой ответ используя эту информацию."
                            ),
                        })

                        response = await client.chat(
                            messages=llm_messages,
                            model=llm_model,
                            temperature=0.7,
                            max_tokens=4000,
                        )

                        parsed = self._parse_chat_response_extended(
                            response.content, sources
                        )
                        content = parsed["content"]
                        used_sources = parsed["sources"]

                        self.logger.info("Ответ дополнен с учётом нового контекста")

                except Exception as e:
                    self.logger.warning("Ошибка загрузки доп. контекста: %s", e)

        # Проверяем, нужно ли уточнение от пользователя
        if parsed.get("needs_clarification"):
            needs_clarification = True
            clarification_options = parsed.get("clarification_options", [])
            self.logger.info(
                "LLM запросил уточнение. Варианты: %s", clarification_options
            )

        return {
            "content": content,
            "sources": used_sources,
            "model": response.model,
            "needs_clarification": needs_clarification,
            "clarification_options": clarification_options,
            "additional_context_loaded": additional_context_loaded,
        }

    def _build_chat_system_prompt(
        self,
        context_text: str,
        sources: list[dict[str, Any]],
    ) -> str:
        """Формирует системный промпт для чата."""
        prompt = """Ты — AI-ассистент базы знаний. Твоя задача — помогать пользователям находить информацию и отвечать на вопросы.

Правила:
1. Отвечай на русском языке
2. Используй информацию из предоставленного контекста для ответов
3. Если в контексте есть только частичная информация — дай ответ на основе того что есть
4. Если в контексте нет релевантной информации — честно скажи об этом
5. Давай развёрнутые, полные ответы. Не обрывай мысль на середине
6. Если пользователь приветствует тебя, поприветствуй в ответ и предложи помощь
7. ВАЖНО: Всегда завершай свои ответы полностью"""

        if context_text:
            prompt += f"""

## Контекст из базы знаний:

{context_text}

---

ПРАВИЛА ИСПОЛЬЗОВАНИЯ МАРКЕРОВ:

1. ИСТОЧНИКИ - в САМОМ КОНЦЕ ответа добавь: [USED: 1, 2] с номерами использованных статей
   - НЕ указывай для приветствий или общих фраз
   - Если не использовал статьи — НЕ добавляй [USED:]

2. ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ - если тебе не хватает контекста для полного ответа:
   - Добавь в конце: [NEED_MORE: поисковый запрос для получения доп. информации]
   - Пример: [NEED_MORE: настройка Docker volumes]
   - Используй ТОЛЬКО когда действительно нужна конкретная информация

3. УТОЧНЯЮЩИЕ ВОПРОСЫ - если вопрос пользователя неоднозначен:
   - Добавь в конце маркер: [CLARIFY: первый вариант | второй вариант | третий вариант]
   - ВАЖНО: Пиши КОНКРЕТНЫЕ варианты, НЕ "вариант1", "вариант2"!
   - Пример для вопроса "как установить Docker": [CLARIFY: Docker на Windows | Docker на Linux | Docker на macOS]
   - Пример для вопроса "расскажи о базе данных": [CLARIFY: PostgreSQL | MySQL | MongoDB]
   - Предлагай 2-4 осмысленных варианта для уточнения"""
        else:
            prompt += """

ОСОБЫЕ ВОЗМОЖНОСТИ:

1. Если вопрос пользователя неоднозначен и требует уточнения:
   - Добавь в конце маркер: [CLARIFY: первый вариант | второй вариант | третий вариант]
   - ВАЖНО: Пиши КОНКРЕТНЫЕ варианты, НЕ "вариант1", "вариант2"!
   - Пример: [CLARIFY: Настройка аккаунта | Техническая проблема | Вопрос по функционалу]

2. Если тебе нужна дополнительная информация из базы знаний:
   - Добавь в конце: [NEED_MORE: поисковый запрос]"""

        return prompt

    def _parse_chat_response(
        self,
        content: str,
        sources: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Парсит ответ LLM и извлекает использованные источники."""
        import re

        used_sources: list[dict[str, Any]] = []

        # Ищем маркер [USED: ...]
        used_match = re.search(r"\[USED:\s*([^\]]+)\]", content, re.IGNORECASE)
        if used_match:
            used_str = used_match.group(1).strip()
            content = re.sub(r"\s*\[USED:\s*[^\]]+\]\s*", "", content).strip()

            # Парсим номера источников
            source_nums = [
                int(n.strip())
                for n in used_str.split(",")
                if n.strip().isdigit()
            ]
            for num in source_nums:
                if 1 <= num <= len(sources):
                    used_sources.append(sources[num - 1])

        # Убираем старый маркер [SOURCES:]
        content = re.sub(r"\s*\[SOURCES:\s*[^\]]*\]\s*", "", content).strip()

        return content, used_sources

    def _parse_chat_response_extended(
        self,
        content: str,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Парсит ответ LLM с поддержкой расширенных маркеров.

        Поддерживаемые маркеры:
        - [USED: 1, 2] - использованные источники
        - [NEED_MORE: запрос] - запрос дополнительного контекста
        - [CLARIFY: вариант1 | вариант2 | вариант3] - уточняющие вопросы

        Args:
            content: Текст ответа LLM
            sources: Список доступных источников

        Returns:
            Словарь с разобранными данными
        """
        import re

        result: dict[str, Any] = {
            "content": content,
            "sources": [],
            "needs_more_context": False,
            "additional_query": "",
            "needs_clarification": False,
            "clarification_options": [],
        }

        # Парсим [USED: ...]
        used_match = re.search(r"\[USED:\s*([^\]]+)\]", content, re.IGNORECASE)
        if used_match:
            used_str = used_match.group(1).strip()
            content = re.sub(r"\s*\[USED:\s*[^\]]+\]\s*", "", content).strip()

            source_nums = [
                int(n.strip())
                for n in used_str.split(",")
                if n.strip().isdigit()
            ]
            for num in source_nums:
                if 1 <= num <= len(sources):
                    result["sources"].append(sources[num - 1])

        # Парсим [NEED_MORE: запрос]
        need_more_match = re.search(
            r"\[NEED_MORE:\s*([^\]]+)\]", content, re.IGNORECASE
        )
        if need_more_match:
            result["needs_more_context"] = True
            result["additional_query"] = need_more_match.group(1).strip()
            content = re.sub(
                r"\s*\[NEED_MORE:\s*[^\]]+\]\s*", "", content
            ).strip()

        # Парсим [CLARIFY: вариант1 | вариант2 | вариант3]
        clarify_match = re.search(
            r"\[CLARIFY:\s*([^\]]+)\]", content, re.IGNORECASE
        )
        if clarify_match:
            result["needs_clarification"] = True
            options_str = clarify_match.group(1).strip()
            result["clarification_options"] = [
                opt.strip()
                for opt in options_str.split("|")
                if opt.strip()
            ]
            content = re.sub(r"\s*\[CLARIFY:\s*[^\]]+\]\s*", "", content).strip()

        # Убираем старый маркер [SOURCES:]
        content = re.sub(r"\s*\[SOURCES:\s*[^\]]*\]\s*", "", content).strip()

        result["content"] = content
        return result

    # ==================== СТАТИСТИКА ИНДЕКСАЦИИ ====================

    async def get_indexation_stats(self) -> dict[str, Any]:
        """
        Получает детальную статистику индексации для визуализации.

        Возвращает информацию о каждой опубликованной статье:
        - наличие эмбеддинга статьи
        - количество чанков и их индексация

        Returns:
            dict: Статистика индексации
        """
        # Получаем все опубликованные статьи
        articles = await self.article_repository.filter_by(is_published=True)

        # Подсчёт общей статистики
        articles_indexed = 0
        articles_not_indexed = 0
        total_chunks = await self.chunk_repository.count_all_chunks()
        chunks_indexed = await self.chunk_repository.count_chunks_with_embeddings()

        # Детальная информация по каждой статье
        articles_stats = []
        for article in articles:
            has_embedding = article.embedding is not None
            if has_embedding:
                articles_indexed += 1
            else:
                articles_not_indexed += 1

            # Получаем статистику чанков для статьи
            chunk_stats = await self.chunk_repository.get_chunks_stats_by_article(
                article.id
            )

            articles_stats.append({
                "id": str(article.id),
                "title": article.title,
                "slug": article.slug,
                "has_embedding": has_embedding,
                "has_chunks": chunk_stats["total"] > 0,
                "chunks_count": chunk_stats["total"],
                "chunks_indexed": chunk_stats["indexed"],
            })

        return {
            "total_published": len(articles),
            "articles_indexed": articles_indexed,
            "articles_not_indexed": articles_not_indexed,
            "total_chunks": total_chunks,
            "chunks_indexed": chunks_indexed,
            "articles": articles_stats,
        }
