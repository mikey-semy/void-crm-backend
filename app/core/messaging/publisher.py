"""
Паблишер для задач индексации статей через RabbitMQ.

Использует aio_pika для публикации сообщений в очередь.
"""

import json
import logging
from uuid import UUID

import aio_pika

from app.core.settings import settings

logger = logging.getLogger(__name__)

# Константы для очереди
QUEUE_NAME = "knowledge_article_indexing"


class KnowledgePublisher:
    """
    Централизованный паблишер задач базы знаний.

    Публикует задачи на индексацию статей для RAG в очередь RabbitMQ.
    """

    async def publish_indexing_task(self, article_id: UUID) -> bool:
        """
        Публикует задачу на индексацию статьи.

        Args:
            article_id: UUID статьи для индексации

        Returns:
            bool: True если задача успешно опубликована
        """
        payload = {
            "article_id": str(article_id),
        }

        connection = None
        try:
            # Подключаемся к RabbitMQ
            connection = await aio_pika.connect_robust(
                settings.rabbitmq_url,
                timeout=settings.RABBITMQ_CONNECTION_TIMEOUT,
            )

            channel = await connection.channel()

            # Декларируем exchange
            exchange = await channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )

            # Декларируем очередь и биндим
            queue = await channel.declare_queue(
                QUEUE_NAME,
                durable=True,
            )
            await queue.bind(exchange, routing_key=QUEUE_NAME)

            # Публикуем сообщение
            message = aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )
            await exchange.publish(message, routing_key=QUEUE_NAME)

            logger.info(
                "📤 Задача на индексацию статьи опубликована: %s",
                article_id,
            )
            return True

        except Exception as exc:
            logger.error(
                "❌ Не удалось опубликовать задачу индексации: %s",
                exc,
                exc_info=True,
            )
            return False

        finally:
            if connection:
                await connection.close()


# Глобальный экземпляр паблишера
knowledge_publisher = KnowledgePublisher()


async def publish_article_indexing(article_id: UUID) -> bool:
    """
    Функция-обёртка для публикации задачи индексации.

    Args:
        article_id: UUID статьи для индексации

    Returns:
        bool: True если задача успешно опубликована
    """
    return await knowledge_publisher.publish_indexing_task(article_id)
