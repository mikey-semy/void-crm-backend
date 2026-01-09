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

        # Индексируем статью
        await service.index_article(article_id, api_key, model)
        logger.info("✅ Статья успешно проиндексирована: %s", article_id)


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
