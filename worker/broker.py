"""
Конфигурация брокера RabbitMQ для воркера.

Определяет:
- Брокер и роутер FastStream
- Exchange и очереди
"""

import aio_pika
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue, RabbitRouter

from app.core.settings import settings

# Создаём брокер
broker = RabbitBroker(settings.rabbitmq_url)

# Создаём роутер для обработчиков
router = RabbitRouter()

# Exchange для всех очередей CRM
exchange = RabbitExchange(
    name=settings.RABBITMQ_EXCHANGE,
    type=aio_pika.ExchangeType.DIRECT,
    durable=True,
)

# ==================== Очереди ====================

# Очередь индексации статей базы знаний
article_indexing_queue = RabbitQueue(
    name="knowledge_article_indexing",
    durable=True,
    routing_key="knowledge_article_indexing",
)

# Будущие очереди:
# email_queue = RabbitQueue(name="email_notifications", durable=True, routing_key="email_notifications")
# sms_queue = RabbitQueue(name="sms_notifications", durable=True, routing_key="sms_notifications")
# push_queue = RabbitQueue(name="push_notifications", durable=True, routing_key="push_notifications")
