"""
Модуль инициализации и завершения работы с RabbitMQ для FastAPI-приложения.

Назначение:
- Автоматически инициализирует подключение к RabbitMQ при запуске приложения.
- Корректно закрывает подключения к RabbitMQ при завершении работы приложения.
- Сохраняет экземпляр клиента в app.state для централизованного доступа из любого места приложения.

Используемые механизмы:
- Декораторы register_startup_handler и register_shutdown_handler регистрируют функции для событий старта и остановки FastAPI.
- Подключение к RabbitMQ создается один раз на старте и закрывается при завершении, что предотвращает утечки ресурсов.

Экспортируемые функции:
- initialize_messaging: Инициализация RabbitMQ при старте приложения.
- close_messaging_connection: Корректное закрытие подключения при остановке приложения.
"""

import logging

from fastapi import FastAPI

from app.core.connections.messaging import RabbitMQClient
from app.core.lifespan.base import register_shutdown_handler, register_startup_handler

logger = logging.getLogger(__name__)


@register_startup_handler
async def initialize_messaging(app: FastAPI):
    """
    Инициализация RabbitMQ при старте приложения.

    Подключает RabbitMQ, сохраняет клиент в app.state для дальнейшего использования.
    """
    logger.info("✨ Начало инициализации RabbitMQ...")
    # Mark messaging as not ready until fully initialized
    app.state.messaging_ready = False
    try:
        client = RabbitMQClient()
        await client.connect()
        app.state.rabbitmq_client = client
        # Ensure exchange and queue are declared early so publishers won't publish to missing
        # destinations before the consumer binds. This reduces race conditions on first publish.
        # Try to call declare_exchange if the client exposes it
        if hasattr(client, "declare_exchange"):
            try:
                logger.info(
                    "🔁 Декларация exchange и queue для готовности messaging..."
                )
                # pylint: disable=no-member
                await client.declare_exchange(app.state, name=None)  # type: ignore[attr-defined]
            except Exception:
                logger.debug(
                    "ℹ️ declare_exchange helper failed; skipping explicit declare"
                )
        else:
            logger.debug(
                "ℹ️ RabbitMQClient has no declare_exchange helper; skipping explicit declare"
            )

        # Mark messaging as ready. Handlers / endpoints can check this flag.
        app.state.messaging_ready = True
        logger.info("✅ RabbitMQ успешно инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации RabbitMQ: {e}")
        raise


@register_shutdown_handler
async def close_messaging_connection(app: FastAPI):
    """
    Закрытие подключения к RabbitMQ при остановке приложения.

    Безопасно закрывает подключение к RabbitMQ, если оно было инициализировано.
    """
    logger.info("🔄 Закрытие подключения к RabbitMQ...")
    if hasattr(app.state, "rabbitmq_client"):
        try:
            await app.state.rabbitmq_client.close()
            logger.info("✅ Подключение к RabbitMQ закрыто")
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии RabbitMQ: {e}")
    else:
        logger.info("ℹ️ RabbitMQ клиент не был инициализирован")
