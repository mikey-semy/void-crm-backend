"""
Обработчики очередей для базы знаний.

Содержит:
- Индексация статей для RAG (создание эмбеддингов)
"""

import logging
from typing import Any
from uuid import UUID

from worker.broker import article_indexing_queue, exchange, router

logger = logging.getLogger(__name__)


async def process_indexing_task(article_id: UUID) -> None:
    """
    Обрабатывает задачу индексации статьи.

    Выполняет полную индексацию:
    1. Создаёт эмбеддинг для всей статьи (для поиска похожих)
    2. Разбивает статью на чанки и создаёт эмбеддинги для каждого (для RAG)

    Args:
        article_id: UUID статьи для индексации
    """
    # Импортируем здесь чтобы избежать circular imports
    from app.core.connections.database import async_session_factory
    from app.services.v1.knowledge import KnowledgeService

    logger.info("📚 Начало индексации статьи: %s", article_id)

    async with async_session_factory() as session:
        service = KnowledgeService(session)

        # Получаем API ключ и модель из системных настроек
        api_key = await service._get_system_api_key()
        if not api_key:
            logger.warning(
                "⚠️ API ключ не настроен - статья не проиндексирована: %s",
                article_id,
            )
            return

        model = await service._get_embedding_model()

        # 1. Индексируем статью целиком (для поиска похожих статей)
        await service.index_article(article_id, api_key, model)
        logger.info("✅ Эмбеддинг статьи создан: %s", article_id)

        # 2. Создаём чанки и индексируем их (для RAG поиска)
        try:
            await service.create_article_chunks(article_id)
            logger.info("✅ Чанки статьи созданы: %s", article_id)

            await service.index_article_chunks(article_id, api_key, model)
            logger.info("✅ Эмбеддинги чанков созданы: %s", article_id)
        except Exception as e:
            logger.error("❌ Ошибка при чанкинге статьи %s: %s", article_id, e)
            # Не прерываем - статья уже проиндексирована целиком

        logger.info("✅ Статья полностью проиндексирована: %s", article_id)


@router.subscriber(article_indexing_queue, exchange=exchange)
async def handle_article_indexing(message: dict[str, Any]) -> None:
    """
    Обработчик очереди индексации статей.

    Args:
        message: Сообщение с данными:
            - article_id: UUID статьи для индексации
    """
    try:
        article_id = UUID(message["article_id"])
        await process_indexing_task(article_id)
    except Exception:
        logger.exception("❌ Ошибка при индексации статьи")
        raise
