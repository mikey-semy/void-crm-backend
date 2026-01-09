"""
Модуль системы обмена сообщениями.

Предоставляет:
- publisher: Публикация сообщений в очереди RabbitMQ
"""

from app.core.messaging.publisher import knowledge_publisher, publish_article_indexing

__all__ = [
    "knowledge_publisher",
    "publish_article_indexing",
]
